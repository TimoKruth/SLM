"""One-shot supervisor: bounded retries, heartbeat, hard deadline, morning report."""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2))
    temp.replace(path)


def wait_until(child, cutoff, heartbeat, run, phase):
    while child.poll() is None:
        now = time.time()
        write_json(heartbeat, {'supervisor_pid': os.getpid(), 'child_pid': child.pid, 'phase': phase, 'updated_at': datetime.now().astimezone().isoformat(), 'cutoff': datetime.fromtimestamp(cutoff).astimezone().isoformat()})
        if now >= cutoff or (run / 'STOP').exists():
            child.terminate()
            try:
                child.wait(timeout=45)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            return child.returncode
        time.sleep(min(15, max(.1, cutoff - now)))
    return child.returncode


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', required=True)
    p.add_argument('--data', default='data')
    p.add_argument('--code-eval', action='store_true')
    p.add_argument('--max-tokens', type=int, default=100000000)
    p.add_argument('--train-until', required=True)
    p.add_argument('--hard-until', required=True)
    p.add_argument('--steps', type=int, default=1000000)
    args = p.parse_args()
    train_cutoff = datetime.fromisoformat(args.train_until).timestamp()
    hard_cutoff = datetime.fromisoformat(args.hard_until).timestamp()
    if hard_cutoff - train_cutoff < 120 or time.time() >= train_cutoff:
        raise ValueError('Need at least two minutes of report reserve and a future training deadline')
    run = (ROOT / args.run).resolve()
    run.mkdir(parents=True, exist_ok=True)
    # Advisory lock prevents two supervisors from training into the same run.
    import fcntl
    lock = (run / 'supervisor.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lock.write(str(os.getpid()))
    lock.flush()
    heartbeat = run / 'supervisor.json'
    caffeinate = subprocess.Popen(['/usr/bin/caffeinate', '-is', '-w', str(os.getpid())])
    child = None
    def stop(signum, frame):
        (run / 'STOP').touch()
        if child and child.poll() is None:
            child.terminate()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        with (run / 'training.log').open('a', buffering=1) as logfile:
            for attempt in range(3):
                if time.time() >= train_cutoff or (run / 'STOP').exists():
                    break
                cmd = [sys.executable, '-m', 'slm.train', '--run', str(run), '--data', args.data, '--until', args.train_until, '--steps', str(args.steps), '--checkpoint-seconds', '300', '--eval-seconds', '1800', '--max-tokens', str(args.max_tokens)]
                if (run / 'latest.json').exists():
                    cmd.append('--resume')
                print(f'Starting training attempt {attempt+1}', flush=True)
                child = subprocess.Popen(cmd, cwd=ROOT, stdout=logfile, stderr=subprocess.STDOUT)
                code = wait_until(child, min(train_cutoff + 60, hard_cutoff - 90), heartbeat, run, 'training')
                if code == 0 or (run / 'STOP').exists() or time.time() >= train_cutoff:
                    break
                print(f'Training exited {code}; last complete checkpoint preserved', flush=True)
                if not (run / 'latest.json').exists():
                    break
                time.sleep(5)
        if (run / 'config.json').exists() and (run / 'status.json').exists():
            status = json.loads((run / 'status.json').read_text())
            if status.get('status') == 'running':
                status['status'] = 'interrupted'
                status['reason'] = 'training_process_exited_without_final_status; use last complete checkpoint'
                write_json(run / 'status.json', status)
            cmd = [sys.executable, '-m', 'slm.report', '--run', str(run)]
            if time.time() < hard_cutoff - 90 and (run / 'latest.json').exists() and not (run / 'STOP').exists():
                cmd += ['--sample', '--until', datetime.fromtimestamp(hard_cutoff - 60).astimezone().isoformat()]
            with (run / 'report.log').open('a') as logfile:
                child = subprocess.Popen(cmd, cwd=ROOT, stdout=logfile, stderr=subprocess.STDOUT)
                code = wait_until(child, hard_cutoff - 15, heartbeat, run, 'report')
            if code != 0:
                # Lightweight report is still useful if sample generation fails.
                subprocess.run([sys.executable, '-m', 'slm.report', '--run', str(run)], cwd=ROOT, timeout=10, check=False)
        if args.code_eval and (run/'best.safetensors').exists() and not (run/'STOP').exists() and time.time()<hard_cutoff-120:
            evaluation=run/'code-eval'
            if not (evaluation/'results.jsonl').exists():
                with (run/'code-eval.log').open('a') as logfile:
                    child=subprocess.Popen([sys.executable,'-u','-m','slm.code_eval','--run',str(run),'--output',str(evaluation)],cwd=ROOT,stdout=logfile,stderr=subprocess.STDOUT)
                    code=wait_until(child,hard_cutoff-15,heartbeat,run,'code_evaluation')
                write_json(run/'code-eval-status.json',dict(exit_code=code,complete=(evaluation/'summary.json').exists(),time=datetime.now().astimezone().isoformat()))
                if (evaluation/'summary.json').exists() and (run/'REPORT.md').exists():
                    summary=json.loads((evaluation/'summary.json').read_text())
                    with (run/'REPORT.md').open('a') as report:
                        report.write(f'\nAusführbare Code-Diagnose des besten Checkpoints: **{summary["passed"]}/{summary["reference_validated_tasks"]} gelöst**. Details: [Code-Bericht](code-eval/REPORT.md).\n')
        if args.code_eval and (run/'code-eval/summary.json').exists() and not (run/'code-eval/mbpp_public_example.json').exists() and not (run/'STOP').exists() and time.time()<hard_cutoff-120:
            with (run/'interface-eval.log').open('a') as logfile:
                child=subprocess.Popen([sys.executable,'-u','-m','slm.interface_eval','--run',str(run),'--output',str(run/'code-eval')],cwd=ROOT,stdout=logfile,stderr=subprocess.STDOUT)
                code=wait_until(child,hard_cutoff-15,heartbeat,run,'interface_evaluation')
        write_json(heartbeat, {'supervisor_pid': os.getpid(), 'phase': 'finished', 'finished_at': datetime.now().astimezone().isoformat(), 'report_exists': (run / 'REPORT.md').exists()})
    finally:
        if child and child.poll() is None:
            child.terminate()
        caffeinate.terminate()
        lock.close()


if __name__ == '__main__':
    main()
