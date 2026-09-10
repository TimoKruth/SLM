"""Fixed-wall-time training, periodic resumable checkpoints, unchanged math."""
import argparse
import copy
from datetime import datetime
from pathlib import Path
import shutil
import signal
import subprocess
import time

from research.common import read,write
from .protocol import signature,phase_for_elapsed


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True)
    parser.add_argument('--plan',required=True);parser.add_argument('--job',required=True)
    parser.add_argument('--wall-seconds',type=float);parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();started=time.monotonic()
    run=Path(args.run);plan=read(args.plan);job=read(args.job);p=job['parameters']
    limit=min(job['train_seconds'],args.wall_seconds or job['train_seconds'])
    reserve=job.get('checkpoint_reserve_seconds',60)
    phase_for_elapsed(0,limit,reserve)
    if (run/'STOP').exists() or (Path(args.plan).parent/'STOP').exists():raise ValueError('STOP')
    if (run/'config.json').exists() and not args.resume:raise ValueError('Use new trial directory')
    if args.resume and (run/'result.json').exists() and read(run/'result.json')['status']=='completed':
        raise ValueError('Completed wall-time trial cannot restart')
    expected=signature(plan,job)
    # Import MLX only in a monitored GPU process.
    import mlx.core as mx
    import psutil
    from mlx.utils import tree_flatten
    from study.trial import load,make_step,step
    from study.design import validate
    from slm.train import checkpoint,restore
    validate(p)
    if p['schedule']!='constant':raise ValueError('This block preregisters constant LR only')
    mx.set_default_device(mx.gpu);mx.set_memory_limit(20*1024**3);mx.set_cache_limit(512*1024**2)
    model,opt,sampler,state,eligible,weights=load(plan,p,job['data_seed'],job['model_seed'])
    if args.resume:
        if read(run/'config.json')['long_signature']!=expected:raise ValueError('Resume signature changed')
        state=restore(run,model,opt,sampler)
        if state['long_signature']!=expected:raise ValueError('Checkpoint signature changed')
        # An uncommitted token snapshot may be ahead of the restored optimizer.
        for path in run.glob('token-*'):
            if path.name not in state['long_snapshots']:
                archive=run/'orphaned-snapshots'/str(time.time_ns());archive.mkdir(parents=True)
                path.rename(archive/path.name)
    else:
        state.update(long_signature=expected,long_base_tokens=state['tokens'],long_base_step=state['step'],
                     long_source_tokens={},long_snapshots=[],long_active_seconds=0.,
                     long_initial_sampler=copy.deepcopy(sampler.rng.bit_generator.state))
        cfg=dict(model=p['model'],parameters=sum(v.size for _,v in tree_flatten(model.parameters())),
                 dtype='float32',forward_precision=p['precision'],batch_size=p['microbatch']*p['accumulation'],
                 manifest_sha256=plan['data_manifest_sha256'],source_weights_by_sequence=weights,
                 long_job=job,long_signature=expected,initialization='parent',eligible_records_by_source=eligible)
        write(run/'config.json',cfg);shutil.copy2(Path(plan['parent'])/'tokenizer.json',run/'tokenizer.json')
    cfg=read(run/'config.json');conditions=read(Path(args.plan).parent/'RUN_CONDITIONS.json')
    conditions.update(recorded_at=datetime.now().astimezone().isoformat(),
        power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),
        power_source=subprocess.check_output(['pmset','-g','batt'],text=True))
    write(run/('RUN_CONDITIONS-resume.json' if args.resume else 'RUN_CONDITIONS.json'),conditions)
    previous_active=state['long_active_seconds'];last_saved=time.monotonic()
    stopped=[]
    for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,lambda n,f:stopped.append(n))
    update=make_step(model,opt,p);monitor=globals().get('_slm_perf')
    def emit(event):
        write(run/'status.json',event)
        if monitor:monitor.event(event)
    def snapshot(target):
        name=f'token-{target:09d}';destination=run/name
        temporary=run/(name+'.tmp')
        if temporary.exists():shutil.rmtree(temporary)
        temporary.mkdir();model.save_weights(str(temporary/'model.safetensors'))
        write(temporary/'config.json',dict(cfg,snapshot_evaluation_only=True,
              snapshot_actual_tokens_delta=state['tokens']-state['long_base_tokens']))
        shutil.copy2(run/'tokenizer.json',temporary/'tokenizer.json')
        write(temporary/'latest.json',{'checkpoint':'.'})
        write(temporary/'snapshot.json',dict(step=state['step'],additional_tokens=state['tokens']-state['long_base_tokens']))
        temporary.rename(destination);state['long_snapshots'].append(name)
    emit(dict(status='running',event='start',step=state['step'],additional_tokens=state['tokens']-state['long_base_tokens']))
    reason='time_budget'
    with (run/'metrics.jsonl').open('a',buffering=1) as log:
        while phase_for_elapsed(time.monotonic()-started,limit,reserve)=='train':
            if stopped or (run/'STOP').exists() or (Path(args.plan).parent/'STOP').exists():reason='requested_stop';break
            if psutil.virtual_memory().available<10*1024**3:reason='memory_pressure';break
            batch=sampler.batch(cfg['batch_size'])
            loss,norm=step(model,opt,update,batch,p,p['lr'])
            state['step']+=1;state['tokens']+=int(batch[2].sum())
            for source,count in sampler.last_batch_source_tokens.items():
                state['long_source_tokens'][source]=state['long_source_tokens'].get(source,0)+count
                state.setdefault('source_tokens',{})[source]=state['source_tokens'].get(source,0)+count
            for target in job['snapshot_tokens']:
                if state['tokens']-state['long_base_tokens']>=target and f'token-{target:09d}' not in state['long_snapshots']:
                    snapshot(target)
            if state['step']%10==0:
                event=dict(status='running',event='train',step=state['step'],additional_tokens=state['tokens']-state['long_base_tokens'],
                           loss=loss,grad_norm=norm,lr=p['lr'],elapsed_seconds=previous_active+time.monotonic()-started)
                log.write(__import__('json').dumps(event)+'\n');emit(event)
            if time.monotonic()-last_saved>=job.get('checkpoint_seconds',300):
                state['long_active_seconds']=previous_active+time.monotonic()-started
                checkpoint(run,model,opt,sampler,state);last_saved=time.monotonic()
    state['long_active_seconds']=previous_active+time.monotonic()-started
    folder=checkpoint(run,model,opt,sampler,state)
    result=dict(status='completed' if reason=='time_budget' else 'paused',endpoint=reason,checkpoint=folder.name,
                additional_tokens=state['tokens']-state['long_base_tokens'],additional_steps=state['step']-state['long_base_step'],
                base_tokens=state['long_base_tokens'],cumulative_tokens=state['tokens'],source_tokens=state['long_source_tokens'],
                initial_sampler=state['long_initial_sampler'],final_sampler=sampler.rng.bit_generator.state,
                snapshots=state['long_snapshots'],elapsed_seconds=previous_active+time.monotonic()-started,
                process_elapsed_seconds=time.monotonic()-started,peak_gpu_gb=mx.get_peak_memory()/1e9,
                long_signature=expected,checkpoint_reserve_seconds=reserve,
                accounting='Campaign stage clock is authoritative, including failed work and recovery.')
    write(run/'result.json',result);emit(result)
    if reason!='time_budget':raise RuntimeError(reason)

if __name__=='__main__':main()
