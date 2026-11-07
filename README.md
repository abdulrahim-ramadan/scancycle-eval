# ScanCycle Eval

Can a model follow a PLC program across scan cycles?

## 1. Short description

ScanCycle Eval tests whether models can follow a PLC program (IEC 61131-3 Structured Text) across scan cycles. The programs use timers, edge detectors, counters, latches, step sequences and 16-bit integers, and state carries from one cycle to the next. Each task has exactly one correct output table. A simulator computes that table, and the simulator is checked against hand traces and against a second implementation written independently. Answers are graded cell by cell in code. Six models were run (five of them on the 24-cycle suite), with 3 trials per task. One model solved every 24-cycle task. The off-delay timer (TOF) broke the other four in every trial: each of them simulated it as an on-delay timer. Every family was solved by at least one model, so the failures reflect real reasoning limits rather than broken tasks.

## 2. Video walkthrough

https://youtu.be/jv1YICCfk0A (about 5 minutes, English narration)

## 3. Domain and expertise

**Domain:** industrial automation, specifically PLC programming in IEC 61131-3 Structured Text (SCL) as used on production lines.

**Author's expertise:** I work with PLC-controlled machines on automotive assembly lines, where I read and debug PLC programs and watch how they behave cycle by cycle. I am also a Python developer. I built the eval around the mistakes that matter in that work: a timer that restarts, an edge that is missed, a counter that counts twice. I checked the reference answers by hand on paper before writing any test.

No real plant code, machine names or production data are used. All programs are written from the public IEC 61131-3 standard.

## 4. What it tests and why it matters

### What it tests

A PLC does not run its program once. It runs it again every few milliseconds:

1. read the inputs,
2. execute the whole program from top to bottom,
3. write the outputs,
4. repeat.

Timers, edge detectors, counters and latches carry state from one cycle to the next.

Each task gives the model three things:

- a short SCL program,
- an input table,
- the full execution rules.

The model must return the value of every output after every cycle. There is exactly one correct table. The input table has one of two lengths:

- normal level: 8 to 16 cycles,
- hard level (`--hard`): 16 to 24 cycles, with several events per task.

Frontier models read each line of SCL correctly. This eval checks whether they keep the **state across cycles** right. That is what an automation engineer does every day when reading a program or debugging a stopped line.

### Why it matters

PLC programs control conveyors, presses, robots and safety functions, and engineers increasingly ask AI assistants to explain or review this code. An assistant that misreads one timer or one edge does not raise an error. It gives a confident, wrong account of when a motor starts or when a counter fires. In practice that can mean a stopped production line, scrapped parts or an unsafe state.

### Task design

There are eight families. Each one is built around a behaviour that people who work with PLCs know well and that is easy to get wrong unless you simulate cycle by cycle. The trap for each family was written down **before** any model was run.

| Family | What the model must track | Typical mistake |
|---|---|---|
| `ton_flicker` | TON with IN dropping for one cycle | Timer keeps counting instead of restarting from zero |
| `edge_inside_if` | R_TRIG called only inside an IF | Edge memory only updates when the block is called |
| `sr_rs_priority` | SR and RS with set and reset TRUE together | Set dominant vs reset dominant |
| `statement_order` | Reads and writes of one variable in a cycle | Using the new value where the old one is read |
| `ctu_edges` | CTU with parts staying on the sensor | Counting cycles instead of rising edges |
| `step_chain` | Step sequence with CASE | Advancing two steps in one cycle |
| `int_overflow` | Accumulating into a 16-bit INT | 32768 instead of -32768 |
| `tof_restart` | TOF re-triggered while running | When the output finally turns off |

Every prompt states the full execution model:

- when inputs are read and when outputs are reported,
- the cycle time,
- how a timer reads the clock (cycle k starts at t = (k-1) · cycle time, and ET counts from the cycle in which timing started),
- that INT is 16-bit and wraps around,
- the exact JSON answer format.

