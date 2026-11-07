# ScanCycle Eval results

166 graded answers, 64 model-task pairs, 133 API calls failed or were cut off by an output limit; they are excluded, not counted as wrong.

pass@1 = share of single answers that are fully correct.
pass^k = share of tasks where ALL k trials are fully correct.
cells = mean share of correct table cells (partial credit).

| model | pass@1 | pass^k | cells | cost USD |
|---|---|---|---|---|
| gemini:gemini-3.5-flash | 100% | 100% | 100% | 0.000 |
| gemini:gemini-3.8-flash | 100% | 100% | 100% | 0.000 |
| gemini:gemma-4-31b-it | 81% | 75% | 88% | 0.000 |
| groq:openai/gpt-oss-120b | 86% | 87% | 90% | 0.000 |
| groq:openai/gpt-oss-20b | 68% | 62% | 83% | 0.000 |
| groq:qwen/qwen3.8-27b | 7% | 0% | 59% | 0.000 |

## pass@1 by task family

| family | gemini:gemini-3.5-flash | gemini:gemini-3.8-flash | gemini:gemma-4-31b-it | groq:openai/gpt-oss-120b | groq:openai/gpt-oss-20b | groq:qwen/qwen3.8-27b |
|---|---|---|---|---|---|---|
| ctu_edges | 2/2 | - | 6/6 | 6/6 | 4/4 | 0/2 |
| edge_inside_if | 4/4 | 3/3 | 6/6 | 6/6 | 4/5 | 0/2 |
| int_overflow | 3/3 | - | 6/6 | 5/5 | 6/6 | 1/2 |
| sr_rs_priority | 3/3 | 3/3 | 6/6 | 5/5 | 5/5 | 0/1 |
| statement_order | 3/3 | 1/1 | 6/6 | 3/3 | - | 0/1 |
| step_chain | 2/2 | - | 5/5 | 6/6 | 2/2 | - |
| tof_restart | 3/3 | - | 0/6 | 0/6 | 0/4 | 0/3 |
| ton_flicker | 4/4 | - | 3/6 | 6/6 | 0/5 | 0/3 |

## First wrong cell per failed answer

- `groq:openai/gpt-oss-120b` `tof_restart_1` trial 1: cycle 1: bFan expected True, got False
- `groq:openai/gpt-oss-120b` `tof_restart_1` trial 2: cycle 1: bFan expected True, got False
- `groq:openai/gpt-oss-120b` `tof_restart_1` trial 3: cycle 1: bFan expected True, got False
- `groq:openai/gpt-oss-20b` `ton_flicker_hard_1` trial 1: cycle 3: fbDelay.ET expected 0, got 10
- `groq:openai/gpt-oss-20b` `ton_flicker_hard_1` trial 3: cycle 3: fbDelay.ET expected 0, got 10
- `groq:openai/gpt-oss-120b` `tof_restart_hard_1` trial 2: cycle 2: bFan expected True, got False
- `groq:openai/gpt-oss-120b` `tof_restart_hard_1` trial 3: cycle 2: bFan expected True, got False
- `groq:openai/gpt-oss-120b` `tof_restart_hard_1` trial 1: cycle 2: bFan expected True, got False
- `groq:qwen/qwen3.8-27b` `ton_flicker_hard_1` trial 1: cycle 3: fbDelay.ET expected 0, got 10
- `groq:qwen/qwen3.8-27b` `ton_flicker_hard_1` trial 2: cycle 3: fbDelay.ET expected 0, got 10
- `groq:qwen/qwen3.8-27b` `ton_flicker_hard_1` trial 3: cycle 3: fbDelay.ET expected 0, got 10
- `groq:qwen/qwen3.8-27b` `sr_rs_priority_hard_1` trial 2: cycle 1: bLampSR expected True, got False
- `groq:openai/gpt-oss-20b` `tof_restart_hard_1` trial 2: cycle 2: bFan expected True, got False
- `groq:qwen/qwen3.8-27b` `edge_inside_if_hard_1` trial 1: cycle 21: nCount expected 3, got 4
- `groq:qwen/qwen3.8-27b` `edge_inside_if_hard_1` trial 2: cycle 4: nCount expected 1, got 0
- `groq:qwen/qwen3.8-27b` `ctu_edges_hard_1` trial 2: cycle 4: nParts expected 1, got 2
- `groq:qwen/qwen3.8-27b` `statement_order_hard_1` trial 3: cycle 12: bAlarm expected False, got True
- `groq:qwen/qwen3.8-27b` `ctu_edges_hard_1` trial 3: cycle 9: nParts expected 0, got 1
- `groq:qwen/qwen3.8-27b` `int_overflow_hard_1` trial 3: cycle 2: nTotal expected 20000, got 15648
- `groq:qwen/qwen3.8-27b` `tof_restart_hard_1` trial 1: cycle 1: bFan expected False, got True
- `groq:qwen/qwen3.8-27b` `tof_restart_hard_1` trial 2: cycle 2: bFan expected True, got False
- `groq:qwen/qwen3.8-27b` `tof_restart_hard_1` trial 3: cycle 4: bFan expected True, got False
- `gemini:gemma-4-31b-it` `ton_flicker_hard_1` trial 1: cycle 3: fbDelay.ET expected 0, got 10
- `gemini:gemma-4-31b-it` `ton_flicker_hard_1` trial 3: cycle 3: fbDelay.ET expected 0, got 10
- `gemini:gemma-4-31b-it` `tof_restart_hard_1` trial 1: cycle 2: bFan expected True, got False
- `gemini:gemma-4-31b-it` `tof_restart_hard_1` trial 3: cycle 2: bFan expected True, got False
- `gemini:gemma-4-31b-it` `tof_restart_hard_1` trial 2: cycle 2: bFan expected True, got False
- `groq:openai/gpt-oss-20b` `edge_inside_if_1` trial 1: cycle 6: nCount expected 1, got 0
- `groq:openai/gpt-oss-20b` `ton_flicker_1` trial 2: cycle 3: fbDelay.ET expected 0, got 10
- `groq:openai/gpt-oss-20b` `ton_flicker_1` trial 1: cycle 3: fbDelay.ET expected 0, got 10
- `groq:openai/gpt-oss-20b` `ton_flicker_1` trial 3: cycle 3: fbDelay.ET expected 0, got 10
- `groq:openai/gpt-oss-20b` `tof_restart_1` trial 2: cycle 1: bFan expected True, got False
- `groq:openai/gpt-oss-20b` `tof_restart_1` trial 3: cycle 1: bFan expected True, got False
- `groq:openai/gpt-oss-20b` `tof_restart_1` trial 1: cycle 1: bFan expected True, got False
- `gemini:gemma-4-31b-it` `ton_flicker_1` trial 2: cycle 3: fbDelay.ET expected 0, got 10
- `gemini:gemma-4-31b-it` `tof_restart_1` trial 1: cycle 1: bFan expected True, got False
- `gemini:gemma-4-31b-it` `tof_restart_1` trial 3: cycle 1: bFan expected True, got False
- `gemini:gemma-4-31b-it` `tof_restart_1` trial 2: cycle 1: bFan expected True, got False
