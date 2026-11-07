"""Build results/report.md from saved run files. No API calls.

Usage: python report.py results/run_*.jsonl"""
import json
import sys
from collections import defaultdict
from pathlib import Path


def main(paths):
    recs = [json.loads(l) for p in paths for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
    def harness_failure(r):  # same rule as run_eval.harness_failure
        return bool(r.get("error")) or (bool(r.get("parse_error")) and (r.get("completion_tokens") or 0) >= 1500)

    errors = [r for r in recs if harness_failure(r)]
    latest = {}
    for r in recs:  # API failures are not model answers; a repeated trial keeps its last answer
        if not harness_failure(r):
            latest[(r["model"], r["task_id"], r["trial"])] = r
    recs = list(latest.values())
    if not recs:
        raise SystemExit("no graded answers (all calls failed?)")
    models = sorted({r["model"] for r in recs})
    families = sorted({r["family"] for r in recs})

    by = defaultdict(list)
    for r in recs:
        by[(r["model"], r["task_id"])].append(r)

    lines = ["# ScanCycle Eval results", "",
             f"{len(recs)} graded answers, {len(by)} model-task pairs, "
             f"{len(errors)} API calls failed or were cut off by an output limit; they are excluded, not counted as wrong.", "",
             "pass@1 = share of single answers that are fully correct.",
             "pass^k = share of tasks where ALL k trials are fully correct.",
             "cells = mean share of correct table cells (partial credit).", "",
             "| model | pass@1 | pass^k | cells | cost USD |", "|---|---|---|---|---|"]
    for m in models:
        rs = [r for r in recs if r["model"] == m]
        tasks = {t for (mm, t) in by if mm == m}
        passk = sum(all(r["passed"] for r in by[(m, t)]) for t in tasks) / len(tasks)
        p1 = sum(r["passed"] for r in rs) / len(rs)
        cells = sum(r["cell_score"] for r in rs) / len(rs)
        cost = sum(r["cost"] or 0 for r in rs)
        lines.append(f"| {m} | {p1:.0%} | {passk:.0%} | {cells:.0%} | {cost:.3f} |")

    lines += ["", "## pass@1 by task family", "",
              "| family | " + " | ".join(models) + " |", "|---|" + "---|" * len(models)]
    for f in families:
        row = []
        for m in models:
            rs = [r for r in recs if r["model"] == m and r["family"] == f]
            row.append(f"{sum(r['passed'] for r in rs)}/{len(rs)}" if rs else "-")
        lines.append(f"| {f} | " + " | ".join(row) + " |")

    lines += ["", "## First wrong cell per failed answer", ""]
    for r in recs:
        if not r["passed"]:
            w = r["wrong"][0] if r["wrong"] else {}
            why = r["parse_error"] or f"cycle {w.get('cycle')}: {w.get('var')} expected {w.get('expected')}, got {w.get('got')}"
            lines.append(f"- `{r['model']}` `{r['task_id']}` trial {r['trial']}: {why}")

    out = Path("results/report.md")
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main(sys.argv[1:])
