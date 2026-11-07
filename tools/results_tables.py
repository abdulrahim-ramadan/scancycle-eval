"""Print the Markdown result tables used in README section 6. No API calls.

Usage: python tools/results_tables.py results/runs.jsonl"""
import json
import sys
from collections import defaultdict
from pathlib import Path

FAMS = ["ton_flicker", "edge_inside_if", "sr_rs_priority", "statement_order",
        "ctu_edges", "step_chain", "int_overflow", "tof_restart"]


def scored(path):
    latest = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        cut = bool(r.get("parse_error")) and (r.get("completion_tokens") or 0) >= 1500
        if not r.get("error") and not cut:
            latest[(r["model"], r["task_id"], r["trial"])] = r
    return list(latest.values())


def main(path):
    recs = scored(path)
    by = defaultdict(list)
    for r in recs:
        by[(r["model"], "hard" if "_hard_" in r["task_id"] else "normal", r["family"])].append(r)
    models = sorted({r["model"] for r in recs})

    print("| model | level | answers | pass@1 | pass^3 | cells |")
    print("|---|---|---|---|---|---|")
    for m in models:
        for lvl in ("normal", "hard"):
            rs = [r for (mm, l, f), v in by.items() if mm == m and l == lvl for r in v]
            if not rs:
                continue
            fams = {f: v for (mm, l, f), v in by.items() if mm == m and l == lvl}
            k3 = sum(len(v) >= 3 and all(x["passed"] for x in v) for v in fams.values())
            print(f"| `{m}` | {lvl} | {len(rs)} | {sum(r['passed'] for r in rs) / len(rs):.0%} | "
                  f"{k3}/{len(fams)} | {sum(r['cell_score'] for r in rs) / len(rs):.0%} |")

    print("\nFully correct answers per family, hard level (24 cycles):\n")
    print("| model | " + " | ".join(FAMS) + " |")
    print("|---|" + "---|" * len(FAMS))
    for m in models:
        cells = []
        for f in FAMS:
            v = by.get((m, "hard", f), [])
            cells.append(f"{sum(x['passed'] for x in v)}/{len(v)}" if v else "-")
        if any(c != "-" for c in cells):
            print(f"| `{m}` | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main(sys.argv[1])
