"""Hand-computed traces. Every expected list here was worked out on paper,
not produced by the simulator."""
from scancycle.blocks import Ctu, Rs, RTrig, Sr, Tof, Ton, to_int


def run_ton(pattern, pt, cycle):
    fb, out = Ton(pt), []
    for k, c in enumerate(pattern):
        fb(c == "1", k * cycle)
        out.append((fb.q, fb.et))
    return out


def test_ton_restarts_after_one_cycle_dropout():
    # PT 30 ms, 10 ms cycle. IN: 0 1 1 0 1 1 1 1
    # ET:                         0 0 10 0 0 10 20 30  -> Q only in the last cycle
    got = run_ton("01101111", 30, 10)
    assert [et for _, et in got] == [0, 0, 10, 0, 0, 10, 20, 30]
    assert [q for q, _ in got] == [False] * 7 + [True]


def test_tof_retrigger():
    # PT 30 ms. IN: 1 1 0 0 1 0 0 0 0
    # Q:            T T T T T T T T F    ET: 0 0 0 10 0 0 10 20 30
    fb, q, et = Tof(30), [], []
    for k, c in enumerate("110010000"):
        fb(c == "1", k * 10)
        q.append(fb.q)
        et.append(fb.et)
    assert q == [True] * 8 + [False]
    assert et == [0, 0, 0, 10, 0, 0, 10, 20, 30]


def test_tof_stays_off_before_first_true():
    fb = Tof(30)
    assert [fb(False, k * 10) for k in range(3)] == [False, False, False]


def test_r_trig_counts_edges_only():
    fb = RTrig()
    assert [fb(c == "1") for c in "011010110"] == [
        False, True, False, False, True, False, True, False, False]


def test_ctu_reset_while_cu_high_does_not_recount():
    # CU: 1 1 0 1 1 1 0 1   R: 0 0 0 0 1 0 0 0
    # CV: 1 1 1 2 0 0 0 1
    fb, cv = Ctu(3), []
    for cu, r in zip("11011101", "00001000"):
        fb(cu == "1", r == "1")
        cv.append(fb.cv)
    assert cv == [1, 1, 1, 2, 0, 0, 0, 1]


def test_sr_and_rs_disagree_when_both_true():
    sr, rs = Sr(), Rs()
    assert (sr(True, True), rs(True, True)) == (True, False)
    assert (sr(False, False), rs(False, False)) == (True, False)


def test_int_wraps():
    assert to_int(32767 + 1) == -32768
    assert to_int(30000 + 9000) == -26536
    assert to_int(-32768 - 1) == 32767


def test_tof_et_stays_at_pt_after_expiry():
    fb = Tof(20)
    for k, c in enumerate("10000"):
        fb(c == "1", k * 10)
    assert (fb.q, fb.et) == (False, 20)
