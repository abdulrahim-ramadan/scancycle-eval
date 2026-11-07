"""Task families. Each family writes the SCL program the model sees and runs
the same logic cycle by cycle in Python to produce the reference answer."""
import random
from dataclasses import dataclass, field

from .blocks import Ctu, Rs, RTrig, Sr, Tof, Ton, to_int


@dataclass
class Task:
    task_id: str
    family: str
    title: str
    scl: str
    cycle_ms: int
    inputs: list[dict]
    outputs: list[str]
    initial: dict
    trap: str
    expected: list[dict] = field(default_factory=list)

    @property
    def cycles(self) -> int:
        return len(self.inputs)


def _bools(rng: random.Random, pattern: str) -> list[bool]:
    return [c == "1" for c in pattern]


def _runs(rng: random.Random, n: int, short=(1, 3), long=(2, 5), start=False) -> list[bool]:
    """Random on/off signal of length n built from runs, like a real sensor."""
    out, val = [], start
    while len(out) < n:
        lo, hi = long if val else short
        out += [val] * rng.randint(lo, hi)
        val = not val
    return out[:n]


class Family:
    name = ""
    title = ""
    trap = ""

    def build(self, seed: int, hard: bool = False) -> Task:
        raise NotImplementedError

    @staticmethod
    def tid(name, seed, hard):
        return f"{name}_{'hard_' if hard else ''}{seed}"


