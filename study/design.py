"""Preregistered finite parameter space; pure CPU, no workload starts."""
from itertools import product
import math

BASE = dict(lr=3e-5, schedule='constant', weight_decay=.1, beta1=.9, beta2=.95,
            eps=1e-8, clip=1., answer_weight=1., prompt_weight=1., reset_optimizer=False,
            microbatch=2, accumulation=1, precision='fp32', execution='compiled',
            train_context=1024, eligibility=1024, mixture='families', boost_family=None,
            initialization='parent', init_std=.02, bias_correction=True, warmup_steps=0,
            model=dict(vocab_size=16384, dim=512, layers=6, heads=8, hidden=1368, context=1024))


def configuration(name, block='adaptation', **overrides):
    return dict(name=name, block=block, parameters={**BASE, **overrides})


def designs(families):
    adaptation = [configuration('baseline')]
    axes = {'lr': [3e-6, 1e-5, 1e-4], 'schedule': ['cosine'], 'weight_decay': [0., .3],
            'beta1': [.8, .95], 'beta2': [.9, .99], 'eps': [1e-6], 'clip': [.5, 2., 0.],
            'answer_weight': [.5, 2., 4.], 'reset_optimizer': [True],
            'precision': ['bf16'], 'execution': ['eager'], 'mixture': ['sources']}
    for key, values in axes.items():
        for value in values:
            adaptation.append(configuration(f'{key}-{value}', **{key: value}))
    adaptation += [configuration('answer-only', prompt_weight=0.),
                   configuration('microbatch-1-effective-2', microbatch=1, accumulation=2),
                   configuration('microbatch-4-effective-4', microbatch=4),
                   configuration('effective-batch-4', accumulation=2),
                   configuration('effective-batch-8', accumulation=4)]
    for context in [1024, 512, 2048]:
        adaptation.append(configuration(f'context-{context}-eligible-512', block='context',
                                         train_context=context, eligibility=512))
    for family in sorted(families):
        adaptation.append(configuration('boost-' + family, boost_family=family))
    cold = [configuration('cold-baseline', block='cold', initialization='random', lr=3e-4, warmup_steps=100)]
    for key, levels in dict(layers=[4, 8], dim=[384, 640], heads=[4], hidden=[1024, 2048]).items():
        for value in levels:
            cold.append(configuration(f'cold-{key}-{value}', block='cold', initialization='random',
                                      lr=3e-4, warmup_steps=100, model={**BASE['model'], key: value}))
    cold += [configuration('cold-97m', block='cold', initialization='random', lr=3e-4, warmup_steps=100,
                           model={**BASE['model'], 'dim':768, 'layers':12, 'heads':12, 'hidden':2048}),
             configuration('cold-init-std-001', block='cold', initialization='random', lr=3e-4, warmup_steps=100, init_std=.01),
             configuration('cold-bias-correction-off', block='cold', initialization='random', lr=3e-4, warmup_steps=100, bias_correction=False),
             configuration('cold-no-warmup', block='cold', initialization='random', lr=3e-4, warmup_steps=0)]
    interactions = [configuration(f'factorial-{i:02d}', block='interaction', lr=lr, answer_weight=answer, weight_decay=decay)
                    for i, (lr, answer, decay) in enumerate(product([1e-5, 3e-5], [1., 2.], [0., .1]))]
    return dict(adaptation=adaptation, cold=cold, interaction=interactions)


def lr_at(p, tokens, target, step):
    decay = .1 + .9 * .5 * (1 + math.cos(math.pi * min(1., tokens / target))) if p['schedule'] == 'cosine' else 1.
    warmup = min(1., (step + 1) / p['warmup_steps']) if p['warmup_steps'] else 1.
    return p['lr'] * decay * warmup


def validate(p):
    m = p['model']
    if m['dim'] % m['heads'] or (m['dim'] // m['heads']) % 2:
        raise ValueError('Head dimension must be positive and even for RoPE')
    if min(p['microbatch'], p['accumulation'], p['eligibility'], p['train_context']) < 1:
        raise ValueError('Invalid batch/context')
    if p['eligibility'] > p['train_context']:
        raise ValueError('Context comparison must preserve eligible records')
    if min(p['prompt_weight'], p['answer_weight']) < 0 or p['answer_weight'] + p['prompt_weight'] <= 0:
        raise ValueError('Invalid loss weights')
    if p['initialization'] == 'parent' and p['model'] != BASE['model']:
        raise ValueError('Architecture changes require new initialization')


def plan_budget(groups):
    return (sum(len(groups[k]) * 2 * cap for k, cap in [('adaptation',480), ('cold',1320), ('interaction',480)])
            + 4*2220 + 4*120 + 5*90 + 120 + 120 + 600)
