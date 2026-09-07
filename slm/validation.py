"""Isolated production-size numerical, resume and real-prompt checks before rollout."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import time

import mlx.core as mx
import mlx.optimizers as optim
from mlx.utils import tree_flatten
import numpy as np
from tokenizers import Tokenizer
from .data import Sampler
from .model import LanguageModel, ModelConfig
from .optimization import make_training_step
from .inference import greedy_generate
from .train import checkpoint, restore, atomic_json


def compare(a, b):
    """Check every model/Adam array with fixed tolerances, recording the largest deviation."""
    left, right = dict(tree_flatten(a)), dict(tree_flatten(b))
    if left.keys() != right.keys():
        raise ValueError('State keys differ')
    maximum = 0.0
    for key in left:
        x, y = np.asarray(left[key]), np.asarray(right[key])
        maximum = max(maximum, float(np.max(np.abs(x.astype(float)-y.astype(float)))))
        np.testing.assert_allclose(x, y, rtol=5e-4, atol=5e-6, err_msg=key)
    return maximum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, help='New validation artifacts directory')
    parser.add_argument('--reference-run', required=True)
    args = parser.parse_args()
    out, ref = Path(args.run), Path(args.reference_run)
    out.mkdir(parents=True, exist_ok=True)
    if (out/'validation.json').exists():
        raise ValueError('Use a new validation directory')
    config = json.loads((ref/'config.json').read_text())
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(20*1024**3)
    mx.set_cache_limit(512*1024**2)
    sampler = Sampler(Path(config['data']), context=config['context'], seed=993)
    models, opts, steps = [], [], []
    for compiled in [False, True]:
        model = LanguageModel(ModelConfig(**config['model']))
        model.load_weights(str(ref/'best.safetensors'))
        opt = optim.AdamW(learning_rate=3e-4, betas=[.9, .95], weight_decay=.1, bias_correction=True)
        steps.append(make_training_step(model, opt, compiled))
        models.append(model)
        opts.append(opt)
    losses = [[], []]
    for i in range(4):
        batch = [mx.array(a) for a in sampler.batch(2)[:3]]
        for j, step in enumerate(steps):
            loss, norm = step(*batch, mx.array(3e-4/(i+1)))
            mx.eval(models[j].parameters(), opts[j].state, loss, norm)
            losses[j].append(float(loss.item()))
    deviation = compare([models[0].parameters(), opts[0].state], [models[1].parameters(), opts[1].state])
    with tempfile.TemporaryDirectory(prefix='slm-resume-check-') as tmp:
        folder = Path(tmp)
        checkpoint(folder, models[1], opts[1], sampler, {'step': 4, 'tokens': 1, 'signature': 'validation'})
        resumed = LanguageModel(ModelConfig(**config['model']))
        opt = optim.AdamW(learning_rate=3e-4, betas=[.9, .95], weight_decay=.1, bias_correction=True)
        restore(folder, resumed, opt, sampler)
        step = make_training_step(resumed, opt, True)
        batch = [mx.array(a) for a in sampler.batch(2)[:3]]
        for model, optimizer, fn in [(models[1], opts[1], steps[1]), (resumed, opt, step)]:
            loss, norm = fn(*batch, mx.array(7e-5))
            mx.eval(model.parameters(), optimizer.state, loss, norm)
        resume_deviation = compare([models[1].parameters(), opts[1].state], [resumed.parameters(), opt.state])
    tokenizer = Tokenizer.from_file(str(ref/'tokenizer.json'))
    prompts = json.loads((ref/'samples.json').read_text())
    checked, seen = [], set()
    for row in prompts:
        if row['source'] in seen:
            continue
        seen.add(row['source'])
        a = greedy_generate(models[0], tokenizer, row['prompt'], 48, cached=False)
        b = greedy_generate(models[0], tokenizer, row['prompt'], 48, cached=True)
        if a['generated'] != b['generated'] or a['stop_reason'] != b['stop_reason']:
            raise AssertionError(f'Cache changes greedy output: {row["source"]}')
        checked.append({'source': row['source'], 'tokens': a['generated_tokens'], 'identical': True})
    atomic_json(out/'validation.json', dict(status='passed', model=config['model'], compiled_vs_eager_max_abs=deviation,
                resumed_max_abs=resume_deviation, losses=losses, real_prompt_checks=checked,
                tolerance={'rtol':5e-4, 'atol':5e-6}, reference_modified=False))
    print('VALIDATION_PASSED', deviation, resume_deviation, len(checked), flush=True)


if __name__ == '__main__':
    main()
