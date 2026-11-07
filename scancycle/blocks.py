"""IEC 61131-3 standard function blocks, evaluated once per scan cycle.

Timing convention used by every task (stated in each prompt):
  * cycle k starts at t = (k - 1) * cycle_ms
  * a timer reads the clock at the moment it is called
  * ET is the time elapsed since the cycle in which the timer started timing
"""
from dataclasses import dataclass

INT_MIN, INT_MAX = -32768, 32767


def to_int(value: int) -> int:
    """16-bit two's complement wrap, as an S7 INT without overflow checks."""
    return (value - INT_MIN) % 65536 + INT_MIN


@dataclass
class RTrig:
    q: bool = False
    _mem: bool = False

    def __call__(self, clk: bool) -> bool:
        self.q = clk and not self._mem
        self._mem = clk
        return self.q


@dataclass
class FTrig:
    q: bool = False
    _mem: bool = False

    def __call__(self, clk: bool) -> bool:
        self.q = (not clk) and self._mem
        self._mem = clk
        return self.q


@dataclass
class Ton:
    pt: int
    q: bool = False
    et: int = 0
    _start: int | None = None

    def __call__(self, inp: bool, now: int) -> bool:
        if not inp:
            self._start = None
            self.et = 0
            self.q = False
            return self.q
        if self._start is None:
            self._start = now
        self.et = min(now - self._start, self.pt)
        self.q = self.et >= self.pt
        return self.q


@dataclass
class Tof:
    pt: int
    q: bool = False
    et: int = 0
    _start: int | None = None

    def __call__(self, inp: bool, now: int) -> bool:
        if inp:
            self._start = None
            self.et = 0
            self.q = True
            return self.q
        if not self.q:
            return self.q  # expired (ET stays at PT) or never started (ET 0)
        if self._start is None:
            self._start = now
        self.et = min(now - self._start, self.pt)
        self.q = self.et < self.pt
        return self.q


@dataclass
class Ctu:
    pv: int
    q: bool = False
    cv: int = 0
    _edge: RTrig | None = None

    def __post_init__(self):
        self._edge = RTrig()

    def __call__(self, cu: bool, reset: bool) -> bool:
        rising = self._edge(cu)
        if reset:
            self.cv = 0
        elif rising and self.cv < INT_MAX:
            self.cv += 1
        self.q = self.cv >= self.pv
        return self.q


@dataclass
class Sr:
    """Set dominant: S1 wins when both inputs are TRUE."""
    q1: bool = False

    def __call__(self, s1: bool, r: bool) -> bool:
        self.q1 = s1 or (self.q1 and not r)
        return self.q1


@dataclass
class Rs:
    """Reset dominant: R1 wins when both inputs are TRUE."""
    q1: bool = False

    def __call__(self, s: bool, r1: bool) -> bool:
        self.q1 = (not r1) and (s or self.q1)
        return self.q1