class TonFlicker(Family):
    name = "ton_flicker"
    title = "On-delay timer with a one-cycle dropout"
    trap = "TON restarts from zero when IN is FALSE for a single cycle; ET only counts from the cycle where IN became TRUE again."

    def build(self, seed, hard=False):
        rng = random.Random(seed)
        cycle = rng.choice([10, 20])
        pt = cycle * rng.choice([3, 4])
        lead = rng.randint(1, 2)
        first = rng.randint(2, pt // cycle)
        tail = pt // cycle + rng.randint(2, 3)
        pattern = "0" * lead + "1" * first + "0" + "1" * tail
        if hard:
            steps = pt // cycle
            pattern = "0" * lead
            for _ in range(3):
                pattern += "1" * rng.randint(1, steps) + "0"
            pattern += "1" * (steps + 2) + "0" * rng.randint(1, 2) + "1" * (steps + rng.randint(0, 2)) + "0"
        sensor = _bools(rng, pattern)
        scl = (
            f"fbDelay(IN := bSensor, PT := T#{pt}MS);\n"
            "bReady := fbDelay.Q;"
        )
        fb = Ton(pt)
        rows, expected = [], []
        for k, s in enumerate(sensor):
            now = k * cycle
            fb(s, now)
            rows.append({"bSensor": s})
            expected.append({"bReady": fb.q, "fbDelay.ET": fb.et})
        return Task(self.tid(self.name, seed, hard), self.name, self.title, scl, cycle, rows,
                    ["bReady", "fbDelay.ET"], {"bReady": False}, self.trap, expected)


class EdgeInsideIf(Family):
    name = "edge_inside_if"
    title = "R_TRIG instance called only inside an IF"
    trap = "The R_TRIG instance keeps its memory from the last cycle it was CALLED, not from the last cycle; while bEnable is FALSE it sees nothing."

    def build(self, seed, hard=False):
        rng = random.Random(seed)
        variants = [
            ("0011110000110", "0000011111111"),
            ("0110001111000", "0000000011111"),
            ("0011001100110", "1100001111000"),
        ]
        sensor_p, enable_p = variants[rng.randrange(len(variants))]
        sensor, enable = _bools(rng, sensor_p), _bools(rng, enable_p)
        if hard:
            sensor = _runs(rng, 24, short=(1, 3), long=(1, 4))
            enable = _runs(rng, 24, short=(2, 4), long=(3, 6))
        scl = (
            "IF bEnable THEN\n"
            "    fbEdge(CLK := bSensor);\n"
            "    IF fbEdge.Q THEN\n"
            "        nCount := nCount + 1;\n"
            "    END_IF;\n"
            "END_IF;"
        )
        fb, count = RTrig(), 0
        rows, expected = [], []
        for s, e in zip(sensor, enable):
            if e:
                if fb(s):
                    count += 1
            rows.append({"bEnable": e, "bSensor": s})
            expected.append({"nCount": count})
        return Task(self.tid(self.name, seed, hard), self.name, self.title, scl, 10, rows,
                    ["nCount"], {"nCount": 0}, self.trap, expected)


class SetResetPriority(Family):
    name = "sr_rs_priority"
    title = "SR versus RS when set and reset are TRUE together"
    trap = "SR is set dominant and RS is reset dominant; with both inputs TRUE the two latches disagree."

    def build(self, seed, hard=False):
        rng = random.Random(seed)
        n = 24 if hard else 10
        set_in = [rng.random() < 0.4 for _ in range(n)]
        reset_in = [rng.random() < 0.35 for _ in range(n)]
        both = rng.sample(range(2, n), 4 if hard else 2)
        for i in both:
            set_in[i] = reset_in[i] = True
        scl = (
            "fbSR(S1 := bSet, R := bReset);\n"
            "fbRS(S := bSet, R1 := bReset);\n"
            "bLampSR := fbSR.Q1;\n"
            "bLampRS := fbRS.Q1;"
        )
        sr, rs = Sr(), Rs()
        rows, expected = [], []
        for s, r in zip(set_in, reset_in):
            sr(s, r)
            rs(s, r)
            rows.append({"bSet": s, "bReset": r})
            expected.append({"bLampSR": sr.q1, "bLampRS": rs.q1})
        return Task(self.tid(self.name, seed, hard), self.name, self.title, scl, 10, rows,
                    ["bLampSR", "bLampRS"], {"bLampSR": False, "bLampRS": False},
                    self.trap, expected)


class StatementOrder(Family):
    name = "statement_order"
    title = "Reading and writing the same variable within one cycle"
    trap = "Statements run top to bottom: nOld reads nVal before it changes, the reset overwrites the addition, and bHighPrev still holds last cycle's value when bAlarm is computed."

    def build(self, seed, hard=False):
        rng = random.Random(seed)
        n = 20 if hard else 10
        limit = rng.choice([6, 8, 10])
        steps = [rng.choice([1, 2, 3, 4]) for _ in range(n)]
        resets = [False] * n
        resets[rng.randint(4, 6)] = True
        if hard:
            resets[rng.randint(11, 14)] = True
            for i in rng.sample(range(n), 3):
                steps[i] = 0
        scl = (
            "nOld := nVal;\n"
            "nVal := nVal + nStep;\n"
            "IF bReset THEN\n"
            "    nVal := 0;\n"
            "END_IF;\n"
            f"bHigh := nVal > {limit};\n"
            "bAlarm := bHigh AND bHighPrev;\n"
            "bHighPrev := bHigh;"
        )
        val, high_prev = 0, False
        rows, expected = [], []
        for step, rst in zip(steps, resets):
            old = val
            val = val + step
            if rst:
                val = 0
            high = val > limit
            alarm = high and high_prev
            high_prev = high
            rows.append({"nStep": step, "bReset": rst})
            expected.append({"nOld": old, "nVal": val, "bAlarm": alarm})
        return Task(self.tid(self.name, seed, hard), self.name, self.title, scl, 10, rows,
                    ["nOld", "nVal", "bAlarm"],
                    {"nVal": 0, "nOld": 0, "bHighPrev": False}, self.trap, expected)


class CounterEdges(Family):
    name = "ctu_edges"
    title = "CTU counting parts that stay on the sensor for several cycles"
    trap = "CTU counts rising edges of CU, not cycles where CU is TRUE; after a reset a CU that is still TRUE does not count again."

    def build(self, seed, hard=False):
        rng = random.Random(seed)
        variants = [
            ("0111001100011110", "0000000010000000"),
            ("0110011100111000", "0000000100000000"),
            ("1110001110110011", "0000001000000000"),
        ]
        part_p, reset_p = variants[rng.randrange(len(variants))]
        pv = rng.choice([2, 3])
        part, reset = _bools(rng, part_p), _bools(rng, reset_p)
        if hard:
            pv = rng.choice([3, 4])
            part = _runs(rng, 24, short=(1, 3), long=(1, 4))
            reset = [False] * 24
            highs = [i for i in range(6, 22) if part[i]]
            for i in rng.sample(highs, 2):  # resets while a part is still on the sensor
                reset[i] = True
        scl = (
            f"fbCount(CU := bPart, R := bReset, PV := {pv});\n"
            "nParts := fbCount.CV;\n"
            "bBoxFull := fbCount.Q;"
        )
        fb = Ctu(pv)
        rows, expected = [], []
        for p, r in zip(part, reset):
            fb(p, r)
            rows.append({"bPart": p, "bReset": r})
            expected.append({"nParts": fb.cv, "bBoxFull": fb.q})
        return Task(self.tid(self.name, seed, hard), self.name, self.title, scl, 10, rows,
                    ["nParts", "bBoxFull"], {"nParts": 0, "bBoxFull": False},
                    self.trap, expected)


class StepChain(Family):
    name = "step_chain"
    title = "Step sequence (Schrittkette) with CASE"
    trap = "CASE runs exactly one branch per cycle, so a step can advance at most once per cycle even when several conditions are TRUE; outputs computed after the CASE already see the new step."

    def build(self, seed, hard=False):
        rng = random.Random(seed)
        variants = [
            ("0110000000000", "0011100111000"),
            ("1000001100000", "1111000000110"),
            ("0100000010000", "0111110001100"),
        ]
        start_p, part_p = variants[rng.randrange(len(variants))]
        start, part = _bools(rng, start_p), _bools(rng, part_p)
        if hard:
            start = _runs(rng, 24, short=(2, 5), long=(1, 2))
            part = _runs(rng, 24, short=(1, 3), long=(1, 4))
        scl = (
            "CASE nStep OF\n"
            "    0:  IF bStart THEN nStep := 10; END_IF;\n"
            "    10: IF bPartIn THEN nStep := 20; END_IF;\n"
            "    20: IF NOT bPartIn THEN nStep := 30; END_IF;\n"
            "    30: nStep := 0;\n"
            "END_CASE;\n"
            "bConveyor := (nStep = 10) OR (nStep = 20);"
        )
        step = 0
        rows, expected = [], []
        for s, p in zip(start, part):
            if step == 0:
                if s:
                    step = 10
            elif step == 10:
                if p:
                    step = 20
            elif step == 20:
                if not p:
                    step = 30
            elif step == 30:
                step = 0
            rows.append({"bStart": s, "bPartIn": p})
            expected.append({"nStep": step, "bConveyor": step in (10, 20)})
        return Task(self.tid(self.name, seed, hard), self.name, self.title, scl, 10, rows,
                    ["nStep", "bConveyor"], {"nStep": 0}, self.trap, expected)


class IntOverflow(Family):
    name = "int_overflow"
    title = "Accumulating into a 16-bit INT"
    trap = "INT is 16-bit; past 32767 it wraps to negative values instead of growing."

    def build(self, seed, hard=False):
        rng = random.Random(seed)
        n = 16 if hard else 8
        deltas = [rng.choice([6000, 7500, 9000, 11000, 12500]) for _ in range(n)]
        deltas[rng.randint(5, 7)] = -rng.choice([3000, 5000])
        if hard:
            for i in rng.sample(range(8, n), 3):
                deltas[i] = -rng.choice([14000, 20000, 25000])
        scl = (
            "nTotal := nTotal + nIn;\n"
            "bNegative := nTotal < 0;"
        )
        total = 0
        rows, expected = [], []
        for d in deltas:
            total = to_int(total + d)
            rows.append({"nIn": d})
            expected.append({"nTotal": total, "bNegative": total < 0})
        return Task(self.tid(self.name, seed, hard), self.name, self.title, scl, 10, rows,
                    ["nTotal", "bNegative"], {"nTotal": 0}, self.trap, expected)


class TofRestart(Family):
    name = "tof_restart"
    title = "Off-delay timer that is re-triggered while running"
    trap = "TOF keeps Q TRUE for PT after IN falls; a new TRUE on IN during that time resets ET, so the delay starts again from the next falling edge."

    def build(self, seed, hard=False):
        rng = random.Random(seed)
        cycle = rng.choice([10, 20])
        steps = rng.choice([3, 4])
        pt = cycle * steps
        pattern = "1" * rng.randint(2, 3) + "0" * (steps - 1) + "1" + "0" * (steps + 2)
        if hard:
            pattern = ("0" * rng.randint(1, 2) + "1" * rng.randint(1, 3) + "0" * rng.randint(1, steps - 1)
                       + "1" + "0" * (steps + 1) + "1" * 2 + "0" * rng.randint(1, steps - 1) + "1" + "0" * (steps + 2))
        run = _bools(rng, pattern)
        scl = (
            f"fbOff(IN := bRun, PT := T#{pt}MS);\n"
            "bFan := fbOff.Q;"
        )
        fb = Tof(pt)
        rows, expected = [], []
        for k, r in enumerate(run):
            fb(r, k * cycle)
            rows.append({"bRun": r})
            expected.append({"bFan": fb.q, "fbOff.ET": fb.et})
        return Task(self.tid(self.name, seed, hard), self.name, self.title, scl, cycle, rows,
                    ["bFan", "fbOff.ET"], {"bFan": False}, self.trap, expected)


FAMILIES: list[Family] = [
    TonFlicker(), EdgeInsideIf(), SetResetPriority(), StatementOrder(),
    CounterEdges(), StepChain(), IntOverflow(), TofRestart(),
]


def build_suite(seeds=(1,), hard=False) -> list[Task]:
    return [fam.build(seed, hard) for fam in FAMILIES for seed in seeds]
