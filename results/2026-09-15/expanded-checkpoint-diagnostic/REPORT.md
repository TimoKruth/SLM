# Expanded checkpoint diagnostic results

Already-opened diagnostic groups, exploratory evidence. Fixed parent and two data orders; not fresh confirmation, independent initializations or external transfer. Surface flags overlap; no causal attribution from flags alone.

| Checkpoint | Additional tokens | Accuracy (family macro) | Correct / scored | Answer loss |
|---|---:|---:|---:|---:|
| parent | parent | 26.87% | 341 / 1280 | 1.4687 |
| r0-A-50M | 50000683 | 25.74% | 336 / 1280 | 1.4729 |
| r0-D-50M | 50000683 | 25.02% | 329 / 1280 | 1.4567 |
| r1-A-50M | 50000289 | 25.69% | 326 / 1280 | 1.4655 |
| r1-D-50M | 50000289 | 24.98% | 323 / 1280 | 1.4490 |
| r0-A-final | 126001643 | 27.04% | 349 / 1280 | 1.4608 |
| r0-D-final | 82908374 | 26.25% | 341 / 1280 | 1.4395 |
| r1-A-final | 88126776 | 23.87% | 310 / 1280 | 1.4843 |
| r1-D-final | 115507385 | 25.62% | 330 / 1280 | 1.4406 |

| Paired comparison | Order 0 (pp) | Order 1 (pp) | Mean (pp) | Exploratory 95% interval (pp) |
|---|---:|---:|---:|---:|
| D-A-50M | -0.72 | -0.71 | -0.72 | -1.75 to +0.32 |
| A-parent-50M | -1.13 | -1.18 | -1.15 | -3.37 to +0.92 |
| D-parent-50M | -1.85 | -1.89 | -1.87 | -3.90 to +0.17 |
| D-A-final | -0.79 | +1.75 | +0.48 | -1.18 to +2.10 |
| A-parent-final | +0.17 | -3.00 | -1.41 | -3.61 to +0.72 |
| D-parent-final | -0.62 | -1.25 | -0.93 | -2.84 to +0.98 |
| A-final-minus-50M | +1.30 | -1.82 | -0.26 | -1.79 to +1.29 |
| D-final-minus-50M | +1.23 | +0.64 | +0.94 | -0.45 to +2.37 |

All nine evaluations and 12,240 saved generations validated with the frozen scorer. The 50M snapshots are nearest-update snapshots; final checkpoints contain unequal additional tokens.

Intervals use 5,000 paired group resamples within source, keeping both data orders paired and preserving source/family macro weights. Parent comparisons reuse the same parent responses across orders. No new acceptance threshold or automatic model adoption.

Per-source/family diagnostics, gains/losses, and source-composition sensitivity intervals are in analysis.json. This diagnostic does not repair the missing fresh-confirmation coverage.
