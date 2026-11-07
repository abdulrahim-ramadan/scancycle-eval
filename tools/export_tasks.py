"""Write every task with its expected output to tasks/*.json. No API calls.

Usage: python tools/export_tasks.py"""
import dataclasses
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scancycle.families import build_suite
from scancycle.prompt import render

out = Path("tasks")
out.mkdir(exist_ok=True)
for hard, name in ((False, "normal"), (True, "hard")):
    suite = build_suite(seeds=(1,), hard=hard)
    rows = [{**dataclasses.asdict(t), "prompt": render(t)} for t in suite]
    (out / f"tasks_{name}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"tasks/tasks_{name}.json: {len(rows)} tasks")
