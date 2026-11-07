"""Code-based grader: compares the model's table with the reference cell by cell.

A task passes only if every cell is correct. Partial credit is the share of
correct cells. Unparseable answers score 0 and are flagged, never guessed."""
import json
import re
from dataclasses import dataclass, field

from .families import Task


@dataclass
class Grade:
    task_id: str
    passed: bool
    cell_score: float
    parse_error: str = ""
    first_wrong_cycle: int | None = None
    wrong: list[dict] = field(default_factory=list)


def _extract_json(text: str) -> dict:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    return json.loads(text[start:end + 1])


def _normalise(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "false"):
            return low == "true"
        m = re.fullmatch(r"(-?\d+)\s*(ms)?", low)
        if m:
            return int(m.group(1))
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def grade(task: Task, answer_text: str) -> Grade:
    total = len(task.expected) * len(task.outputs)
    try:
        cycles = _extract_json(answer_text)["cycles"]
        if not isinstance(cycles, list):
            raise ValueError("'cycles' is not a list")
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return Grade(task.task_id, False, 0.0, parse_error=str(exc))

    by_cycle = {}
    for i, row in enumerate(cycles, start=1):
        if not isinstance(row, dict):
            continue
        k = _normalise(row.get("cycle", i))
        if type(k) is not int:
            k = i  # unreadable cycle number: fall back to position, never crash
        by_cycle.setdefault(k, row)

    correct, wrong = 0, []
    for k, exp in enumerate(task.expected, start=1):
        got_row = by_cycle.get(k, {})
        for name in task.outputs:
            got = _normalise(got_row.get(name))
            want = exp[name]
            # bool is a subclass of int in Python, so compare types explicitly
            if type(got) is type(want) and got == want:
                correct += 1
            else:
                wrong.append({"cycle": k, "var": name, "expected": want, "got": got})

    first = wrong[0]["cycle"] if wrong else None
    return Grade(task.task_id, not wrong, round(correct / total, 4),
                 first_wrong_cycle=first, wrong=wrong)