Nothing the grader checks is left implicit. Tasks are generated from a fixed seed, so the same command always produces the same suite.

**All tasks, including the inputs, the expected outputs and the exact prompt, are in `tasks/tasks_normal.json` and `tasks/tasks_hard.json`.** You can regenerate them with `python tools/export_tasks.py`. Every task's `trap` field names the edge case it targets.

### Scoring logic

The grader (`scancycle/grader.py`) is code only. No model judges another model.

- The answer must be JSON with one object per cycle: `{"cycles": [{"cycle": 1, "<output>": ...}, ...]}`.
- Every output in every cycle is compared with the reference.
- Types are strict. BOOL must be `true`/`false`, and INT and TIME must be integers. `TRUE` is not accepted for `1`, and `"30 ms"` is not accepted for `30`.
- A task **passes** only if every cell is correct. `cell_score` gives partial credit as the share of correct cells.
- An answer that cannot be parsed scores 0 and is recorded with the reason. Nothing is guessed. If the cycle numbers are missing or garbled, the row position is used.
- Reported metrics:
  - *pass@1*: the share of single answers that are fully correct.
  - *pass^3*: the number of tasks where all 3 trials are fully correct.
  - *cells*: mean partial credit.
- Harness failures are recorded but never scored. A harness failure is either an API error (rate limit, quota, timeout) or an answer cut off by an output-token limit (a parse error after 1500 or more output tokens). These calls are retried, so an outage never counts as a wrong answer.

The reference answers come from a small simulator (`scancycle/blocks.py`). It implements TON, TOF, R_TRIG, CTU, SR, RS and INT wrap-around as defined in IEC 61131-3. The simulator is checked in three ways:

- **Hand traces.** Traces worked out on paper (`tests/test_blocks.py`).
- **Independent derivation.** Every timer, counter, edge, latch and INT task is derived a second time, over 20 seeds at both levels, by code that does not use the simulator (`tests/test_independent.py`). One wrong assumption therefore cannot pass silently.
- **Grader tests.** The grader itself is tested with several kinds of answer (`tests/test_grader.py`):
  - correct answers,
  - deliberately wrong answers,
  - wrong types,
  - partial answers,
  - garbled cycle numbers,
  - free text.

## 5. Setup and run

Requirements:

- Python 3.11 or newer.
- No third-party packages are needed to run the eval, because the runner uses only the standard library. `pytest` is needed only for the tests.

