"""Fixed-work adaptation from an immutable parent, plus a real-checkpoint control."""
import argparse
from collections import Counter
import copy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import time

import mlx.core as mx
import mlx.optimizers as optim
from mlx.utils import tree_flatten
import numpy as np
import psutil

from slm.data import Sampler
from slm.model import LanguageModel, ModelConfig
from slm.optimization import make_training_step
from slm.train import restore, checkpoint
from .common import read, write, weighted_mask


def load(plan, seed=None):
    parent = Path(plan['parent'])
    config = read(parent / 'config.json')
    if read(parent / 'latest.json')['checkpoint'] != plan['parent_checkpoint']:
        raise ValueError('Parent checkpoint changed')
    model = LanguageModel(ModelConfig(**config['model']))
    optimizer = optim.AdamW(learning_rate=3e-5, betas=[.9, .95], weight_decay=.1)
    sampler = Sampler(Path(plan['data']), context=config['context'], weights=config['source_weights_by_sequence'])
    state = restore(parent, model, optimizer, sampler)
    if seed is not None:
        sampler.rng = np.random.default_rng(seed)
    model.train()
    return model, optimizer, sampler, state, config


def step(model, optimizer, update, batch, lr, weight):
    x, y, real, answer = batch
    mask = weighted_mask(real, answer, weight)
    loss, norm = update(mx.array(x), mx.array(y), mx.array(mask), mx.array(lr))
    mx.eval(model.parameters(), optimizer.state, loss, norm)
    loss, norm = float(loss.item()), float(norm.item())
    if not math.isfinite(loss) or not math.isfinite(norm):
        raise FloatingPointError('Nonfinite loss or gradient')
    return loss, norm


