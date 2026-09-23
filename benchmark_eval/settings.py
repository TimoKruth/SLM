"""CPU-only validation of model, context, output and wall-clock budgets."""
from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    backend: str
    context_tokens: int
    max_output_tokens: int = 16384
    temperature: float = 0.0
    thinking: bool = False
    seed: int = 20260921
    task_seconds: int = 3600
    min_output_tokens: int = 64
    context_policy: str = 'require_full_output'
    model: str = ''

    def __post_init__(self):
        if self.backend not in {'slm', 'ollama'}:
            raise ValueError('Unsupported backend')
        for name in ('context_tokens', 'max_output_tokens', 'task_seconds', 'min_output_tokens'):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f'{name} must be a positive integer')
        if self.min_output_tokens > self.max_output_tokens:
            raise ValueError('Minimum output exceeds requested maximum')
        if not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2:
            raise ValueError('Invalid temperature')
        if type(self.thinking) is not bool or type(self.seed) is not int:
            raise ValueError('Thinking must be boolean; seed must be integer')
        if self.context_policy not in {'require_full_output', 'use_remaining'}:
            raise ValueError('Invalid context policy')
        if self.backend == 'slm' and (self.thinking or self.temperature != 0):
            raise ValueError('Current SLM backend supports greedy decoding without a thinking channel')
        if self.backend == 'ollama' and not self.model:
            raise ValueError('Ollama model tag required')

    @classmethod
    def load(cls, path):
        return cls(**json.loads(Path(path).read_text()))

    def to_dict(self):
        return asdict(self)

    def allocation(self, prompt_tokens):
        if type(prompt_tokens) is not int or prompt_tokens < 1:
            raise ValueError('Positive prompt token count required')
        remaining = self.context_tokens - prompt_tokens
        effective = max(0, min(self.max_output_tokens, remaining))
        supported = effective >= self.min_output_tokens
        if self.context_policy == 'require_full_output':
            supported = supported and effective == self.max_output_tokens
        return dict(prompt_tokens=prompt_tokens, context_tokens=self.context_tokens,
                    requested_output_tokens=self.max_output_tokens,
                    effective_output_tokens=effective,
                    output_reduced_by_context=effective < self.max_output_tokens,
                    supported=supported)
