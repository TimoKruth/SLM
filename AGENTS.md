# Current project instructions — 16 September 2026

## Active task and authorization

- The user requested commit/push to `main`, retirement of all previous reports/results, and preparation of a completely new training on the larger benchmark list.
- Current data: `data/v7-benchmarks47-fresh-2026-09-16/`, 47 sources / 13 families, 2,343,583 training examples, fresh train-only tokenizer. All files are independent regular files.
- Current prepared campaign: `runs/fresh47-97m-2026-09-16/`. Plan: `FRESH_47_TRAINING.md`; committed aggregate preparation evidence under `plans/fresh47-2026-09-16/`.
- **Preparation only. No model training or GPU evaluation has started. STOP remains set.** A 24-hour cap and 97.54M model are the user-selected preparation; they are not an authorization to start. Do not install a starter or queue.
- A future explicit start must match the frozen plan hash and recheck inputs, mains power, free GPU lease and actual resource conditions. No automatic retry, extension, model adoption, or budget reset. A paused run requires a budget-correct continuation plan.
- Start regular training/evaluation through `.venv/bin/python run_slm.py --run ... --module ...`. `run_defaults.json`: monitoring `light`, 10 warmup steps, 60-second flushes. Only explicit user instruction disables monitoring. Keep PowerWatch active.
- Fresh training initializes model and AdamW randomly/new, with no legacy checkpoint. Preserve frozen inputs once a run starts.

## Legacy archive policy — supersedes historical run instructions

- **Every report, score and run artifact from before the fresh 47-source restart is DEPRECATED.** They are not current baselines or evidence for selecting a new model.
- Old benchmark-list results must be retained **only as ZIP/ZIP64 archives**, never as persistent unpacked files. This includes generated responses, checkpoints, evaluation outputs, diagnostics and old report copies.
- Public curated reports: `archives/deprecated-reports-2026-09-16.zip`. Complete private runs and all historical worktree code/branch commits: `/Users/timokruth/SLM-Sicherungen/2026-09-16-legacy-retired/`. See `archives/README.md`, `archives/legacy-index.json` and `SICHERUNG.md`.
- Verify archive SHA256, every member hash/CRC, and restoration before pruning sources. `tools/retire_legacy_results.py` rechecks the entire source against the verified ZIP before deletion.
- For a requested historical inspection, read members directly from ZIP where possible. If restoration is necessary, use a temporary reference directory and remove the unpacked copy afterward. Never revive an old controller or treat archived start instructions as current authorization.
- Existing Git history is not rewritten. Local historical refs are retained; retired worktrees are represented in the private code/branch ZIP.
- Raw corpus inputs and live `runs/system-resources` monitoring are not old experiment results; preserve them. They must not be uploaded as public results. New 47-source run artifacts may remain unpacked while active.

## Data and evaluation

- Broad capability coverage is the goal; coding is one capability, not the default priority. Sampling gives equal sequence mass to each of 13 families, then each source in a family.
- Source provenance, original training splits, grouping, label handling and context limits are authoritative in the new manifest/audit. Historical SciTail/WIQA converter defects stay fixed.
- No original validation or external test records enter this training. Known ambiguous reference groups are excluded using `fresh47/reference_exclusions.json`.
- Training/dev/confirmation groups and exact prompt-answer pairs are disjoint. This is not a semantic independence guarantee. Some inherited holdout groups were used in historical experiments; the new confirmation is held out from this fresh model, not universally unseen research data.
- All 47 sources contribute training. HotpotQA has no safely separated direct holdout; suites cover 46 sources, with explicit small-source quota deficits. Report these gaps.
- The primary endpoint is the final checkpoint on confirmation, not the best checkpoint chosen afterward. Report source/family metrics, denominators, unscored capabilities, actual tokens/updates and measured resource conditions. Do not compare fresh-tokenizer loss or new suite scores directly to legacy runs.
- Code syntax, SQL text matching and summary lexical metrics are not functional or factual correctness. Do not imply official benchmark coverage from internal proxies.

## Repository workflow

- Commit completed changes promptly. Push only when authorized; the retirement/preparation task includes authorization to push `main`.
- Do not put raw datasets, model weights, generated responses or system-wide process logs in the public repository.
- `read-training-status` remains a project skill. `read-system-resources` is global. Status questions are read-only and do not authorize starting/restarting runs.
