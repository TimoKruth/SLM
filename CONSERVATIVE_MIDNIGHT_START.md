# Conservative comparison scheduled for midnight

Explicit user instruction: “Can you create a start that runs the next test at midnight?”

The prepared FP32 comparison is authorized for **15 September 2026, 00:00 Europe/Berlin**. Its unchanged code remains `e43367d` in `/Users/timokruth/Projekte/SLM-conservative-optimization`; the experiment plan and frozen inputs are unchanged and were verified before scheduling. The separate CPU starter is `experiments/conservative_midnight.py`, commit `e04c080` in the main repository.

A one-shot user launchd job `local.slm.conservative-midnight-20260915` is installed and verified running. It keeps the Mac awake on AC while waiting, checks the wall clock, and cannot launch the GPU comparison before the scheduled time. This is a local OS job and does not depend on this chat staying open. It changes no permanent power settings.

At or after midnight it requires the current campaign `runs/long-horizon-round2-resume-2026-09-14/` to finish successfully, mains power, no other project GPU worker, and the exclusive GPU lease. The current training is not paused, signalled or changed. If still running, the starter waits. If it pauses/fails, the scheduled comparison does not start. The latest allowed start is **06:00 on 15 September**; unmet conditions then expire this one attempt. Waiting time does not consume the comparison's six-hour execution budget.

Immediately before launch, the starter rechecks frozen hashes and the unchanged preparation STOP, then archives only that STOP and invokes the existing `conservative_optimization.direct` watchdog. The study uses `run_slm.py` with light monitoring. It gets at most 21,600 seconds from actual launch, including controls, evaluation and cleanup; the expected latest finish is about 06:00 if it starts at midnight. No extra experiments, automatic restart, model adoption or next rotation are authorized.

Artifacts in `/Users/timokruth/Projekte/SLM-conservative-optimization/runs/conservative-fp32-6h-2026-09-12/`:

- `SCHEDULE.json`: exact date/time, expiry, predecessor and pinned scheduler/plan hashes.
- `schedule-status.json`: waiting state, heartbeat, process ID and one-shot launch latch.
- `SCHEDULE_INSTALL.json`: verified local launchd registration.
- `AUTHORIZATION.json`: this new time-constrained start instruction, distinct from the old preparation-only record.
- `status.json` and `direct-status.json`: created only after actual launch.

Cancellation: create `SCHEDULE_STOP` in that run directory. Before launch this cancels the timer; after launch it stops only the scheduled comparison's owned processes. Changing the preparation STOP also prevents its automatic release. A durable attempt latch and terminal-state checks prevent login/reload from repeating a run.

Verification before handoff: timing/predecessor/AC/busy-GPU/expiry checks passed on CPU; all original frozen inputs and package versions verified; launchd registration and fresh `waiting_for_midnight` heartbeat confirmed. The preparation STOP was still present and no GPU campaign had started. No current training inputs or historical results were modified, and nothing was pushed remotely.