def control(plan, run):
    """w=1 matches the production full-token update including all Adam state."""
    a, oa, sa, _, _ = load(plan)
    b, ob, sb, _, _ = load(plan)
    fa, fb = make_training_step(a, oa), make_training_step(b, ob)
    for _ in range(2):
        batch = sa.batch(2)
        other = sb.batch(2)
        for x, y in zip(batch, other):
            np.testing.assert_array_equal(x, y)
        step(a, oa, fa, batch, 3e-5, 1)
        x, y, real, _ = other
        loss, norm = fb(mx.array(x), mx.array(y), mx.array(real), mx.array(3e-5))
        mx.eval(b.parameters(), ob.state, loss, norm)
    aa = dict(tree_flatten([a.parameters(), oa.state]))
    bb = dict(tree_flatten([b.parameters(), ob.state]))
    assert aa.keys() == bb.keys()
    max_error = 0.
    for key in aa:
        x, y = np.array(aa[key]), np.array(bb[key])
        np.testing.assert_allclose(x, y, rtol=5e-4, atol=3e-6, err_msg=key)
        max_error = max(max_error, float(np.max(np.abs(x - y))))
    assert sa.rng.bit_generator.state == sb.rng.bit_generator.state
    write(run / 'control.json', dict(passed=True, steps=2, compared_arrays=len(aa), max_absolute_error=max_error,
                                    rtol=5e-4, atol=3e-6, parent=plan['parent_checkpoint']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--variant')
    parser.add_argument('--repetition', type=int, default=0)
    parser.add_argument('--control-only', action='store_true')
    args = parser.parse_args()
    started = time.monotonic()
    run, plan = Path(args.run), read(args.plan)
    run.mkdir(parents=True, exist_ok=True)
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(12 * 1024**3)
    mx.set_cache_limit(512 * 1024**2)
    if args.control_only:
        control(plan, run)
        return
    if (run / 'config.json').exists():
        raise ValueError('Trial outputs cannot be reused')
    variant = next(v for v in plan['variants'] if v['name'] == args.variant)
    seed = plan['data_order_seeds'][args.repetition]
    model, optimizer, sampler, state, config = load(plan, seed)
    base_step, base_tokens = state['step'], state['tokens']
    initial_sampler = copy.deepcopy(sampler.rng.bit_generator.state)
    signature = hashlib.sha256(json.dumps(dict(parent=state['signature'], variant=variant, seed=seed,
                                               objective='research_weighted_v1'), sort_keys=True).encode()).hexdigest()
    state.update(signature=signature, research_trial=True)
    config.update(run=str(run), initialization='adaptation_from_six_hour_checkpoint', parent=plan['parent'],
                  parent_checkpoint=plan['parent_checkpoint'], research_trial=True, repetition=args.repetition,
                  training_objective='sum(CE * real * (1+(answer_weight-1)*answer)) / sum(real * (1+(answer_weight-1)*answer))',
                  intervention=variant, forward_precision='fp32', schedule_tokens=0,
                  snapshot_tokens=[], max_tokens=base_tokens + plan['additional_tokens'])
    write(run / 'config.json', config)
    shutil.copy2(Path(plan['parent']) / 'tokenizer.json', run / 'tokenizer.json')
    shutil.copy2(Path(args.plan).parent / 'RUN_CONDITIONS.json', run / 'RUN_CONDITIONS.json')
    update = make_training_step(model, optimizer, compiled=True)
    source_tokens = Counter()
    batches_hash = hashlib.sha256()
    monitor = globals().get('_slm_perf')
    if monitor:
        monitor.event(dict(event='start', step=base_step, tokens=base_tokens))
    with (run / 'metrics.jsonl').open('w', buffering=1) as log:
        while state['tokens'] - base_tokens < plan['additional_tokens']:
            # Leave checkpoint time inside the supervisor's hard per-process cap.
            if time.monotonic() - started >= plan['trial_seconds'] - 12 or (run / 'STOP').exists():
                break
            if psutil.virtual_memory().available < 6 * 1024**3:
                raise MemoryError('Less than 6 GiB available system memory')
            batch = sampler.batch(config['batch_size'])
            batches_hash.update(batch[0].tobytes())
            batches_hash.update(batch[1].tobytes())
            loss, norm = step(model, optimizer, update, batch, variant['learning_rate'], variant['answer_weight'])
            state['step'] += 1
            state['tokens'] += int(batch[2].sum())
            source_tokens.update(sampler.last_batch_source_tokens)
            if (state['step'] - base_step) % 10 == 0:
                event = dict(event='train', step=state['step'], tokens=state['tokens'], additional_tokens=state['tokens'] - base_tokens,
                             loss=loss, loss_kind='weighted_training_objective', grad_norm=norm,
                             lr=variant['learning_rate'], elapsed_seconds=time.monotonic() - started,
                             mlx_peak_gb=mx.get_peak_memory()/1e9, system_available_gb=psutil.virtual_memory().available/1e9)
                log.write(json.dumps(event) + '\n')
                write(run / 'status.json', dict(status='running', updated_at=datetime.now().astimezone().isoformat(), **event))
                if monitor:
                    monitor.event(event)
    for source, count in source_tokens.items():
        state.setdefault('source_tokens', {})[source] = state.get('source_tokens', {}).get(source, 0) + count
    state['best_dev_loss'] = None
    folder = checkpoint(run, model, optimizer, sampler, state)
    complete = state['tokens'] - base_tokens >= plan['additional_tokens']
    result = dict(status='completed' if complete else 'incomplete', checkpoint=folder.name,
                  additional_tokens=state['tokens'] - base_tokens, additional_steps=state['step'] - base_step,
                  base_tokens=base_tokens, cumulative_tokens=state['tokens'], source_tokens=dict(source_tokens),
                  batches_sha256=batches_hash.hexdigest(), initial_sampler=initial_sampler,
                  final_sampler=sampler.rng.bit_generator.state, elapsed_seconds=time.monotonic() - started,
                  finished=datetime.now().astimezone().isoformat())
    write(run / 'result.json', result)
    write(run / 'status.json', result)
    if monitor:
        monitor.event(dict(event='finished', step=state['step'], tokens=state['tokens']))
    if not complete:
        raise RuntimeError('Fixed token target not reached; no matched-work comparison allowed')


if __name__ == '__main__':
    main()
