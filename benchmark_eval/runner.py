"""Explicit, budgeted evaluation with persistent inference and durable partial results."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
import signal
import sqlite3
import subprocess
import threading
import time
import psutil
from slm_perf.gpu_lease import GPULease
from slm_perf.__main__ import active_jobs
from .settings import Settings
from .prepare import sha, write
from .tasks import load_tasks, grade, legacy_scorer
from .backends import Ollama, SLM


def admission():
    if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True,timeout=3):
        raise RuntimeError('Mains power required')
    database = Path.home()/'Library/Application Support/PowerWatch/data/powerwatch.sqlite3'
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=1) as db:
        db.execute('PRAGMA query_only=ON')
        last = db.execute('SELECT ts FROM samples ORDER BY ts DESC LIMIT 1').fetchone()
    if not last or not -5<=time.time()-last[0]<=90:
        raise RuntimeError('Fresh PowerWatch data required')
    if active_jobs():
        raise RuntimeError('Another supported GPU workload is active')
    for p in psutil.process_iter(['name','cmdline']):
        try:
            if 'ollama' in (p.info['name'] or '').lower() and any(x in {'serve','runner'} for x in p.info['cmdline'] or []):
                raise RuntimeError('Another Ollama server/runner is active')
        except (psutil.NoSuchProcess,psutil.AccessDenied):
            pass


def summarize(plan, results, status, error=None):
    by_source = defaultdict(lambda:dict(attempted=0,scored=0,correct=0,format_errors=0,unscored=0,cutoffs=0,unsupported=0))
    for r in results:
        v = by_source[r['source']]
        v['attempted'] += 1
        v['cutoffs'] += r['stop_reason'] in {'output_limit','context_limit'}
        v['unsupported'] += r['stop_reason']=='unsupported_context'
        g = r['grade']
        v['format_errors'] += g['status']=='format_error'
        if g['correct'] is not None:
            v['scored'] += 1
            v['correct'] += g['correct']
        else:
            v['unscored'] += 1
    complete = status=='completed' and len(results)==plan['tasks'] and not any(v['unsupported'] for v in by_source.values())
    return dict(status=status, error=error, selected=plan['tasks'], attempted=len(results),
                generation_coverage_complete=complete,
                all_answers_ended_naturally=complete and all(r['stop_reason']=='eos' for r in results),
                official_artificial_analysis_score=False,
                by_source=dict(by_source), stop_reasons=dict(Counter(r['stop_reason'] for r in results)),
                full_suite_accuracy=None,  # Mixed proxies/external graders cannot form an Intelligence Index.
                interpretation='Per-source internal metrics; partial subsets are not full-suite rankings. External graders remain unscored.')


def report(run, plan, results, status, error=None):
    summary = summarize(plan,results,status,error)
    write(run/'summary.json',summary)
    lines = ['# Configurable evaluation','',summary['interpretation'],'',
             f"Status: {status}. Attempted {len(results)}/{plan['tasks']}. Generation coverage complete: {summary['generation_coverage_complete']}.",
             '', '| Source | Attempted | Correct / scored | Format errors | Cutoffs | Unsupported | Unscored |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for source,v in summary['by_source'].items():
        lines.append(f"| {source} | {v['attempted']} | {v['correct']}/{v['scored']} | {v['format_errors']} | {v['cutoffs']} | {v['unsupported']} | {v['unscored']} |")
    if error:
        lines += ['', 'Stopped: '+error]
    (run/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return summary


def execute(run, plan_hash, budget_seconds):
    run = Path(run).resolve()
    if not 0<budget_seconds<365*86400:
        raise ValueError('Explicit positive wall budget required (less than one year)')
    if sha(run/'plan.json')!=plan_hash:
        raise ValueError('Plan hash mismatch')
    if any((run/n).exists() for n in ['status.json','responses.jsonl','STOP']):
        raise ValueError('Existing or stopped run; prepare a new plan, no implicit restart/reset')
    plan = json.loads((run/'plan.json').read_text())
    settings = Settings(**plan['settings'])
    admission()
    required = (24 if settings.backend=='ollama' else 8)*1024**3
    if psutil.virtual_memory().available < required:
        raise RuntimeError('Insufficient available memory before model loading')
    status = dict(status='running',phase='preflight',started=datetime.now().astimezone().isoformat(),
                  deadline=datetime.fromtimestamp(time.time()+budget_seconds).astimezone().isoformat(),
                  completed_tasks=0,total_tasks=plan['tasks'],pid=__import__('os').getpid())
    end = time.monotonic()+budget_seconds
    wall_end = datetime.fromisoformat(status['deadline']).timestamp()
    task_end = [end]
    stopped = threading.Event()
    done = threading.Event()
    errors = []
    results = []
    backend = None
    caffeine = None
    thread = None
    close_lock = threading.Lock()

    def close():
        with close_lock:
            if backend is not None:
                backend.close()

    def emit(**values):
        status.update(values,heartbeat=datetime.now().astimezone().isoformat())
        write(run/'status.json',status)

    def check():
        if stopped.is_set() or (run/'STOP').exists():
            raise RuntimeError(errors[0] if errors else 'User stop/signal')
        if time.monotonic()>=min(end,task_end[0]) or time.time()>=wall_end:
            raise TimeoutError('Task or total wall budget exhausted')

    def guard():
        next_power = 0
        while not done.wait(.25):
            try:
                check()
                if backend is not None:
                    getattr(backend, 'observe', lambda:None)()
                if time.monotonic()>=next_power:
                    if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True,timeout=3):
                        raise RuntimeError('Mains power lost')
                    next_power = time.monotonic()+5
            except Exception as exc:
                errors.append(str(exc));stopped.set();close();return

    with GPULease() as lease:
        admission()
        old_signals = {sig:signal.signal(sig,lambda *_:stopped.set()) for sig in [signal.SIGTERM,signal.SIGINT]}
        try:
            emit()
            caffeine = subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(status['pid'])], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            write(run/'AUTHORIZATION.json',dict(explicit_start=True,plan_sha256=plan_hash,budget_seconds=budget_seconds,
                  authorized_at=status['started'],deadline=status['deadline'],no_automatic_retry=True))
            thread = threading.Thread(target=guard,daemon=True);thread.start()
            for path,digest in {**plan['inputs'],**plan.get('model_blobs',{})}.items():
                check()
                if sha(path)!=digest:
                    raise ValueError('Frozen input mismatch: '+path)
            tasks = load_tasks(plan['suite'])
            if len(tasks)!=plan['tasks']:
                raise ValueError('Task count changed')
            scorer = legacy_scorer() if any(t['kind']=='legacy_proxy' for t in tasks) else None
            write(run/'RUN_CONDITIONS.json',dict(time=status['started'],available_ram=psutil.virtual_memory().available,
                  monitoring='light',power=subprocess.check_output(['pmset','-g','custom'],text=True,timeout=3)))
            backend = (Ollama if settings.backend=='ollama' else SLM)(plan,run,lease)
            check();backend.start();check()
            emit(phase='evaluation')
            with (run/'responses.jsonl').open('x',buffering=1) as output:
                for i,task in enumerate(tasks):
                    check();task_end[0]=min(end,time.monotonic()+settings.task_seconds)
                    start = time.monotonic()
                    response = backend.generate(task)
                    check()  # Never score a cancelled/incomplete response.
                    metric = dict(status='unscored_unsupported_context',correct=None) if response['stop_reason']=='unsupported_context' else grade(task,response['text'],scorer)
                    result = dict(index=i,id=task['id'],source=task['source'],wall_seconds=time.monotonic()-start,
                                  grade=metric,**response)
                    output.write(json.dumps(result,ensure_ascii=False)+'\n');output.flush()
                    results.append(result)
                    emit(completed_tasks=len(results))
            task_end[0]=end
            close();check()
            # Check code/data again; model blobs were fully verified before admission to inference.
            for path,digest in plan['inputs'].items():
                check()
                if sha(path)!=digest:
                    raise ValueError('Input changed during evaluation: '+path)
            summary = report(run,plan,results,'completed')
            emit(status='completed',phase='finished',generation_coverage_complete=summary['generation_coverage_complete'])
        except BaseException as exc:
            close()
            message = errors[0] if errors else str(exc)
            report(run,plan,results,'incomplete',message)
            (run/'STOP').write_text(message+'\nNo automatic retry or budget reset.\n')
            emit(status='paused',error=message)
            raise
        finally:
            done.set();close()
            if thread is not None:
                thread.join(timeout=10)
            if caffeine is not None:
                caffeine.terminate()
                caffeine.wait(timeout=5)
            for sig,handler in old_signals.items():
                signal.signal(sig,handler)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True)
    p.add_argument('--start',action='store_true')
    p.add_argument('--plan-sha256')
    p.add_argument('--budget-seconds',type=int)
    args = p.parse_args()
    if not args.start or not args.plan_sha256 or args.budget_seconds is None:
        p.error('Explicit --start, --plan-sha256 and --budget-seconds required; use benchmark_eval.prepare for CPU-only planning')
    execute(args.run,args.plan_sha256,args.budget_seconds)


if __name__ == '__main__':
    main()
