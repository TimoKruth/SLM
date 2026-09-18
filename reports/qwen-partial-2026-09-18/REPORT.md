# Qwen comparison — user-stopped partial evaluation

Stopped at the user’s request on 18 September 2026 at 22:49:18 CEST after 510/1,267 tasks (40.3%). The controller, owned Ollama server and runner exited; STOP remains present. No restart or further inference. The second model (`qwen3.8:27b`) never started.

The controller records a closed HTTP connection because the stop watchdog terminated the owned server during an in-flight request. This was the requested shutdown, not evidence of a preceding spontaneous model failure. Only saved, completed responses are analyzed.

## Matched partial results

Local model: `batiai/qwen3.6-27b:q4`. Same 510 task identities and original frozen scorer as the saved SLM outputs. Of these, 414 have correctness scores and 96 are unscored for correctness.

| Fixed scorer, identical observed subset | Correct / scored | Rate |
| --- | ---: | ---: |
| Qwen | 40/414 | 9.7% |
| SLM final checkpoint | 81/414 | 19.6% |

Paired outcomes: Qwen alone correct on 21; SLM alone correct on 62. These are descriptive scores on the observed subset, **not full-suite scores or a model-capability ranking**. Do not compare Qwen’s partial rate against the SLM’s full-suite 28.2%.

Tasks are ordered by source: 16 source blocks finished and MATH stopped at 29/32. Only 17/46 held-out sources were reached; this prefix is not a representative random sample. No family-wide or full-suite estimates are reported.

## Why the apparent scores are misleading

Inspection of the first two outputs in nine sources found a mismatch between conversational answers and strict scoring. ANLI, ARC and CB examples contain correct explicit conclusions plus explanations but receive zero because the scorer expects a bare label or exact answer. Some prompts specify labels but do not enforce answer-only output; other sources expect dataset-specific final markers without stating that output contract. The SLM trained on those dataset answer formats, while Qwen received only the original task text and a neutral system message. Thus identical prompts and scoring do not isolate reasoning capability.

This is a qualitative diagnostic, not a manually corrected score. Some inspected answers are substantively wrong as well. Original scores remain unchanged; no answer extraction tuned to references or repaired answers were used.

Qwen reached its 256-native-token cap on **178/510 answers (34.9%)**: AQuA 32/32, GSM8K 29/32, LogiQA 31/32 and MATH 29/29 observed tasks. These zeros cannot distinguish unfinished solutions, output-format failures and reasoning errors. Thinking was disabled, but the ordinary answer channel still contained explanations.

BoolQ is a useful narrow observation: Qwen 30/32 versus SLM 17/32, with no Qwen cutoffs and a yes/no prompt compatible with scoring. This does not establish broader superiority. Code and open-generation tasks in this subset do not have functional correctness scores.

## Source details

| Source | Evaluated / selected | Scored | Qwen correct | SLM correct | Qwen cutoffs | SLM cutoffs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| anli | 32/32 | 32 | 0 | 15 | 5 | 0 |
| apps | 32/32 | 0 | — | — | 7 | 9 |
| aqua_rat | 32/32 | 32 | 0 | 3 | 32 | 16 |
| arc | 32/32 | 32 | 0 | 5 | 12 | 0 |
| boolq | 32/32 | 32 | 30 | 17 | 0 | 0 |
| cb | 8/8 | 8 | 0 | 7 | 0 | 0 |
| code_contests | 32/32 | 0 | — | — | 20 | 7 |
| commonsenseqa | 32/32 | 32 | 0 | 4 | 2 | 0 |
| copa | 25/25 | 25 | 0 | 3 | 0 | 0 |
| cosmos_qa | 32/32 | 32 | 0 | 7 | 3 | 0 |
| dream | 32/32 | 32 | 0 | 5 | 0 | 0 |
| drop | 32/32 | 32 | 2 | 1 | 1 | 0 |
| go_emotions | 32/32 | 32 | 8 | 12 | 0 | 0 |
| gsm8k | 32/32 | 32 | 0 | 0 | 29 | 6 |
| hellaswag | 32/32 | 0 | — | — | 7 | 5 |
| logiqa | 32/32 | 32 | 0 | 2 | 31 | 0 |
| math | 29/32 | 29 | 0 | 0 | 29 | 25 |

## Runtime and verification

Total controller time: 2.18 hours. Completed requests generated 74,011 native tokens at 10.85 tokens/second during decoding. Prompt processing: 983.1s; decoding: 6821.6s; per-request loading overhead combined: 0.639s. Initial neutral smoke loading was separate. The model remained resident; requests were sequential.

All 51 frozen comparison input hashes reverified after stop. All saved Qwen responses reproduced their stored scores; the full saved SLM baseline rescored identically and the compared prefix matched task identity/order. Controller PARTIAL.json matched independent aggregation. Suite, checkpoint and response hashes are in aggregate.json. No weights, raw prompts or generated answers are included here.

## Recommended next comparison

Before spending more inference time, define a reference-independent answer contract per task (bare label/choice, numeric final answer or explicit final marker) and test its parser with synthetic correct/incorrect/ambiguous examples. Validate prompt/scorer compatibility on development data. Apply any revised protocol symmetrically to both models and retain this original result unchanged. Because confirmation outputs have now informed protocol changes, further measurements on this suite are exploratory; reserve a separately audited untouched holdout for a final claim.

Use longer output budgets where explanations are required and record truncation separately. Qwen can use a larger answer budget without retraining; the SLM is still bounded by its 1,024-token total context. Measure runtime on development tasks before setting a full-suite budget. No new training is needed to diagnose answer-format and generation-budget effects. No new run, extension or model adoption is authorized by this report.

Other limitations: local model tags are not independently verified upstream provenance; Qwen pretraining exposure is unknown; models differ greatly in parameter count, tokenizer and native wrappers. Equal native token limits are not equal text length or compute. Internal proxies are not official benchmark results.
