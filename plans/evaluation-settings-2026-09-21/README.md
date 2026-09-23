# Evaluation settings preparation evidence

`preparation.json` records the final **v3** CPU-only development plans for the SLM and both Qwen models, their hashes, task admission counts and historical input verification. Earlier local preparation snapshots are STOP-blocked as superseded. No new inference or training started. Raw task data and model artifacts remain local.

All 1,269 development tasks pass input admission for all three profiles. The SLM's available output is 247–1,006 tokens (trained context 1,024). Qwen standard profiles reserve 16,384 output tokens in a 32,768-token context. Large-context presets are not memory-validated.

Validation: **51 CPU tests passed** (`tests/benchmark_eval`, launcher-default and GPU-lease tests), including mocked end-to-end persistence and blocked-request cancellation. Module compilation and CPU-only preparation/controller import checks passed. All **337 SLM + 51 Qwen** historical frozen hashes match. Mock tests do not establish real inference throughput or official benchmark readiness.

See [settings and readiness assessment](../../BENCHMARK_SETTINGS.md). Full Artificial Analysis harnesses and official graders remain outside the text runner; these prepared runs are internal development evaluations.

## Reasoning reference addition

`reasoning-preparation.json` is the latest preparation index: two reasoning-enabled Qwen plans plus refreshed **v4** non-reasoning/SLM reference plans. The previous v3 plan files are preserved but STOP-blocked: the separate chat improvement in commit `2611bcf` changed a pinned dependency. No historical training/comparison input changed.

Reasoning profiles: 65,536 context, 32,768 shared generation tokens, temperature 0.6, thinking enabled, 7,200-second task cap. All 1,269 development tasks pass CPU input admission for both models. **55 CPU tests passed**, including reasoning-channel separation and reasoning-only truncation. No model load or inference occurred. Real-mode compliance, memory use, throughput and an explicitly approved total run budget remain prerequisites for execution.
