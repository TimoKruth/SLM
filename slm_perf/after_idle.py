"""One-shot calibration queue, sequenced after the existing run and GPU benchmark."""
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/monitoring-2026-09-07'


def save(**status):
    path=OUT/'status.json';temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(dict(updated_at=datetime.now().astimezone().isoformat(),**status),indent=2)+'\n');temporary.replace(path)


def ready(plan):
    from .__main__ import active_jobs
    run=Path(plan['run']);prior=Path(plan['prior_benchmark'])
    try:
        supervisor=json.loads((run/'supervisor.json').read_text())
        before=json.loads((prior/'status.json').read_text())
    except (FileNotFoundError,json.JSONDecodeError):return False
    terminal={'completed','benchmark_failed','benchmark_timeout','expired_without_gpu_benchmark','skipped_source_changed','skipped_training_not_completed','cancelled'}
    return supervisor.get('phase')=='finished' and before.get('status') in terminal and not active_jobs()


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    lock=(OUT/'queue.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    plan=json.loads((OUT/'plan.json').read_text());run=Path(plan['run'])
    deadline=datetime.fromisoformat(plan['queue_deadline']).timestamp()
    while time.time()<deadline:
        if (OUT/'STOP').exists() or (run/'STOP').exists():save(status='cancelled');return
        if ready(plan):break
        save(status='waiting_for_training_evaluation_and_prior_benchmark',pid=os.getpid());time.sleep(30)
    else:save(status='expired');return
    if json.loads((run/'status.json').read_text()).get('status')!='completed':save(status='skipped_training_not_completed');return
    for path,digest in plan['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:save(status='skipped_source_changed',file=path);return
    save(status='calibration_running')
    caffeine=subprocess.Popen(['/usr/bin/caffeinate','-is','-w',str(os.getpid())])
    try:
        with (OUT/'calibration.log').open('w') as log:
            command=[sys.executable,'-u','-m','slm_perf.ab','--run',str(run),'--output',str(OUT/'calibration')]
            if plan.get('metal_capture'):command.append('--metal-capture')
            child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'MTL_CAPTURE_ENABLED':'1'})
            from .__main__ import active_jobs
            cutoff=time.monotonic()+plan['timeout_seconds']
            while child.poll() is None:
                competitors=[pid for pid in active_jobs() if pid!=child.pid]
                cancelled=(OUT/'STOP').exists() or (run/'STOP').exists()
                if competitors or cancelled or time.monotonic()>=cutoff:
                    child.kill();child.wait()
                    save(status='yielded_to_other_gpu_job' if competitors else ('cancelled' if cancelled else 'calibration_timeout'))
                    return
                time.sleep(2)
            code=child.returncode
        save(status='completed' if code==0 else 'calibration_failed',exit_code=code)
    finally:caffeine.terminate()


if __name__=='__main__':main()
