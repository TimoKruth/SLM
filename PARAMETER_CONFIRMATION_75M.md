# Matched 75M parameter confirmation

Authorized by “Start the comparison”, 15 September 2026. Five saved-checkpoint evaluations on the prepared 1,360-task suite; no additional training. Controller started **17:09:04 Europe/Berlin**, first parent evaluation **17:09:10**. The focused FP32 comparison was already completed; no other GPU workload or lease holder was found at admission. Mains power confirmed.

The hard deadline is **18:33:00 Europe/Berlin**, charging preparation conservatively from **17:03:00**. The 90-minute total includes up to 20 minutes of preparation, 55 minutes for serial evaluations and 15 minutes for verification/reporting. Each evaluation has a 600-second inference/reference-loss allowance and a 630-second outer process limit, further bounded by the phase and total deadlines. Early completion ends the block; no automatic retry, extension, training or adoption.

## Frozen comparison

| Checkpoint | Additional tokens | Global update |
|---|---:|---:|
| Unchanged original parent | 0 | 135,594 |
| A, data order 0 | 75,001,030 | 177,001 |
| D, data order 0 | 75,001,030 | 177,001 |
| A, data order 1 | 75,000,676 | 176,964 |
| D, data order 1 | 75,000,676 | 176,964 |

A uses constant LR 3e-5; D retains its original cosine schedule from 3e-5 to 3e-6 over 100M additional tokens. The nearest-update snapshots match tokens and updates exactly within each data order. Both orders are fixed data sequences from the same parent, not independent model initializations. No checkpoint will be selected after seeing this confirmation. Historical 50M and time-end diagnostics remain separate.

Hypothesis: at matched 75M exposure, D improves family-macro free-answer accuracy over A and the unchanged parent. Predeclared gates:

- At least +2 percentage points D−A in **each** data order.
- Strictly positive D−parent in **each** data order.
- No mean family regression larger than 5 percentage points against either A or parent, averaging the fixed data orders.
- Passing all gates supports further validation, without automatic model replacement. A failure retains the parent as the reference.

Primary metric averages source correctness within each of six scored families, then averages those families. The suite contains 1,280 correctness-scored tasks from 20 sources plus 80 tasks from five unscored sources. The latter remain outside accuracy. Report loss, repetition, output limits, per-source/family denominators and task transitions separately. Paired 95% intervals use 5,000 group resamples within source; intervals remain exploratory and conditional on the fixed parent and data orders. No external-transfer claim.

## Integrity and operation

Run: `runs/parameter-confirmation-75m-2026-09-15/` in the main workspace. Execution worktree `/Users/timokruth/Projekte/SLM-confirmation-75m`, branch `codex/confirmation-75m`, commit `da3a466`; numerical training/model/inference/scoring/monitoring code matches `4c30196` unchanged. The controller and CPU report are separate additions.

All five weights, tokenizers, configurations and latest pointers have independent evaluation copies. 257 frozen inputs cover source/copy files, suite, preparation provenance and execution code. The 81 preparation input hashes were checked again; all 61 other discovered suite reservations were checked for selected group and exact-content overlap, with zero matches. Prepared original validation remains evaluation-only. The original preparation STOP and all historical campaign artifacts remain untouched.

The suite is unchanged: SHA-256 `1ec15a68f17b49096b3df611841ff842805ed36882ec680744319f17a2c053b4`. It contains 256 original-validation tasks and 1,104 unconsumed internal-dev tasks; internal dev may have been exposed through development loss. Provenance and limits: [reference refresh](PARAMETER_REFERENCE_REFRESH.md).

Each GPU child runs through `run_slm.py --module slm.broad_eval --monitoring light`, with 256 output tokens and full reference loss. An exclusive inherited GPU lease covers evaluation and is released before CPU analysis. PowerWatch and existing power settings remain unchanged; per-model power conditions are recorded. `caffeinate -i -w` prevents idle sleep while this controller lives. This is a quality comparison, not a throughput experiment.

The controller verifies complete generation/reference-loss counts, correct checkpoint/suite hashes, no context-limit failures and final input integrity. The CPU report independently rescoring all 6,800 expected answers checks task identities and counts, recomputes paired comparisons, and applies the fixed gates. A stable evaluation-completion record separates verified evaluation evidence from the controller's continuing heartbeat. A partial/failed run produces paused status and STOP; it is not reported as a completed comparison.

36 CPU tests passed for pairing, decision gates, matched endpoints, complete coverage, GPU lease and monitored launcher. Successful parent generation was observed after launch. Live state and deadline: `status.json`; CPU report state: `analysis-status.json`; final report: `analysis/REPORT.md` and `analysis/analysis.json` in the run directory.

To stop only this comparison, create `runs/parameter-confirmation-75m-2026-09-15/STOP`. Only this controller's child process groups are stopped. No new budget or automatic restart is granted by this document.
