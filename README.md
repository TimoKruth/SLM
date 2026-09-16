# Benchmark-only SLM

The active work is a fresh model trained on **47 benchmark sources across 13 capability families**. The fresh 97.54M model **started training on 16 September 2026 at 11:08:52 Europe/Berlin**. Its hard campaign deadline is 17 September at 11:08:52. See [start record](FRESH_47_START.md); the local campaign `status.json` is authoritative.

[Fresh training plan](FRESH_47_TRAINING.md) · [Source coverage](BENCHMARKS_47.md) · [Deprecated archives](archives/README.md)

The user-selected preparation is a randomly initialized 97.54M-parameter decoder with a new 16,384-token tokenizer trained only on the training partition. The prepared future campaign has a 24-hour total cap, including checks, training, evaluation and reporting. It uses no old checkpoint or optimizer state.

All experiments and reports predating this restart are **deprecated**. Their scores are historical reference only. They are retained as verified ZIP archives; the unpacked reports, run artifacts and old worktrees have been retired. Git history is preserved. See [archive policy](SICHERUNG.md).

Data, weights, generated responses and system process logs remain local and are excluded from Git. The new data version is `data/v7-benchmarks47-fresh-2026-09-16/`; the prepared campaign is `runs/fresh47-97m-2026-09-16/`.

The repository uses Python 3.12 and the dependencies in `pyproject.toml` / `uv.lock`. CPU preparation is implemented in `fresh47/prepare.py`; `fresh47/campaign.py` supervises a separately authorized future run. Regular workloads use `run_slm.py` with [light monitoring](PERFORMANCE.md). [PowerWatch](RESOURCE_MONITORING.md) remains active independently.

To inspect the prepared command without model initialization:

```sh
.venv/bin/python -m fresh47.campaign --run runs/fresh47-97m-2026-09-16 --dry-run
```

This project measures internal task proxies. They are not official benchmark scores, proof of external transfer, or deployment readiness. Dataset terms remain source-specific; preparation does not grant permission to redistribute dataset contents or trained artifacts.
