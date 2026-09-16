# Live system monitoring

PowerWatch remains active independently of model training and the legacy archive migration. The live dashboard is `runs/system-resources/latest.html`; adapter status is `runs/system-resources/status.json`.

The existing collector samples about every 15 seconds and retains a 30-day history in `~/Library/Application Support/PowerWatch/data/powerwatch.sqlite3`. The read-only reporting adapter refreshes the dashboard every minute. Its source is `resource_monitor/report.py`; its installed copy runs independently of Git worktrees.

User services are `com.local.powerwatch` and `com.local.powerwatch.slm-report` under `~/Library/LaunchAgents/`. The collector was left running unchanged. During preparation, the reporting job was repaired to use the existing working Python interpreter because `/usr/bin/python3` was blocked by the Xcode license prompt. No license was accepted; fresh dashboard output was verified. `resource_monitor/install.py` now uses its invoking interpreter (or explicit `--python`) and verifies it before replacing the reporting service. The collector still uses its original interpreter configuration; after a future login/reboot, verify it is collecting fresh samples before starting training.

Always check measurement age. CPU/GPU figures cover the whole system, free RAM differs from reclaimable available RAM, and sleep creates gaps. GPU driver percentages are not a measurement of peak compute or memory bandwidth. System process logs remain private and do not belong in the public repository.

The live monitoring directory is operational telemetry, not a deprecated model-result directory, and remains unpacked. Historical experiment-specific resource reports are in the private ZIP archives.
