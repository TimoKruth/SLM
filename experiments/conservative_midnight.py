"""CPU-only, one-shot deferred start for a frozen conservative comparison."""
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


def read(path):return json.loads(Path(path).read_text())


def write(path,value):
    p=Path(path);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(p)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def eligible(now,config,predecessor,ac,busy):
    if now>=config['latest_start_unix']:return 'expired'
    if now<config['not_before_unix']:return 'waiting_for_midnight'
    if predecessor in ('paused','failed','stopped'):return 'predecessor_not_completed'
    if predecessor!='completed':return 'waiting_for_current_run'
    if not ac:return 'waiting_for_ac_power'
    if busy:return 'waiting_for_gpu'
    return 'ready'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
    config_path=Path(args.config).resolve();config=read(config_path);config_hash=sha(config_path);run=Path(config['run'])
    if config['scheduler_sha256']!=sha(__file__):raise ValueError('Scheduler code changed')
    if config['budget_seconds']!=21600:raise ValueError('Unexpected budget')
    if not config['not_before_unix']<config['latest_start_unix']:raise ValueError('Invalid time window')
    sys.path.insert(0,config['worktree'])
    from optimization_lab.protocol import verify,capture,utc,conditions
    from conservative_optimization.design import validate_plan
    from slm_perf.__main__ import active_jobs
    from slm_perf.gpu_lease import GPULease,GPUBusy
    from experiments.optimization_start import stop_owned
    status_path=run/'schedule-status.json';cancel=run/'SCHEDULE_STOP'
    # launchd may load a user job again at login; terminal/attempted work is never restarted.
    with (run/'schedule.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        if cancel.exists():return
        if status_path.exists() and read(status_path).get('status') in ('completed','failed','cancelled','expired','predecessor_not_completed','launch_attempted'):
            return
        if (run/'direct-status.json').exists() or (run/'status.json').exists():return
        stopped=[];child=None
        for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:stopped.append(True))
        state=dict(status='armed',pid=os.getpid(),not_before=config['not_before'],latest_start=config['latest_start'],
                   budget_seconds=21600,created_at=utc(),child_pid=None)
        def emit(**changes):
            state.update(changes,heartbeat=utc());write(status_path,state)
        try:
            plan=read(run/'plan.json');validate_plan(plan);verify(plan)
            if sha(run/'plan.json')!=config['plan_sha256']:raise ValueError('Plan changed')
            if sha(run/'AUTHORIZATION.json')!=config['authorization_sha256']:raise ValueError('Authorization changed')
            while True:
                if stopped or cancel.exists():
                    cancel.touch(exist_ok=True);emit(status='cancelled');return
                stop=run/'STOP'
                if not stop.exists() or sha(stop)!=config['preparation_stop_sha256'] or stop.stat().st_mtime_ns!=config['preparation_stop_mtime_ns']:
                    raise ValueError('Preparation STOP changed; refusing automatic release')
                predecessor=read(Path(config['predecessor'])/'status.json').get('status')
                decision=eligible(time.time(),config,predecessor,'AC Power' in capture(['pmset','-g','batt']),bool(active_jobs()))
                emit(status=decision,predecessor_status=predecessor)
                if decision in ('expired','predecessor_not_completed'):return
                if decision!='ready':time.sleep(5);continue
                try:
                    with GPULease() as lease:
                        if active_jobs():time.sleep(1);continue
                        # Revalidate frozen inputs and cancellation immediately before the one-shot launch.
                        verify(plan)
                        if sha(config_path)!=config_hash:
                            raise ValueError('Schedule changed')
                        if stopped or cancel.exists():continue
                        if eligible(time.time(),config,read(Path(config['predecessor'])/'status.json').get('status'),
                                    'AC Power' in capture(['pmset','-g','batt']),False)!='ready':continue
                        if sha(stop)!=config['preparation_stop_sha256'] or stop.stat().st_mtime_ns!=config['preparation_stop_mtime_ns']:
                            raise ValueError('STOP changed during verification')
                        write(run/'SCHEDULE_START_CONDITIONS.json',conditions())
                        # Durable latch comes first: crashes cannot create a second attempt.
                        emit(status='launch_attempted',actual_start=utc())
                        stop.rename(run/'STOP.scheduled-preparation-history')
                        with (run/'scheduled-launch.log').open('x') as log:
                            child=subprocess.Popen([config['python'],'-m','conservative_optimization.direct','--run',str(run)],
                                cwd=config['worktree'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                                start_new_session=True,**lease.child_options())
                        emit(child_pid=child.pid)
                        # The existing direct launcher is the primary six-hour watchdog; this is an independent backstop.
                        outer_deadline=time.monotonic()+21600
                        while child.poll() is None:
                            if stopped or cancel.exists() or time.monotonic()>=outer_deadline:
                                (run/'STOP').write_text('Scheduled launch cancelled or six-hour outer limit.\n')
                                stop_owned(child);break
                            emit();time.sleep(2)
                        direct=read(run/'direct-status.json') if (run/'direct-status.json').exists() else {}
                        emit(status='completed' if direct.get('status')=='completed' else 'failed',
                             study_status=direct.get('status'),exit_code=child.returncode,finished_at=utc())
                        return
                except GPUBusy:
                    emit(status='waiting_for_gpu');time.sleep(5)
        except BaseException as exc:
            emit(status='failed',error=str(exc),finished_at=utc());raise
        finally:
            if child is not None:stop_owned(child)

if __name__=='__main__':main()
