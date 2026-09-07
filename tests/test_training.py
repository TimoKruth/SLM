import json
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np

from slm.data import Sampler
from slm.model import LanguageModel, ModelConfig, loss_fn
from slm.prepare import convert, partition, exclude_shared_code_groups, code_key
from slm.train import checkpoint, restore


def tiny_model():
    mx.random.seed(7)
    return LanguageModel(ModelConfig(vocab_size=64, dim=32, layers=2, heads=4, hidden=64, context=16))


def test_future_tokens_cannot_change_past_logits():
    model = tiny_model()
    a = model(mx.array([[1, 2, 3, 4, 5]]))
    b = model(mx.array([[1, 2, 3, 18, 19]]))
    np.testing.assert_allclose(np.array(a[:, :3]), np.array(b[:, :3]), rtol=1e-5, atol=1e-5)


def test_padding_targets_do_not_affect_loss():
    model = tiny_model()
    x = mx.array([[1, 2, 3, 0]])
    mask = mx.array([[1., 1., 0., 0.]])
    a = loss_fn(model, x, mx.array([[2, 3, 4, 5]]), mask)
    b = loss_fn(model, x, mx.array([[2, 3, 30, 31]]), mask)
    assert abs(float(a.item()) - float(b.item())) < 1e-6


def test_tiny_batch_can_be_learned():
    model = tiny_model()
    opt = optim.AdamW(learning_rate=.01, weight_decay=0., bias_correction=True)
    x, y = mx.array([[1, 2, 3, 4]]), mx.array([[2, 3, 4, 5]])
    mask = mx.ones((1, 4))
    initial = float(loss_fn(model, x, y, mask).item())
    grad = nn.value_and_grad(model, loss_fn)
    for _ in range(15):
        loss, grads = grad(model, x, y, mask)
        opt.update(model, grads)
        mx.eval(model.parameters(), opt.state, loss)
    assert float(loss_fn(model, x, y, mask).item()) < initial * .5


def make_data(tmp_path):
    for split in ['train', 'dev']:
        np.array([1, 2, 3, 4, 5, 6, 7], dtype=np.uint16).tofile(tmp_path / f'toy.{split}.bin')
        np.array([0, 0, 1, 1, 0, 0, 1], dtype=np.uint8).tofile(tmp_path / f'toy.{split}.mask.bin')
        np.save(tmp_path / f'toy.{split}.index.npy', np.array([[0, 4], [4, 3]]))


def test_packing_and_checkpoint_resume(tmp_path):
    make_data(tmp_path)
    sampler = Sampler(tmp_path, context=16, weights={'toy': 1.})
    model = tiny_model()
    opt = optim.AdamW(learning_rate=.01, bias_correction=True)
    x, y, mask, answer = [mx.array(v) for v in sampler.batch(2)]
    assert bool(mx.all(answer <= mask).item())
    assert bool(mx.all((y != 0) == (mask > 0)).item())
    grad = nn.value_and_grad(model, loss_fn)
    loss, grads = grad(model, x, y, mask)
    opt.update(model, grads)
    mx.eval(model.parameters(), opt.state)
    expected_logits = np.array(model(x))
    state = {'step': 1, 'tokens': 20, 'signature': 'test'}
    checkpoint(tmp_path, model, opt, sampler, state)
    expected_batch = sampler.batch(2)
    second = tiny_model()
    second_opt = optim.AdamW(learning_rate=.01, bias_correction=True)
    second_sampler = Sampler(tmp_path, context=16, weights={'toy': 1.})
    restored = restore(tmp_path, second, second_opt, second_sampler)
    assert restored == state
    np.testing.assert_array_equal(np.array(second(x)), expected_logits)
    for actual, expected in zip(second_sampler.batch(2), expected_batch):
        np.testing.assert_array_equal(actual, expected)
    # One more update must match: tests optimizer moments, not just weight loading.
    for m, o in [(model, opt), (second, second_opt)]:
        _, g = nn.value_and_grad(m, loss_fn)(m, x, y, mask)
        o.update(m, g)
        mx.eval(m.parameters(), o.state)
    np.testing.assert_allclose(np.array(model(x)), np.array(second(x)), atol=1e-6)


def test_human_hellaswag_target_only():
    rows, rejected = convert('hellaswag', [{'ctx': 'A person opens a door.', 'endings': ['Synthetic negative one', 'They walk inside.', 'Synthetic negative two'], 'label': '1', 'source_id': 'video1'}])
    assert rows[0]['answer'] == 'They walk inside.'
    assert 'Synthetic' not in json.dumps(rows)


def test_squad_article_stays_in_one_partition():
    rows, _ = convert('squad', [{'id': str(i), 'title': 'One article', 'context': 'Different passage ' + str(i), 'question': 'Question ' + str(i), 'answers': {'text': ['answer']}} for i in range(3)])
    assert len({r['group'] for r in rows}) == 1
    assert len({r['split'] for r in rows}) == 1


def test_real_data_has_no_group_or_prompt_overlap():
    root = Path(__file__).resolve().parents[1]
    groups, prompts = {'train': set(), 'dev': set()}, {'train': set(), 'dev': set()}
    code = {'train': set(), 'dev': set()}
    for line in (root / 'data/records.jsonl').open():
        row = json.loads(line)
        assert row['original_split'] == 'train'
        groups[row['split']].add(row['group'])
        prompts[row['split']].add(' '.join(row['prompt'].lower().split()))
        if row['source'] in ['apps', 'mbpp']:
            key = code_key(row['answer'])
            if key:
                code[row['split']].add(key)
    assert groups['train'].isdisjoint(groups['dev'])
    assert prompts['train'].isdisjoint(prompts['dev'])
    assert code['train'].isdisjoint(code['dev'])


def test_shared_code_removes_entire_development_group_only():
    rows = [
        {'source': 'apps', 'split': 'train', 'group': 'a', 'answer': 'print(1)'},
        {'source': 'apps', 'split': 'dev', 'group': 'b', 'answer': 'print( 1 ) # equivalent'},
        {'source': 'apps', 'split': 'dev', 'group': 'b', 'answer': 'print(2)'},
        {'source': 'apps', 'split': 'dev', 'group': 'c', 'answer': 'print(3)'},
    ]
    kept, audit = exclude_shared_code_groups(rows)
    assert kept == [rows[0], rows[3]]
    assert audit['excluded_development_records'] == 2
