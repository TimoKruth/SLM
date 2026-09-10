"""Eight serial GPU trainings, fixed wall endpoints and a single remaining budget."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from research.common import read,write,sha,quality
from study.safety import failure_kind,RecoverableStop
from slm_perf.after_idle import stop_process
from .protocol import validate_plan
from .report import report

ROOT=Path(__file__).resolve().parents[1]
EVONN=Path('/Users/timokruth/Projekte/EvoNN-confirmation-v2-20260909/.artifacts/confirmation-execution-20260910/status.json')


def evonn_state():
    try:return read(EVONN)
    except (OSError,ValueError):return {'state':'unavailable'}


class Runner:
    def __init__(self,run,plan,state,deadline,stop):
        self.run,self.plan,self.state,self.deadline,self.stop=run,plan,state,deadline,stop
        self.frozen=read(run/'frozen-inputs.json');self.stamps={}
    def verify(self,full=False):
        for path,digest in self.frozen.items():
            p=Path(path);stamp=(p.stat().st_size,p.stat().st_mtime_ns)
            if full and sha(p)!=digest:raise RecoverableStop('Frozen input changed: '+path)
            if path in self.stamps and stamp!=self.stamps[path]:raise RecoverableStop('Input modified: '+path)
            self.stamps[path]=stamp
    def check(self):
        if self.stop or (self.run/'STOP').exists():raise RecoverableStop('Requested stop')
        if time.monotonic()>=self.deadline:raise RecoverableStop('Global deadline')
        import psutil
        if psutil.virtual_memory().available<10*1024**3:raise RecoverableStop('Memory pressure')
    def attempt(self,name,module,target,args,seconds):
        self.check();self.verify()
        if time.monotonic()+seconds>self.deadline:raise RecoverableStop('Insufficient remaining budget for next complete stage')
        command=[sys.executable,'-u',str(ROOT/'run_slm.py'),'--module',module,'--run',str(target),*args]
        stage=dict(name=name,module=module,status='running',started=datetime.now().astimezone().isoformat(),
                   maximum_seconds=seconds,evonn_start=evonn_state())
        self.state['phase']=name;self.state['stages'].append(stage);write(self.run/'status.json',self.state)
        process=None;start=time.monotonic();ok=False
        try:
            with (self.run/(name+'.log')).open('w') as log:
                process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                stage['pid']=process.pid;write(self.run/'status.json',self.state)
                last_heartbeat=0
                while process.poll() is None:
                    self.check()
                    if time.monotonic()-start>=seconds:raise RecoverableStop('Stage process timeout: '+name)
                    if time.monotonic()-last_heartbeat>=60:
                        self.state.update(heartbeat=datetime.now().astimezone().isoformat(),evonn_current=evonn_state())
                        write(self.run/'status.json',self.state);last_heartbeat=time.monotonic()
                    time.sleep(1)
                stage['exit_code']=process.returncode;ok=process.returncode==0
        finally:
            stop_process(process)
            stage.update(status='completed' if ok else 'failed',elapsed_seconds=time.monotonic()-start,evonn_end=evonn_state())
            write(self.run/'status.json',self.state)
        if not ok:
            stage['failure_kind']=failure_kind((self.run/(name+'.log')).read_text()[-131072:])
            write(self.run/'status.json',self.state)
        return ok,stage
    def job(self,name,module,target,args,seconds):
        started=time.monotonic()
        ok,stage=self.attempt(name,module,target,args,seconds)
        if ok:return
        if stage['failure_kind']!='gpu_service':raise RecoverableStop('Stage failed: '+name+' ('+stage['failure_kind']+')')
        count=self.state.get('gpu_recovery_attempts',0)
        if count>=2:raise RecoverableStop('Campaign GPU recovery limit')
        self.state['gpu_recovery_attempts']=count+1
        time.sleep(2)
        if seconds-(time.monotonic()-started)<100:raise RecoverableStop('Insufficient stage recovery budget')
        healthy,_=self.attempt(name+'-health','study.health',self.run/'recovery-health'/str(count+1),['--seconds','3'],20)
        if not healthy:raise RecoverableStop('Recovery health failed')
        retry=list(args)
        if module=='long_study.trial':
            if (target/'latest.json').exists():retry+=['--resume']
            elif target.exists():
                dest=self.run/'attempts'/name/'partial';dest.parent.mkdir(parents=True);target.rename(dest)
            retry+=['--wall-seconds',str(seconds-(time.monotonic()-started))]
        elif module=='slm.broad_eval':
            out=Path(args[args.index('--output')+1])
            if not out.resolve().is_relative_to(self.run.resolve()):raise RecoverableStop('Unsafe retry output')
            if out.exists():
                dest=self.run/'attempts'/name/'partial';dest.parent.mkdir(parents=True);out.rename(dest)
        else:raise RecoverableStop('Preflight failed; pause before trials')
        remaining=seconds-(time.monotonic()-started)
        ok,_=self.attempt(name+'-retry',module,target,retry,remaining)
        if not ok:raise RecoverableStop('Retry failed; no further trials')
    def evaluate(self,target,label,suite='search'):
        output=(self.run/'parent-confirmation') if label=='parent-confirmation' else target/suite
        self.job(label,'slm.broad_eval',target,['--suite',str(self.run/(suite+'-suite.json')),
                 '--output',str(output),'--checkpoint','latest','--maximum','256','--max-seconds',str(self.plan['evaluation_seconds']),
                 '--skip-code','--answer-loss'],self.plan['evaluation_process_seconds'])
        quality(read(output/'summary.json'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);args=parser.parse_args()
    run=Path(args.run).resolve();plan=read(run/'plan.json');validate_plan(plan)
    if (run/'STOP').exists():raise ValueError('STOP blocks startup')
    if (run/'status.json').exists():raise ValueError('One-shot campaign; do not reset budget')
    started=time.time();clock=time.monotonic();stop=[]
    state=dict(status='running',phase='verify',pid=os.getpid(),started=datetime.now().astimezone().isoformat(),
               deadline=datetime.fromtimestamp(started+plan['budget_seconds']).astimezone().isoformat(),stages=[])
    write(run/'status.json',state)
    for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,lambda n,f:stop.append(n))
    runner=Runner(run,plan,state,clock+plan['budget_seconds']-plan['report_seconds'],stop)
    caffeine=None
    try:
        runner.verify(full=True)
        caffeine=subprocess.Popen(['/usr/bin/caffeinate','-is','-w',str(os.getpid())])
        runner.job('health-start','study.health',run/'health-start',['--seconds','3'],20)
        runner.job('controls','study.trial',run/'controls',['--plan',str(run/'plan.json'),'--control-only'],plan['control_seconds']-20)
        if not read(run/'controls/control.json')['passed']:raise RecoverableStop('Control failed')
        runner.evaluate(Path(plan['parent']),'parent-confirmation','confirmation')
        for identifier in plan['jobs']:
            job=read(run/'jobs'/(identifier+'.json'));trial=run/'trials'/identifier
            runner.job(identifier,'long_study.trial',trial,['--plan',str(run/'plan.json'),
                       '--job',str(run/'jobs'/(identifier+'.json'))],job['train_seconds'])
            if read(trial/'result.json')['status']!='completed':raise RecoverableStop('Incomplete wall endpoint')
            for target in [15000000,50000000]:
                snapshot=trial/f'token-{target:09d}'
                if snapshot.exists():runner.evaluate(snapshot,identifier+f'-{target}-search')
                else:state.setdefault('missing_token_snapshots',[]).append(str(snapshot))
            runner.evaluate(trial,identifier+'-search')
            runner.evaluate(trial,identifier+'-confirmation','confirmation')
            report(run,state)
        state.update(status='completed',phase='finished')
    except BaseException as exc:
        state.update(status='paused',error=repr(exc));(run/'STOP').write_text('Paused; preserve results and remaining budget.\n')
    finally:
        stop_process(caffeine)
        state.update(finished=datetime.now().astimezone().isoformat(),elapsed_seconds=time.time()-started,
                     total_budget_spent_seconds=plan['previous_budget_spent_seconds']+time.time()-started)
        try:runner.verify(full=True);state['frozen_inputs_unchanged']=True
        except BaseException as exc:state.update(status='invalid',error=repr(exc),frozen_inputs_unchanged=False)
        write(run/'status.json',state);report(run,state)
    if state['status']!='completed':raise SystemExit(1)

if __name__=='__main__':main()
