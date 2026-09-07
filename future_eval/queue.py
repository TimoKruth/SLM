"""One-shot offline preparation after the frozen campaign completes; no GPU computation."""
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

stopped=False

def interrupt(signum,frame):
    global stopped
    stopped=True

def save(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2)+'\n');temp.replace(path)

def ready(campaign):
    from slm_perf.__main__ import active_jobs
    try:status=json.loads((campaign/'status.json').read_text()).get('status')
    except (FileNotFoundError,json.JSONDecodeError):return False
    if status in {'failed','stopped'}:raise RuntimeError('Prerequisite campaign did not complete')
    return status=='completed' and not active_jobs()

def validate(plan):
    for name,expected in plan['sha256'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Queued source/input changed: '+name)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);a=p.parse_args()
    out=Path(a.run);out.mkdir(parents=True,exist_ok=True)
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
    child=caffeine=None
    from slm_perf.after_idle import stop_process
    with (out/'queue.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        plan=json.loads((out/'plan.json').read_text());until=datetime.fromisoformat(plan['admission_until']).timestamp()
        try:
            validate(plan)
            while not ready(Path(plan['campaign'])):
                if stopped or (out/'STOP').exists():raise InterruptedError('Stopped')
                if time.time()>=until:raise TimeoutError('Admission deadline expired')
                save(out/'status.json',{'status':'waiting_for_campaign','updated_at':datetime.now().astimezone().isoformat()})
                time.sleep(30)
            if stopped or (out/'STOP').exists():raise InterruptedError('Stopped')
            if time.time()>=until:raise TimeoutError('Admission deadline expired')
            validate(plan)
            from slm_perf.gpu_lease import GPULease
            with GPULease() as lease:
                if not ready(Path(plan['campaign'])):raise RuntimeError('New GPU work arrived')
                caffeine=subprocess.Popen(['/usr/bin/caffeinate','-is','-w',str(os.getpid())])
                options=lease.child_options()
                options['env'].update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
                args=[sys.executable,'run_slm.py','--module','future_eval.prepare','--run',plan['output'],'--seconds',str(plan['seconds'])]
                with (out/'prepare.log').open('a') as log:
                    child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,**options)
                    cutoff=time.time()+plan['seconds']+30
                    save(out/'status.json',{'status':'preparing','pid':child.pid,'until':cutoff})
                    while child.poll() is None:
                        if stopped or (out/'STOP').exists():raise InterruptedError('Stopped')
                        if time.time()>=cutoff:raise TimeoutError('Preparation deadline expired')
                        time.sleep(5)
                    if child.returncode:raise RuntimeError('Preparation exited '+str(child.returncode))
                    save(out/'status.json',{'status':'completed','output':plan['output']})
        except BaseException as exc:
            save(out/'status.json',{'status':'stopped' if stopped or (out/'STOP').exists() else 'failed','error':str(exc)})
            raise
        finally:
            stop_process(child);stop_process(caffeine)

if __name__=='__main__':main()
