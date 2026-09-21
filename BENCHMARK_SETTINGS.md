# Evaluation settings and Artificial Analysis readiness

Prepared 21 September 2026. No training, model inference, external benchmark download, paid API call, or comparison restart was performed. Historical SLM/Qwen runs and frozen input files are unchanged.

## Assessment

Artificial Analysis is the requested provider. Its [published methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking) was consulted on 21 September 2026. It specifies 16,384 output tokens for non-reasoning models, reduced for models with smaller limits; reasoning budgets are model-specific. It also uses explicit prompts, answer extraction and task-specific grading. Our old 256-token cap and conversational-output/strict-scorer mismatch prevented a useful broad capability comparison.

The implementation now separates context capacity, requested answer length, effective per-question answer space, task timeout and total budget. Raising these settings does not add learned abilities to the 97.54M SLM. The existing SLM was trained at 1,024 tokens. A context override cannot be used to relabel it as a long-context model.

The current Artificial Analysis suite includes agent tasks, long documents, specialized code execution and external grading. **This implementation is a text-generation evaluation runner, not an implementation of the full Intelligence Index.** Task-specific harnesses, sandboxed execution, graders and appropriately licensed/versioned datasets remain necessary for that. It never produces a purported Artificial Analysis index or treats successful generation as benchmark success.

## Implemented settings

| Setting | SLM current checkpoint | Qwen standard profiles | Qwen optional long-context profiles |
| --- | ---: | ---: | ---: |
| Total context | 1,024, enforced from checkpoint config | 32,768 | 262,144 |
| Requested maximum output | 16,384 | 16,384 | 16,384 |
| Effective output | Minimum of requested maximum and remaining context | Full output reserve required | Full output reserve required |
| Minimum admitted answer space | 64 | 64 | 64 |
| Temperature | 0, greedy | 0 | 0 |
| Thinking channel | Unsupported | Disabled | Disabled |
| Task wall-time cap | 3,600 seconds | 3,600 seconds | 3,600 seconds |
| Whole-run budget | Must be supplied explicitly at start | Must be supplied explicitly at start | Must be supplied explicitly at start |
| Concurrency | One persistent model, serial tasks | One persistent model, serial tasks | One persistent model, serial tasks |
| Automatic retries/extensions | None | None | None |

Profiles live in `benchmark_eval/profiles/`. They are configurable; prepare a new plan after editing a profile. There is no hidden 256-token generation cap in the new runner. No sliding-window truncation is used. Unsupported prompts are recorded explicitly and make generation coverage incomplete.

The current local Qwen metadata declares a 262,144-token context. Preparation rejects larger values. The optional long-context profiles are configuration support, **not a memory/throughput validation on this Mac**; large context allocation may fail or be impractical. Standard profiles avoid allocating maximum context when short prompts do not need it. Neither local model is established here to support a one-million-token context. Runtime verifies the model tag/digest and metadata and checks token accounting.

SLM admission counts its exact tokenizer tokens, including the answer-format instruction and model wrapper. On all **1,269 development tasks**, the current model has **247–1,006 output tokens available**, depending on prompt length; all pass the 64-token minimum. Thus some long questions still leave less than the historical 256-token cap. This is reported rather than hidden. Qwen's conservative prompt allowance admits all 1,269 tasks with the full 16,384-output reserve. Those are CPU preparation checks, not measured model performance.

Qwen admission uses UTF-8 bytes plus the saved template/system byte lengths and a 4,096-token reserve as an upper allowance for the audited local `qwen35` family. It can conservatively reject a prompt that would actually fit. Runtime prompt counts must fit that allowance and leave the requested output reserve; any violation stops the run rather than publishing a score. Arbitrary model families require a dedicated tokenizer adapter. Native token budgets still do not imply equal text length or compute across models.

The output and wall limits are independent. At the previously measured ~10.85 output tokens/s, using the entire 16,384-token allowance takes about **25 minutes per response**, excluding prefill. A full 1,267-task suite at that maximum would take roughly **531 generation hours per model**. This is a worst-output planning scenario, not a runtime prediction. Measure a small development pilot before approving a large run. The former 2h45 per-model restriction is not present in this new runner; the explicitly chosen whole-run budget still applies.

## Answer contracts and scoring

For locally scored tasks, both backends receive the same instruction to end with `Final answer: <answer>`. Extraction uses only the generated response, never the reference. Bare single-line answers are also accepted. Conflicting final markers, text after the final answer and missing final lines in multiline prose are rejected. Incorrect answers remain incorrect. No substring search for the expected answer, judge-based repair or reference hints are used.

- Choice tasks: select a single valid letter from the visible choices.
- Numeric tasks: finite decimal/scientific numeric equality; no arbitrary code execution, units or symbolic-equivalence claims.
- Text tasks: normalized short-answer equality; not semantic judging.
- Existing 47-source tasks: a new final-answer contract feeds the unchanged historical task-specific scorer. Format markers for GSM8K/MATH/AQuA/QASC are adapted deterministically. These remain internal proxies.
- Code, SQL, summaries, narrative outputs and canonical `external` tasks: answers are saved; correctness remains **unscored pending an appropriate external grader**. No syntax-only success is counted as functional correctness.

Reports separate format errors, output-limit stops, context-limit stops, unsupported inputs and missing graders. They preserve all attempts and denominators; truncated responses are not silently discarded to improve scores. Per-source scores on a partial run remain partial. No mixed-proxy global accuracy or Intelligence Index is fabricated.

