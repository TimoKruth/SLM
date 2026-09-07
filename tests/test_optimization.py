"""Execution changes must preserve updates, resume state and bounded generation."""
import json
import mlx.core as mx
import mlx.optimizers as optim
from mlx.utils import tree_flatten
import numpy as np
import pytest
from slm.model import LanguageModel, ModelConfig
from slm.optimization import make_training_step
from slm.inference import cached_forward, greedy_generate
from slm.train import checkpoint, restore


@pytest.fixture(autouse=True)
def cpu():
    previous = mx.default_device()
    mx.set_default_device(mx.cpu)
    yield
    mx.set_default_device(previous)


def model():
    mx.random.seed(13)
    return LanguageModel(ModelConfig(vocab_size=64, dim=32, layers=2, heads=4, hidden=64, context=32))


def assert_state(a, b):
    aa, bb = dict(tree_flatten(a)), dict(tree_flatten(b))
    assert aa.keys() == bb.keys()
    for key in aa:
        np.testing.assert_allclose(np.array(aa[key]), np.array(bb[key]), rtol=5e-4, atol=3e-6, err_msg=key)


def test_compiled_checkpoint_resume_preserves_optimizer_and_next_update(tmp_path):
    a, b = model(), model()
    oa, ob = [optim.AdamW(learning_rate=3e-4, betas=[.9, .95], weight_decay=.1) for _ in range(2)]
    fa, fb = make_training_step(a, oa, False), make_training_step(b, ob, True)
    class SamplerState:
        rng = np.random.default_rng(31)
    sampler = SamplerState()
    x, y, mask = mx.array([[1, 2, 3, 4]]), mx.array([[2, 3, 4, 5]]), mx.ones((1, 4))
    for i in range(3):
        la, _ = fa(x, y, mask, mx.array(3e-4/(i+1)))
        lb, _ = fb(x, y, mask, mx.array(3e-4/(i+1)))
        mx.eval(a.parameters(), b.parameters(), oa.state, ob.state, la, lb)
    checkpoint(tmp_path, b, ob, sampler, {'step': 3, 'tokens': 12, 'signature': 'test'})
    c = model()
    oc = optim.AdamW(learning_rate=3e-4, betas=[.9, .95], weight_decay=.1)
    restore(tmp_path, c, oc, sampler)
    fc = make_training_step(c, oc, True)
    for m, o, f in [(a, oa, fa), (b, ob, fb), (c, oc, fc)]:
        loss, norm = f(x, y, mask, mx.array(7e-5))
        mx.eval(m.parameters(), o.state, loss, norm)
    assert_state([a.parameters(), oa.state], [b.parameters(), ob.state])
    assert_state([b.parameters(), ob.state], [c.parameters(), oc.state])
    assert int(oc.step.item()) == 4


def test_cached_chunk_logits_and_complete_prompt_boundary():
    m = model()
    ids = mx.array([[1, 2, 3, 4, 5]])
    a, cache = cached_forward(m, ids[:, :2])
    b, cache = cached_forward(m, ids[:, 2:], cache)
    np.testing.assert_allclose(np.concatenate([np.array(a), np.array(b)], axis=1), np.array(m(ids)), rtol=2e-5, atol=2e-6)
    class Tokenizer:
        def encode(self, text):
            from types import SimpleNamespace
            return SimpleNamespace(ids=[1, 2, 3])
        def token_to_id(self, token):
            return -1
        def decode(self, ids):
            return str(ids)
    tokenizer = Tokenizer()
    assert greedy_generate(m, tokenizer, '', 8)['generated'] == greedy_generate(m, tokenizer, '', 8, cached=False)['generated']
    m.config.context = 3
    result = greedy_generate(m, tokenizer, '', 8)
    assert result['stop_reason'] == 'context_exceeded'
    assert result['generated_tokens'] == 0
