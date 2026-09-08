"""Deadline-aware MLX training with atomic, resumable checkpoints and development loss."""
import argparse
import json
import math
import os
import shutil
import signal
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np
import psutil
from mlx.utils import tree_flatten, tree_unflatten

from .data import Sampler, WEIGHTS
from .model import ModelConfig, LanguageModel, loss_fn
from .prepare import digest

ROOT = Path(__file__).resolve().parents[1]


def atomic_json(path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False))
    tmp.replace(path)


def checkpoint(run, model, optimizer, sampler, state):
    folder = run / f"checkpoint-{state['step']:07d}"
    tmp = run / (folder.name + '.tmp')
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    model.save_weights(str(tmp / 'model.safetensors'))
    mx.savez(str(tmp / 'optimizer.npz'), **dict(tree_flatten(optimizer.state)))
    atomic_json(tmp / 'state.json', dict(state, sampler_state=sampler.rng.bit_generator.state))
    atomic_json(tmp / 'model_config.json', asdict(model.config))
    if folder.exists():
        # The previous complete version stays recoverable until the new directory is ready.
        old = folder.with_name(folder.name + '.old')
        if old.exists():
            shutil.rmtree(old)
        folder.rename(old)
        tmp.rename(folder)
        shutil.rmtree(old)
    else:
        tmp.rename(folder)
    atomic_json(run / 'latest.json', {'checkpoint': folder.name})
    completed = sorted(p for p in run.glob('checkpoint-*') if p.is_dir() and p.name[-7:].isdigit())
    for old in completed[:-2]:
        shutil.rmtree(old)
    return folder


def token_snapshots(run, model, state, thresholds):
    """Preserve small evaluation-only snapshots on first crossing a token threshold."""
    saved = state.setdefault('token_snapshots', [])
    for target in thresholds:
        if state['tokens'] < target or target in saved:
            continue
        folder = run / f'token-{target:09d}'
        if not folder.exists():
            tmp = folder.with_name(folder.name + '.tmp')
            if tmp.exists():
                shutil.rmtree(tmp)
            tmp.mkdir()
            model.save_weights(str(tmp / 'best.safetensors'))
            config = json.loads((run / 'config.json').read_text())
            config.update(snapshot_target_tokens=target, snapshot_actual_tokens=state['tokens'],
                          checkpoint_selection='First complete training step crossing fixed token threshold')
            atomic_json(tmp / 'config.json', config)
            atomic_json(tmp / 'snapshot.json', dict(target_tokens=target, tokens=state['tokens'],
                step=state['step'], source_tokens=state.get('source_tokens', {}),
                evaluation_only=True, optimizer_state_saved=False))
            shutil.copy2(run / 'tokenizer.json', tmp / 'tokenizer.json')
            tmp.rename(folder)
        saved.append(target)


def training_signature(config, manifest_sha256, batch_size, weights, seed, schedule_tokens=0, snapshot_tokens=(), forward_precision='fp32'):
    """Preserve historical FP32 signatures and prevent cross-precision resume."""
    signature = digest(json.dumps({'config': config, 'manifest': manifest_sha256, 'batch_size': batch_size, 'weights': weights, 'seed': seed}, sort_keys=True))
    if schedule_tokens or snapshot_tokens:
        signature = digest(json.dumps(dict(base_signature=signature, schedule_tokens=schedule_tokens, snapshot_tokens=list(snapshot_tokens)), sort_keys=True))
    if forward_precision != 'fp32':
        signature = digest(json.dumps(dict(base_signature=signature, forward_precision=forward_precision), sort_keys=True))
    return signature


def schedule_fraction(tokens, maximum_tokens, started_at, deadline, now, schedule_tokens=0):
    """Optional shared token clock for equal-exposure model-size comparisons."""
    fraction = tokens / schedule_tokens if schedule_tokens else max(tokens / maximum_tokens, (now-started_at)/max(1., deadline-started_at))
    return min(1., max(0., fraction))