The changed prompts define a new protocol. Do not overwrite or compare directly with historical scores. Confirmation has already informed diagnosis; protocol development belongs on development tasks. Future claims need a separately audited untouched holdout.

## Preparation and execution

New code is isolated in `benchmark_eval/`. Historical `run_slm.py`, numerical code, scorers, controllers and data are frozen inputs and were not edited. The dedicated `benchmark_eval.launch` entry point registers the new module **in memory** with the existing `slm_perf` launcher and reads the same `run_defaults.json` (light monitoring, 10 warmup steps, 60-second flushes). It uses the shared GPU lease. This separate entry point is necessary to preserve the old launcher hashes.

CPU-only preparation example for the SLM:

```sh
.venv/bin/python -m benchmark_eval.prepare \
  --profile benchmark_eval/profiles/slm97m.json \
  --suite data/v7-benchmarks47-fresh-2026-09-16/dev-suite.json \
  --output runs/new-slm-evaluation \
  --model-dir runs/fresh47-97m-2026-09-16/model \
  --checkpoint runs/fresh47-97m-2026-09-16/model/checkpoint-0215720/model.safetensors
```

CPU-only Qwen preparation:

```sh
.venv/bin/python -m benchmark_eval.prepare \
  --profile benchmark_eval/profiles/qwen36.json \
  --suite data/v7-benchmarks47-fresh-2026-09-16/dev-suite.json \
  --output runs/new-qwen-evaluation \
  --metadata runs/qwen-reference-confirmation-2026-09-16/model-0-metadata.json
```

For the other Qwen use `qwen38.json` and `model-1-metadata.json`. For future inventories, capture `/api/show` metadata from the intended local model and use its matching local manifest. Preparation never loads weights into a model. Full Ollama blob hashes are verified at actual start.

Only after an explicitly approved run budget:

```sh
.venv/bin/python -m benchmark_eval.launch \
  --run runs/new-qwen-evaluation --start \
  --plan-sha256 PLAN_HASH_PRINTED_BY_PREPARATION \
  --budget-seconds APPROVED_WALL_SECONDS
```

Prepared plans are snapshots. A code/data/profile change invalidates their hashes and requires a new output directory. Existing/stopped run directories are never reused or silently resumed. Each completed response is flushed to local JSONL; reports retain partial work on interruption. `STOP`, signals, mains loss and absolute task/run deadlines terminate the owned backend process tree. Both monotonic and calendar deadlines protect the total budget. HTTP timeout alone is not relied upon to cancel inference. An interrupted in-flight response is not scored or retried. Ollama runs on a dedicated loopback port 11440 with a 30-minute keep-alive and is unloaded when the owned server exits. Other Ollama servers/workloads block admission; they are not killed. PowerWatch must already be fresh and remains active; an owned caffeinate process prevents idle sleep during the run.

## External text benchmark interface

Import authorized dataset records into local `.jsonl` with `id`, `source`, `prompt`, `kind`, and (for local grading) `reference`. `system` may optionally supply system instructions (native role for Qwen, explicitly prepended text for the SLM). `kind` is `choice`, `number`, `text`, or `external`; choice records also supply `choices` and a letter reference. `tests/benchmark_eval/synthetic.jsonl` demonstrates all four. Do not publish real datasets or generated answers. Tool/image tasks are rejected explicitly.

Use `external` when preserving an upstream prompt exactly (for example, HLE or AA-LCR with the official prompt and grader). This mode generates outputs without adding the local answer contract. It does **not** substitute normalized string matching for an official equality judge, execute generated code on the host, or claim the dataset is the exact private Artificial Analysis suite.

| Benchmark requirement | Current support / remaining work |
| --- | --- |
| Short text or multiple choice | Runnable with canonical local tasks; local proxy graders available |
| HLE / AA-Omniscience | Text generation available; exact dataset version, official prompts, grading/abstention methodology and judge integration still needed |
| AA-LCR / long documents | Qwen configurable up to declared 262K; memory/performance and actual full-prompt admission require validation. Current SLM cannot handle long documents |
| SciCode / code benchmarks | Text output available; official isolated execution environment/tests and task harness still needed |
| Terminal / workplace / automation agents | Not implemented by this text runner; official tool harness, environment, turn budgets, artifacts and graders required |
| Full Artificial Analysis Intelligence Index | Not available; a settings change alone cannot implement it |

## Training implications

Increasing output allowances needs no retraining. A reliable SLM context beyond 1,024 needs a separate data/context-training experiment and long-context validation. Existing weights can be a starting point; a fresh random model is not inherently required for context adaptation. The current checkpoint configuration is immutable and larger-context inference is rejected. The original data preparation also filtered out long records; changing only a training CLI flag would not restore that material. Tokenizer/data rebuilding, split audits, positional treatment, training cost and long-context tests need a separate plan. No such training has been started.

## Validation

CPU-only tests exercise settings admission, answer extraction, ambiguity/wrong-answer rejection, numeric grading, legacy format adaptation, unsupported tasks, partial denominators, Ollama payload/token accounting, checkpoint context refusal, durable mocked runs and cancellation of a blocked backend. Mock inference tests do not establish real model compatibility, throughput or capability. Local full-development preparation and historical frozen-input verification are recorded under `plans/evaluation-settings-2026-09-21/`.
