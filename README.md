# Benchmark-only SLM

**New evaluation settings:** [Artificial Analysis readiness, current limits and commands](BENCHMARK_SETTINGS.md). Qwen can now be configured for 16,384 output tokens; the existing SLM remains bound by its trained 1,024-token context. Implementation and CPU preparation are complete; no new benchmark run has started.

Chat with the trained model locally (Apple Silicon, existing project environment):

```sh
.venv/bin/python -m slm.chat
```

Use `--device gpu` for faster inference or `--prompt 'Your question'` for a single
answer. See [local chat instructions](CHAT.md) for checkpoint selection, JSON
output, conversation controls, and Ollama format considerations.

To open it through the project skill, ask **"Start the latest trained SLM for
chat"** or invoke **`$start-latest-slm`**. The
[skill](.agents/skills/start-latest-slm/SKILL.md) selects the latest completed
training campaign from local records and opens an interactive Terminal window.

The current trained model uses **47 benchmark sources across 13 capability families**. Training of the fresh 97.54M model ended at the user's request on **18 September 2026 at 20:20:23 Europe/Berlin**, with final chronological checkpoint `checkpoint-0215720`. Final evaluations completed at 20:27:53. See the [final report](reports/fresh47-2026-09-18/REPORT.md); local campaign `status.json` is authoritative.

[Fresh training plan](FRESH_47_TRAINING.md) · [Source coverage](BENCHMARKS_47.md) · [Deprecated archives](archives/README.md)

The model started from random initialization with a new 16,384-token tokenizer trained only on the training partition. It used no legacy checkpoint or optimizer state. The authorized training and continuation windows are recorded in [project instructions](AGENTS.md).

All experiments and reports predating this restart are **deprecated**. Their scores are historical reference only. They are retained as verified ZIP archives; the unpacked reports, run artifacts and old worktrees have been retired. Git history is preserved. See [archive policy](SICHERUNG.md).

Data, weights, generated responses and system process logs remain local and are excluded from Git. The new data version is `data/v7-benchmarks47-fresh-2026-09-16/`; the prepared campaign is `runs/fresh47-97m-2026-09-16/`.

The repository uses Python 3.12 and the dependencies in `pyproject.toml` / `uv.lock`. CPU preparation is implemented in `fresh47/prepare.py`; `fresh47/campaign.py` supervises a separately authorized future run. Regular workloads use `run_slm.py` with [light monitoring](PERFORMANCE.md). [PowerWatch](RESOURCE_MONITORING.md) remains active independently.

To inspect the prepared command without model initialization:

```sh
.venv/bin/python -m fresh47.campaign --run runs/fresh47-97m-2026-09-16 --dry-run
```

This project measures internal task proxies. They are not official benchmark scores, proof of external transfer, or deployment readiness. Dataset terms remain source-specific; preparation does not grant permission to redistribute dataset contents or trained artifacts.