def restore(run, model, optimizer, sampler):
    pointer = json.loads((run / 'latest.json').read_text())
    folder = run / pointer['checkpoint']
    model.load_weights(str(folder / 'model.safetensors'))
    optimizer.state = tree_unflatten(list(mx.load(str(folder / 'optimizer.npz')).items()))
    state = json.loads((folder / 'state.json').read_text())
    sampler.rng.bit_generator.state = state.pop('sampler_state')
    if (run / 'best.json').exists() and 'best_dev_loss' in state:
        best = json.loads((run / 'best.json').read_text())['macro_answer_loss']
        if state['best_dev_loss'] is None or best < state['best_dev_loss']:
            state['best_dev_loss'] = best
    mx.eval(model.parameters(), optimizer.state)
    return state


def evaluate(model, data, context, batch_size=2, batches=2, deadline=None):
    sampler = Sampler(data, 'dev', 991, context)
    out = {}
    model.eval()
    for name in sampler.names:
        if deadline and time.time() >= deadline:
            break
        total, n, answer_total, an = 0., 0., 0., 0.
        for _ in range(batches):
            x, y, mask, answer = [mx.array(v) for v in sampler.batch(batch_size, name)]
            losses = nn.losses.cross_entropy(model(x), y, reduction='none')
            sums = [mx.sum(losses * mask), mx.sum(mask), mx.sum(losses * answer), mx.sum(answer)]
            mx.eval(sums)
            s, count, a, acount = [float(v.item()) for v in sums]
            total += s
            n += count
            answer_total += a
            an += acount
        out[name] = {'loss': total / max(n, 1), 'answer_loss': answer_total / max(an, 1), 'tokens': int(n), 'answer_tokens': int(an)}
    model.train()
    return out


