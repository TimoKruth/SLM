# Current project instructions — 16 September 2026

## Active task and authorization

- The user requested commit/push to `main`, retirement of all previous reports/results, and preparation of a completely new training on the larger benchmark list.
- Current data: `data/v7-benchmarks47-fresh-2026-09-16/`, 47 sources / 13 families, 2,343,583 training examples, fresh train-only tokenizer. All files are independent regular files.
- Current active campaign: `runs/fresh47-97m-2026-09-16/`. Plan: `FRESH_47_TRAINING.md`; committed aggregate preparation evidence under `plans/fresh47-2026-09-16/`.
- User explicitly authorized start with “I want to start it”. **Started 16 September 2026 at 11:08:52 Europe/Berlin**, hard deadline **17 September 2026 at 11:08:52**. Fresh 97,536,768-parameter FP32 training is progressing. Plan SHA256 `6b963b91190e9c7b691b60304d5994b46d5465f27c2c4e00c49ab1e4139c8740`, numerical/controller code `77100d4`; 337 frozen inputs verified. Light monitoring, mains power, GPU lease and PowerWatch active. Details: `FRESH_47_START.md`; local `status.json` is authoritative. No automatic retry, extension or adoption. The historical preparation STOP was renamed `PREPARATION_STOP.txt`; a new `STOP` stops this campaign.
- Mains loss paused this run at 18:46:03. User authorized “resume”; restarted **16 September 19:30:46** from `checkpoint-0088459` (88,459 updates / 161,767,873 tokens), with optimizer/sampler restored. Separate CPU supervisor `fresh47/resume.py` leaves every original frozen input unchanged; GPU children still use `run_slm.py` with light monitoring. Original training cutoff **17 September 09:37:24** and total deadline **11:08:52** remain unchanged; downtime counts against the cap. One-shot local authorization/evidence: `RESUME_2026-09-16*`. No automatic retry or Qwen start.
- A future explicit start must match the frozen plan hash and recheck inputs, mains power, free GPU lease and actual resource conditions. No automatic retry, extension, model adoption, or budget reset. A paused run requires a budget-correct continuation plan.
- Start regular training/evaluation through `.venv/bin/python run_slm.py --run ... --module ...`. `run_defaults.json`: monitoring `light`, 10 warmup steps, 60-second flushes. Only explicit user instruction disables monitoring. Keep PowerWatch active.
- Fresh training initializes model and AdamW randomly/new, with no legacy checkpoint. Preserve frozen inputs once a run starts.

## Prepared Qwen comparison

- User selected **six additional hours, confirmation suite only** for `batiai/qwen3.6-27b:q4` and `qwen3.8:27b`. This does not change the active SLM budget.
- Preparation only: `runs/qwen-reference-confirmation-2026-09-16/` remains STOP-blocked with no actual start authorization or queue. Code is in `/Users/timokruth/Projekte/SLM-qwen-reference`, branch `codex/qwen-reference`; details `QWEN_REFERENCE_COMPARISON.md`.
- Before an explicit comparison start, require successful SLM training, both final evaluations and report, mains power, and free GPU lease. Use the isolated worktree launcher; do not merge its launcher/monitoring modifications into this active frozen checkout.
- 46 CPU tests passed. Real Qwen model loading and full blob verification are deferred until after SLM completion.

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
