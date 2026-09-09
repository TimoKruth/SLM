"""Configurable fixed-token experiments, keeping original production code frozen."""
import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time
from datetime import datetime

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten, tree_map
import numpy as np
import psutil

from research.common import read, write
from slm.data import Sampler
from slm.model import ModelConfig, LanguageModel, loss_fn
from slm.precision import MixedModel
from slm.train import restore, checkpoint
from slm.breadth import sampling_weights, SOURCE_FAMILY
from .design import BASE, validate, lr_at


def mask_of(real, answer, p):
    return real * (p['prompt_weight'] * (1 - answer) + p['answer_weight'] * answer)


def make_step(model, optimizer, p):
    """Accumulate token-weighted microbatch gradients, then clip/update once."""
    optimizer.init(model.trainable_parameters())
    state = [model.state, optimizer.state]
    grad = nn.value_and_grad(model, loss_fn)
    micro = p['microbatch']

    def update(x, y, mask, lr):
        optimizer.learning_rate = lr
        accumulated, numerator = None, mx.array(0.)
        denominator = mx.maximum(mx.sum(mask), 1.)
        for i in range(p['accumulation']):
            sl = slice(i * micro, (i + 1) * micro)
            loss, gradients = grad(model, x[sl], y[sl], mask[sl])
            count = mx.sum(mask[sl])
            numerator = numerator + loss * count
            gradients = tree_map(lambda v: v * (count / denominator), gradients)
            accumulated = gradients if accumulated is None else tree_map(lambda a, b: a+b, accumulated, gradients)
        if p['clip']:
            accumulated, norm = optim.clip_grad_norm(accumulated, p['clip'])
        else:
            norm = mx.sqrt(sum(mx.sum(g*g) for _, g in tree_flatten(accumulated)))
        optimizer.update(model, accumulated)
        return numerator / denominator, norm
    return mx.compile(update, inputs=state, outputs=state) if p['execution'] == 'compiled' else update


def load(plan, p, data_seed, model_seed):
    mx.random.seed(model_seed)
    cls = MixedModel if p['precision'] == 'bf16' else LanguageModel
    model = cls(ModelConfig(**p['model']))
    opt = optim.AdamW(learning_rate=p['lr'], betas=[p['beta1'], p['beta2']],
                      eps=p['eps'], weight_decay=p['weight_decay'], bias_correction=p['bias_correction'])
    data = Path(plan['data'])
    original = read(data / 'manifest.json')['source_weights']
    weights = sampling_weights(original, p['mixture'])
    if p['boost_family']:
        weights = {s:w*(2 if SOURCE_FAMILY[s] == p['boost_family'] else 1) for s,w in weights.items()}
        total = sum(weights.values())
        weights = {s:w/total for s,w in weights.items()}
    sampler = Sampler(data, seed=data_seed, context=p['train_context'], weights=weights)
    eligible = {}
    for source in sampler.names:
        sampler.indices[source] = sampler.indices[source][sampler.indices[source][:,1] <= p['eligibility']]
        eligible[source] = len(sampler.indices[source])
        if not eligible[source]:
            raise ValueError('Source lost by context eligibility: ' + source)
    parent = Path(plan['parent'])
    if p['initialization'] == 'parent':
        if read(parent/'latest.json')['checkpoint'] != plan['parent_checkpoint']:
            raise ValueError('Parent changed')
        if p['reset_optimizer']:
            model.load_weights(str(parent / plan['parent_checkpoint'] / 'model.safetensors'))
            state = read(parent / plan['parent_checkpoint'] / 'state.json')
            state.pop('sampler_state')
        else:
            state = restore(parent, model, opt, sampler)
        sampler.rng = np.random.default_rng(data_seed)
    else:
        if p['init_std'] != .02:
            model.update(tree_map(lambda v: v * (p['init_std']/.02) if v.ndim >= 2 else v, model.parameters()))
        state = dict(step=0, tokens=0, source_tokens={}, best_dev_loss=None)
    mx.eval(model.parameters(), opt.state)
    model.train()
    return model, opt, sampler, state, eligible, weights


def step(model, opt, update, batch, p, lr):
    x, y, real, answer = batch
    loss, norm = update(mx.array(x), mx.array(y), mx.array(mask_of(real, answer, p)), mx.array(lr))
    mx.eval(model.parameters(), opt.state, loss, norm)
    loss, norm = float(loss.item()), float(norm.item())
    if not math.isfinite(loss) or not math.isfinite(norm):
        raise FloatingPointError('Nonfinite objective or gradient')
    return loss, norm


