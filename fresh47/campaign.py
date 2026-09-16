"""Explicitly authorized, one-shot fresh training; importing this module is CPU-only."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from fresh47.prepare import sha


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)

ROOT=Path(__file__).resolve().parents[1]


def validate(plan):
    assert plan['schema']=='fresh47.random.v1' and plan['source_count']==47
    assert plan['initialization']=='random' and plan['parent_checkpoint'] is None
    assert plan['optimizer_initialization']=='new' and plan['forward_precision']=='fp32'
    assert plan['total_seconds'] in [21600,86400]
    assert sum(plan['phase_seconds'].values())==plan['total_seconds']
    assert plan['phase_seconds']['evaluation']>=2*1770
    assert plan['automatic_retry'] is False and plan['automatic_adoption'] is False
    assert plan['model']['vocab_size']==16384
    assert plan['phase_seconds']['training']>90
    assert all(value>0 for value in plan['phase_seconds'].values())


def authorized(run,plan):
    validate(plan)
    if (run/'STOP').exists():raise ValueError('STOP: preparation only; an explicit later start is required')
    path=run/'AUTHORIZATION.json'
    if not path.exists():raise ValueError('Explicit start authorization is missing')
    auth=json.loads(path.read_text())
    if auth.get('start_authorized') is not True or auth.get('plan_sha256')!=sha(run/'plan.json'):
        raise ValueError('Start authorization does not match this plan')
    if (run/'status.json').exists():raise ValueError('One-shot run already has status; do not reset the budget')


def train_args(plan,run,until):
    m=plan['model']
    return ['--run',str(run/'model'),'--module','slm.train','--monitoring','light','--data',plan['data'],
            '--until',until,'--dim',str(m['dim']),'--layers',str(m['layers']),'--heads',str(m['heads']),
            '--hidden',str(m['hidden']),'--context',str(m['context']),'--batch-size','2',
            '--seed',str(plan['seed']),'--steps','10000000','--max-tokens','1000000000000',
            '--schedule-tokens',str(plan['schedule_tokens']),'--snapshot-tokens','10000000','25000000','50000000','100000000','200000000',
            '--checkpoint-seconds','300','--eval-seconds','1800','--forward-precision','fp32','--execution','compiled']


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    run=a.run.resolve();plan=json.loads((run/'plan.json').read_text());validate(plan)
    if a.dry_run:
        print(json.dumps(dict(preparation_only=True,total_seconds=plan['total_seconds'],training_command=train_args(plan,run,'SET_ONLY_ON_EXPLICIT_START'),start_blocked=(run/'STOP').exists()),indent=2));return
    authorized(run,plan)
    from slm_perf.gpu_lease import GPULease
    from slm_perf.__main__ import active_jobs
    import fcntl
    with (run/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);authorized(run,plan)
        origin=time.monotonic();deadline=origin+plan['total_seconds'];stop=[];child=None;caffeine=None
        for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,lambda *_:stop.append(True))
        state=dict(status='preflight',started=datetime.now().astimezone().isoformat(),pid=os.getpid(),
                   deadline=datetime.fromtimestamp(time.time()+plan['total_seconds']).astimezone().isoformat(),training_started=False)
        def emit(**changes):state.update(changes,heartbeat=datetime.now().astimezone().isoformat());write(run/'status.json',state)
        def terminate():
            if child is not None and child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=45)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
        def cancelled():return bool(stop) or (run/'STOP').exists() or time.monotonic()>=deadline
        def job(name,args,cutoff,lease):
            nonlocal child
            if cancelled() or active_jobs():raise RuntimeError('Stopped, deadline, or competing workload')
            with (run/'logs'/f'{name}.log').open('x') as log:
                child=subprocess.Popen([sys.executable,str(ROOT/'run_slm.py'),*args],cwd=ROOT,stdin=subprocess.DEVNULL,
                                       stdout=log,stderr=subprocess.STDOUT,start_new_session=True,**lease.child_options())
            emit(active_job=name,active_pid=child.pid)
            while child.poll() is None:
                if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True):
                    terminate();raise RuntimeError('Mains power lost; checkpoint preserved, no automatic restart')
                if cancelled() or time.monotonic()>=cutoff:
                    terminate();raise RuntimeError('Stopped or job deadline reached')
                emit();time.sleep(5)
            if child.returncode:raise RuntimeError(f'{name} failed: {child.returncode}')
            child=None;emit(active_job=None,active_pid=None)
        try:
            (run/'logs').mkdir(exist_ok=True)
            (run/'evaluations').mkdir(exist_ok=True)
            emit()
            for path,expected in plan['inputs'].items():assert sha(path)==expected,path
            if active_jobs():raise RuntimeError('GPU busy')
            conditions=dict(recorded=datetime.now().astimezone().isoformat(),power_source=subprocess.check_output(['pmset','-g','batt'],text=True),
                            power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),monitoring='light')
            if 'AC Power' not in conditions['power_source']:raise RuntimeError('Mains power required at start')
            write(run/'RUN_CONDITIONS.json',conditions)
            if time.monotonic()-origin>plan['phase_seconds']['preflight']:raise RuntimeError('Preflight budget exceeded')
            with GPULease() as lease:
                caffeine=subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(os.getpid())])
                training_end=min(time.monotonic()+plan['phase_seconds']['training'],deadline-plan['phase_seconds']['evaluation']-plan['phase_seconds']['report'])
                until=datetime.fromtimestamp(time.time()+training_end-time.monotonic()-90).astimezone().isoformat()
                emit(status='running',phase='training',training_started=True)
                job('train',train_args(plan,run,until),training_end,lease)
                training=json.loads((run/'model/status.json').read_text())
                if training['status']!='completed' or training.get('reason') not in ['deadline','token_limit','step_limit']:
                    raise RuntimeError('Training interrupted; checkpoint preserved, no automatic continuation')
                eval_end=min(time.monotonic()+plan['phase_seconds']['evaluation'],deadline-plan['phase_seconds']['report'])
                jobs=[('final-dev',run/'model','dev','latest'),('final-confirmation',run/'model','confirmation','latest')]
                emit(phase='evaluation')
                for name,model,split,checkpoint in jobs:
                    if eval_end-time.monotonic()<1770:raise RuntimeError('Insufficient evaluation reserve')
                    suite=Path(plan['data'])/f'{split}-suite.json';out=run/'evaluations'/name
                    args=['--run',str(model),'--module','slm.broad_eval','--monitoring','light','--suite',str(suite),
                          '--output',str(out),'--checkpoint',checkpoint,'--maximum','256','--max-seconds','1740','--skip-code','--answer-loss']
                    job(name,args,min(eval_end,time.monotonic()+1770),lease)
                    summary=json.loads((out/'summary.json').read_text());n=len(json.loads(suite.read_text())['general'])
                    assert summary['evaluated_general']==n and summary['answer_loss']['examples']==n and not summary['deadline_reached']
                    assert not any(v['context_exceeded'] for v in summary['by_source'].values())
            emit(phase='report')
            results={p.parent.name:json.loads(p.read_text()) for p in (run/'evaluations').glob('*/summary.json')}
            for path,expected in plan['inputs'].items():assert sha(path)==expected,path
            report=dict(status='completed',initialization='random',source_count=47,training=training,evaluations=results,
                        automatic_adoption=False,historical_results_comparable=False,inputs_unchanged=True)
            write(run/'RESULT.json',report)
            (run/'REPORT.md').write_text('# Fresh 47-source training\n\nRandom initialization, new train-only tokenizer, no legacy checkpoint. Primary endpoint: final checkpoint on sealed confirmation.\n\n'+
                '\n'.join(f"- {name}: {s['evaluated_general']} tasks; per-family accuracy {s['mean_source_accuracy_by_family']}" for name,s in results.items())+
                '\n\nHistorical small-list results are deprecated. These are internal source-specific proxies, not official benchmark scores or proof of transfer. Code/SQL functionality and summary factuality remain unmeasured.\n')
            if cancelled():raise RuntimeError('Final deadline/stop')
            emit(status='completed',phase='finished',finished=datetime.now().astimezone().isoformat(),budget_spent_seconds=time.monotonic()-origin)
        except BaseException as exc:
            terminate();(run/'STOP').write_text('Paused; no automatic restart. Preserve checkpoint and consumed budget.\n')
            emit(status='paused',error=str(exc),budget_spent_seconds=time.monotonic()-origin);raise
        finally:
            terminate()
            if caffeine is not None:caffeine.terminate();caffeine.wait(timeout=5)


if __name__=='__main__':main()
