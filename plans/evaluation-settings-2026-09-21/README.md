# Evaluation settings preparation evidence

`preparation.json` records the final **v3** CPU-only development plans for the SLM and both Qwen models, their hashes, task admission counts and historical input verification. Earlier local preparation snapshots are STOP-blocked as superseded. No new inference or training started. Raw task data and model artifacts remain local.

All 1,269 development tasks pass input admission for all three profiles. The SLM's available output is 247–1,006 tokens (trained context 1,024). Qwen standard profiles reserve 16,384 output tokens in a 32,768-token context. Large-context presets are not memory-validated.

Validation: **51 CPU tests passed** (`tests/benchmark_eval`, launcher-default and GPU-lease tests), including mocked end-to-end persistence and blocked-request cancellation. Module compilation and CPU-only preparation/controller import checks passed. All **337 SLM + 51 Qwen** historical frozen hashes match. Mock tests do not establish real inference throughput or official benchmark readiness.

See [settings and readiness assessment](../../BENCHMARK_SETTINGS.md). Full Artificial Analysis harnesses and official graders remain outside the text runner; these prepared runs are internal development evaluations.
