"""Resume a user-paused campaign in an independently copied run, preserving budgets."""
import argparse
import copy
from datetime import datetime
import math
import os
from pathlib import Path
import signal
import subprocess
import time

from research.common import read, write, sha, quality
from slm_perf.after_idle import stop_process
from study.safety import RecoverableStop
from .campaign import Runner
from .protocol import signature
from .report import report


def remaining_jobs(plan, spec, previous):
    if previous['status'] != 'paused' or not previous.get('frozen_inputs_unchanged'):
        raise ValueError('Source must be a validated paused campaign')
    spent = previous['total_budget_spent_seconds'] + spec['preparation_seconds']
    if spec['preparation_seconds'] < 0 or not math.isclose(plan['previous_budget_spent_seconds'], spent, abs_tol=.001):
        raise ValueError('Incorrect cumulative budget')
    if not math.isclose(spent + plan['budget_seconds'], 86400, abs_tol=.001):
        raise ValueError('Budget reset or extension')
    if not 0 < plan['budget_seconds'] <= 86400:
        raise ValueError('Invalid remaining budget')
    completed = set(spec['completed_jobs'])
    if not completed.issubset(plan['jobs']) or len(set(plan['jobs'])) != 8:
        raise ValueError('Changed job list')
    recorded = {s['name'] for s in previous['stages'] if s['status'] == 'completed'}
    if not completed.issubset(recorded):
        raise ValueError('Cannot reuse incomplete training')
    pending = [name for name in plan['jobs'] if name not in completed]
    if not pending or pending[0] != spec['partial_job']:
        raise ValueError('Partial job must be first remaining job')
    used = sum(s['elapsed_seconds'] for s in previous['stages'] if s['name'] == spec['partial_job'])
    if not math.isclose(used, spec['partial_spent_seconds'], abs_tol=.001) or not 0 < used < 7140:
        raise ValueError('Incorrect partial stage budget')
    required = len(pending) * (7200 + 4 * plan['evaluation_process_seconds']) - used + 20 + plan['report_seconds']
    if required + 60 > plan['budget_seconds']:
        raise ValueError('Remaining stage caps exceed budget')
    return pending


def run_pending(runner, plan, spec, pending):
    for name in pending:
        trial = runner.run / 'trials' / name
        job = read(runner.run / 'jobs' / (name + '.json'))
        seconds = job['train_seconds']
        args = ['--plan', str(runner.run / 'plan.json'), '--job', str(runner.run / 'jobs' / (name + '.json'))]
        if name == spec['partial_job']:
            seconds -= spec['partial_spent_seconds']
            args += ['--resume', '--wall-seconds', str(seconds)]
        runner.job(name, 'long_study.trial', trial, args, seconds)
        if read(trial / 'result.json')['status'] != 'completed':
            raise RecoverableStop('Incomplete time endpoint')
        for target in [15000000, 50000000]:
            folder = trial / f'token-{target:09d}'
            if folder.exists():
                runner.evaluate(folder, name + f'-{target}-search')
            else:
                runner.state.setdefault('missing_token_snapshots', []).append(str(folder))
        runner.evaluate(trial, name + '-search')
        runner.evaluate(trial, name + '-confirmation', 'confirmation')
        report(runner.run, runner.state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = Path(args.run).resolve()
    if (run / 'STOP').exists() or (run / 'status.json').exists():
        raise ValueError('STOP or existing session blocks start')
    plan, spec, previous = [read(run / name) for name in ('plan.json', 'resume.json', 'previous-status.json')]
    pending = remaining_jobs(plan, spec, previous)
    started, clock, stop = time.time(), time.monotonic(), []
    state = dict(status='running', phase='resume-verify', pid=os.getpid(),
                 started=datetime.now().astimezone().isoformat(),
                 deadline=datetime.fromtimestamp(started + plan['budget_seconds']).astimezone().isoformat(),
                 source_campaign=spec['source_campaign'],
                 stages=[dict(copy.deepcopy(s), reused=True) for s in previous['stages'] if s['status'] == 'completed'],
                 gpu_recovery_attempts=previous.get('gpu_recovery_attempts', 0))
    write(run / 'status.json', state)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda n, f: stop.append(n))
    runner = Runner(run, plan, state, clock + plan['budget_seconds'] - plan['report_seconds'], stop)
    caffeine = None
    try:
        runner.verify(full=True)
        for path, digest in spec['initial_copy_hashes'].items():
            if sha(Path(path)) != digest:
                raise ValueError('Copied artifact mismatch: ' + path)
        for name in spec['completed_jobs']:
            if read(run / 'trials' / name / 'result.json')['status'] != 'completed':
                raise ValueError('Incomplete copied trial')
            for suffix in ('token-015000000/search', 'token-050000000/search', 'search', 'confirmation'):
                quality(read(run / 'trials' / name / suffix / 'summary.json'))
        trial = run / 'trials' / spec['partial_job']
        checkpoint = trial / read(trial / 'latest.json')['checkpoint']
        restored = read(checkpoint / 'state.json')
        expected = signature(plan, read(run / 'jobs' / (spec['partial_job'] + '.json')))
        if restored['long_signature'] != expected or 'sampler_state' not in restored:
            raise ValueError('Invalid resume checkpoint signature or sampler')
        caffeine = subprocess.Popen(['/usr/bin/caffeinate', '-is', '-w', str(os.getpid())])
        runner.job('health-resume', 'study.health', run / 'health-resume', ['--seconds', '3'], 20)
        run_pending(runner, plan, spec, pending)
        state.update(status='completed', phase='finished')
    except BaseException as exc:
        state.update(status='paused', error=repr(exc))
        (run / 'STOP').write_text('Paused; preserve remaining budget and results.\n')
    finally:
        stop_process(caffeine)
        state.update(finished=datetime.now().astimezone().isoformat(), elapsed_seconds=time.time() - started,
                     total_budget_spent_seconds=plan['previous_budget_spent_seconds'] + time.time() - started)
        try:
            runner.verify(full=True)
            state['frozen_inputs_unchanged'] = True
        except BaseException as exc:
            state.update(status='invalid', error=repr(exc), frozen_inputs_unchanged=False)
        write(run / 'status.json', state)
        report(run, state)
    if state['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
