# Fresh 97M / 47-source training — start record

The user authorized launch with “I want to start it”. The campaign started **16 September 2026 at 11:08:52 Europe/Berlin** with a hard deadline of **17 September 2026 at 11:08:52**. The total cap is 86,400 seconds, including controller checks, training, final evaluations and reporting. No automatic retry, extension or model adoption is authorized.

- Active run: `runs/fresh47-97m-2026-09-16/`; `status.json` and `model/status.json` are authoritative.
- Frozen plan SHA256: `6b963b91190e9c7b691b60304d5994b46d5465f27c2c4e00c49ab1e4139c8740`.
- Numerical/controller code: `77100d40b4d92a1ebee9de7d3ae2cca493075ebe`; all 337 frozen input hashes verified before launch and again by the controller.
- Fresh 97,536,768-parameter model and AdamW state; random initialization, FP32, no resume or parent checkpoint. New train-only tokenizer and v7 data: 47 sources, 2,343,583 training records.
- Mains power, free exclusive GPU lease, fresh PowerWatch measurements, sufficient available memory/disk, and no competing supported GPU job verified. Runtime conditions are recorded locally; no system process logs are published.
- Launched through `run_slm.py --module fresh47.campaign` with light monitoring. Controller PID at launch: 24919; training child: 25029. PIDs alone are not future proof of liveness.
- Initial GPU development loss completed; 70 training updates and 128,653 tokens were confirmed at 11:09:22. This is startup progress, not a quality conclusion.
- Training workload deadline: **17 September at 09:37:24**, followed by a 90-second checkpoint reserve and two final evaluations. The last chronological checkpoint is the primary endpoint. Holdouts cover 46 sources; HotpotQA is training-only.

The prepared phase caps remain 15 minutes checks, 22h30 training/checkpoints, one hour evaluation and 15 minutes reporting. Unused reserve does not extend training. There is no scheduled starter or automatic restart. `AUTHORIZATION.json`, `START_PREFLIGHT.json`, `launch.json` and `RUN_CONDITIONS.json` retain local evidence. The preparation STOP was renamed `PREPARATION_STOP.txt`; creating a new `STOP` in this run directory requests a stop. Any later continuation requires consumed-budget accounting.

Legacy reports and results remain deprecated in ZIP archives. This fresh run does not use legacy scores as a baseline. Frozen preparation JSON and its committed STOP document the earlier preparation stage; live authorization/status take precedence for this launched campaign.

## Authorized continuation — 16 September 2026

Mains power loss paused the campaign at 18:46:03. The trainer saved `checkpoint-0088459` with 88,459 updates and 161,767,873 tokens, including AdamW and sampler state. The user explicitly requested “resume”. Mains power, current PowerWatch data, free GPU lease, memory/disk and all 337 frozen inputs were rechecked.

Continuation launched at **19:30:46 Europe/Berlin**, with restored-state training confirmed at 19:30:52 (update 88,460). The absolute training cutoff remains **17 September 09:37:24**, followed by a 90-second checkpoint reserve and the original final dev/confirmation evaluations. The overall deadline remains **17 September 11:08:52**; downtime consumes the original cap. There is no new 24-hour budget and no automatic retry.

`fresh47/resume.py` is a separate CPU-only continuation supervisor because the frozen original controller is deliberately one-shot. Numerical code, original controller, launcher, data, tokenizer and plan are unchanged. Every GPU child still runs through `run_slm.py` with light monitoring and the inherited exclusive GPU lease. The continuation preserves `started`/`deadline`, hashes the checkpoint and prior state, consumes its authorization once, archives the pause STOP/status, restores model/optimizer/sampler through the existing `--resume` path, and retains both final evaluations and reporting. Elapsed campaign accounting includes downtime; active controller time is recorded separately.

Local evidence: `RESUME_2026-09-16.json`, its preflight/conditions/consumption/launch records, preserved prior model configuration/status, and `controller-resume-2026-09-16.log`. Supervisor PID at continuation launch: 90236; trainer: 90293. These are historical identifiers, not future liveness evidence. The Qwen comparison remains STOP-blocked and unstarted.

Validation: **39 CPU tests passed**, including continuation deadline preservation, changed-checkpoint and replay rejection, fake-child complete evaluation flow, failed training/evaluation stopping without retries, original campaign tests and GPU lease tests. Actual trainer output confirmed `resumed: true` at the saved step and subsequent progress.
