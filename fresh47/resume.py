"""Explicit one-shot continuation, preserving the original absolute deadlines.

CPU-only supervisor; all GPU children use the frozen run_slm launcher.
The original campaign and every frozen numerical input remain unchanged.
"""
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
from fresh47.campaign import train_args, validate


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)

ROOT=Path(__file__).resolve().parents[1]


def continuation(run, plan, request, now=None):
    """Fail closed before changing STOP/status or starting any workload."""
    validate(plan)
    now = time.time() if now is None else now
    auth = json.loads(request.read_text())
    if auth.get('resume_authorized') is not True:
        raise ValueError('Explicit resume authorization missing')
    if auth['plan_sha256'] != sha(run/'plan.json'):
        raise ValueError('Frozen plan mismatch')
    if auth['controller_sha256'] != sha(Path(__file__)):
        raise ValueError('Continuation controller mismatch')
    if request.with_suffix('.consumed.json').exists():
        raise ValueError('Continuation authorization already consumed; no automatic retry')
    for relative, expected in auth['resume_inputs'].items():
        if sha(run/relative) != expected:
            raise ValueError(f'Continuation input changed: {relative}')
    state = json.loads((run/'status.json').read_text())
    if state['status'] != 'paused' or state['phase'] != 'training':
        raise ValueError('Only a paused training phase can continue')
    if not (run/'STOP').exists():
        raise ValueError('Expected preserved pause STOP')
    if state['deadline'] != auth['deadline'] or state['started'] != auth['original_started']:
        raise ValueError('Original budget timestamps changed')
    config = json.loads((run/'model/config.json').read_text())
    if config['until'] != auth['training_until']:
        raise ValueError('Original training cutoff changed')
    deadline = datetime.fromisoformat(state['deadline']).timestamp()
    started = datetime.fromisoformat(state['started']).timestamp()
    training_until = datetime.fromisoformat(auth['training_until']).timestamp()
    if deadline-started > plan['total_seconds']+0.01:
        raise ValueError('Original campaign exceeds budget')
    if training_until+90 > deadline-plan['phase_seconds']['evaluation']-plan['phase_seconds']['report']:
        raise ValueError('Insufficient final evaluation/report reserve')
    if now >= training_until-90:
        raise ValueError('Insufficient remaining training time; no budget reset')
    pointer = json.loads((run/'model/latest.json').read_text())['checkpoint']
    if pointer != auth['checkpoint'] or Path(pointer).name != pointer:
        raise ValueError('Latest checkpoint changed')
    required = ['model.safetensors', 'optimizer.npz', 'state.json', 'model_config.json']
    for filename in required:
        rel = f'model/{pointer}/{filename}'
        if rel not in auth['resume_inputs'] or not (run/rel).is_file():
            raise ValueError(f'Checkpoint component missing: {filename}')
    import psutil
    for pid in [state.get('pid'), state.get('active_pid')]:
        if pid and psutil.pid_exists(pid):
            raise ValueError('Previous process still exists')
    if (run/'RESULT.json').exists() or list((run/'evaluations').glob('*/summary.json')):
        raise ValueError('Evaluation results already exist')
    return auth, state, deadline, training_until


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--authorization',type=Path,required=True);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    run=a.run.resolve();plan=json.loads((run/'plan.json').read_text());validate(plan)
    request=a.authorization.resolve()
    auth,previous,wall_deadline,wall_training_until=continuation(run,plan,request)
    if a.dry_run:
        print(json.dumps(dict(continuation=True,deadline=auth['deadline'],training_until=auth['training_until'],
                              checkpoint=auth['checkpoint'],remaining_seconds=wall_deadline-time.time()),indent=2));return
    from slm_perf.gpu_lease import GPULease
    from slm_perf.__main__ import active_jobs
    import fcntl
    with (run/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        auth,previous,wall_deadline,wall_training_until=continuation(run,plan,request)
        origin=time.monotonic();deadline=origin+wall_deadline-time.time();stop=[];child=None;caffeine=None
        for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,lambda *_:stop.append(True))
        state=dict(previous,status='preflight',pid=os.getpid(),active_pid=None,active_job=None,
                   resumed_at=datetime.now().astimezone().isoformat(),resume_checkpoint=auth['checkpoint'])
        state.pop('error',None)
        def budget():
            return dict(budget_spent_seconds=time.time()-datetime.fromisoformat(state['started']).timestamp(),
                        active_controller_seconds=previous.get('active_controller_seconds',previous['budget_spent_seconds'])+time.monotonic()-origin)
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
            with (run/'logs'/f'{name}-{request.stem}.log').open('x') as log:
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
            for path,expected in plan['inputs'].items():assert sha(path)==expected,path
            if active_jobs():raise RuntimeError('GPU busy')
            conditions=dict(recorded=datetime.now().astimezone().isoformat(),power_source=subprocess.check_output(['pmset','-g','batt'],text=True),
                            power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),monitoring='light')
            if 'AC Power' not in conditions['power_source']:raise RuntimeError('Mains power required at start')
            write(request.with_suffix('.conditions.json'),conditions)
            import psutil, shutil
            if psutil.virtual_memory().available<16*1024**3:raise RuntimeError('Insufficient available memory')
            if shutil.disk_usage(run).free<10*1024**3:raise RuntimeError('Insufficient free disk')
            if time.monotonic()-origin>plan['phase_seconds']['preflight']:raise RuntimeError('Preflight budget exceeded')
            with GPULease() as lease:
                # Consume only after checks and exclusive GPU admission; never reset on failure.
                continuation(run,plan,request)
                if stop:raise RuntimeError('Stop signal during preflight')
                write(request.with_suffix('.consumed.json'),dict(started=datetime.now().astimezone().isoformat(),pid=os.getpid()))
                (run/'STOP').rename(request.with_suffix('.prior-stop.txt'))
                write(request.with_suffix('.prior-status.json'),previous)
                caffeine=subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(os.getpid())])
                training_end=time.monotonic()+wall_training_until+90-time.time()
                emit(status='running',phase='training',training_started=True,**budget())
                job('train',train_args(plan,run,auth['training_until'])+['--resume'],training_end,lease)
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
                        automatic_adoption=False,historical_results_comparable=False,inputs_unchanged=True,
                        continuation=dict(checkpoint=auth['checkpoint'],deadline=auth['deadline'],training_until=auth['training_until']))
            write(run/'RESULT.json',report)
            (run/'REPORT.md').write_text('# Fresh 47-source training\n\nRandom initialization, new train-only tokenizer, no legacy checkpoint. Primary endpoint: final checkpoint on sealed confirmation.\n\n'+
                '\n'.join(f"- {name}: {s['evaluated_general']} tasks; per-family accuracy {s['mean_source_accuracy_by_family']}" for name,s in results.items())+
                '\n\nHistorical small-list results are deprecated. These are internal source-specific proxies, not official benchmark scores or proof of transfer. Code/SQL functionality and summary factuality remain unmeasured.\n')
            if cancelled():raise RuntimeError('Final deadline/stop')
            emit(status='completed',phase='finished',finished=datetime.now().astimezone().isoformat(),**budget())
        except BaseException as exc:
            terminate();(run/'STOP').write_text('Paused; no automatic restart. Preserve checkpoint and consumed budget.\n')
            emit(status='paused',error=str(exc),**budget());raise
        finally:
            terminate()
            if caffeine is not None:caffeine.terminate();caffeine.wait(timeout=5)


if __name__=='__main__':main()
