"""Sequential, restartable broad experiments; all GPU work uses run_slm.py."""
import argparse
from datetime import datetime, timedelta
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .train import atomic_json

ROOT = Path(__file__).resolve().parents[1]
shutdown = None


def interrupted(signum, frame):
    """Record shutdown without interrupting resource acquisition or cleanup."""
    global shutdown
    shutdown = signum if shutdown is None else shutdown


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def validate_plan(plan):
    """Reject changed workload sources or manifests before starting another stage."""
    for filename, expected in plan['sha256'].items():
        if digest(ROOT/filename) != expected:
            raise ValueError(f'Frozen campaign input changed: {filename}')
    if len({j['name'] for j in plan['jobs']}) != len(plan['jobs']):
        raise ValueError('Duplicate stage names')


def control_ready(plan):
    """Require clear training-set learning before spending the comparison budget."""
    control = ROOT/plan['control_run']
    before = json.loads((control/'recall-before/summary.json').read_text())
    after = json.loads((control/'recall-after/summary.json').read_text())
    counts = lambda r: sum(v['correct'] for v in r['by_source'].values())
    seen = sum(v['scored'] for v in after['by_source'].values())
    metrics = [json.loads(s) for s in (control/'metrics.jsonl').read_text().splitlines()]
    losses = [r['loss'] for r in metrics if r['event']=='train']
    return dict(passed=bool(losses and losses[-1]<losses[0]*.5 and counts(after)>=counts(before)+10 and seen==128),
                recall_before=counts(before), recall_after=counts(after), examples=seen,
                train_loss_first=losses[0] if losses else None, train_loss_last=losses[-1] if losses else None,
                interpretation='Training-set recall diagnoses learnability, not generalization.')


def wait_child(child, out, deadline):
    """Poll termination conditions; the caller owns one bounded cleanup attempt."""
    while child.poll() is None:
        if shutdown is not None or (out/'STOP').exists():
            raise InterruptedError('Campaign stopped')
        if time.time() >= deadline:
            raise TimeoutError('Stage runtime limit reached')
        time.sleep(2)
    return child.returncode


def run_job(job, out, progress):
    """Persist each deadline once; resumed training never gains a fresh time budget."""
    from slm_perf.__main__ import active_jobs
    if job.get('optional_snapshot') and not (ROOT/job['run']/'snapshot.json').exists():
        progress['jobs'][job['name']] = dict(status='skipped', reason='Token threshold not reached within training budget')
        atomic_json(out/'progress.json',progress)
        return
    admission = datetime.fromisoformat(job['admission_until']).timestamp()
    while active_jobs():
        if time.time() >= admission:
            raise TimeoutError('GPU admission deadline reached')
        if shutdown is not None or (out/'STOP').exists():
            raise InterruptedError('Stopped while waiting for GPU')
        atomic_json(out/'status.json',dict(status='waiting_for_gpu',stage=job['name'],pid=os.getpid()))
        time.sleep(5)
    if shutdown is not None or (out/'STOP').exists():
        raise InterruptedError('Stopped before launching stage')
    if time.time() >= admission:
        raise TimeoutError('GPU admission deadline reached')
    saved = progress['jobs'].setdefault(job['name'], {})
    if 'started_at' not in saved:
        now = datetime.now().astimezone()
        saved.update(started_at=now.isoformat(), cutoff=(now+timedelta(seconds=job['timeout_seconds'])).isoformat(), attempts=0)
        if job['module']=='slm.train':
            saved['train_until']=(now+timedelta(seconds=job['training_seconds'])).isoformat()
    deadline = datetime.fromisoformat(saved['cutoff']).timestamp()
    if time.time()>=deadline or saved['attempts']>=2:
        raise RuntimeError(f'Stage deadline/retry limit: {job["name"]}')
    if job['module']=='slm_perf.ab':
        # This explicitly authorized diagnostic chooses off/light/detail internally.
        args=[sys.executable,'-m','slm_perf.ab','--run',job['run'],*job['args']]
    else:
        args=[sys.executable,str(ROOT/'run_slm.py'),'--module',job['module'],'--run',job['run'],*job['args']]
    if job['module']=='slm.train':
        args += ['--until',saved['train_until']]
        if (ROOT/job['run']/'latest.json').exists():
            args.append('--resume')
    elif saved['attempts']:
        raise RuntimeError('Partial evaluation requires inspection; no silent overwrite')
    saved['attempts']+=1
    atomic_json(out/'progress.json',progress)
    atomic_json(out/'status.json',dict(status='running',stage=job['name'],until=saved['cutoff'],pid=os.getpid()))
    child = None
    with (out/(job['name']+'.log')).open('a') as log:
        try:
            environment=dict(os.environ)
            if job['module']=='slm_perf.ab':
                environment['MTL_CAPTURE_ENABLED']='1'
            if job['module']=='slm.train':
                saved['power_settings_at_start']=subprocess.run(['pmset','-g','custom'],capture_output=True,text=True,check=True).stdout
                atomic_json(out/'progress.json',progress)
            child=subprocess.Popen(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=environment)
            saved['pid']=child.pid
            atomic_json(out/'progress.json',progress)
            code=wait_child(child,out,deadline)
        finally:
            if child is not None:
                from slm_perf.after_idle import stop_process
                stop_process(child)
    saved['exit_code']=code
    if code:
        atomic_json(out/'progress.json',progress)
        raise RuntimeError(f'{job["name"]} exited {code}')
    if job['module']=='slm.train':
        status=json.loads((ROOT/job['run']/'status.json').read_text())
        if status['reason'] not in {'deadline','step_limit','token_limit'}:
            raise RuntimeError(f'Training stopped unexpectedly: {status}')
    else:
        output = job['args'][job['args'].index('--output')+1]
        if job['module']=='slm_perf.ab':
            summary=json.loads((ROOT/output/'results.json').read_text())
            if not summary['numerically_equivalent']:
                raise RuntimeError('Monitoring numerical check failed')
        else:
            summary = json.loads((ROOT/output/'summary.json').read_text())
            if summary['deadline_reached'] or summary['selected_general']!=summary['evaluated_general']:
                raise RuntimeError('Incomplete evaluation; inspect before continuing')
    saved.update(status='completed',finished_at=datetime.now().astimezone().isoformat())
    atomic_json(out/'progress.json',progress)


