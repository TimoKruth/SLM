# Conservative FP32 study: analysis of saved results

Completed analysis on 15 September 2026. The optimization is promising at the measured equal-update checkpoint, but the existing evidence does not justify adopting it across longer training. No training, inference or GPU experiment was started; historical study files and acceptance gates remain unchanged.

At 8,192 identical updates there were **zero correct-to-incorrect changes and two incorrect-to-correct changes across 1,596 scored comparisons** (532 distinct tasks, each assessed under three data orders). All paired token counts and batch-exposure hashes match. This supports preservation of the measured answer accuracy at that checkpoint. It is not 1,596 independent tasks or proof of unchanged general capabilities.

Generated text was not identical: 109 of 2,016 paired outputs changed across both suites and three orders, including unscored outputs. The search/confirmation reference-loss differences were +0.029% / −0.008%, and extraction token-F1 was identical at matched exposure. FP32 scheduling can therefore preserve the tested answer scores without being bit-for-bit identical.

| Endpoint | Scored comparisons across orders | Correct → incorrect | Incorrect → correct | Family-weighted accuracy difference |
|---|---:|---:|---:|---:|
| matched-search | 912 | 0 | 1 | +0.116 pp |
| matched-confirmation | 684 | 0 | 1 | +0.154 pp |
| wall-search | 912 | 33 | 33 | +0.058 pp |
| wall-confirmation | 684 | 36 | 21 | -2.508 pp |

The equal-time confirmation decline is an observed result: 36 regressions and 21 gains, for 15 fewer correct answers across 684 scored comparisons. Its family-weighted difference is −2.508 percentage points, with the original task-bootstrap interval **−6.251 to +0.733 pp**. This interval includes zero; it does not establish a causal 2.5-point capability loss. The search set has 33 regressions and 33 gains; its small nonzero macro difference comes from family weighting.

| Data order | Search difference at equal time | Confirmation difference at equal time | Confirmation regressions / gains |
|---|---:|---:|---:|
| 1 | -1.128 pp | -3.009 pp | 12 / 7 |
| 2 | +1.302 pp | -4.398 pp | 15 / 5 |
| 3 | +0.000 pp | -0.116 pp | 9 / 9 |

The strongest confirmation contributors are below. Counts are repeated task/order comparisons, not independent examples. Contributions include gains within the source and add to the overall family-weighted difference.

| Source | Regressions | Gains | Contribution to overall confirmation difference |
|---|---:|---:|---:|
| dream | 4 | 2 | -0.926 pp |
| winogrande | 7 | 2 | -0.579 pp |
| gsm8k | 3 | 0 | -0.463 pp |
| qasc | 3 | 0 | -0.347 pp |
| arc | 2 | 0 | -0.231 pp |
| boolq | 2 | 0 | -0.231 pp |
| aqua_rat | 2 | 1 | -0.154 pp |
| sciq | 1 | 0 | -0.116 pp |
| commonsenseqa | 0 | 1 | +0.116 pp |
| social_i_qa | 1 | 2 | +0.116 pp |
| anli | 1 | 2 | +0.154 pp |
| snli | 2 | 3 | +0.154 pp |

Two particular tasks regress in **all three** orders: one DREAM dialogue question and one WinoGrande reference-resolution question. Four other tasks regress in two orders. Inspection of the saved prompts and answers confirms that the two persistent cases are substantive wrong answers, not merely formatting differences. Raw case reviews are retained locally in `runs/conservative-analysis-2026-09-15-verified/repeated_case_review.json`.

For the persistent WinoGrande case, both variants are wrong at 8,192 updates; the baseline later becomes correct in all three orders while the candidate stays wrong. For the dialogue case, both variants are initially correct in the first order and wrong in the other two; only the baseline is correct in all three final evaluations. Thus “the optimization forgot previously correct answers” does not fully describe the pattern: some differences are missed later improvements.

Family scores are coarse here. Confirmation has only **12 distinct dialogue tasks**; one changed answer moves that order’s dialogue score by 8.33 pp and overall macro score by 1.39 pp. The family margin is 2.5 pp. Search also fails per-order family checks despite its nearly unchanged overall average. Confirmation order 3 is only −0.116 pp overall but fails its entailment-family margin. These are expected consequences of the prespecified strict gates, not evidence of a reporting bug; the gates were not relaxed after seeing results.

All six long trials continued beyond the only measured common checkpoint, and the faster variant consumed additional data:

