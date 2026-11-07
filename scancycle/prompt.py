import json

from .families import Task

RULES = """Execution model (IEC 61131-3, cyclic task):
- At the start of each cycle the inputs in the table are copied into the program. They do not change during the cycle.
- The program runs once per cycle, top to bottom.
- Report every output variable as its value AFTER the program finished that cycle.
- Variables keep their value from one cycle to the next. Initial values are given below; any variable not listed starts at 0 or FALSE.
- Cycle k starts at t = (k - 1) * {cycle} ms. A timer reads the clock when it is called. ET is the time since the cycle in which the timer started timing, capped at PT.
- TON, TOF, R_TRIG, CTU, SR and RS behave as defined in IEC 61131-3. SR is set dominant, RS is reset dominant. CTU counts rising edges of CU.
- INT is a 16-bit signed integer. Overflow wraps around (two's complement), there is no overflow error.
- Times are reported as integers in milliseconds."""

ANSWER = """Answer with JSON only, no explanation, in exactly this shape:
{{"cycles": [{example}, ...]}}
Give one object per cycle, cycles 1 to {n}, in order. Use true/false for BOOL and integers for INT and TIME."""


def _cell(value) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value)


def render(task: Task) -> str:
    names = list(task.inputs[0])
    header = "| cycle | " + " | ".join(names) + " |"
    sep = "|" + "---|" * (len(names) + 1)
    lines = [header, sep]
    for k, row in enumerate(task.inputs, start=1):
        lines.append(f"| {k} | " + " | ".join(_cell(row[n]) for n in names) + " |")
    initial = ", ".join(f"{k} = {_cell(v)}" for k, v in task.initial.items())
    example = json.dumps({"cycle": 1, **{o: "..." for o in task.outputs}})
    return "\n\n".join([
        "You are checking a PLC program written in Structured Text (SCL).",
        RULES.format(cycle=task.cycle_ms),
        f"Cycle time: {task.cycle_ms} ms. Number of cycles: {task.cycles}.",
        f"Initial values: {initial}.",
        "Program (runs once per cycle):\n```\n" + task.scl + "\n```",
        "Inputs per cycle:\n" + "\n".join(lines),
        "Outputs to report: " + ", ".join(task.outputs) + ".",
        ANSWER.format(example=example, n=task.cycles),
    ])
