"""Run the ScanCycle suite against models on OpenRouter and grade every answer.

Usage:
    python run_eval.py --models MODEL [MODEL ...] --trials 3 --seeds 1 2
    python run_eval.py --dry-run          # print one prompt, no API call

Models named gemini:<id> use GEMINI_API_KEY (Google AI Studio, free tier works),
groq:<id> use GROQ_API_KEY (free tier);
all others use OPENROUTER_API_KEY (free models end in ":free"). Keys come from the
environment or a .env file and are never printed or saved.
Every raw answer is saved, so the report can be rebuilt without new calls."""
import argparse
import http.client
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from scancycle.families import build_suite
from scancycle.grader import grade
from scancycle.prompt import render

OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
GROQ = "https://api.groq.com/openai/v1/chat/completions"
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
MAX_TOKENS = 32768  # reasoning models spend thousands of tokens before the answer


def harness_failure(r: dict) -> bool:
    """True when the answer was cut off by an output limit in an older run, which
    says nothing about the model's reasoning. Such answers are re-asked and never scored."""
    return bool(r.get("error")) or (bool(r.get("parse_error")) and (r.get("completion_tokens") or 0) >= 1500)


def load_key(name: str) -> str:
    key = os.environ.get(name, "")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        raise SystemExit(f"{name} is missing (set it in .env)")
    return key


def _post(url: str, body: dict, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(20 * (attempt + 1))
                continue
            return {"error": f"HTTP {exc.code}: {exc.read()[:300].decode(errors='replace')}"}
        except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            if attempt < 3:
                time.sleep(10)
                continue
            return {"error": str(exc)}
    return {"error": "gave up after retries"}


def call(model: str, prompt: str, timeout: int = 300) -> tuple[str, dict, str]:
    """Return (answer text, usage, error). 'gemini:<id>' goes to Google AI Studio,
    'groq:<id>' to Groq, anything else to OpenRouter."""
    if model.startswith("gemini:"):
        resp = _post(GEMINI.format(model=model.split(":", 1)[1]),
                     {"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"maxOutputTokens": MAX_TOKENS}},
                     {"x-goog-api-key": load_key("GEMINI_API_KEY")}, timeout)
        if "error" in resp:
            return "", {}, str(resp["error"])
        cand = (resp.get("candidates") or [{}])[0]
        if cand.get("finishReason") == "MAX_TOKENS":
            return "", {}, f"truncated at {MAX_TOKENS} output tokens"
        parts = cand.get("content", {}).get("parts", [])
        meta = resp.get("usageMetadata", {})
        usage = {"prompt_tokens": meta.get("promptTokenCount"),
                 "completion_tokens": meta.get("candidatesTokenCount"), "cost": 0}
        return "".join(p.get("text", "") for p in parts), usage, ""
    if model.startswith("groq:"):
        # Free Groq tiers cap output tokens per minute per model. Ask for the most the
        # tier allows: start high, and if the request is refused as too large, retry at
        # the limit Groq reports.
        limit = MAX_TOKENS
        for _ in range(3):
            resp = _post(GROQ, {"model": model.split(":", 1)[1],
                                "messages": [{"role": "user", "content": prompt}],
                                "max_completion_tokens": limit},
                         {"Authorization": f"Bearer {load_key('GROQ_API_KEY')}",
                          "User-Agent": "scancycle-eval"}, timeout)
            m = re.search(r"Request too large.*?Limit (\d+)", str(resp.get("error", "")))
            if not m:
                break
            limit = int(m.group(1)) - 20
            time.sleep(61)  # let the per-minute window reset
    else:
        resp = _post(OPENROUTER,
                     {"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": MAX_TOKENS, "usage": {"include": True}},
                     {"Authorization": f"Bearer {load_key('OPENROUTER_API_KEY')}",
                      "X-Title": "ScanCycle Eval"}, timeout)
    if "error" in resp:
        return "", {}, str(resp["error"])
    choice = resp["choices"][0]
    if choice.get("finish_reason") == "length":
        return "", {}, f"truncated at {MAX_TOKENS} output tokens"
    return choice["message"].get("content") or "", resp.get("usage") or {}, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=[])
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--pause", type=float, default=0, help="seconds between calls, for free-tier rate limits")
    ap.add_argument("--seeds", nargs="+", type=int, default=[1])
    ap.add_argument("--max-cost", type=float, default=5.0, help="stop when reported spend passes this (USD)")
    ap.add_argument("--workers", type=int, default=4, help="parallel calls")
    ap.add_argument("--hard", action="store_true", help="longer tasks (16-24 cycles, several events)")
    ap.add_argument("--list-models", action="store_true", help="save the model IDs your keys can use to results/models.txt")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.list_models:
        RESULTS.mkdir(exist_ok=True)
        lines = []
        for name, url, hdr in [
            ("groq", "https://api.groq.com/openai/v1/models",
             lambda: {"Authorization": f"Bearer {load_key('GROQ_API_KEY')}", "User-Agent": "scancycle-eval"}),
            ("gemini", "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
             lambda: {"x-goog-api-key": load_key("GEMINI_API_KEY")}),
        ]:
            try:
                req = urllib.request.Request(url, headers=hdr())
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                ids = [m.get("id") or m.get("name", "").removeprefix("models/") for m in data.get("data", data.get("models", []))]
                lines += [f"{name}:{i}" for i in sorted(ids)]
            except (Exception, SystemExit) as exc:
                lines.append(f"{name}: could not list ({exc})")
        (RESULTS / "models.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
        return

    suite = build_suite(seeds=tuple(args.seeds), hard=args.hard)
    if args.dry_run:
        print(render(suite[0]))
        print(f"\n{len(suite)} tasks would be sent, {args.trials} trials each.")
        return

    if not args.models:
        raise SystemExit("give at least one model: --models <model-id>")
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "runs.jsonl"

    # resume: an answer that already came back (no API error) is never asked again
    done = set()
    for f in RESULTS.glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if not harness_failure(r):
                    done.add((r["model"], r["task_id"], r["trial"]))

    jobs = [(m, t, k) for m in args.models for t in suite for k in range(1, args.trials + 1)
            if (m, t.task_id, k) not in done]
    print(f"{len(done)} answers already saved, {len(jobs)} to go, {args.workers} at a time")
    lock = threading.Lock()
    state = {"spent": 0.0}

    def work(job):
        model, task, trial = job
        if state["spent"] > args.max_cost:
            return
        t0 = time.time()
        try:
            text, usage, error = call(model, render(task))
        except Exception as exc:  # never let one bad call stop the whole run
            text, usage, error = "", {}, f"{type(exc).__name__}: {exc}"
        g = grade(task, text) if text else None
        rec = {
            "model": model, "task_id": task.task_id, "family": task.family,
            "trial": trial, "seconds": round(time.time() - t0, 1),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "cost": usage.get("cost"),
            "error": error,
            "passed": bool(g and g.passed),
            "cell_score": g.cell_score if g else 0.0,
            "parse_error": g.parse_error if g else "no answer",
            "wrong": g.wrong[:10] if g else [],
            "answer": text,
        }
        mark = "PASS" if rec["passed"] else f"{rec['cell_score']:.2f}"
        if error:
            mark = "API ERROR " + error[:120]
        with lock:
            state["spent"] += float(usage.get("cost") or 0)
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")
            print(f"{model:32} {task.task_id:20} t{trial} {mark}  {rec['seconds']}s", flush=True)
        time.sleep(args.pause)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, jobs))
    print(f"\nsaved to {out}. Run it again to retry any API errors.")


if __name__ == "__main__":
    main()
