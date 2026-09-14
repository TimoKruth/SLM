# Conservative comparison restarted — 15 September 2026

The user requested a fix and continuation or restart after the midnight comparison paused. The verified cause was `Matched exposure not reached`: the first baseline fell short of 16,384 updates before its 2,690-second training cutoff, and the worker raised before the final checkpoint. No GPU hang was reported. Historical logs and periodic checkpoints remain unchanged and STOP-locked.

The repaired study started **15 September at 01:47:37 Europe/Berlin**, with a hard deadline of **06:44:47**. Authoritative state: `/Users/timokruth/Projekte/SLM-conservative-recovery/runs/conservative-fp32-recovery-2026-09-15/status.json` and `direct-status.json`. Code: branch `codex/conservative-recovery`, commit `781ccb4`, worktree `/Users/timokruth/Projekte/SLM-conservative-recovery`; design details in its `CONSERVATIVE_RECOVERY.md`.

All six long comparisons restart uniformly from the original parent: FP32, synchronization every one versus four updates, three paired data orders, 2,100 process seconds each, and matched quality snapshots after 8,192 updates. Both original 384/288-task suites and every quality gate remain unchanged. The failed baseline is excluded from the new comparisons; this revised endpoint is not a result for the original 16,384-update design.

Twenty completed replay controls, the checkpoint control and two parent evaluations are preserved in 93 independently copied, verified files. A fresh real checkpoint continuation control precedes the restarted long trials. The final-checkpoint failure path is repaired: a missing matched endpoint now preserves model/Adam/sampler and writes an explicit paused result. Missing quality evidence still blocks a success claim. 55 CPU tests passed, followed by 10 targeted tests after the last preparation change.

Original total budget: **21,600 seconds**. Failed attempt charged: **3,173 seconds**. Diagnosis/preparation plus launch reserve charged: **597 seconds**. New session maximum: **17,830 seconds (4h 57m 10s)**. Pause time excluded; no fresh six-hour allocation. Planned remaining maxima total 16,260 seconds, with 1,570 seconds additional contingency inside the cap.

AC power, exclusive GPU lease, light monitoring and PowerWatch remain active. To stop this session, create `STOP` in its run directory. No automatic retry, extension or model adoption. The older long-horizon training campaign completed successfully on 14 September at 23:55; it is not being restarted.
