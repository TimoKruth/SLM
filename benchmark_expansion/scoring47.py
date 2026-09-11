"""Internal metrics for additional benchmarks; no official-score claims."""
from collections import Counter
import re

from benchmark_expansion.scoring import normalize

SOURCES = {'multinli', 'mrpc', 'qqp', 'cb', 'copa', 'multirc', 'wic', 'wsc',
           'go_emotions', 'medqa', 'samsum', 'logiqa'}


def score_wave6(row, generated):
    source = row['source']
    if source not in SOURCES:
        raise ValueError(source)
    if source == 'samsum':
        actual = Counter(re.findall(r'\w+', normalize(generated)))
        expected = Counter(re.findall(r'\w+', normalize(row['answer'])))
        overlap = sum((actual & expected).values())
        return dict(metric='summary_unigram_f1_proxy_not_factuality',
                    token_f1=2*overlap/max(1, sum(actual.values())+sum(expected.values())),
                    official_benchmark_score=False,
                    interpretation='Lexical overlap only. Human assessment of factuality, omissions and attribution remains necessary.')
    if source == 'go_emotions':
        actual = {normalize(x) for x in re.split(r'[;,]', generated) if normalize(x)}
        expected = set(row['original_labels'])
        intersection = len(actual & expected)
        return dict(metric='emotion_label_set_exact_and_f1', correct=actual == expected,
                    label_f1=2*intersection/max(1, len(actual)+len(expected)),
                    official_benchmark_score=False)
    if row.get('choices') and re.fullmatch(r'[A-D][.)]?', generated.strip()):
        index = ord(generated.strip()[0]) - ord('A')
        if index < len(row['choices']):
            generated = row['choices'][index]
    return dict(metric='original_label_or_answer_match',
                correct=normalize(generated) == normalize(row['answer']),
                official_benchmark_score=False,
                interpretation='Internal item-level proxy. MultiRC is scored per answer candidate, not official question-level exact match.')
