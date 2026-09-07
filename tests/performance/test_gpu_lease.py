"""Process-level lease regressions; no MLX import, device allocation or training."""
import json
import os
from pathlib import Path
import select
import subprocess
import sys

import pytest
from slm_perf.gpu_lease import FD_ENV, GPUBusy, GPULease

ROOT = Path(__file__).resolve().parents[2]


def await_owner(child):
    """Bound the child handshake so a locking regression cannot hang the test suite."""
    readable, _, _ = select.select([child.stdout], [], [], 5)
    assert readable, 'child did not acknowledge lease ownership'
    assert child.stdout.readline().strip() == 'owned'


def probe(path):
    """Try the same lock in a separate process, returning 23 when it is busy."""
    code = '''
import sys
from slm_perf.gpu_lease import GPULease, GPUBusy
try:
    with GPULease(sys.argv[1]): pass
except GPUBusy:
    raise SystemExit(23)
'''
    return subprocess.run([sys.executable, '-c', code, str(path)], cwd=ROOT,
                          env={k: v for k, v in os.environ.items() if k != FD_ENV}, timeout=10).returncode


def test_lease_serializes_processes_and_releases_after_exception(tmp_path):
    """A second process cannot acquire the lock until its owner exits the context."""
    path = tmp_path / 'gpu.lock'
    with pytest.raises(ValueError):
        with GPULease(path):
            assert probe(path) == 23
            raise ValueError('work failed')
    assert probe(path) == 0


def test_inherited_lease_stays_held_until_child_exit(tmp_path):
    """Closing the parent's descriptor cannot expose the GPU while its child runs."""
    path = tmp_path / 'gpu.lock'
    code = '''
import sys
from slm_perf.gpu_lease import GPULease
with GPULease(sys.argv[1]):
    print('owned', flush=True)
    sys.stdin.readline()
'''
    child = None
    try:
        with GPULease(path) as lease:
            child = subprocess.Popen([sys.executable, '-c', code, str(path)], cwd=ROOT,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                     **lease.child_options())
            await_owner(child)
        assert probe(path) == 23
        child.communicate('\n', timeout=10)
        assert child.returncode == 0
        assert probe(path) == 0
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait()


