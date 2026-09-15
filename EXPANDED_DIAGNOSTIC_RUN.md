# Expanded saved-checkpoint diagnostic evaluation

User authorization: “Do it as proposed.” Scope: evaluate the saved parent plus baseline A and cosine D, both data orders, at the 50M snapshots and final training endpoints. Nine evaluations; no additional training or automatic model adoption.

Started **15 September 2026 at 09:38:58 Europe/Berlin**. Hard deadline **11:34:56 Europe/Berlin**, conservatively charging preparation from 09:34:56 to the two-hour cap. Each evaluation receives at most 600 seconds plus 30 seconds of process reserve, always bounded by the overall deadline. No automatic retry, restart or extension.

Run directory: `runs/expanded-checkpoint-diagnostic-2026-09-15/` in the main workspace. `status.json` is authoritative for evaluation, `analysis-status.json` for the final CPU analysis. The prepared diagnostic suite has 1,360 tasks, including 1,280 correctness-scored groups from 20 sources; five further sources remain outside correctness scoring. All 25 sources are the same as the earlier confirmation set. These are already-opened groups, not fresh confirmation or external transfer.

## Execution and integrity

- Frozen evaluation code: `/Users/timokruth/Projekte/SLM-expanded-diagnostic`, commit `b5f0b26`, based on the original comparison code `4c30196`. Only the evaluation controller and its tests were added. All training/model/scoring code retains the original numerical implementation.
- Every checkpoint is independently copied, with its original tokenizer/configuration and a private latest-checkpoint pointer. Monitoring output goes into those new copies, not the original runs. There are 202 frozen input hashes covering source/copy files and tracked execution code.
- Each GPU evaluation uses `run_slm.py --module slm.broad_eval --monitoring light`, original strict scoring, 256 generated tokens, full reference loss and the latest pointer to the selected copy. An exclusive inherited GPU lease covers the serial pass; only owned child process groups can be stopped by the controller.
- The focused hardware comparison was already paused at `requested_stop`; no recognized GPU job or lease holder was active at admission. It was not resumed by this task.
- The Mac was on battery at admission. Power conditions are recorded for every checkpoint. This pass compares quality, not throughput. Existing power settings and PowerWatch are unchanged. A `caffeinate -i -w` process prevents idle sleep only while this controller exists.
- STOP or controller termination stops owned evaluation work. No historical STOP is removed. To cancel this pass: create `runs/expanded-checkpoint-diagnostic-2026-09-15/STOP`.

## Automatic final report

CPU report code: `experiments/report_expanded_diagnostic.py`, launch commit `12307b9` in `/Users/timokruth/Projekte/SLM-diagnostic-report`. It waits for all nine successful evaluations, then checks every generated answer against the frozen scorer and reproduces source counts and family macros.

The report includes D−A at both endpoints, A/D versus parent, and final-minus-50M trajectories. Paired uncertainty uses 5,000 group resamples within source with the same resample weights across data orders; source/family macro weights are preserved. Data orders are not independent model initializations. Source-composition sensitivity and source/family diagnostics remain separate.

Output after successful completion: `analysis/REPORT.md`, `analysis/analysis.json` and `analysis/provenance.json` inside the new run. Raw generations remain local. A paused/incomplete pass produces no complete comparison report. No fresh holdout is opened and no old acceptance rule is replaced.

## Checks

32 controller, GPU-lease and project-launcher tests passed before launch. Eleven targeted controller/report/paired-analysis tests passed before starting the report watcher. Complete task and reference-loss coverage, zero context-limit failures, expected suite/weight hashes and final input integrity are required. Historical input files are not modified.

## Completed result

All nine evaluations completed at **09:53:04 Europe/Berlin**; the automatic answer-level verification and report completed at **09:53:10**. The complete pass consumed 1,094.063 seconds including preparation and automatic analysis (about 18m14s), well within the two-hour cap; the evaluations themselves finished at 1,088.896 seconds. All 202 frozen input hashes remained unchanged. All 12,240 generated answers were validated against the original scorer; no failed evaluation, new training or model adoption.

| Model / endpoint | Order 0 | Order 1 | Mean macro accuracy |
|---|---:|---:|---:|
| Original parent | 26.87% | same checkpoint | 26.87% |
| A at 50M | 25.74% | 25.69% | 25.71% |
| D at 50M | 25.02% | 24.98% | 25.00% |
| A final | 27.04% | 23.87% | 25.45% |
| D final | 26.25% | 25.62% | 25.93% |

Cosine minus baseline is **−0.72pp** at matched 50M snapshots (exploratory 95% interval −1.75 to +0.32pp), and **+0.48pp** at final time endpoints (−1.18 to +2.10pp). Its final advantage again changes sign between data orders (−0.79 / +1.75pp). Both final cosine checkpoints score below the parent; the mean difference is −0.93pp with interval −2.84 to +0.98pp, which does not establish a reliable deficit or improvement. No replacement is justified by these diagnostic results.

Final A/D models improve some entailment, science and math point estimates but lose reading/extraction, commonsense and dialogue accuracy relative to the parent. For example, final mean reading/extraction falls by 3.91pp for A and 3.32pp for D; dialogue falls by 6.25pp and 4.69pp. These descriptive capability tradeoffs do not establish a causal forgetting mechanism. Mathematics remains weak: the parent solves 4/192 tasks; final A solves 7 and 6, final D 7 and 4. Repetition and output-cap flags remain frequent. Lower cosine reference loss (final mean 1.4401 versus parent's 1.4687) does not translate into higher overall free-answer accuracy.

Recommended sequence remains: retain the original parent as the comparison anchor, keep LR 3e-5 as the configuration reference, correct confirmed references in a new version and fill fresh-confirmation coverage before another targeted training experiment. The already-opened diagnostic suite cannot certify a winner. Existing and new scores from different suites must not be compared as a learning curve.

Versioned evidence: [full report](results/2026-09-15/expanded-checkpoint-diagnostic/REPORT.md), [metrics and paired intervals](results/2026-09-15/expanded-checkpoint-diagnostic/analysis.json), [completion](results/2026-09-15/expanded-checkpoint-diagnostic/completion.json). Raw generations and original model copies remain local. No remote push.
