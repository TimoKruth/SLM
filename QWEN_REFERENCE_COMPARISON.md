# Qwen reference comparison after fresh training

The user requested a comparison with locally installed Qwen models as targets for the fresh SLM. This document prepares the comparison protocol. **No Qwen inference, server start, GPU work or queue has been initiated.** The user selected a separate **six-hour cap, confirmation suite only**. The evaluator is being prepared in an isolated worktree so the active campaign’s frozen launcher and monitoring files remain unchanged. Proposal and local model inventory: `plans/qwen-reference-2026-09-16/plan.json`, guarded by STOP.

## Models found locally

| Local Ollama tag | Size declared in local config | Quantization |
| --- | ---: | --- |
| `batiai/qwen3.6-27b:q4` | 26.9B | Q4_K_M |
| `qwen3.8:27b` | 27.3B | Q4_K_M |
| Current fresh SLM | 97,536,768 | FP32 |

All referenced Qwen blob files are present. Manifest hashes, config digests and expected layer sizes/digests are recorded. Full weight hashes will be verified after the active campaign finishes to avoid heavy disk work during training. Names and sizes above are local metadata, not independently verified upstream provenance. Both model configs identify the `qwen35` family; the second requires Ollama at least 0.32.12, and the installed client reports 0.33.3. The default local Ollama endpoint was not running during inventory, so actual loading/template compatibility remains untested.

These Qwen models are roughly 275–280 times larger than the SLM. Treat them as practical score targets. This comparison cannot isolate architecture/training efficiency, and possible overlap between their unknown pretraining data and these benchmarks cannot be ruled out.

## Comparison protocol

1. Wait for the active SLM campaign to finish successfully, including **both final evaluations**, reporting and input verification. Record its exact final-checkpoint hash from the saved evaluation protocol. Never start on the mere end of the training subprocess, and never interrupt it or consume its reserved evaluation budget.
2. Use the exact existing 1,267-task confirmation suite as the primary comparison. The optional larger profile also uses the 1,269-task development suite. Both cover 46 sources, with 1,064 correctness-scored tasks across 38 sources in each suite. HotpotQA remains training-only; small-source deficits remain visible.
3. Reuse the exact task prompt text, references, scorer and family/source aggregation. Use each model's native prompt wrapper and record the complete template/system configuration before any benchmark outputs are viewed. No task-specific hints, reference-derived prompting, answer repair or scorer changes. The existing SLM outputs can be reused: no additional SLM inference is needed.
4. Proposed deterministic Qwen settings: temperature 0, seed 20260916, one response per task, 256 output tokens, thinking disabled. Verify the installed models honor this on neutral nonbenchmark probes. An unsupported thinking toggle is a setup failure, not permission to silently switch to a longer reasoning protocol. Ollama documents the `think` and native-template generation controls in its [generation API](https://docs.ollama.com/api/generate) and [thinking documentation](https://docs.ollama.com/capabilities/thinking).
5. Use an 8,192-token Qwen context to hold the identical input text and its native template without clipping; this supplies no extra task content. Suite prompts are at most 3,323 UTF-8 bytes. Verify template overhead and token accounting at runtime; never silently truncate prompts. A 256-token ceiling is in each model's own tokenizer, so it is not equal text length or equal compute.
6. Score final answer content, retain raw responses locally, and report formatting failures, length cutoffs and missing tasks. Score syntax/SQL/narrative/summary proxies separately from correctness. Do not compare cross-tokenizer loss/perplexity as if they were the same measure.
7. Report a source/family table with denominators, paired SLM–Qwen differences, wins/losses on identical tasks, latency and output-token counts. Any paired uncertainty intervals describe these task groups only, not independent model-training repetitions. These are internal task proxies, not official benchmark scores or guaranteed unseen generalization.

## Separate budget proposal

| Profile | Coverage | Total cap | Allocation |
| --- | --- | ---: | --- |
| Recommended | Confirmation only, both Qwen models | 6 hours | 15m setup, 2h45 per model, 15m report |
| Expanded | Confirmation and development, both Qwen models | 12 hours | 15m setup, 5h45 per model, 15m report |

These are additional wall-time caps, not completion-time estimates or additions to the active training cap. No throughput assumption has been measured for these models here. If a cap is reached, preserve and label partial results; do not rank a partial suite against a complete one. No automatic retry, extension or model adoption.

Once a budget is selected, implement and test a separate evaluator/controller without editing the active campaign's frozen files. Admission must require successful SLM completion, mains power, no competing GPU job and the same exclusive GPU lease. The local Ollama process must be supervised so a deadline/STOP actually ends inference and releases model memory. A network timeout alone is insufficient. Freeze exact model digests, suite/scorer hashes, template and generation settings before the first benchmark response. No auto-start mechanism is installed by this preparation.