def generate(model, tokenizer, prompt, max_tokens=96, deadline=None):
    """Generate within the model context using the production KV cache."""
    from .inference import greedy_generate
    model.eval()
    try:
        return greedy_generate(model, tokenizer, prompt, max_tokens, deadline=deadline)['generated']
    finally:
        model.train()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', required=True)
    p.add_argument('--data', default='data')
    p.add_argument('--until', required=True, help='Timezone-aware ISO timestamp')
    p.add_argument('--steps', type=int, default=1000000)
    p.add_argument('--batch-size', type=int, default=2)
    p.add_argument('--context', type=int, default=1024)
    p.add_argument('--dim', type=int, default=768)
    p.add_argument('--layers', type=int, default=12)
    p.add_argument('--heads', type=int, default=12)
    p.add_argument('--hidden', type=int, default=2048)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--forward-precision', choices=['fp32','bf16'], default='fp32', help='BF16 matmuls with FP32 master weights; standalone evaluation uses FP32')
    p.add_argument('--execution', choices=['compiled', 'eager'], default='compiled')
    p.add_argument('--seed', type=int, default=20260906)
    p.add_argument('--checkpoint-seconds', type=int, default=600)
    p.add_argument('--eval-seconds', type=int, default=1800)
    p.add_argument('--max-tokens', type=int, default=100000000)
    p.add_argument('--skip-initial-eval', action='store_true')
    p.add_argument('--schedule-tokens', type=int, default=0, help='Shared token-clock cosine decay; zero retains original wall/token schedule')
    p.add_argument('--snapshot-tokens', type=int, nargs='*', default=[])
    args = p.parse_args()
    if args.schedule_tokens < 0 or any(t <= 0 for t in args.snapshot_tokens):
        p.error('Token schedule and snapshots must be positive')
    args.snapshot_tokens = sorted(set(args.snapshot_tokens))
    deadline_dt = datetime.fromisoformat(args.until)
    if deadline_dt.tzinfo is None:
        raise ValueError('Deadline must contain a timezone')
    deadline = deadline_dt.timestamp()
    if time.time() >= deadline:
        raise ValueError('Deadline already passed')
    run = (ROOT / args.run).resolve()
    run.mkdir(parents=True, exist_ok=True)
    data = (ROOT / args.data).resolve()
    manifest = json.loads((data / 'manifest.json').read_text())
    for name, expected in manifest.get('derived_files_sha256', {}).items():
        if digest((data / name).read_bytes()) != expected:
            raise ValueError(f'Derived data checksum mismatch: {name}')
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(32 * 1024 ** 3)
    mx.set_cache_limit(4 * 1024 ** 3)
    mx.random.seed(args.seed)
    config = ModelConfig(vocab_size=manifest['tokenizer']['vocab_size'], dim=args.dim, layers=args.layers, heads=args.heads, hidden=args.hidden, context=args.context)
    if args.forward_precision == 'bf16':
        from .precision import MixedModel
        model = MixedModel(config)
    else:
        model = LanguageModel(config)
    optimizer = optim.AdamW(learning_rate=3e-4, betas=[0.9, 0.95], weight_decay=0.1, bias_correction=True)
    sampler = Sampler(data, 'train', args.seed, args.context)
    mx.eval(model.parameters())
    count = sum(x.size for _, x in tree_flatten(model.parameters()))
    signature = training_signature(asdict(config), digest((data / 'manifest.json').read_bytes()), args.batch_size, sampler.weights, args.seed, args.schedule_tokens, args.snapshot_tokens, args.forward_precision)
    state = {'step': 0, 'tokens': 0, 'started_at': time.time(), 'best_dev_loss': None, 'signature': signature}
    if args.resume and (run / 'latest.json').exists():
        state = restore(run, model, optimizer, sampler)
        if state['signature'] != signature:
            raise ValueError('Resume config/data signature mismatch')
    elif (run / 'latest.json').exists():
        raise ValueError('Run already exists; pass --resume')
    config_out = dict(vars(args), model=asdict(config), parameters=count, initialization='random', dtype='float32', training_objective='full next-token loss over complete packed original task/answer records', source_weights_by_sequence=sampler.weights, manifest_sha256=digest((data / 'manifest.json').read_bytes()), device=mx.device_info())
    atomic_json(run / 'config.json', config_out)
    shutil.copy2(data / 'tokenizer.json', run / 'tokenizer.json')
    shutil.copy2(data / 'manifest.json', run / 'data_manifest.json')
    stop = []
    def stopping(signum, frame):
        stop.append(f'signal_{signum}')
    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGINT, stopping)
    metrics = (run / 'metrics.jsonl').open('a', buffering=1)
    def emit(event):
        event = dict(event, time=datetime.now().astimezone().isoformat(), step=state['step'], tokens=state['tokens'])
        metrics.write(json.dumps(event, allow_nan=False) + '\n')
        print(json.dumps(event, allow_nan=False), flush=True)
    def dev_eval():
        values = evaluate(model, data, args.context, args.batch_size, deadline=deadline)
        expected = manifest.get('evaluation_weights', manifest['sources'])
        if len(values) != len(expected):
            return
        mean = float(np.mean([v['answer_loss'] for v in values.values()]))
        if not math.isfinite(mean):
            raise FloatingPointError('Non-finite development loss')
        improved = state['best_dev_loss'] is None or mean < state['best_dev_loss']
        if improved:
            state['best_dev_loss'] = mean
            temp = run / 'best.tmp.safetensors'
            model.save_weights(str(temp))
            temp.replace(run / 'best.safetensors')
            atomic_json(run / 'best.json', {'step': state['step'], 'tokens': state['tokens'], 'macro_answer_loss': mean})
        emit({'event': 'development', 'macro_answer_loss': mean, 'sources': values, 'best': improved, 'is_external_benchmark': False})
    emit({'event': 'start', 'parameters': count, 'resumed': state['step'] > 0})
    if state['step'] == 0 and not args.skip_initial_eval:
        dev_eval()
    from .optimization import make_training_step
    update = make_training_step(model, optimizer, compiled=args.execution == 'compiled')

    def step(x, y, mask):
        loss, norm = update(x, y, mask, mx.array(optimizer.learning_rate))
        mx.eval(model.parameters(), optimizer.state, loss, norm)
        return float(loss.item()), float(norm.item())

    last_checkpoint = last_eval = time.time()
    interval_start = time.perf_counter()
    interval_tokens, interval_losses = 0, []
    reason = 'step_limit'
    try:
        while state['step'] < args.steps and state['tokens'] < args.max_tokens:
            if time.time() >= deadline or stop or (run / 'STOP').exists():
                reason = stop[-1] if stop else ('requested_stop' if (run / 'STOP').exists() else 'deadline')
                break
            if psutil.virtual_memory().available < 6 * 1024 ** 3:
                reason = 'low_system_memory'
                break
            x, y, mask, _ = sampler.batch(args.batch_size)
            actual_tokens = int(mask.sum())
            elapsed_fraction = schedule_fraction(state['tokens'], args.max_tokens, state['started_at'], deadline, time.time(), args.schedule_tokens)
            decay = .1 + .9 * .5 * (1 + math.cos(math.pi * elapsed_fraction))
            lr = 3e-4 * min(1., (state['step'] + 1) / 100) * decay
            optimizer.learning_rate = lr
            loss, norm = step(mx.array(x), mx.array(y), mx.array(mask))
            if not math.isfinite(loss) or not math.isfinite(norm):
                raise FloatingPointError(f'Nonfinite loss/gradient: {loss}, {norm}; prior checkpoint retained')
            state['step'] += 1
            state['tokens'] += actual_tokens
            source_tokens = state.setdefault('source_tokens', {})
            for name, count in sampler.last_batch_source_tokens.items():
                source_tokens[name] = source_tokens.get(name, 0) + count
            if args.snapshot_tokens:
                token_snapshots(run, model, state, args.snapshot_tokens)
            interval_tokens += actual_tokens
            interval_losses.append(loss)
            if state['step'] % 10 == 0:
                elapsed = time.perf_counter() - interval_start
                status = {'event': 'train', 'loss': float(np.mean(interval_losses)), 'grad_norm': norm, 'lr': lr, 'tokens_per_second': interval_tokens / elapsed, 'mlx_peak_gb': mx.get_peak_memory() / 1e9, 'system_available_gb': psutil.virtual_memory().available / 1e9, 'status': 'running', 'until': args.until}
                emit(status)
                atomic_json(run / 'status.json', dict(status, step=state['step'], tokens=state['tokens'], updated_at=datetime.now().astimezone().isoformat()))
                interval_start, interval_tokens, interval_losses = time.perf_counter(), 0, []
            if time.time() - last_checkpoint >= args.checkpoint_seconds:
                checkpoint(run, model, optimizer, sampler, state)
                last_checkpoint = time.time()
                emit({'event': 'checkpoint'})
            if time.time() - last_eval >= args.eval_seconds and deadline - time.time() > 120:
                dev_eval()
                last_eval = time.time()
                interval_start, interval_tokens, interval_losses = time.perf_counter(), 0, []
        else:
            reason = 'token_limit' if state['tokens'] >= args.max_tokens else 'step_limit'
        if deadline - time.time() > 60:
            dev_eval()
        folder = checkpoint(run, model, optimizer, sampler, state)
        result = {'status': 'completed', 'reason': reason, 'step': state['step'], 'tokens': state['tokens'], 'checkpoint': folder.name, 'finished_at': datetime.now().astimezone().isoformat(), 'best_dev_answer_loss': state['best_dev_loss']}
        atomic_json(run / 'status.json', result)
        emit(dict(result, event='finished'))
    except Exception as exc:
        atomic_json(run / 'status.json', {'status': 'failed', 'error': repr(exc), 'step': state['step'], 'tokens': state['tokens']})
        raise
    finally:
        metrics.close()


if __name__ == '__main__':
    main()
