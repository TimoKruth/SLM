"""python -m slm_perf run --mode light --output ... --module slm.train -- <original args>"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
GPU_MODULES = {'random_search.pilot','slm.train','slm.report','slm.code_eval','slm.interface_eval','slm.broad_eval','slm.validation',
               'experiments.performance.benchmark','slm_perf.ab','slm_perf.workload'}
SUPERVISOR_MODULES = {'slm.sixhour', 'slm.overnight', 'slm.campaign'}


def active_jobs():
    import psutil
    result=[]
    for proc in psutil.process_iter(['pid','cmdline']):
        try:
            if proc.pid!=os.getpid() and GPU_MODULES.intersection(proc.info['cmdline'] or []):
                result.append(proc.pid)
        except (psutil.AccessDenied,psutil.NoSuchProcess): pass
    return result


def environment():
    import psutil
    return dict(machine=platform.machine(),processor=platform.processor(),system=platform.platform(),
                physical_memory_bytes=psutil.virtual_memory().total,python=platform.python_version(),
                packages={name:importlib.metadata.version(name) for name in ['mlx','numpy','psutil']},
                settings={key:os.environ[key] for key in ['OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS','MTL_CAPTURE_ENABLED'] if key in os.environ})


def arg_value(args,flag):
    if flag in args: return args[args.index(flag)+1]
    return next((arg.split('=',1)[1] for arg in args if arg.startswith(flag+'=')),None)


def workload(module,args):
    """Describe comparison inputs, hashing the checkpoint actually used by evaluation."""
    run=arg_value(args,'--run')
    config={}
    if run and (Path(run)/'config.json').exists():
        config=json.loads((Path(run)/'config.json').read_text())
    stable={k:config[k] for k in ['model','batch_size','dtype','manifest_sha256','source_weights_by_sequence','initialization','checkpoint_seconds','eval_seconds','max_tokens'] if k in config}
    # Retain functional CLI overrides; remove only paths and absolute time deadlines.
    omit={'--run','--output','--until'}
    normalized=[];skip=False
    for arg in args:
        if skip: skip=False;continue
        if arg in omit: skip=True;continue
        if any(arg.startswith(flag+'=') for flag in omit):continue
        normalized.append(arg)
    stable['arguments']=normalized
    stable['module']=module
    if config.get('device'):stable['device']=config['device']
    if module in {'slm.code_eval','slm.interface_eval','slm.report','slm.broad_eval'} and run:
        path=Path(run)/'best.safetensors'
        use_latest=module=='slm.report' or (module=='slm.broad_eval' and arg_value(args,'--checkpoint')=='latest')
        if use_latest and (Path(run)/'latest.json').exists():
            pointer=json.loads((Path(run)/'latest.json').read_text())
            path=Path(run)/pointer['checkpoint']/'model.safetensors'
        if path.exists():
            h=hashlib.sha256()
            with path.open('rb') as f:
                for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
            stable['checkpoint_sha256']=h.hexdigest()
    return stable


def launch(args):
    """Run an isolated instrumented module, refusing competing GPU jobs and reused output."""
    from .instrument import MODULES
    if args.module not in MODULES:raise ValueError('Unsupported module: '+args.module)
    # Only lightweight artifact reading and a sleeping queue may coexist with training.
    if args.module not in {'future_eval.analyze','future_eval.queue'} and active_jobs():
        raise RuntimeError('An SLM GPU job is active. No competing workload was started.')
    if args.module in GPU_MODULES or (args.mode=='off' and args.module in SUPERVISOR_MODULES):
        from .gpu_lease import GPULease
        with GPULease() as lease:
            if active_jobs():
                raise RuntimeError('An SLM GPU job became active before launch.')
            if args.mode=='off':
                lease.survive_exec()
            return launch_workload(args)
    return launch_workload(args)


def launch_workload(args):
    """Execute after admission; GPU leaf modules keep their lease through this call."""
    from .instrument import Finder
    target=args.target[1:] if args.target[:1]==['--'] else args.target
    if args.mode=='off':
        # Actual uninstrumented entry point; no profiler, import hook or monitoring files.
        os.execv(sys.executable,[sys.executable,'-m',args.module,*target])
    if not args.output:raise ValueError('--output is required for monitoring')
    out=Path(args.output).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Monitoring output must be new/empty; use a separate directory for resume')
    from .runtime import Monitor
    from .report import write_report
    env=environment()
    mon=Monitor(out,args.mode,args.warmup_steps,args.flush_seconds,args.detail_seconds)
    mon.metadata.update(environment=env,module=args.module,label=args.label,arguments=target,
                        started_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'slm').glob('*.py')},
                        monitoring_source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'slm_perf').glob('*.py')})
    finder=Finder(mon)
    sys.meta_path.insert(0,finder)
    oldargv=sys.argv
    sys.argv=[args.module,*target]
    status='completed'
    mon.start_detail()
    try:
        with mon.span('program'):
            runpy.run_module(args.module,run_name='__main__',init_globals={'_slm_perf':mon})
    except BaseException as exc:
        status='completed' if isinstance(exc,SystemExit) and exc.code in (0,None) else 'failed'
        raise
    finally:
        mon.ended=mon.clock()
        mon.stop_detail()
        sys.argv=oldargv
        sys.meta_path.remove(finder)
        # Bookkeeping after program timing; no device activity or workload writes.
        try:mon.metadata['workload']=workload(args.module,target)
        except Exception as exc:mon.errors.append('Metadata: '+repr(exc))
        mon.finish(status)
        try:write_report(out)
        except OSError as exc:print('Performance report unavailable: '+str(exc),file=sys.stderr)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('--mode',choices=['off','light','detail'],default='off')
    run.add_argument('--module',required=True);run.add_argument('--output');run.add_argument('--label',default='')
    run.add_argument('--warmup-steps',type=int,default=10);run.add_argument('--flush-seconds',type=float,default=60)
    run.add_argument('--detail-seconds',type=float,default=30);run.add_argument('target',nargs=argparse.REMAINDER)
    compare=sub.add_parser('compare');compare.add_argument('baseline');compare.add_argument('candidate');compare.add_argument('--output',required=True)
    inv=sub.add_parser('inventory');inv.add_argument('--output',required=True)
    args=p.parse_args()
    if args.command=='run':
        if args.warmup_steps<0 or args.flush_seconds<=0 or args.detail_seconds<=0:p.error('Invalid timing limits')
        launch(args)
    elif args.command=='compare':
        from .report import comparison
        result=comparison(json.loads(Path(args.baseline).read_text()),json.loads(Path(args.candidate).read_text()))
        Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='phase_deltas'},indent=2))
        if not result['comparable']:raise SystemExit(2)
    else:
        from .instrument import MODULES,transformed
        result={}
        for module in sorted(MODULES):
            path=ROOT/(module.replace('.','/')+'.py')
            if path.exists():
                _,coverage=transformed(path.read_text(),str(path),module)
                result[module]=dict(source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),instrumented=coverage)
        Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
        print(f'{len(result)} modules inspected; no workload executed')


if __name__=='__main__':main()
