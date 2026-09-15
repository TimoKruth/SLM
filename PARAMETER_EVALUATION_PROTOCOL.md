# Parameter evaluation protocol: diagnostic preparation

Version 1, 15 September 2026. Scope: stronger evaluation for the existing 27.3M FP32 comparison. This is not a training plan or a launch authorization. Existing campaign metrics and acceptance gates remain unchanged.

## Prepared diagnostic set

- Same 25 sources as the round-2 confirmation, including the same 20 correctness-scored sources in six families. 64 unique groups per scored source; 16 per unscored source. Total 1,360 tasks, 1,280 correctness-scored.
- Candidate selection uses only original v4 `dev` records from already-consumed suites of completed campaigns. One variant per group, chosen by a fixed hash salt, without looking at configuration scores. All original `train` groups excluded.
- Reference issue exclusions are recorded in the manual review, plus the earlier project's reference findings. No changes to historical data. Context is checked both for the complete reference and for prompt plus 256 generation tokens, using the original tokenizer.
- The local suite is STOP-guarded and has no model outputs. Its SHA-256 and per-source coverage are in the archived audit. This set can support diagnosis and future selection; it cannot serve as fresh confirmation.

## Metrics and completion checks

Primary descriptive metric: average source correctness within each scored family, then average across the six families. Always show source/family denominators, raw correct counts, paired task transitions, and the maximum weight of one task. Keep unscored outputs outside this metric; syntax validity and SQL text match are not functional correctness.

Keep the frozen strict scorer as the comparable reference. Show surface diagnostics separately: parseability, stop reason, output length and repetition. If an alternative final-answer normalization is later implemented, give it a distinct version and report it as sensitivity; preserve option-text conflicts and test wrong numeric answers behind correct letters. Never infer that parsing a final answer validates its explanation.

Report answer loss separately at source and family level, including the contribution of sources excluded from correctness scoring. A loss improvement is not an answer-quality acceptance criterion by itself.

Reject incomplete evaluation: expected task identities must match exactly, no duplicated groups, full generation/reference-loss counts, no deadline exhaustion, and a verified parent/control result. Training budgets and evaluation budgets are separate. Any future model evaluation must use the normal `run_slm.py` entry point and light monitoring, with an explicitly bounded execution plan.

## Uncertainty and comparisons

Use paired group resampling within each source with identical resample indices for all configurations and data orders. Average fixed data orders after pairing, then preserve source and family macro weights. Report 5,000-draw percentile 95% intervals, a recorded seed, per-order values and per-family intervals. Resampling sources within each family is a separately labeled composition sensitivity. Do not resample individual answers from the same group independently or count repeated model answers as independent tasks.

These are exploratory intervals conditional on the parent, existing data orders, scorer and source set. They do not replace old thresholds, establish equivalence, or support claims about independent model initializations. More groups reduce task-sampling noise but do not create more training seeds. All-failure samples can produce degenerate intervals and must be labeled accordingly.

For any future A-versus-D training comparison, fix the common additional-token endpoint, data-order pairing, parent checkpoint, hypothesis, selection rule and resource budget before evaluating fresh confirmation. Use the existing 15M/50M search outputs for retrospective analysis only. The existing two-hour final comparisons remain affected by unequal tokens and different positions along the cosine schedule.

## Fresh confirmation: unresolved data requirements

Target the same source coverage and at least 64 independent groups per scored source. The fresh inventory excludes training and all discovered existing/reserved suite groups across local SLM worktrees. It currently lacks **245 groups across ARC, DREAM, QuaRel and Quoref** to meet that target. Do not substitute extra SNLI/math tasks for missing dialogue or extraction groups, shrink quotas silently, or reuse diagnostic groups while calling them fresh.

Next preparation must identify unused source development material, preserve source provenance, and audit passage/dialogue/question groups and content overlap against training and every reserved suite. Context and original-reference checks must precede selection. The metadata inventory is not an exclusive reservation across concurrent tasks; rescan before use. Do not open the reserved external final benchmarks for this purpose.

No fresh confirmation suite or READY claim is issued until coverage, overlap checks, fixed hypothesis and selection rule are all complete. No new model evaluation or training starts from this document.
