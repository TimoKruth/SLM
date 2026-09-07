"""Pack complete examples into causal sequences; keep padding out of the loss."""
import json
from collections import Counter
import numpy as np

WEIGHTS = {'apps': .30, 'mbpp': .02, 'gsm8k': .12, 'math': .12, 'squad': .16, 'boolq': .04, 'hellaswag': .07, 'piqa': .07, 'winogrande': .06, 'arc': .04}


class Sampler:
    def __init__(self, directory, split='train', seed=42, context=1024, weights=None):
        self.rng = np.random.default_rng(seed)
        self.context = context
        manifest_path = directory / 'manifest.json'
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        key = 'evaluation_weights' if split == 'dev' else 'source_weights'
        self.weights = weights if weights is not None else manifest.get(key, WEIGHTS)
        self.names = list(self.weights)
        self.probs = np.array(list(self.weights.values()), dtype=float)
        self.probs /= self.probs.sum()
        self.tokens, self.answers, self.indices = {}, {}, {}
        for name in self.names:
            prefix = directory / f'{name}.{split}'
            self.tokens[name] = np.memmap(str(prefix) + '.bin', dtype=np.uint16, mode='r')
            self.answers[name] = np.memmap(str(prefix) + '.mask.bin', dtype=np.uint8, mode='r')
            index = np.load(str(prefix) + '.index.npy')
            self.indices[name] = index[index[:, 1] <= context]
            if not len(self.indices[name]):
                raise ValueError(f'No complete examples fit {name} {split} context={context}')

    def batch(self, batch_size, source=None):
        self.last_batch_source_tokens = Counter()
        arr = np.zeros((batch_size, self.context + 1), dtype=np.int32)
        real = np.zeros(arr.shape, dtype=np.float32)
        answer = np.zeros(arr.shape, dtype=np.float32)
        for i in range(batch_size):
            name = source or str(self.rng.choice(self.names, p=self.probs))
            used = 0
            for _ in range(128):
                index = self.indices[name]
                start, length = index[self.rng.integers(len(index))]
                start, length = int(start), int(length)
                if used + length > self.context + 1:
                    break
                arr[i, used:used+length] = self.tokens[name][start:start+length]
                real[i, used:used+length] = 1
                answer[i, used:used+length] = self.answers[name][start:start+length]
                used += length
            self.last_batch_source_tokens[name] += max(0, used - 1)
        return arr[:, :-1], arr[:, 1:], real[:, 1:], answer[:, 1:]
