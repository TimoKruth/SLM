# Local training dashboard

Open **http://127.0.0.1:8766/** on this Mac. The dashboard is running as an independent, CPU-only local process and reads the fresh 47-source campaign. Refresh the page or use **Refresh** for a new snapshot; optional **Auto · 30s** refreshes every 30 seconds.

- Graphs: cumulative training tokens, optimizer updates, evaluated development answer loss, and training throughput.
- **Current session / Full history** selects the time range.
- **Continuous training** removes gaps between recorded sessions and labels the axis as elapsed logged session time. This estimates pause boundaries from the logs; it is not exact GPU execution time. Missing samples within a session stay gaps. Checkpoint rollback points remain visible.
- Range and continuous-view preferences persist across reloads. The original wall-clock timestamps remain available in chart tooltips.
- Throughput graph points average the recorded samples within each minute; cumulative graphs retain minute endpoints and exact session starts. The speed card shows the latest fresh training sample. Development loss is plotted on a labeled logarithmic scale and is not benchmark accuracy.
- Paused status shows the recoverable checkpoint counts instead of stale unsaved trainer progress. Missing/stale telemetry is distinguished from a live run. Final dev, confirmation and report completion are shown separately.

The server binds only to `127.0.0.1`, has no training controls, and serves only its static assets and a whitelisted aggregate status response. It does not load a model, import MLX, access raw examples/responses, alter any run file, or change frozen training inputs. It reads the campaign status and JSONL metrics on each refresh; there are no external dependencies or CDN calls in the page.

After a reboot, start it again from the repository:

```sh
.venv/bin/python -m training_dashboard.server \
  --run runs/fresh47-97m-2026-09-16 --port 8766
```

The run is explicitly selected, so a future campaign cannot silently replace the one you are viewing. Use its directory with `--run` when starting a different dashboard. The current detached server PID and URL are recorded locally under `runs/training-dashboard/server.json`; stopping that server does not stop training. No login/startup service is installed.

Validation: five Python tests cover log sampling/resume boundaries/partial writes, stale and paused state, partial evaluations, and HTTP route restrictions. Two Node tests verify pause compression and current-session time offsets. Safari visual checks covered all four rendered charts, full-history/continuous toggles and fresh values plus preference persistence after reload.

```sh
.venv/bin/python -m pytest -q tests/test_training_dashboard.py
node --test tests/training_dashboard_axis.cjs
```
