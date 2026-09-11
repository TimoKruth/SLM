"""Conservative exact-answer diagnostics, explicitly not official benchmark metrics."""
import unicodedata


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def score_prepared(row, generated):
    source = row['source']
    if source not in {'triviaqa', 'tydiqa', 'tabmwp'}:
        raise ValueError(source)
    references = row['answers'] if source == 'tydiqa' else [row['answer']]
    actual = normalize(generated)
    return dict(metric='original_answer_exact_proxy',
                correct=any(actual == normalize(answer) for answer in references),
                official_benchmark_score=False,
                interpretation=('Canonical answer only; unreviewed original aliases excluded.' if source == 'triviaqa'
                                else 'Exact answer and unit; equivalent numeric expressions may score false.' if source == 'tabmwp'
                                else 'Unicode-normalized original answer text; reported separately by language.'))
