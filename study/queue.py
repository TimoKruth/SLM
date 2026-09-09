"""Light CPU-only queue: wait for the existing campaign, then start the authorized 24h budget once."""
import argparse
from datetime import datetime
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from research.common import read,write,sha
from slm_perf.after_idle import stop_process
from slm_perf.__main__ import active_jobs

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);a=p.parse_args()
    run=Path(a.run).resolve();plan=read(run/'plan.json');stop=[];child=None
    for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,lambda n,f:stop.append(n))
    with (run/'queue.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (run/'status.json').exists():raise ValueError('Campaign has already started; no restart')
        write(run/'queue.json',dict(status='waiting',pid=os.getpid(),prerequisite=plan['prerequisite'],budget_seconds=86400))
        try:
            while True:
                if stop or (run/'STOP').exists():
                    write(run/'queue.json',dict(status='cancelled_before_start'));return
                prior=read(Path(plan['prerequisite'])/'status.json')
                if prior['status'] in ['completed','stopped','invalid'] and not active_jobs():break
                time.sleep(10)
            for path,digest in read(run/'initial-inputs.json').items():
                if sha(path)!=digest:raise ValueError('Queued input changed: '+path)
            with (run/'supervisor.log').open('w') as log:
                command=[sys.executable,'-u',str(ROOT/'run_slm.py'),'--module','study.campaign','--run',str(run)]
                child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                write(run/'queue.json',dict(status='launched',pid=os.getpid(),child_pid=child.pid,
                      launched=datetime.now().astimezone().isoformat(),prerequisite_status=prior['status']))
                while child.poll() is None:
                    if stop:break
                    time.sleep(5)
                write(run/'queue.json',dict(status='finished' if not stop else 'cancelled',exit_code=child.poll()))
        except BaseException as exc:
            write(run/'queue.json',dict(status='failed',error=repr(exc)));raise
        finally:stop_process(child)


if __name__=='__main__':main()