def control(plan, run):
    """Two full checkpoint updates: production vs accumulated microbatch path."""
    from slm.optimization import make_training_step
    p = dict(BASE)
    a, oa, sa, _, _, _ = load(plan, p, 202609099, 12)
    b, ob, sb, _, _, _ = load(plan, p, 202609099, 12)
    fa = make_training_step(a, oa)
    accumulated = dict(p, microbatch=1, accumulation=2)
    fb = make_step(b, ob, accumulated)
    for _ in range(2):
        batch, other = sa.batch(2), sb.batch(2)
        for x,y in zip(batch,other):
            np.testing.assert_array_equal(x,y)
        x,y,real,_ = batch
        loss,norm = fa(mx.array(x),mx.array(y),mx.array(real),mx.array(p['lr']))
        mx.eval(a.parameters(),oa.state,loss,norm)
        step(b,ob,fb,other,accumulated,p['lr'])
    aa,bb = [dict(tree_flatten([m.parameters(),o.state])) for m,o in [(a,oa),(b,ob)]]
    assert aa.keys()==bb.keys()
    worst=0.
    for k in aa:
        x,y=np.array(aa[k]),np.array(bb[k])
        np.testing.assert_allclose(x,y,rtol=5e-4,atol=3e-6,err_msg=k)
        worst=max(worst,float(np.max(np.abs(x-y))))
    write(run/'control.json',dict(passed=True,compared_arrays=len(aa),max_absolute_error=worst,
                                  rtol=5e-4,atol=3e-6,steps=2))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',required=True)
    parser.add_argument('--plan',required=True)
    parser.add_argument('--job')
    parser.add_argument('--control-only',action='store_true')
    args=parser.parse_args()
    started=time.monotonic()
    run,plan=Path(args.run),read(args.plan)
    run.mkdir(parents=True,exist_ok=True)
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(20*1024**3)
    mx.set_cache_limit(512*1024**2)
    if args.control_only:
        control(plan,run)
        return
    if (run/'config.json').exists():
        raise ValueError('Never reuse trial outputs')
    job=read(args.job);p=job['parameters'];validate(p)
    model,opt,sampler,state,eligible,weights=load(plan,p,job['data_seed'],job['model_seed'])
    start_step,start_tokens=state['step'],state['tokens']
    sampler_initial=copy.deepcopy(sampler.rng.bit_generator.state)
    state.update(signature=hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest(), research_trial=True,
                 best_dev_loss=None)
    cfg=dict(model=p['model'],parameters=sum(v.size for _,v in tree_flatten(model.parameters())),
             dtype='float32',forward_precision=p['precision'],batch_size=p['microbatch']*p['accumulation'],
             initialization=p['initialization'],source_weights_by_sequence=weights,
             manifest_sha256=plan['data_manifest_sha256'],research_trial=True,study_job=job,
             training_objective='Weighted full-token CE; prompt/answer weights explicit; no padding; microbatch token-weighted accumulation')
    write(run/'config.json',cfg)
    shutil.copy2(Path(plan['parent'])/'tokenizer.json',run/'tokenizer.json')
    conditions=read(Path(args.plan).parent/'RUN_CONDITIONS.json')
    conditions.update(trial_recorded_at=datetime.now().astimezone().isoformat(),
                      trial_power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),
                      trial_power_source=subprocess.check_output(['pmset','-g','batt'],text=True))
    write(run/'RUN_CONDITIONS.json',conditions)
    update=make_step(model,opt,p)
    source_tokens=Counter();batches_hash=hashlib.sha256();monitor=globals().get('_slm_perf');snapshots=[]
    def emit(event):
        write(run/'status.json',event)
        if monitor:monitor.event(event)
    emit(dict(status='running',event='start',step=start_step,tokens=start_tokens))
    with (run/'metrics.jsonl').open('w',buffering=1) as log:
        while state['tokens']-start_tokens < job['target_tokens']:
            if time.monotonic()-started >= job['train_seconds']-15 or (run/'STOP').exists():break
            if psutil.virtual_memory().available < 6*1024**3:raise MemoryError('Available RAM below 6 GiB')
            batch=sampler.batch(cfg['batch_size'])
            batches_hash.update(batch[0].tobytes());batches_hash.update(batch[1].tobytes())
            lr=lr_at(p,state['tokens']-start_tokens,job['target_tokens'],state['step']-start_step)
            loss,norm=step(model,opt,update,batch,p,lr)
            state['step']+=1;state['tokens']+=int(batch[2].sum());source_tokens.update(sampler.last_batch_source_tokens)
            for target in job.get('snapshot_tokens',[]):
                name=f'token-{target:09d}'
                if state['tokens']-start_tokens>=target and name not in snapshots:
                    destination=run/name;destination.mkdir()
                    model.save_weights(str(destination/'model.safetensors'))
                    write(destination/'config.json',dict(cfg,snapshot_evaluation_only=True,
                          snapshot_actual_tokens_delta=state['tokens']-start_tokens))
                    shutil.copy2(run/'tokenizer.json',destination/'tokenizer.json')
                    write(destination/'latest.json',{'checkpoint':'.'})
                    snapshots.append(name)
            if (state['step']-start_step)%10==0:
                event=dict(status='running',event='train',step=state['step'],tokens=state['tokens'],
                           loss=loss,grad_norm=norm,lr=lr,additional_tokens=state['tokens']-start_tokens,
                           elapsed_seconds=time.monotonic()-started,mlx_peak_gb=mx.get_peak_memory()/1e9)
                log.write(json.dumps(event)+'\n');emit(event)
    for s,n in source_tokens.items():state.setdefault('source_tokens',{})[s]=state.get('source_tokens',{}).get(s,0)+n
    folder=checkpoint(run,model,opt,sampler,state)
    complete=state['tokens']-start_tokens>=job['target_tokens']
    result=dict(status='completed' if complete else 'incomplete',checkpoint=folder.name,
                additional_tokens=state['tokens']-start_tokens,additional_steps=state['step']-start_step,
                base_tokens=start_tokens,cumulative_tokens=state['tokens'],source_tokens=dict(source_tokens),
                batches_sha256=batches_hash.hexdigest(),initial_sampler=sampler_initial,final_sampler=sampler.rng.bit_generator.state,
                eligible_records_by_source=eligible,elapsed_seconds=time.monotonic()-started,
                peak_gpu_gb=mx.get_peak_memory()/1e9,snapshots=snapshots)
    write(run/'result.json',result);emit(dict(result,event='finished',step=state['step'],tokens=state['tokens']))
    if not complete:raise RuntimeError('Incomplete fixed-token target')


if __name__=='__main__':main()
