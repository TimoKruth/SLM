"""Idle-only, fixed-work A/B calibration; never modifies a training checkpoint."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True);p.add_argument('--output',required=True)
    p.add_argument('--steps',type=int,default=20);p.add_argument('--warmup',type=int,default=5)
    p.add_argument('--repeats',type=int,default=3);p.add_argument('--metal-capture',action='store_true')
    p.add_argument('--state-rtol',type=float,default=5e-4)
    p.add_argument('--state-atol',type=float,default=5e-6,
                   help='Predeclare the FP32 state tolerance; record any pilot-based change in the experiment protocol.')
    args=p.parse_args()
    if args.steps<=args.warmup or args.warmup<0 or args.repeats<2:p.error('Need timed steps and at least two repetitions')
    if any(not math.isfinite(x) or x<0 for x in (args.state_rtol,args.state_atol)):
        p.error('State tolerances must be finite and nonnegative')
    from .__main__ import active_jobs
    if active_jobs():raise RuntimeError('Active SLM GPU job; calibration refused')
    from .gpu_lease import GPULease
    with GPULease():
        if active_jobs():
            raise RuntimeError('Active SLM GPU job; calibration refused')
        calibrate(args)


def calibrate(args):
    """Measure fixed work only while the calling process holds the shared GPU lease."""
    from .__main__ import environment
    out=Path(args.output)
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new calibration output directory')
    out.mkdir(parents=True)
    import gc
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    from mlx.utils import tree_flatten
    import numpy as np
    from slm.model import LanguageModel,ModelConfig,loss_fn
    from slm.data import Sampler
    from . import workload
    from .instrument import transformed
    from .runtime import Monitor
    from .report import write_report
    run=Path(args.run);config=json.loads((run/'config.json').read_text())
    mx.set_default_device(mx.gpu);mx.set_memory_limit(12*1024**3);mx.set_cache_limit(512*1024**2)
    sampler=Sampler(Path(config['data']),context=config['model']['context'],seed=77197)
    batches=[sampler.batch(config['batch_size']) for _ in range(args.steps)]
    code,coverage=transformed(Path(workload.__file__).read_text(),workload.__file__,'slm_perf.workload')
    trials=[]
    reference_arrays=None
    state_rtol,state_atol=args.state_rtol,args.state_atol
    for repeat in range(args.repeats):
        # Rotate which mode is first; all modes start from identical weights and Adam state.
        modes=['off','light','detail'];modes=modes[repeat%3:]+modes[:repeat%3]
        for mode in modes:
            model=LanguageModel(ModelConfig(**config['model']));model.load_weights(str(run/'best.safetensors'))
            optimizer=optim.AdamW(learning_rate=3e-4,betas=[.9,.95],weight_decay=.1,bias_correction=True)
            optimizer.init(model.trainable_parameters());mx.eval(model.parameters(),optimizer.state)
            grad_fn=nn.value_and_grad(model,loss_fn)
            mon=None;step=workload.step
            if mode!='off':
                mon=Monitor(out/f'{repeat}-{mode}',mode=mode,warmup_steps=args.warmup)
                mon.metadata.update(environment=environment(),workload={'config':config['model'],'manifest':config['manifest_sha256'],'batch_size':config['batch_size'],'steps':args.steps,'seed':77197,'fixed_learning_rate_sequence':True},coverage=coverage)
                scope={'_slm_perf':mon};exec(code,scope);step=scope['step'];mon.start_detail()
            losses=[];measured=None
            begin=time.perf_counter()
            for i,batch in enumerate(batches):
                if i==args.warmup:measured=time.perf_counter()
                x,y,mask=[mx.array(b) for b in batch[:3]]
                loss,norm=step(model,optimizer,grad_fn,x,y,mask,3e-4/(1+i/20));losses.append(loss)
            end=time.perf_counter()
            if mon:mon.ended=mon.clock();mon.finish();write_report(mon.output)
            h=hashlib.sha256()
            arrays={name:np.asarray(value) for name,value in tree_flatten([model.parameters(),optimizer.state])}
            for name,value in arrays.items():
                h.update(name.encode());h.update(value.tobytes())
            if reference_arrays is None:
                reference_arrays={name:value.copy() for name,value in arrays.items()}
            state_close=arrays.keys()==reference_arrays.keys() and all(np.allclose(value,reference_arrays[name],rtol=state_rtol,atol=state_atol) for name,value in arrays.items())
            max_difference=max(float(np.max(np.abs(value.astype(float)-reference_arrays[name].astype(float)))) for name,value in arrays.items())
            result=dict(repeat=repeat,mode=mode,total_seconds=end-begin,steady_seconds=end-measured,
                        timed_steps=args.steps-args.warmup,step_mean_seconds=(end-measured)/(args.steps-args.warmup),
                        nonpadding_tokens=int(sum(b[2].sum() for b in batches[args.warmup:])),
                        losses=losses,weights_and_optimizer_sha256=h.hexdigest(),state_within_tolerance=state_close,max_abs_state_difference=max_difference)
            trials.append(result)
            with (out/'trials.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
            print(json.dumps(result),flush=True)
            del arrays,model,optimizer,grad_fn,step
            if mon:del scope
            gc.collect();mx.clear_cache()
    reference=trials[0]
    identical=all(t['weights_and_optimizer_sha256']==reference['weights_and_optimizer_sha256'] and t['losses']==reference['losses'] for t in trials)
    equivalent=all(t['state_within_tolerance'] and np.allclose(t['losses'],reference['losses'],rtol=2e-5,atol=2e-6) for t in trials)
    medians={mode:statistics.median(t['step_mean_seconds'] for t in trials if t['mode']==mode) for mode in ['off','light','detail']}
    overhead={mode:100*(medians[mode]/medians['off']-1) for mode in ['light','detail']}
    # Report spread, never interpret a single small negative difference as a speed gain.
    spread={mode:[min(t['step_mean_seconds'] for t in trials if t['mode']==mode),max(t['step_mean_seconds'] for t in trials if t['mode']==mode)] for mode in medians}
    result=dict(status='completed',environment=environment(),identical_weights_optimizer_and_losses=identical,numerically_equivalent=bool(equivalent),state_tolerance={'rtol':state_rtol,'atol':state_atol},
                median_step_seconds=medians,observed_overhead_percent=overhead,trial_min_max_seconds=spread,trials=trials,
                light_under_one_percent_observed=bool(equivalent and overhead['light']<=1),
                notes='Fixed work and LR, same data/weights, rotated order. Short calibration, not a universal overhead guarantee. Real wall-clock LR/deadlines can shift with any instrumentation. Final profile export excluded; normal 60s flush cost is separately recorded by actual monitoring runs.')
    if args.metal_capture:
        # Separate diagnostic only; none of the A/B timing intervals include capture.
        try:
            model=LanguageModel(ModelConfig(**config['model']));model.load_weights(str(run/'best.safetensors'))
            optimizer=optim.AdamW(learning_rate=3e-4);optimizer.init(model.trainable_parameters());mx.eval(model.parameters(),optimizer.state)
            grad_fn=nn.value_and_grad(model,loss_fn)
            x,y,mask=[mx.array(v) for v in batches[0][:3]]
            workload.step(model,optimizer,grad_fn,x,y,mask,3e-4)
            mx.metal.start_capture(str((out/'kernels.gputrace').resolve()))
            try:
                for _ in range(2):workload.step(model,optimizer,grad_fn,x,y,mask,3e-4)
            finally:mx.metal.stop_capture()
            result['metal_capture']='kernels.gputrace'
        except Exception as exc:result['metal_capture_error']=repr(exc)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'REPORT.md').write_text('# Monitoring-A/B-Vergleich\n\n'+f"Bitidentische Gewichte, Optimiererzustände und Loss: {identical}. Numerisch innerhalb der dokumentierten Toleranzen: {equivalent}.\n\n"+'\n'.join(f"- {mode}: {medians[mode]*1000:.3f} ms/Schritt; beobachteter Zusatzaufwand {overhead[mode]:+.2f} %." for mode in ['light','detail'])+'\n\n'+result['notes']+'\n')
    if not equivalent:raise SystemExit(2)


if __name__=='__main__':main()
