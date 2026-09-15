"""Bounded five-checkpoint 75M confirmation controller; children use the project's monitored launcher."""
import argparse
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
sys.path.insert(0, str(ROOT))


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def now():
    return datetime.now().astimezone().isoformat()


def verify(inputs):
    for path, expected in inputs.items():
        if sha(path) != expected:
            raise ValueError('Frozen input changed: ' + path)


def validate_summary(summary, expected):
    if (summary['selected_general'] != expected or summary['evaluated_general'] != expected
            or summary['answer_loss']['examples'] != expected or summary['deadline_reached']):
        raise ValueError('Incomplete evaluation')
    if sum(s['scored'] for s in summary['by_source'].values()) != 1280:
        raise ValueError('Unexpected scored coverage')
    if any(s['context_exceeded'] for s in summary['by_source'].values()):
        raise ValueError('Context limit exceeded')


def stop_child(child):
    if child is None or child.poll() is not None:
        return
    os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=5)


def validate_plan(plan):
    assert plan['mode'] == 'evaluation_only' and len(plan['jobs']) == 5
    assert plan['total_budget_seconds'] == 5400
    assert plan['deadline_unix']-plan['budget_origin_unix'] == 5400
    assert {(j['condition'], j['order'], j['endpoint']) for j in plan['jobs']} == {
        ('parent', None, 'parent'), ('A', 0, '75M'), ('D', 0, '75M'), ('A', 1, '75M'), ('D', 1, '75M')}
    for order in (0, 1):
        pair = [j for j in plan['jobs'] if j['order'] == order]
        assert len({(j['additional_tokens'], j['step']) for j in pair}) == 1
        assert 75000000 <= pair[0]['additional_tokens'] < 75010000
    assert plan['gates'] == dict(minimum_gain_vs_A_per_order=0.02, strictly_positive_vs_parent_per_order=True,
                                 maximum_mean_family_regression_vs_each_reference=0.05, automatic_adoption=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    plan = read(run/'plan.json')
    with (run/'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (run/'status.json').exists() or (run/'STOP').exists():
            raise ValueError('Refusing reuse or STOP-guarded run')
        validate_plan(plan)
        assert plan['max_seconds_per_evaluation'] == 600 and plan['maximum_generated_tokens'] == 256
        assert sha(__file__) == plan['controller_sha256']
        from slm_perf.gpu_lease import GPULease
        from slm_perf.__main__ import active_jobs
        stopped = []
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: stopped.append(True))
        state = dict(status='preflight', phase='verification', pid=os.getpid(), started=now(),
                     deadline=plan['deadline'], completed_evaluations=0, planned_evaluations=5,
                     evaluations={}, automatic_adoption=False)
        child = None
        deadline = time.monotonic() + max(0, plan['deadline_unix']-time.time())
        def emit(**changes):
            state.update(changes, heartbeat=now())
            write(run/'status.json', state)
        def cancelled():
            return bool(stopped) or (run/'STOP').exists() or time.monotonic() >= deadline
        try:
            emit()
            verify(plan['inputs'])
            if cancelled():
                raise RuntimeError('Stopped or deadline reached before evaluation')
            if active_jobs():
                raise RuntimeError('Another GPU workload is active')
            with GPULease() as lease:
                if active_jobs():
                    raise RuntimeError('Another GPU workload became active')
                if time.time()-plan['budget_origin_unix'] > 1200:
                    raise RuntimeError('Preparation exceeded 20-minute limit')
                evaluation_deadline = min(deadline-900, time.monotonic()+3300)
                emit(status='running', phase='evaluation')
                for job in plan['jobs']:
                    if cancelled() or evaluation_deadline-time.monotonic() < 630:
                        raise RuntimeError('Insufficient evaluation budget or requested stop')
                    # All original/copy/code/suite hashes are checked at admission and completion;
                    # each selected checkpoint and suite are rechecked immediately before use.
                    verify({p: plan['inputs'][p] for p in job['input_paths']})
                    if active_jobs():
                        raise RuntimeError('Competing GPU workload detected')
                    target = run/'evaluations'/job['id']
                    if target.exists():
                        raise ValueError('Evaluation output already exists')
                    conditions = dict(recorded_at=now(), power_source=subprocess.check_output(['pmset','-g','batt'],text=True),
                                      power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),
                                      monitoring='light', interpretation='Saved-checkpoint quality evaluation; no speed comparison or training.')
                    write(run/'conditions'/(job['id']+'.json'), conditions)
                    command = [sys.executable, str(ROOT/'run_slm.py'), '--run', job['shadow'], '--module', 'slm.broad_eval',
                               '--monitoring', 'light', '--suite', str(run/'confirmation-suite.json'), '--output', str(target),
                               '--checkpoint', 'latest', '--maximum', '256', '--max-seconds', '600', '--skip-code', '--answer-loss']
                    started = time.monotonic()
                    with (run/'logs'/(job['id']+'.log')).open('x') as log:
                        child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                                 stderr=subprocess.STDOUT, start_new_session=True, **lease.child_options())
                    state['evaluations'][job['id']] = dict(status='running', started=now(), pid=child.pid,
                                                          checkpoint_sha256=job['checkpoint_sha256'])
                    emit(active_evaluation=job['id'], active_pid=child.pid)
                    while child.poll() is None:
                        if cancelled() or time.monotonic() >= evaluation_deadline or time.monotonic()-started >= 630:
                            stop_child(child)
                            raise RuntimeError('Requested stop or evaluation/total time limit')
                        result = target/'results.jsonl'
                        generated = sum(1 for _ in result.open()) if result.exists() else 0
                        emit(generated_in_active_evaluation=generated)
                        time.sleep(2)
                    if child.returncode != 0:
                        raise RuntimeError(job['id']+' failed with exit '+str(child.returncode))
                    summary = read(target/'summary.json')
                    validate_summary(summary, 1360)
                    protocol = read(target/'protocol.json')
                    assert protocol['checkpoint_sha256'] == job['checkpoint_sha256']
                    assert protocol['suite_sha256'] == plan['inputs'][str(run/'confirmation-suite.json')]
                    state['evaluations'][job['id']].update(status='completed', finished=now(),
                        elapsed_seconds=time.monotonic()-started,
                        accuracy=sum(summary['mean_source_accuracy_by_family'].values())/len(summary['mean_source_accuracy_by_family']),
                        answer_loss=summary['answer_loss']['macro_source_answer_loss'])
                    state['completed_evaluations'] += 1
                    emit(active_evaluation=None, active_pid=None, generated_in_active_evaluation=None)
                    child = None
                verify(plan['inputs'])
                emit(status='evaluations_completed', phase='analysis', frozen_inputs_unchanged=True)
                write(run/'evaluation-completion.json', state)
            # CPU analysis releases the GPU lease and remains inside the same hard budget.
            with (run/'logs'/'analysis.log').open('x') as log:
                child = subprocess.Popen([sys.executable, str(ROOT/'experiments/report_parameter_confirmation.py'),
                                          '--run', str(run)], cwd=ROOT, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            analysis_started = time.monotonic()
            while child.poll() is None:
                if cancelled() or time.monotonic()-analysis_started >= 900:
                    stop_child(child)
                    raise RuntimeError('Analysis deadline or requested stop')
                emit()
                time.sleep(2)
            if child.returncode != 0:
                raise RuntimeError('CPU analysis failed')
            child = None
            verify(plan['inputs'])
            if cancelled():
                raise RuntimeError('Deadline or stop before final integrity completion')
            emit(status='completed', phase='finished', finished=now(),
                 budget_spent_seconds=time.time()-plan['budget_origin_unix'],
                 report=str(run/'analysis/REPORT.md'), frozen_inputs_unchanged=True)
        except BaseException as exc:
            stop_child(child)
            if state.get('active_evaluation'):
                state['evaluations'][state['active_evaluation']]['status'] = 'interrupted'
            (run/'STOP').write_text('Evaluation controller stopped; no automatic retry.\n')
            emit(status='paused', phase='stopped', error=str(exc), finished=now(), active_pid=None)
            raise
        finally:
            stop_child(child)


if __name__ == '__main__':
    main()
