# Parameter comparison: answer errors and evaluation coverage

Analysis dated 15 September 2026. CPU-only inspection of the completed second learning-rate block; no training, new model evaluation, metric replacement, or model adoption. The frozen historical inputs and scores remain unchanged.

## What was checked

All **13,152 saved generations in 33 evaluations** were rescored using the three pure scoring functions extracted from the frozen campaign's `slm/broad_eval.py`. No training backend was imported. Every task/reference pairing, source count, correctness result, and reported family macro was checked. Search checkpoints at 15M, 50M and time-end, final confirmation, and the unchanged parent's confirmation are included. Conditions were read for the campaign and all eight trials. Provenance records **81 input hashes**, checked again after analysis.

The detailed aggregate results are in [analysis.json](results/2026-09-15/parameter-error-analysis/analysis.json). Raw answers and review extracts remain local in `runs/parameter-error-analysis-2026-09-15-verified/`. Thirteen targeted task reviews are summarized without raw task text in [manual-review.json](results/2026-09-15/parameter-error-analysis/manual-review.json). These were chosen to explain changes and surface flags, not to estimate the prevalence of reference errors in the dataset.

## Errors are not primarily a formatting-only problem

Final confirmation, pooling the two fixed data orders (320 scored responses per configuration):

| Configuration | Incorrect responses | Incorrect with surface flags | Incorrect without those flags |
|---|---:|---:|---:|
| A: constant 3e-5 | 232 | 42 | 190 |
| B: constant 3e-6 | 239 | 40 | 199 |
| C: constant 1e-4 | 248 | 46 | 202 |
| D: cosine | 231 | 33 | 198 |

Surface flags include repeated three-word sequences, exhausting the generation allowance, empty output, an unparseable required final-answer marker, or an unparseable reference. Flags overlap. Their absence does not prove a reasoning error; their presence does not establish that correcting formatting would fix the answer. The recorded `token_limit` means the output reached its cap, not that extra tokens would yield a correct answer.

Mathematics is particularly weak. A gets **0/48** confirmation math responses correct; D gets **2/48**. A has 38 repetition flags, 28 output-cap flags and 31 missing required final-answer formats in those 48 responses; D has 30, 21 and 23. Manual inspection finds arithmetic mistakes and irrelevant loops together with missing/wrong markers. Examples include using the wrong weekly chore counts and adding test scores to sleep hours. A marker change would not repair those calculations.

The targeted semantic checks also find correctly formatted wrong entailment labels and restaurant/hotel confusions. Conversely, one QASC cosine response has a correct final answer with an irrelevant explanation. Final-answer correctness does not establish faithful or correct reasoning.

## Why lower answer loss can accompany worse accuracy

B's mean confirmation answer-loss change versus A is **−0.02253**. Approximately half (**−0.01123**) comes from the five sources excluded from correctness scoring; they are only one fifth of the 25 sources. The remaining scored sources contribute **−0.01130**. Thus the two overall metrics cover different outputs and apply different weighting.

There is also a within-source mismatch: ANLI and SciQ have lower mean reference loss but lower generated-answer accuracy for B. Teacher-forced probability of the reference and correctness of a freely generated answer are different measurements. Only source-level loss is saved here, so loss cannot be attributed to a particular erroneous response.

## Reference and parser review

Two newly flagged AQuA confirmation tasks are excluded from the *new diagnostic selection*:

- `32965`: assigning four distinct boys to three distinct nonempty rooms yields `3^4 − 3×2^4 + 3 = 36`, but the reference gives 24 and none of the choices gives 36.
- `79813`: the stated investment ratios imply 35 months of participation in an annual-profit scenario with withdrawal within the year; the task is internally inconsistent.

Removing those two tasks in a separate retrospective sensitivity calculation leaves all final confirmation macro scores unchanged: every configuration failed them and had zero correctness on the remaining AQuA confirmation tasks as well. Historical scores and acceptance decisions are preserved.

An automatic audit found **four** wrong-scored AQuA responses whose explicit option letter agreed with the reference. Manual review found one final-value formatting discrepancy (`4%` versus `+4%` in r1-A at 15M), but three conflicting numeric answers behind matching letters. Accepting the letter alone would create false positives. The one equivalent final value does not validate its explanation. No permissive parser was substituted.

## Uncertainty in the parameter effects

Paired percentile bootstrap, 5,000 draws with seed 20260915. Task groups are resampled within each source; sources are averaged within each family and the six scored families are equally weighted. The **same resampled groups are used for both data orders**, which are then averaged. The effective task sample is 160 unique scored confirmation groups, not 320 independent tasks or two independent model initializations.