def test_off_mode_descriptor_survives_exec(tmp_path):
    """Replacing the launcher with an uninstrumented process must retain its lease."""
    path = tmp_path / 'gpu.lock'
    code = '''
import os,sys
from slm_perf.gpu_lease import GPULease
with GPULease(sys.argv[1]) as lease:
    lease.survive_exec()
    os.execv(sys.executable,[sys.executable,'-c',"import sys; print('owned', flush=True); sys.stdin.readline()"])
'''
    child = subprocess.Popen([sys.executable, '-c', code, str(path)], cwd=ROOT,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        await_owner(child)
        assert probe(path) == 23
        child.communicate('\n', timeout=10)
        assert probe(path) == 0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


def test_launcher_refuses_a_held_lease_before_work(tmp_path, monkeypatch):
    """An empty process snapshot cannot bypass a lease already held by another owner."""
    from types import SimpleNamespace
    from slm_perf import __main__ as cli, gpu_lease
    path = tmp_path / 'gpu.lock'
    monkeypatch.setattr(gpu_lease, 'LOCK_PATH', path)
    monkeypatch.setattr(cli, 'active_jobs', lambda: [])
    with GPULease(path):
        with pytest.raises(GPUBusy):
            cli.launch(SimpleNamespace(module='slm.train', mode='light'))


@pytest.mark.parametrize('bad', [None, [], 'invalid', 3])
@pytest.mark.parametrize('broken', ['supervisor', 'benchmark'])
def test_queue_rejects_non_object_status(tmp_path, monkeypatch, bad, broken):
    """Valid JSON with the wrong shape must be treated as not ready, not as an exception."""
    from slm_perf import after_idle, __main__ as cli
    run, prior = tmp_path / 'run', tmp_path / 'prior'
    run.mkdir()
    prior.mkdir()
    (run / 'supervisor.json').write_text(json.dumps(bad if broken == 'supervisor' else {'phase': 'finished'}))
    (prior / 'status.json').write_text(json.dumps(bad if broken == 'benchmark' else {'status': 'completed'}))
    monkeypatch.setattr(cli, 'active_jobs', lambda: [])
    assert not after_idle.ready({'run': str(run), 'prior_benchmark': str(prior)})


@pytest.mark.parametrize('failure', [RuntimeError, KeyboardInterrupt])
def test_queue_reaps_both_children_after_poll_failure(tmp_path, monkeypatch, failure):
    """Unexpected watcher failures must reap calibration and caffeinate and release the lease."""
    from slm_perf import after_idle, gpu_lease, __main__ as cli
    run, out = tmp_path / 'run', tmp_path / 'out'
    run.mkdir()
    out.mkdir()
    (run / 'status.json').write_text('{"status":"completed"}')
    monkeypatch.setattr(after_idle, 'OUT', out)
    monkeypatch.setattr(gpu_lease, 'LOCK_PATH', tmp_path / 'gpu.lock')
    processes = []

    class Child:
        """Represent an owned process and record that it was terminated and reaped."""
        def __init__(self, *args, **kwargs):
            """Keep launch options for the inherited-descriptor assertion."""
            self.pid = 700 + len(processes)
            self.returncode = None
            self.waited = False
            self.options = kwargs
            processes.append(self)

        def poll(self):
            """Expose whether cleanup has stopped this fake process."""
            return self.returncode

        def terminate(self):
            """Record graceful termination without touching a real process."""
            self.returncode = -15

        def wait(self, timeout=None):
            """Record that the parent reaped the process."""
            self.waited = True
            return self.returncode

    def active():
        """Fail only after both children have been launched."""
        if len(processes) == 2:
            raise failure('poll failed')
        return []

    monkeypatch.setattr(cli, 'active_jobs', active)
    monkeypatch.setattr(after_idle.subprocess, 'Popen', Child)
    with pytest.raises(failure):
        after_idle.run_calibration({'run': str(run), 'source_sha256': {}, 'timeout_seconds': 60})
    assert len(processes) == 2
    assert all(p.waited and p.returncode == -15 for p in processes)
    assert processes[1].options['pass_fds']
    with GPULease(tmp_path / 'gpu.lock'):
        pass


def test_direct_queue_script_has_actionable_error(tmp_path):
    """An unsupported file invocation must stop before accessing queue files."""
    result = subprocess.run([sys.executable, str(ROOT / 'slm_perf/after_idle.py')], cwd=tmp_path,
                            text=True, capture_output=True, timeout=10)
    assert result.returncode != 0
    assert 'python -m slm_perf.after_idle' in result.stderr
    assert 'ImportError' not in result.stderr
    assert not list(tmp_path.iterdir())


def test_cleanup_escalates_and_reaps_unresponsive_child():
    """A child ignoring termination must be killed and reaped within bounded cleanup."""
    from unittest.mock import Mock
    from slm_perf.after_idle import stop_process
    child = Mock()
    child.poll.return_value = None
    child.wait.side_effect = [subprocess.TimeoutExpired('test-child', 5), -9]
    stop_process(child)
    child.terminate.assert_called_once()
    child.kill.assert_called_once()
    assert child.wait.call_count == 2


def test_cleanup_has_a_deadline_after_kill():
    """An unreapable process must produce an error after two bounded waits."""
    from unittest.mock import Mock
    from slm_perf.after_idle import CleanupTimeout, stop_process
    child = Mock(pid=123)
    child.poll.return_value = None
    child.wait.side_effect = subprocess.TimeoutExpired('test-child', 5)
    with pytest.raises(CleanupTimeout, match='Process 123'):
        stop_process(child)
    assert [c.kwargs for c in child.wait.call_args_list] == [{'timeout': 5}, {'timeout': 5}]


def test_cleanup_error_still_cleans_other_child_and_records_failure(tmp_path, monkeypatch):
    """A stuck calibration child must not skip caffeinate cleanup or look successful."""
    from unittest.mock import Mock
    from slm_perf import after_idle, gpu_lease, __main__ as cli
    run, out = tmp_path / 'run', tmp_path / 'out'
    run.mkdir()
    out.mkdir()
    (run / 'status.json').write_text('{"status":"completed"}')
    monkeypatch.setattr(after_idle, 'OUT', out)
    monkeypatch.setattr(gpu_lease, 'LOCK_PATH', tmp_path / 'gpu.lock')
    monkeypatch.setattr(cli, 'active_jobs', lambda: [])
    caffeine, child = Mock(pid=1), Mock(pid=2)
    child.poll.return_value = 0
    child.returncode = 0
    spawn = Mock(side_effect=[caffeine, child])
    stop = Mock(side_effect=[after_idle.CleanupTimeout('stuck child'), None])
    monkeypatch.setattr(after_idle.subprocess, 'Popen', spawn)
    monkeypatch.setattr(after_idle, 'stop_process', stop)
    with pytest.raises(RuntimeError, match='cleanup failed'):
        after_idle.run_calibration({'run': str(run), 'source_sha256': {}, 'timeout_seconds': 60})
    assert [c.args[0] for c in stop.call_args_list] == [child, caffeine]
    status = json.loads((out / 'status.json').read_text())
    assert status['status'] == 'cleanup_failed'
    assert status['processes'] == [{'pid': 2, 'error': 'stuck child'}]
