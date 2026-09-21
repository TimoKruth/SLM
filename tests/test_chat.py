"""Chat artifact selection, context accounting, and real CPU decoding regressions."""
import json
from types import SimpleNamespace

import mlx.core as mx
import pytest
from tokenizers import Tokenizer, models, pre_tokenizers

from slm.chat import Chat, SPECIAL_TOKENS, generate, interactive, main, prepare_prompt, resolve_model
from slm.inference import greedy_generate
from slm.model import LanguageModel, ModelConfig


@pytest.fixture
def saved_model(tmp_path):
    mx.set_default_device(mx.cpu)
    mx.random.seed(7)
    vocab = {token: i for i, token in enumerate((*SPECIAL_TOKENS, '[UNK]', 'hello', 'world', 'yes'))}
    tokenizer = Tokenizer(models.WordLevel(vocab, unk_token='[UNK]'))
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    tokenizer.add_special_tokens(list(SPECIAL_TOKENS))
    folder = tmp_path / 'model'
    folder.mkdir()
    tokenizer.save(str(folder / 'tokenizer.json'))
    config = dict(vocab_size=len(vocab), dim=16, layers=2, heads=2, hidden=32, context=64)
    (folder / 'config.json').write_text(json.dumps({'model': config}))
    checkpoint = folder / 'checkpoint-0000007'
    checkpoint.mkdir()
    (checkpoint / 'model_config.json').write_text(json.dumps(config))
    (folder / 'latest.json').write_text(json.dumps({'checkpoint': checkpoint.name}))
    model = LanguageModel(ModelConfig(**config))
    model.save_weights(str(checkpoint / 'model.safetensors'))
    return folder, tokenizer, model


def test_loads_latest_or_explicit_checkpoint_without_touching_files(saved_model):
    folder, _, _ = saved_model
    before = {p: p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    files = resolve_model(folder.parent)
    assert files == resolve_model(folder, 'checkpoint-0000007')
    assert files.weights.parent.name == 'checkpoint-0000007'
    chat = Chat(files, maximum=4)
    result = chat.reply('hello')
    assert result['generated_tokens'] <= 4
    assert chat.history == [('hello', result['text'])]
    assert before == {p: p.read_bytes() for p in before}


def test_missing_checkpoint_never_falls_back_to_best(saved_model):
    folder, _, _ = saved_model
    (folder / 'best.safetensors').write_bytes(b'not a checkpoint')
    with pytest.raises(ValueError, match='Missing model file'):
        resolve_model(folder, 'checkpoint-9999999')
    for name in ('../checkpoint-0000007', 'best', '/checkpoint-0000007', 'checkpoint-1.tmp'):
        with pytest.raises(ValueError):
            resolve_model(folder, name)
    (folder / 'checkpoint-0000007/model_config.json').write_text('{}')
    with pytest.raises(ValueError, match='architecture'):
        resolve_model(folder)


def test_context_drops_complete_turns_and_preserves_current_prompt(saved_model):
    _, tok, _ = saved_model
    history = [('hello ' * 20, 'world ' * 20), ('hello', 'yes')]
    ids, kept, dropped = prepare_prompt(tok, 'world', history, context=32, maximum=8)
    expected = '<bos><question>\nhello\n<answer>\nyes<eos>\n<bos><question>\nworld\n<answer>\n'
    assert ids == tok.encode(expected).ids
    assert kept == history[1:] and dropped == 1
    assert len(history) == 2
    with pytest.raises(ValueError, match='Shorten'):
        prepare_prompt(tok, 'hello ' * 40, history, context=32, maximum=8)
    for prompt in (' ', '<eos>', 'hello <answer>'):
        with pytest.raises(ValueError):
            prepare_prompt(tok, prompt, [], 32, 8)


def test_single_turn_uses_existing_inference_format_and_fresh_cache(saved_model):
    _, tok, model = saved_model
    ids, _, _ = prepare_prompt(tok, 'hello world', [], 64, 5)
    actual = generate(model, tok, ids, 5, 60)
    expected = greedy_generate(model, tok, 'hello world', maximum=5)
    assert actual['text'] == expected['generated']
    assert actual['generated_tokens'] == expected['generated_tokens']
    assert generate(model, tok, ids, 5, 60)['text'] == actual['text']


def test_deadline_and_context_budget(saved_model, monkeypatch):
    _, tok, model = saved_model
    ticks = iter([0, 2, 3])
    monkeypatch.setattr('slm.chat.time.monotonic', lambda: next(ticks))
    result = generate(model, tok, [0, 3, 6, 4], 4, 1)
    assert result['stop_reason'] == 'time_limit'
    assert result['generated_tokens'] == 0
    with pytest.raises(ValueError, match='context'):
        generate(model, tok, [0] * 63, 4, 1)


def test_stateless_mode_and_failed_prompt_keep_history_consistent(saved_model):
    folder, _, _ = saved_model
    chat = Chat(resolve_model(folder), maximum=3, remember=False)
    chat.reply('hello')
    assert chat.history == []
    chat.remember = True
    chat.reply('hello')
    history = list(chat.history)
    with pytest.raises(ValueError):
        chat.reply('hello ' * 100)
    assert chat.history == history


def test_cli_json_and_error_exit(saved_model, capsys):
    folder, _, _ = saved_model
    assert main(['--model', str(folder), '--prompt', 'hello', '--json', '--max-tokens', '3']) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)['checkpoint'].endswith('checkpoint-0000007/model.safetensors')
    assert 'Loaded' in output.err
    assert main(['--model', str(folder), '--checkpoint', 'checkpoint-missing']) == 1
    assert 'Missing model file' in capsys.readouterr().err


def test_multiline_reset_and_eof(monkeypatch):
    prompts = []
    chat = SimpleNamespace(history=[('old', 'turn')])
    def reply(prompt):
        prompts.append(prompt)
        return dict(text='yes', dropped_turns=0, stop_reason='special_token')
    chat.reply = reply
    inputs = iter(['/reset', '/multiline', 'hello', 'world', '/end', '/quit'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    interactive(chat)
    assert prompts == ['hello\nworld'] and not chat.history
    def eof(_):
        raise EOFError
    monkeypatch.setattr('builtins.input', eof)
    interactive(chat)
