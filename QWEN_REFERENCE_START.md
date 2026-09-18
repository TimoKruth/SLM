# Qwen confirmation comparison — authorized start

User instruction: **“Start Qwen once for comparison and note the results”**. Started **18 September 2026 at 20:38:17 Europe/Berlin**; hard deadline **19 September 2026 at 02:38:17**. The separate six-hour cap includes verification, both model phases and reporting. One answer per model/task, no automatic retry, extension or adoption.

## Fixed comparison

- Local models, sequentially: `batiai/qwen3.6-27b:q4` and `qwen3.8:27b` (approximately 27B parameters, Q4_K_M). Names are local tags, not independently verified upstream provenance.
- Exact existing confirmation suite: **1,267 tasks / 46 sources**, including **1,064 correctness-scored tasks**. No new SLM inference. Internal task proxies, not official benchmark scores.
- Baseline: fresh 97,536,768-parameter FP32 SLM, user-ended final chronological checkpoint `checkpoint-0215720`; **300/1,064 correct (28.2%)**. Both SLM evaluations and report completed before Qwen admission. Early training stop and suite limitations are documented in `reports/fresh47-2026-09-18/REPORT.md`.
- Same task text and scorer; neutral system message, each model's native wrapper, temperature zero, seed 20260916, 256 native output tokens, thinking disabled, 8,192 context tokens. No answer repair or reference-derived hints. Native token limits do not imply equal text length or compute.
- Fifteen minutes preflight, up to 2h45 per model, fifteen minutes reporting; total cap six hours. Incomplete suites are preserved and labeled partial, without a full-suite ranking. A model failure stops the campaign without retry.

## Admission and runtime evidence

All **51 frozen input hashes** verified. Full local weight/config blob SHA256 verification completed. All 1,267 saved SLM answers rescore identically and retain exact task order and identity. Both final SLM evaluation summaries, full reference-loss denominators, input verification and report were present.

Mains power, free exclusive GPU lease, fresh PowerWatch samples (normal observed thermal state), approximately 41.8 GB available RAM, 934 GB free disk and no existing supported GPU/Ollama workload were verified. No existing Ollama service was stopped. Runtime uses an owned server on `127.0.0.1:11439`, serial requests and one loaded model, with a watchdog that terminates owned inference on STOP, mains loss or deadline.

The first model passed its actual neutral thinking-disabled smoke test and produced benchmark responses by 20:39. Both models' metadata/templates were saved before benchmark generation. The second model's load/smoke occurs when its phase starts. First-model task counts are progress, not final scores.

**46 CPU tests passed** before launch. Worktree: `/Users/timokruth/Projekte/SLM-qwen-reference`, commit `d228a8f4e39a4ad59efcd8732998e659a74d210f`. Launched through its `run_slm.py --module qwen_reference.campaign --monitoring light`; controller PID at launch 2672 (historical identifier only).

Frozen plan SHA256: `857c654f0b41069c87527e8b0179650e83e5c8ab555ce294eb308bcac5e87659`.

SLM final model SHA256: `00e4435ad8e3ed50a5a71951e76d6298f320ee6d76909b9d0b69b9c557eb3ba6`.

Confirmation suite SHA256: `58af517d0db33749c91fd1e0e64085646d5c332fe9f6e5845f0dc620a72e7cc0`.

## Where results are recorded

Local run: `runs/qwen-reference-confirmation-2026-09-16/`.

- `status.json`: live model, progress and budget deadline.
- `AUTHORIZATION.json`, `launch.json`, `RUN_CONDITIONS.json`, `SLM_BASELINE.json`: authorization and provenance.
- `model-0-responses.jsonl` / `model-1-responses.jsonl`: raw answers, native timing/token data and task metrics; local only.
- `model-0-summary.json` / `model-1-summary.json`: aggregate source/family results and paired differences.
- `RESULT.json` and `REPORT.md`: automatically written after successful completion and final hash verification.
- `PARTIAL.json` and STOP: written on failure or exhaustion; no automatic retry or ranking of partial subsets.

Results are pending at this start record. No Qwen performance number is inferred from setup success. Final comparison must retain small-source/label-imbalance and generation-cap limitations, the large model-size difference, and unknown Qwen pretraining exposure. Raw answers, weights and system-wide logs stay out of the public repository.