Set up a clean environment:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q                # 256 tests, under 1 s, no API calls
```

API keys are read from environment variables, or from a `.env` file in the project folder. Copy `.env.example` to `.env` and fill in only the keys you have. All three work on free tiers. Keys are never printed or saved to results.

```
GEMINI_API_KEY=       # Google AI Studio, models written as gemini:<model-id>
GROQ_API_KEY=         # Groq, models written as groq:<model-id>
OPENROUTER_API_KEY=   # OpenRouter, free models end in ":free"
```

**One command runs the eval and writes the report.** This example uses the hard suite and one model:

```bash
python run_eval.py --hard --models gemini:gemini-3.5-flash --trials 3 && python report.py results/runs.jsonl
```

Useful options:

- `--dry-run`: prints one prompt and makes no API call.
- `--list-models`: saves the model IDs your keys can reach to `results/models.txt`.
- `--workers N`: number of calls made in parallel. The default is 4.
- `--pause S`: spaces calls out for free-tier rate limits.
- `--seeds 1 2 3`: builds a larger suite.

Runs resume automatically. A trial that already has a scored answer in `results/runs.jsonl` is skipped, so an interrupted run can simply be started again.

Approximate runtime and cost:

| Item | Time | Cost |
|---|---|---|
| Tests | under 1 second | $0 |
| One model, one level (8 tasks × 3 trials = 24 calls) | about 10–30 minutes on free tiers | $0 |
| Full run reported below (299 calls, 166 of them graded: 6 models, both levels) | about 6 hours of total model time; 2–3 hours wall clock with `--workers 4`, mostly waiting on rate limits | $0 (all free tiers) |

On paid tiers the cost is dominated by output tokens. A 24-cycle answer from a reasoning model uses roughly 3,000–15,000 output tokens.

To rebuild every number below from the saved raw outputs, without any API calls, run:

```bash
python report.py results/runs.jsonl          # writes results/report.md
python tools/results_tables.py results/runs.jsonl
```

## 6. Models tested and results

**Run date:** 7–8 November 2026.

**Settings:**

- 3 trials per task.
- Temperature left at each provider's default (not set by the runner).
- Maximum output: 32,768 tokens. On Groq the request is retried at the per-request limit the API reports.
- One seed per level: 8 normal tasks and 8 hard tasks.

**Exact model IDs**, as passed to the API:

| Model ID | Provider |
|---|---|
| `gemini-3.5-flash` | Google AI Studio |
| `gemini-3.8-flash` | Google AI Studio |
| `gemma-4-31b-it` | Google AI Studio |
| `openai/gpt-oss-120b` | Groq |
| `openai/gpt-oss-20b` | Groq |
| `qwen/qwen3.8-27b` | Groq |

**Raw outputs:** every answer is in `results/runs.jsonl`. Each record holds the full model text, the score, the first wrong cell, token counts and the time taken. The files `results/run_2026*.jsonl` are earlier runs from the same day and are kept for transparency. The rebuilt report is `results/report.md`.

| model | level | answers | pass@1 | pass^3 | cells |
|---|---|---|---|---|---|
| `gemini:gemini-3.5-flash` | normal | 2 | 100% | 0/2 | 100% |
| `gemini:gemini-3.5-flash` | hard | 22 | 100% | 6/8 | 100% |
| `gemini:gemini-3.8-flash` | normal | 7 | 100% | 2/3 | 100% |
| `gemini:gemma-4-31b-it` | normal | 23 | 83% | 5/8 | 89% |
| `gemini:gemma-4-31b-it` | hard | 24 | 79% | 6/8 | 88% |
| `groq:openai/gpt-oss-120b` | normal | 23 | 87% | 6/8 | 90% |
| `groq:openai/gpt-oss-120b` | hard | 20 | 85% | 5/7 | 89% |
| `groq:openai/gpt-oss-20b` | normal | 20 | 65% | 3/7 | 81% |
| `groq:openai/gpt-oss-20b` | hard | 11 | 73% | 1/6 | 87% |
| `groq:qwen/qwen3.8-27b` | hard | 14 | 7% | 0/7 | 59% |

Fully correct answers per family, hard level (16–24 cycles):

| model | ton_flicker | edge_inside_if | sr_rs_priority | statement_order | ctu_edges | step_chain | int_overflow | tof_restart |
|---|---|---|---|---|---|---|---|---|
| `gemini:gemini-3.5-flash` | 3/3 | 3/3 | 3/3 | 3/3 | 2/2 | 2/2 | 3/3 | 3/3 |
| `gemini:gemma-4-31b-it` | 1/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 |
| `groq:openai/gpt-oss-120b` | 3/3 | 3/3 | 3/3 | - | 3/3 | 3/3 | 2/2 | 0/3 |
| `groq:openai/gpt-oss-20b` | 0/2 | 2/2 | 2/2 | - | 1/1 | - | 3/3 | 0/1 |
| `groq:qwen/qwen3.8-27b` | 0/3 | 0/2 | 0/1 | 0/1 | 0/2 | - | 1/2 | 0/3 |

Some cells have fewer than three trials. This happens where calls failed at the API (rate limits, daily quota) or were cut off by an output limit, because those calls are excluded rather than scored as wrong. Two coverage gaps apply to whole models:

- Gemini 3.8 Flash ran out of its free daily quota after a few answers, so it appears only in the short suite.
- Qwen was run only on the hard suite.

What the tables show:

- Every family is solved by at least one model, so no task is impossible or mis-specified.
- The models separate clearly on the 24-cycle suite. One model solved every family, and one failed almost all of them.

## 7. Failure analysis

**Off-delay timer (TOF): the clearest limitation.** Four of the five models failed TOF in every trial they answered.

- gpt-oss-120b, gpt-oss-20b and Gemma 4 all produced the same wrong table: the output stays FALSE while the input is TRUE, and ET counts up while the input is TRUE. That is the behaviour of an on-delay timer (TON). The models recognise the block name and then simulate the wrong block.
- Qwen made a different TOF error: it switched the output on in cycle 1, before the input had ever been TRUE.

On a machine this is the difference between a cooling fan that keeps running after the motor stops and a fan that never starts.

**On-delay timer with dropouts (TON).** Three models made the same mistake on the long TON task. In the first cycle after the input returns, they report ET as one cycle time instead of 0. The prompt states this rule explicitly (ET counts from the cycle in which timing started), and two models followed it in every trial. This is therefore a failure to apply a stated timing rule consistently over 20 or more cycles, not a hidden trick.

**Edge memory inside an IF (R_TRIG).** gpt-oss-20b missed the edge in cycle 6 of the short task. While the IF condition was FALSE, the block was not called, so it still remembered FALSE. When it was called again it saw TRUE, which is a rising edge. The model assumed the edge had already been consumed.

**Counting and arithmetic over long runs.** Qwen made three kinds of mistake here:

- it counted a part that stayed on the sensor more than once (CTU),
- it swapped the SR and RS priorities in the very first cycle,
- it drifted in 16-bit arithmetic (INT) after two additions.

**Consistency.** The failures were mostly the same in all three trials, TOF in particular. That points to a wrong internal model of the block rather than random sampling noise. It matters in practice: an engineer who asks twice gets the same confident, wrong answer twice.

`results/report.md` lists the first wrong cell for every failed answer: the cycle, the variable, the expected value and the value the model gave.

### Limitations

- **Suite size.** There are eight families with one seed per level in the main run, so 16 tasks. The generator supports more seeds (`--seeds 1 2 3`) for a larger suite.
- **Simulator coverage.** The simulator implements the subset of IEC 61131-3 that the tasks use. It is not a full SCL interpreter. Each family runs, in Python, the same logic that its SCL text describes.
- **Timer convention.** Timer semantics follow one explicit convention: ET counts from the cycle in which timing started. Real PLCs differ slightly in how they sample the clock. Because the prompt states the convention, the answer is still unique.
- **Free tiers.** Free-tier quotas left some cells with fewer than 3 trials. Results also depend on the model versions available at the time of the run.

## 8. Prior work and sources

- **IEC 61131-3**, *Programmable controllers, Part 3: Programming languages* (International Electrotechnical Commission). This is the source for the behaviour of TON, TOF, R_TRIG, CTU, SR and RS, for the Structured Text syntax and for 16-bit INT. Vendor manuals for SCL (Structured Control Language) describe the same standard blocks.
- **Existing benchmarks.** No existing benchmark, dataset or third-party code was used. As far as I know, general code benchmarks such as HumanEval and MBPP test writing code in general-purpose languages. They do not test simulating PLC programs over many scan cycles with stateful function blocks. LLM4PLC and other work on LLMs for PLC code focus on *generating* PLC code. This eval instead tests whether a model can *trace the behaviour* of existing code, which is what review and debugging require.
- **Metrics.** pass@k comes from the HumanEval paper (Chen et al., 2021, *Evaluating Large Language Models Trained on Code*). The stricter pass^k ("all k trials correct") follows its use in τ-bench (Yao et al., 2024) to measure consistency.
- **Original work.** All tasks, the simulator, the grader and the tests are my own original work, written for this eval.
