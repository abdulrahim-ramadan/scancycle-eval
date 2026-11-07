import json

from scancycle.families import FAMILIES, build_suite
from scancycle.grader import grade


def answer_from(task, mutate=None):
    rows = [{"cycle": k, **row} for k, row in enumerate(task.expected, start=1)]
    if mutate:
        mutate(rows)
    return json.dumps({"cycles": rows})


def test_reference_answer_passes_every_task():
    for task in build_suite(seeds=(1, 2, 3)) + build_suite(seeds=(1, 2, 3), hard=True):
        g = grade(task, answer_from(task))
        assert g.passed and g.cell_score == 1.0, task.task_id


def test_one_wrong_cell_fails_with_partial_credit():
    task = FAMILIES[0].build(1)

    def flip(rows):
        rows[-1]["bReady"] = not rows[-1]["bReady"]

    g = grade(task, answer_from(task, flip))
    assert not g.passed
    assert 0 < g.cell_score < 1
    assert g.first_wrong_cycle == task.cycles


def test_true_is_not_accepted_for_integer_one():
    task = FAMILIES[1].build(1)

    def as_bool(rows):
        for r in rows:
            r["nCount"] = bool(r["nCount"])

    assert not grade(task, answer_from(task, as_bool)).passed


def test_fenced_json_and_string_values_are_accepted():
    task = FAMILIES[7].build(1)
    rows = [{"cycle": k, "bFan": "TRUE" if r["bFan"] else "FALSE", "fbOff.ET": f"{r['fbOff.ET']}ms"}
            for k, r in enumerate(task.expected, start=1)]
    text = "```json\n" + json.dumps({"cycles": rows}) + "\n```"
    assert grade(task, text).passed


def test_missing_cycles_and_garbage_score_low():
    task = FAMILIES[2].build(1)
    half = json.dumps({"cycles": [{"cycle": 1, **task.expected[0]}]})
    assert grade(task, half).cell_score < 0.2
    bad = grade(task, "I think the lamp is on.")
    assert not bad.passed and bad.cell_score == 0 and bad.parse_error


def test_suite_is_reproducible():
    a = [t.expected for t in build_suite(seeds=(1, 2))]
    b = [t.expected for t in build_suite(seeds=(1, 2))]
    assert a == b


def test_malformed_cycle_numbers_never_crash():
    task = FAMILIES[0].build(1)
    for text in ['{"cycles":[{"cycle":null}]}', '{"cycles":[{"cycle":"abc"}]}',
                 '{"cycles":[1, "x", {"cycle":1.5}]}', '{"cycles":"x"}', '{}', '[]', '']:
        g = grade(task, text)
        assert not g.passed


def test_time_with_space_before_unit_is_read():
    task = FAMILIES[0].build(1)
    rows = [{"cycle": k, "bReady": r["bReady"], "fbDelay.ET": f"{r['fbDelay.ET']} ms"}
            for k, r in enumerate(task.expected, start=1)]
    assert grade(task, json.dumps({"cycles": rows})).passed
