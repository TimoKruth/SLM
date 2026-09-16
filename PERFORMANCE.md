# Current workload monitoring

Regular workloads use `run_slm.py`. `run_defaults.json` sets `light` monitoring, 10 warmup steps and 60-second flushes. Each invocation writes a distinct `<run>/performance/<session>/` directory. Disable monitoring only on explicit request; `detail` is reserved for a separate diagnostic task.

The fresh supervisor is `fresh47.campaign`. Its training and evaluation children use the project launcher and share the exclusive GPU lease at `~/.cache/benchmark-slm/gpu-lease.lock`. Mains power is checked before and during work; competing supported GPU workloads are rejected. System conditions are recorded at start.

Light instrumentation measures host-side phases and existing synchronization points. It adds no GPU synchronization and does not isolate kernel time. Inclusive phase times overlap; do not sum them. Throughput comparisons must also account for actual tokens, context lengths, precision, power settings and system load.

The current campaign is prepared and STOP-blocked. See [the plan](FRESH_47_TRAINING.md). Previous performance reports are deprecated and available only in [ZIP archives](archives/README.md).
