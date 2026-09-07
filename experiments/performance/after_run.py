"""One-shot low-overhead watcher; benchmarks only after training AND evaluation finish."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timedelta
from experiments.performance.benchmark import active_slm_jobs

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'runs/expanded-2026-09-07-6h'
OUT=ROOT/'runs/performance-2026-09-07'


def write(value):
    p=OUT/'status.json';t=OUT/'status.tmp';t.write_text(json.dumps(value,indent=2));t.replace(p)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(OUT/'watcher.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    config=json.loads((OUT/'plan.json').read_text());deadline=datetime.fromisoformat(config['queue_deadline']).timestamp()
    while time.time()<deadline:
        if (OUT/'STOP').exists() or (RUN/'STOP').exists():write(dict(status='cancelled'));return
        phase=json.loads((RUN/'supervisor.json').read_text()).get('phase')
        if phase=='finished' and not active_slm_jobs():break
        write(dict(status='waiting_for_training_and_evaluation',updated_at=datetime.now().astimezone().isoformat(),pid=os.getpid()));time.sleep(30)
    else:write(dict(status='expired_without_gpu_benchmark'));return
    status=json.loads((RUN/'status.json').read_text())
    if status.get('status')!='completed':write(dict(status='skipped_training_not_completed'));return
    for path,digest in config['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:write(dict(status='skipped_source_changed',file=path));return
    write(dict(status='benchmark_running',started_at=datetime.now().astimezone().isoformat()))
    caffeine=subprocess.Popen(['/usr/bin/caffeinate','-is','-w',str(os.getpid())])
    try:
        with (OUT/'benchmark.log').open('w') as log:
            child=subprocess.Popen([sys.executable,'-u','-m','experiments.performance.benchmark','--run',str(RUN),'--output',str(OUT)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            try:code=child.wait(timeout=600)
            except subprocess.TimeoutExpired:child.kill();child.wait();write(dict(status='benchmark_timeout'));return
        write(dict(status='completed' if code==0 else 'benchmark_failed',exit_code=code,finished_at=datetime.now().astimezone().isoformat(),results_exist=(OUT/'results.json').exists()))
    finally:caffeine.terminate()


if __name__=='__main__':main()