| Order | Baseline final updates | Candidate final updates | Extra updates | Extra nonpadding tokens | Speed ratio at 8,192 updates | Equal-time token-throughput ratio |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 11,278 | 11,864 | 586 | 1,061,768 | 1.0284× | 1.0521× |
| 2 | 12,285 | 12,580 | 295 | 535,756 | 1.0217× | 1.0241× |
| 3 | 12,295 | 12,572 | 277 | 502,050 | 1.0220× | 1.0226× |

The median time-to-identical-exposure speedup is **2.20%**, saving approximately 29 seconds over a 22–25 minute segment; the equal-time throughput median is 2.41%. The first pair’s 5.21% full-run gain is larger than its 2.84% matched-segment gain, so using the best pair as the expected benefit would be misleading. All timings include the online sampling and monitoring present in the experiment.

The following within-run changes show why extra training cannot be assumed to improve these small accuracy suites monotonically. They describe movement from 8,192 updates to each run’s own final checkpoint; the final update counts differ.

| Suite / order | Baseline accuracy: matched → final | Candidate accuracy: matched → final |
|---|---:|---:|
| search / 1 | 24.65% → 23.26% | 24.65% → 22.14% |
| search / 2 | 22.83% → 21.18% | 23.18% → 22.48% |
| search / 3 | 24.22% → 23.78% | 24.22% → 23.78% |
| confirmation / 1 | 27.31% → 28.70% | 27.78% → 25.69% |
| confirmation / 2 | 25.35% → 30.09% | 25.35% → 25.69% |
| confirmation / 3 | 22.34% → 24.54% | 22.34% → 24.42% |

Search accuracy drops from matched to final in both variants in all orders. Confirmation improves in all three baseline runs and in two of three candidate runs. At equal time, the candidate’s mean reference loss is slightly better on both suites (search −0.206%, confirmation −0.144%), while confirmation extraction F1 falls from 0.1431 to 0.1287. Reference loss and free-answer correctness therefore do not move together reliably. No general overtraining explanation follows from these mixed results.

The saved evaluations do **not** compare the final baseline and candidate at the same later update count. Consequently they cannot separate the effects of extra updates/data from small numerical differences accumulating after the matched checkpoint. The common 8,192-update result is encouraging; extrapolating it to 12,000+ updates would be an inference that still needs testing.

All evaluation summaries were complete, and none reported an unparseable reference. Candidate confirmation outputs hit the 192-token limit 120 times versus 113 for baseline at equal time, across 864 generated outputs; this small aggregate change does not explain the two persistent short-answer errors. Correctness covers **304/384 search tasks and 228/288 confirmation tasks**, from 19 sources in six families. Apps, Code Contests, WikiSQL, HellaSwag and PIQA are excluded from this correctness aggregate; their reference loss and limited text diagnostics do not establish functional code/SQL or narrative quality.

All recorded trial starts used mains power and unchanged power settings, with at least 43.35 GiB available memory. Five of six intervals contain nonzero **system-wide swap-in counter increments** (baseline/candidate: 76/4, 30/16, 40/0), while all show zero swap-out increments. This violates the original zero-swap-activity gate. It does not demonstrate memory pressure caused by this training, identify a responsible process, or show that paging explains the speed gain. No counter-to-byte conversion or retrospective gate change was made.

My recommendation is to retain the production FP32 baseline and use the next small confirmation budget for a **later common update endpoint**, around 12,000 updates, across the same paired data orders. Measure time to that endpoint and evaluate both variants there. Reuse the current tasks only as explicitly diagnostic checks; use fresh group-disjoint tasks, with more dialogue and other sparsely sampled family tasks, for a new confirmation claim. Define operating-condition rules before running. This directly tests the unresolved late-training question; another broad search or another early-only 8,192-update comparison would be less informative. This is a recommendation, not a prepared or started run.

Reproducibility: `experiments/analyze_conservative.py` uses only the Python standard library. It independently reconstructs all 26 saved evaluation summaries, reproduces all four endpoint and per-order macro deltas, checks that source contributions sum correctly, verifies paired exposure hashes and checks 76 input-file hashes before/after analysis. Detailed machine-readable results and task-level changes are local under `runs/conservative-analysis-2026-09-15-verified/`; historical results are untouched. Re-run with a fresh output directory:

```sh
.venv/bin/python experiments/analyze_conservative.py \
  --run /Users/timokruth/Projekte/SLM-conservative-recovery/runs/conservative-fp32-recovery-2026-09-15 \
  --output runs/conservative-analysis-recheck
```
