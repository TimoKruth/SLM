import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def weighted_mask(real, answer, weight):
    """Real-token normalization; padding stays excluded even for malformed answer bits."""
    if weight < 1:
        raise ValueError('This screen only supports answer weights >= 1')
    return real * (1 + (weight - 1) * answer)


def quality(summary):
    if (summary['evaluated_general'] != summary['selected_general']
            or summary['deadline_reached']
            or summary['answer_loss']['examples'] != summary['selected_general']):
        raise ValueError('Incomplete evaluation cannot select a candidate')
    families = summary['mean_source_accuracy_by_family']
    if not families:
        raise ValueError('No scored families')
    return dict(accuracy=sum(families.values()) / len(families), families=families,
                answer_loss=summary['answer_loss']['macro_source_answer_loss'])


def contrast(baselines, candidates):
    if len(baselines) != 2 or len(candidates) != 2:
        raise ValueError('Two matched data-order repetitions required')
    if any(set(b['families']) != set(c['families']) for b, c in zip(baselines, candidates)):
        raise ValueError('Family coverage differs')
    deltas = [c['accuracy'] - b['accuracy'] for b, c in zip(baselines, candidates)]
    families = {f: sum(c['families'][f] - b['families'][f]
                      for b, c in zip(baselines, candidates)) / 2 for f in baselines[0]['families']}
    return dict(accuracy_deltas=deltas, mean_accuracy_delta=sum(deltas) / 2,
                family_deltas=families,
                mean_answer_loss_delta=sum(c['answer_loss'] - b['answer_loss']
                                           for b, c in zip(baselines, candidates)) / 2,
                passes_screen=all(d >= .02 for d in deltas) and min(families.values()) >= -.05)


def parent_guard(parent, candidates):
    """A candidate must also outperform leaving the six-hour checkpoint untouched."""
    if len(candidates) != 2 or any(set(c['families']) != set(parent['families']) for c in candidates):
        raise ValueError('Parent comparison requires two candidates with matching coverage')
    accuracy = [c['accuracy'] - parent['accuracy'] for c in candidates]
    loss = [c['answer_loss'] - parent['answer_loss'] for c in candidates]
    return dict(accuracy_deltas=accuracy, answer_loss_deltas=loss,
                passed=all(d >= 0 for d in accuracy) and all(d <= 0 for d in loss))
