"""Local, read-only terminal chat with this project's MLX checkpoints."""
import argparse
from contextlib import nullcontext
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / 'runs/fresh47-97m-2026-09-16/model'
SPECIAL_TOKENS = ('<bos>', '<eos>', '<pad>', '<question>', '<answer>')


@dataclass(frozen=True)
class ModelFiles:
    directory: Path
    weights: Path
    config: dict
    tokenizer: Path


def resolve_model(directory, checkpoint='latest'):
    """Resolve once; never fall back to best weights or initialize an unsaved model."""
    directory = Path(directory).expanduser().resolve()
    if not (directory / 'config.json').is_file() and (directory / 'model/config.json').is_file():
        directory /= 'model'
    config = json.loads((directory / 'config.json').read_text())['model']
    if checkpoint == 'latest':
        checkpoint = json.loads((directory / 'latest.json').read_text())['checkpoint']
    if not isinstance(checkpoint, str) or Path(checkpoint).name != checkpoint or not checkpoint.startswith('checkpoint-'):
        raise ValueError('Checkpoint must be a checkpoint-… directory name inside the model directory')
    folder = directory / checkpoint
    if folder.resolve().parent != directory or folder.name.endswith(('.tmp', '.old')):
        raise ValueError('Checkpoint must be a complete checkpoint inside the model directory')
    weights = folder / 'model.safetensors'
    tokenizer = directory / 'tokenizer.json'
    for path in (weights, tokenizer, folder / 'model_config.json'):
        if not path.is_file():
            raise ValueError(f'Missing model file: {path}')
    if json.loads((folder / 'model_config.json').read_text()) != config:
        raise ValueError('Checkpoint architecture does not match model/config.json')
    return ModelFiles(directory, weights, config, tokenizer)


def validate_text(text):
    if not text.strip():
        raise ValueError('Please enter a nonempty message')
    if any(token in text for token in SPECIAL_TOKENS):
        raise ValueError('Messages must not contain the model control tokens: ' + ', '.join(SPECIAL_TOKENS))


def prepare_prompt(tokenizer, prompt, history, context, maximum):
    """Use native task records, dropping only whole oldest turns to reserve output space."""
    validate_text(prompt)
    if not 1 <= maximum < context:
        raise ValueError(f'--max-tokens must be between 1 and {context - 1}')
    current = f'<bos><question>\n{prompt}\n<answer>\n'
    encode = lambda text: tokenizer.encode(text).ids
    ids = encode(current)
    if len(ids) + maximum > context:
        raise ValueError(f'Message uses {len(ids)} tokens; at most {context - maximum} fit '
                         f'with {maximum} answer tokens reserved. Shorten it or reduce --max-tokens.')
    kept = list(history)
    while kept:
        prefix = ''.join(f'<bos><question>\n{question}\n<answer>\n{answer}<eos>\n'
                         for question, answer in kept)
        candidate = encode(prefix + current)
        if len(candidate) + maximum <= context:
            ids = candidate
            break
        kept.pop(0)
    return ids, kept, len(history) - len(kept)


def generate(model, tokenizer, ids, maximum, max_seconds):
    """Greedy decoding with the existing cached forward pass and request-local state.

    The next step is queued with mx.async_eval before the current token is read on
    the host, so device work overlaps Python overhead. Tokens are unchanged; a step
    queued after a stop token or deadline is discarded.
    """
    import mlx.core as mx
    from .inference import cached_forward

    if maximum < 1 or not ids or len(ids) + maximum > model.config.context:
        raise ValueError('Invalid generation context budget')
    if max_seconds <= 0:
        raise ValueError('Generation time limit must be positive')
    stops = {tokenizer.token_to_id(token) for token in ('<bos>', '<eos>', '<pad>', '<question>')}

    def step(tokens, cache):
        logits, cache = cached_forward(model, tokens, cache)
        return mx.argmax(logits[:, -1:, :], axis=-1).astype(mx.int32), cache

    output = []
    started = time.monotonic()
    reason = 'token_limit'
    pending, cache = step(mx.array([ids], dtype=mx.int32), None)
    mx.async_eval(pending)
    for n in range(maximum):
        if time.monotonic() - started >= max_seconds:
            reason = 'time_limit'
            break
        current = pending
        # Queue only positions inside the validated budget: len(ids) + n + 1 < context.
        if n + 1 < maximum:
            pending, cache = step(current, cache)
            mx.async_eval(pending)
        token = current.item()
        if token in stops:
            reason = 'special_token'
            break
        output.append(token)
    text = tokenizer.decode(output)
    seconds = time.monotonic() - started
    return dict(text=text, prompt_tokens=len(ids), generated_tokens=len(output),
                stop_reason=reason, seconds=seconds,
                tokens_per_second=len(output) / seconds if seconds > 0 else None)


