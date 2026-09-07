"""A small randomly initialized causal decoder. No downloaded model weights."""
from dataclasses import dataclass
import math

import mlx.core as mx
import mlx.nn as nn


@dataclass
class ModelConfig:
    vocab_size: int = 16384
    dim: int = 768
    layers: int = 12
    heads: int = 12
    hidden: int = 2048
    context: int = 1024


class Attention(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.heads = c.heads
        self.head_dim = c.dim // c.heads
        self.qkv = nn.Linear(c.dim, 3 * c.dim, bias=False)
        self.out = nn.Linear(c.dim, c.dim, bias=False)
        self.rope = nn.RoPE(self.head_dim, traditional=False)

    def __call__(self, x):
        b, t, d = x.shape
        q, k, v = mx.split(self.qkv(x), 3, axis=-1)
        q, k, v = [z.reshape(b, t, self.heads, self.head_dim).transpose(0, 2, 1, 3) for z in (q, k, v)]
        q, k = self.rope(q), self.rope(k)
        a = mx.fast.scaled_dot_product_attention(q, k, v, scale=self.head_dim ** -0.5, mask='causal')
        return self.out(a.transpose(0, 2, 1, 3).reshape(b, t, d))


class Block(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.norm1, self.norm2 = nn.RMSNorm(c.dim), nn.RMSNorm(c.dim)
        self.attn = Attention(c)
        self.gate = nn.Linear(c.dim, c.hidden, bias=False)
        self.up = nn.Linear(c.dim, c.hidden, bias=False)
        self.down = nn.Linear(c.hidden, c.dim, bias=False)

    def __call__(self, x):
        x = x + self.attn(self.norm1(x))
        h = self.norm2(x)
        return x + self.down(nn.silu(self.gate(h)) * self.up(h))


class LanguageModel(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.embedding = nn.Embedding(config.vocab_size, config.dim)
        self.blocks = [Block(config) for _ in range(config.layers)]
        self.norm = nn.RMSNorm(config.dim)
        from mlx.utils import tree_flatten
        updates = []
        for name, value in tree_flatten(self.parameters()):
            if value.ndim >= 2:
                std = 0.02 / math.sqrt(2 * config.layers) if name.endswith(('attn.out.weight', 'down.weight')) else 0.02
                updates.append((name, mx.random.normal(value.shape) * std))
        self.load_weights(updates, strict=False)

    def __call__(self, tokens):
        x = self.embedding(tokens)
        for block in self.blocks:
            x = block(x)
        return self.embedding.as_linear(self.norm(x))


def loss_fn(model, x, y, mask):
    losses = nn.losses.cross_entropy(model(x), y, reduction='none')
    return mx.sum(losses * mask) / mx.maximum(mx.sum(mask), 1)