def report(plan, out, progress):
    """Compare per-capability outcomes and observed token exposure at equal wall time."""
    if plan.get('comparison_kind')=='model_size':
        from experiments.size_report import report as size_report
        return size_report(plan,out,progress)
    data=[]
    for item in plan['comparisons']:
        run=ROOT/item['run']
        result=json.loads((run/'broad-eval/summary.json').read_text())
        pointer=json.loads((run/'latest.json').read_text())
        state=json.loads((run/pointer['checkpoint']/'state.json').read_text())
        data.append(dict(name=item['name'],run=item['run'],tokens=state['tokens'],source_tokens=state.get('source_tokens',{}),evaluation=result))
    atomic_json(out/'comparison.json',dict(runs=data,quality_scope='Development proxies, no external benchmark-family transfer measurement'))
    lines=['# Broad mixture comparison','', 'Same architecture, tokenizer, examples and training wall-clock budget; only sampling weights differ. Actual source-token exposure is reported separately.', '', '| Capability | Equal families | Equal sources |','| --- | ---: | ---: |']
    keys=set().union(*(r['evaluation']['mean_source_accuracy_by_family'] for r in data))
    for key in sorted(keys):
        values=[r['evaluation']['mean_source_accuracy_by_family'].get(key) for r in data]
        lines.append('| '+key+' | '+' | '.join('n/a' if v is None else f'{v:.3f}' for v in values)+' |')
    lines += ['', 'Narrative and SQL execution quality require separate assessment; no aggregate score is used to hide these gaps.',
              'Next prepared stage: compare the smaller model with the same broad mixture, then choose any longer continuation from the observed learning curves. No automatic specialization or external-test opening.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',required=True)
    a=p.parse_args()
    out=ROOT/a.run
    out.mkdir(parents=True,exist_ok=True)
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    with (out/'campaign.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        plan=json.loads((out/'plan.json').read_text())
        progress=json.loads((out/'progress.json').read_text()) if (out/'progress.json').exists() else {'jobs':{}}
        caffeine=None
        try:
            validate_plan(plan)
            control_deadline=datetime.fromisoformat(plan['control_wait_until']).timestamp()
            while not (ROOT/plan['control_run']/'recall-after/summary.json').exists() or not (ROOT/plan['control_run']/'development/summary.json').exists():
                if shutdown is not None or (out/'STOP').exists():
                    raise InterruptedError('Stopped before control completed')
                if time.time()>=control_deadline:
                    raise TimeoutError('Learning control did not complete in time')
                atomic_json(out/'status.json',dict(status='waiting_for_learning_control',pid=os.getpid()))
                time.sleep(5)
            gate=control_ready(plan)
            atomic_json(out/'control-gate.json',gate)
            if not gate['passed']:
                raise RuntimeError('Learning control has not passed; comparison budget preserved')
            caffeine=subprocess.Popen(['/usr/bin/caffeinate','-is','-w',str(os.getpid())])
            for job in plan['jobs']:
                validate_plan(plan)
                if progress['jobs'].get(job['name'],{}).get('status')=='completed':
                    continue
                run_job(job,out,progress)
            report(plan,out,progress)
            atomic_json(out/'status.json',dict(status='completed',finished_at=datetime.now().astimezone().isoformat()))
        except BaseException as exc:
            atomic_json(out/'status.json',dict(status='stopped' if shutdown is not None or (out/'STOP').exists() else 'failed',error=str(exc),time=datetime.now().astimezone().isoformat()))
            raise
        finally:
            if caffeine is not None:
                from slm_perf.after_idle import stop_process
                stop_process(caffeine)


if __name__=='__main__':
    main()
