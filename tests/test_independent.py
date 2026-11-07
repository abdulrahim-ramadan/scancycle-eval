"""Second, independent derivation of the reference answers.

These do not use scancycle.blocks. Timers are counted in whole cycles and
edges/latches are written from their truth tables, so a mistake in the main
simulator would show up as a disagreement here."""
import pytest

from scancycle.families import FAMILIES

SEEDS = [(s, h) for s in range(1, 21) for h in (False, True)]


def fam(name):
    return next(f for f in FAMILIES if f.name == name)


@pytest.mark.parametrize("seed,hard", SEEDS)
def test_ton(seed, hard):
    t = fam("ton_flicker").build(seed, hard)
    pt_cycles = int(t.scl.split("T#")[1].split("MS")[0]) // t.cycle_ms
    run = 0  # cycles since IN went TRUE, counting the first one as 0
    for row, exp in zip(t.inputs, t.expected):
        run = run + 1 if row["bSensor"] else 0
        et = 0 if run == 0 else min(run - 1, pt_cycles) * t.cycle_ms
        assert exp == {"bReady": run - 1 >= pt_cycles and run > 0, "fbDelay.ET": et}


@pytest.mark.parametrize("seed,hard", SEEDS)
def test_tof(seed, hard):
    t = fam("tof_restart").build(seed, hard)
    pt_cycles = int(t.scl.split("T#")[1].split("MS")[0]) // t.cycle_ms
    ever_on, off_for = False, None
    for row, exp in zip(t.inputs, t.expected):
        if row["bRun"]:
            ever_on, off_for = True, None
            q, et = True, 0
        elif not ever_on:
            q, et = False, 0
        else:
            off_for = 0 if off_for is None else off_for + 1
            et = min(off_for, pt_cycles) * t.cycle_ms
            q = off_for < pt_cycles
        assert exp == {"bFan": q, "fbOff.ET": et}


@pytest.mark.parametrize("seed,hard", SEEDS)
def test_ctu(seed, hard):
    t = fam("ctu_edges").build(seed, hard)
    pv = int(t.scl.split("PV := ")[1].split(")")[0])
    prev, cv = False, 0
    for row, exp in zip(t.inputs, t.expected):
        rising = row["bPart"] and not prev
        prev = row["bPart"]
        cv = 0 if row["bReset"] else cv + rising
        assert exp == {"nParts": cv, "bBoxFull": cv >= pv}


@pytest.mark.parametrize("seed,hard", SEEDS)
def test_edge_inside_if(seed, hard):
    t = fam("edge_inside_if").build(seed, hard)
    seen, count = False, 0
    for row, exp in zip(t.inputs, t.expected):
        if row["bEnable"]:
            count += row["bSensor"] and not seen
            seen = row["bSensor"]
        assert exp == {"nCount": count}


@pytest.mark.parametrize("seed,hard", SEEDS)
def test_sr_rs(seed, hard):
    t = fam("sr_rs_priority").build(seed, hard)
    table_sr = {(0, 0): None, (1, 0): True, (0, 1): False, (1, 1): True}
    table_rs = {(0, 0): None, (1, 0): True, (0, 1): False, (1, 1): False}
    sr = rs = False
    for row, exp in zip(t.inputs, t.expected):
        key = (int(row["bSet"]), int(row["bReset"]))
        sr = sr if table_sr[key] is None else table_sr[key]
        rs = rs if table_rs[key] is None else table_rs[key]
        assert exp == {"bLampSR": sr, "bLampRS": rs}


@pytest.mark.parametrize("seed,hard", SEEDS)
def test_int_overflow(seed, hard):
    t = fam("int_overflow").build(seed, hard)
    total = 0
    for row, exp in zip(t.inputs, t.expected):
        total = int.from_bytes(((total + row["nIn"]) & 0xFFFF).to_bytes(2, "big"), "big", signed=True)
        assert exp == {"nTotal": total, "bNegative": total < 0}
