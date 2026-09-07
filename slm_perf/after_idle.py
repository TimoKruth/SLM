"""One-shot calibration queue, sequenced after the existing run and GPU benchmark."""
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/monitoring-2026-09-07'
_shutdown_signal = None


class CleanupTimeout(RuntimeError):
    """An owned child did not exit within either bounded termination wait."""


def save(**status):
    """Atomically replace the queue heartbeat with a timezone-aware timestamp."""
    path = OUT / 'status.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(dict(updated_at=datetime.now().astimezone().isoformat(), **status), indent=2) + '\n')
    temporary.replace(path)


def ready(plan):
    """Treat missing or malformed prerequisite status as not ready, without GPU work."""
    from .__main__ import active_jobs
    run, prior = Path(plan['run']), Path(plan['prior_benchmark'])
    try:
        supervisor = json.loads((run / 'supervisor.json').read_text())
        before = json.loads((prior / 'status.json').read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    if not isinstance(supervisor, dict) or not isinstance(before, dict):
        return False
    terminal = {'completed', 'benchmark_failed', 'benchmark_timeout', 'expired_without_gpu_benchmark',
                'skipped_source_changed', 'skipped_training_not_completed', 'cancelled'}
    return supervisor.get('phase') == 'finished' and before.get('status') in terminal and not active_jobs()


def stop_process(process):
    """Reap an owned child, escalating to kill if graceful termination takes too long."""
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired as exc:
            raise CleanupTimeout(f'Process {process.pid} did not exit after terminate and kill') from exc


def run_calibration(plan):
    """Reserve the GPU before spawn and clean up both children on every Python exit path."""
    from .__main__ import active_jobs
    from .gpu_lease import GPULease
    run = Path(plan['run'])
    with GPULease() as lease:
        # Legacy/direct entry points do not own leases, so retain their process guard too.
        if active_jobs():
            from .gpu_lease import GPUBusy
            raise GPUBusy('A legacy SLM GPU process is active')
        status = json.loads((run / 'status.json').read_text())
        if not isinstance(status, dict) or status.get('status') != 'completed':
            save(status='skipped_training_not_completed')
            return
        for path, digest in plan['source_sha256'].items():
            if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
                save(status='skipped_source_changed', file=path)
                return
        child = caffeine = None
        try:
            save(status='calibration_running')
            caffeine = subprocess.Popen(['/usr/bin/caffeinate', '-is', '-w', str(os.getpid())])
            with (OUT / 'calibration.log').open('w') as log:
                command = [sys.executable, '-u', '-m', 'slm_perf.ab', '--run', str(run), '--output', str(OUT / 'calibration')]
                if plan.get('metal_capture'):
                    command.append('--metal-capture')
                options = lease.child_options()
                options['env']['MTL_CAPTURE_ENABLED'] = '1'
                child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, **options)
                cutoff = time.monotonic() + plan['timeout_seconds']
                while child.poll() is None:
                    competitors = [pid for pid in active_jobs() if pid != child.pid]
                    cancelled = _shutdown_signal is not None or (OUT / 'STOP').exists() or (run / 'STOP').exists()
                    if competitors or cancelled or time.monotonic() >= cutoff:
                        save(status='yielded_to_other_gpu_job' if competitors else ('cancelled' if cancelled else 'calibration_timeout'))
                        return
                    time.sleep(2)
                save(status='completed' if child.returncode == 0 else 'calibration_failed', exit_code=child.returncode)
        except BaseException as exc:
            try:
                save(status='calibration_failed', error=type(exc).__name__)
            except OSError:
                pass
            raise
        finally:
            cleanup_errors = []
            for process in (child, caffeine):
                try:
                    stop_process(process)
                except Exception as exc:
                    cleanup_errors.append({'pid': process.pid, 'error': str(exc)})
            if cleanup_errors:
                try:
                    save(status='cleanup_failed', processes=cleanup_errors)
                finally:
                    raise RuntimeError(f'Calibration cleanup failed: {cleanup_errors}')


def run_queue():
    """Wait for prerequisites and a shared lease without extending the queue deadline."""
    from .gpu_lease import GPUBusy
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'queue.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = json.loads((OUT / 'plan.json').read_text())
        run = Path(plan['run'])
        deadline = datetime.fromisoformat(plan['queue_deadline']).timestamp()
        while time.time() < deadline:
            if _shutdown_signal is not None or (OUT / 'STOP').exists() or (run / 'STOP').exists():
                save(status='cancelled')
                return
            if ready(plan):
                try:
                    run_calibration(plan)
                    return
                except GPUBusy:
                    pass
            save(status='waiting_for_training_evaluation_and_prior_benchmark', pid=os.getpid())
            time.sleep(30)
        save(status='expired')


def interrupted(signum, frame):
    """Record shutdown without raising between resource acquisition and cleanup."""
    global _shutdown_signal
    if _shutdown_signal is None:
        _shutdown_signal = signum


def main():
    """Report signal exit only after the queue has unwound child and lease cleanup."""
    try:
        run_queue()
    finally:
        if _shutdown_signal is not None:
            raise SystemExit(128 + _shutdown_signal)


if __name__ == '__main__':
    if not __package__:
        raise SystemExit('Use the package entry point: python -m slm_perf.after_idle')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    main()