class Chat:
    def __init__(self, files, maximum=128, max_seconds=60, remember=True):
        import mlx.core as mx
        from tokenizers import Tokenizer
        from .model import LanguageModel, ModelConfig

        self.tokenizer = Tokenizer.from_file(str(files.tokenizer))
        if self.tokenizer.get_vocab_size() != files.config['vocab_size']:
            raise ValueError('Tokenizer vocabulary size does not match the model')
        if any(self.tokenizer.token_to_id(token) is None for token in SPECIAL_TOKENS):
            raise ValueError('Tokenizer is missing required task control tokens')
        if not 1 <= maximum < files.config['context']:
            raise ValueError(f"--max-tokens must be between 1 and {files.config['context'] - 1}")
        self.model = LanguageModel(ModelConfig(**files.config))
        self.model.load_weights(str(files.weights), strict=True)
        self.model.eval()
        mx.eval(self.model.parameters())
        self.maximum, self.max_seconds, self.remember = maximum, max_seconds, remember
        self.history = []

    def reply(self, prompt):
        ids, kept, dropped = prepare_prompt(self.tokenizer, prompt, self.history,
                                            self.model.config.context, self.maximum)
        result = generate(self.model, self.tokenizer, ids, self.maximum, self.max_seconds)
        # No partial turn is stored if generation raises or the user interrupts it.
        self.history = kept + [(prompt, result['text'])] if self.remember else []
        return dict(result, dropped_turns=dropped)


HELP = '/quit exits; /reset clears history; /multiline reads until /end; /help shows commands.'


def print_speed(result):
    speed = result['tokens_per_second']
    rate = f'{speed:.1f} tokens/s' if speed is not None else 'speed unavailable'
    print(f"[{result['generated_tokens']} output tokens in {result['seconds']:.2f}s; "
          f"{rate} including prompt processing.]", file=sys.stderr)


def interactive(chat):
    print(HELP, file=sys.stderr)
    while True:
        try:
            prompt = input('\nYou> ')
            command = prompt.strip()
            if command in ('/quit', '/exit'):
                return
            if command == '/reset':
                chat.history.clear()
                print('History cleared.', file=sys.stderr)
                continue
            if command == '/help':
                print(HELP, file=sys.stderr)
                continue
            if command == '/multiline':
                print('Paste your message; enter /end on its own line to send.', file=sys.stderr)
                lines = []
                while (line := input('... ')) != '/end':
                    lines.append(line)
                prompt = '\n'.join(lines)
            if not prompt.strip():
                continue
            result = chat.reply(prompt)
            print('\nSLM> ' + (result['text'] or '[empty response]'))
            print_speed(result)
            if result['dropped_turns']:
                print(f"[Dropped {result['dropped_turns']} oldest turn(s) to fit context.]", file=sys.stderr)
            if result['stop_reason'] != 'special_token':
                print(f"[Answer stopped at {result['stop_reason']}; {result['generated_tokens']} tokens.]", file=sys.stderr)
        except EOFError:
            return
        except KeyboardInterrupt:
            print('\nInterrupted. Use /quit to exit.', file=sys.stderr)
        except ValueError as exc:
            print(f'Error: {exc}', file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=DEFAULT_MODEL,
                        help='Campaign or model directory containing config.json and tokenizer.json')
    parser.add_argument('--checkpoint', default='latest', help='latest or a checkpoint-… directory name')
    parser.add_argument('--device', choices=('cpu', 'gpu'), default='cpu')
    parser.add_argument('--max-tokens', type=int, default=128)
    parser.add_argument('--max-seconds', type=float, default=60,
                        help='Per-answer time budget, checked between decoding steps')
    parser.add_argument('--no-history', action='store_true', help='Answer each message independently')
    parser.add_argument('--prompt', help='Answer once and exit; use - to read the entire prompt from stdin')
    parser.add_argument('--json', action='store_true', help='Emit one JSON result (requires --prompt)')
    args = parser.parse_args(argv)
    if args.json and args.prompt is None:
        parser.error('--json requires --prompt')
    if not 0 < args.max_seconds < float('inf'):
        parser.error('--max-seconds must be finite and positive')
    try:
        files = resolve_model(args.model, args.checkpoint)
        from slm_perf.gpu_lease import GPULease
        with GPULease() if args.device == 'gpu' else nullcontext():
            import mlx.core as mx
            mx.set_default_device(mx.cpu if args.device == 'cpu' else mx.gpu)
            chat = Chat(files, args.max_tokens, args.max_seconds, not args.no_history)
            print(f'Loaded {files.weights} ({args.device}, {chat.model.config.context} token context).', file=sys.stderr)
            if args.prompt is not None:
                prompt = sys.stdin.read() if args.prompt == '-' else args.prompt
                result = chat.reply(prompt)
                result['checkpoint'] = str(files.weights)
                print(json.dumps(result, ensure_ascii=False) if args.json else result['text'])
                if not args.json:
                    print_speed(result)
            else:
                print('Benchmark-trained model; conversation quality is experimental. History stays in memory.', file=sys.stderr)
                interactive(chat)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f'Chat error: {exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