| Comparison against A | Mean confirmation change | Exploratory 95% interval |
|---|---:|---:|
| B | −3.00 pp | −7.08 to +0.76 pp |
| C | −3.51 pp | −8.13 to +1.34 pp |
| D | +0.24 pp | −4.03 to +4.44 pp |

At the equal 50M-token search checkpoint, D averages **+0.06 pp**, with an interval of **−2.38 to +2.55 pp**. The apparent cosine advantage is not stable enough to justify replacement. These exploratory intervals do not replace the preregistered gates and are not proof of equivalence or no effect.

A secondary sensitivity analysis also resamples sources within each fixed family. D's confirmation interval becomes **−5.05 to +5.66 pp**. This asks about source composition, not additional independent training runs. No multiple-comparison adjustment or claim about new model initializations is made. Zero-width intervals in all-failure subsets reflect an uninformative observed sample, not certainty about future tasks. Per-order and per-family intervals are retained in the JSON.

## Stronger evaluation prepared

The original confirmation has 8 groups per source. A single DREAM response changes its overall macro by **2.083 pp**. The prepared diagnostic suite has **1,360 tasks: 64 groups for each of the 20 scored sources and 16 for each of the five unscored sources**, maintaining the same 25-source coverage. This is **1,280 scored groups**, eight times the previous scored sample. One DREAM response now contributes **0.260 pp**.

All selected diagnostic groups come from suites of six explicitly completed campaigns, never from another task's prepared but unopened confirmation suite. Selection is deterministic and independent of candidate correctness. There is one task per group, no training-group overlap, known reference issues are excluded, full references fit the 1,024-token context, and each prompt leaves room for all 256 generated tokens. This is an **already-opened diagnostic set**, not fresh confirmation. It is prepared but has not been evaluated on models.

Local preparation: `runs/parameter-evaluation-preparation-2026-09-15-verified/`, with `STOP`, `diagnostic-suite.json`, `coverage-audit.json`, and a metadata-only inventory of remaining fresh candidates. [Coverage audit](results/2026-09-15/parameter-error-analysis/coverage-audit.json) and [evaluation protocol](PARAMETER_EVALUATION_PROTOCOL.md) are versioned.

A matching fresh confirmation set is **not ready**. After excluding existing and reserved suites across local SLM worktrees, training groups and context/reference failures, these sources cannot meet 64 groups each:

| Source | Available fresh groups | Additional groups needed |
|---|---:|---:|
| ARC | 11 | 53 |
| DREAM | 0 | 64 |
| QuaRel | 0 | 64 |
| Quoref | 0 | 64 |

The remaining inventory has 22,258 eligible groups overall, but abundance in other sources cannot fill these coverage gaps without changing the comparison. Some groups were reserved by separate studies, not necessarily already evaluated. This inventory is a dated snapshot, not a cross-process reservation lock; exclusions must be rechecked before future use. Fresh candidate prompts/answers were not manually reviewed and no fresh model scores were generated. Historical inline development-loss exposure remains possible, so even the residual pool is not an untouched external test.

The concrete next data step is an overlap audit of unused original development splits for those four sources, before constructing a new confirmation set. Existing training tasks must not be relabeled as holdout. No new source download was performed here, and the reserved external final benchmarks remain unopened.

## Reproduction and validation

From the project root, using the existing environment:

```sh
.venv/bin/python experiments/analyze_parameters.py \
  --run runs/long-horizon-round2-resume-2026-09-14 \
  --output runs/parameter-error-analysis-new \
  --frozen-scorer /Users/timokruth/Projekte/SLM-long-round2/slm/broad_eval.py \
  --reviews results/2026-09-15/parameter-error-analysis/manual-review.json

.venv/bin/python experiments/prepare_parameter_evaluation.py \
  --project . --output runs/parameter-evaluation-preparation-new \
  --scorer /Users/timokruth/Projekte/SLM-long-round2/slm/broad_eval.py \
  --reviews results/2026-09-15/parameter-error-analysis/manual-review.json

.venv/bin/python -m pytest tests/test_parameter_analysis.py -q
```

The preparer uses the verified analysis at the documented local path and scans the current suite inventory, so a later run can legitimately find fewer fresh groups. Both scripts require a new output directory. Five tests cover paired data-order dependence, equal source weighting, group clustering, diagnostic flag overlap and deterministic group selection/exclusion. Aggregate exports omit raw answers, new task text and systemwide process logs. No GPU job was started.
