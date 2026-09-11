"""Twelve distinct benchmark training sources for the 47-source preparation."""
import argparse
from collections import defaultdict
import csv
import html
import json
import os
from pathlib import Path
import re
import sys

import pyarrow as pa
import pyarrow.parquet as pq

from benchmark_expansion.prepare import key, norm, prepare
from slm.breadth import BENCHMARK47_FAMILIES
from slm.prepare import digest

ADMITTED = ('multinli', 'mrpc', 'qqp', 'cb', 'copa', 'multirc', 'wic', 'wsc',
            'go_emotions', 'medqa', 'samsum', 'logiqa')
FAMILIES = BENCHMARK47_FAMILIES
PARENT_VERSION, PARENT_SOURCES, VERSION = 5, 35, 6
EMOTIONS = ['admiration', 'amusement', 'anger', 'annoyance', 'approval', 'caring',
            'confusion', 'curiosity', 'desire', 'disappointment', 'disapproval', 'disgust',
            'embarrassment', 'excitement', 'fear', 'gratitude', 'grief', 'joy', 'love',
            'nervousness', 'optimism', 'pride', 'realization', 'relief', 'remorse', 'sadness',
            'surprise', 'neutral']
LABELS = {'multinli': ['entailment', 'neutral', 'contradiction'],
          'cb': ['entailment', 'contradiction', 'neutral'],
          'mrpc': ['not_equivalent', 'equivalent'], 'qqp': ['not_duplicate', 'duplicate'],
          'copa': ['choice1', 'choice2'], 'multirc': ['False', 'True'],
          'wic': ['False', 'True'], 'wsc': ['False', 'True'], 'go_emotions': EMOTIONS}


class RejectedRecord(ValueError):
    """Known original data defects, counted explicitly instead of silently dropped."""


def clean(text):
    return html.unescape(re.sub(r'<[^>]+>', ' ', text))


def dialogue_key(text):
    # Cross-source check ignores speaker names but preserves utterance wording/order.
    text = text.replace('\\n', '\n')
    return key('dialogue-content', ' '.join(re.sub(r'^[^:\n]{1,60}:\s*', '', line)
                                          for line in text.splitlines()))


def original_rows(stage, source):
    folder = stage/source
    if source in LABELS:
        parquet = pq.ParquetFile(folder/'train.parquet')
        features = json.loads(parquet.schema_arrow.metadata[b'huggingface'])['info']['features']
        label = features['labels']['feature'] if source == 'go_emotions' else features['label']
        if label['names'] != LABELS[source]:
            raise ValueError('Unexpected original label order: ' + source)
        for batch in parquet.iter_batches(batch_size=256):
            for raw in batch.to_pylist():
                yield None, raw
    elif source == 'samsum':
        with (folder/'train.csv').open(newline='') as stream:
            for raw in csv.DictReader(stream):
                yield raw['id'], raw
    else:
        path = folder/('train.jsonl' if source == 'medqa' else 'train.txt')
        with path.open() as stream:
            for i, line in enumerate(stream):
                yield str(i), json.loads(line)


def label_index(source, raw):
    label = raw['label']
    if not isinstance(label, int) or not 0 <= label < len(LABELS[source]):
        raise RejectedRecord('invalid_original_label')
    return label


def convert(source, raw, uid=None):
    identities, checks, extras, labels = [], [], {}, []
    def context(text):
        if not isinstance(text, str) or not text.strip():
            raise RejectedRecord('empty_original_text')
        value = key('context', clean(text))
        identities.append(value)
        checks.append(value)
        return text.strip()
    if source in {'multinli', 'cb'}:
        premise = context(raw['premise'])
        hypothesis = raw['hypothesis'].strip()
        if not hypothesis:
            raise RejectedRecord('empty_hypothesis')
        index = label_index(source, raw)
        answer = LABELS[source][index]
        labels = [answer]
        prompt = 'Classify the hypothesis as entailment, neutral, or contradiction.\n\nPremise: ' + premise + '\nHypothesis: ' + hypothesis
        uid = raw['pairID'] if source == 'multinli' else str(raw['idx'])
        if source == 'multinli':
            identities.append(key('multinli-prompt', str(raw['promptID'])))
            extras['genre'] = raw['genre']
    elif source in {'mrpc', 'qqp', 'wic'}:
        a, b = ('question1', 'question2') if source == 'qqp' else ('sentence1', 'sentence2')
        first, second = context(raw[a]), context(raw[b])
        answer = 'yes' if label_index(source, raw) else 'no'
        labels = [answer]
        uid = str(raw['idx'])
        if source == 'wic':
            # Mark the exact target occurrences rather than asking about an ambiguous lemma.
            spans = []
            for i in (1, 2):
                sentence = raw[f'sentence{i}']
                start, end = raw[f'start{i}'], raw[f'end{i}']
                if not 0 <= start < end <= len(sentence):
                    raise RejectedRecord('invalid_word_span')
                spans.append(sentence[:start] + '[TARGET]' + sentence[start:end] + '[/TARGET]' + sentence[end:])
            first, second = spans
            instruction = 'Is the marked word used with the same meaning in both sentences? Answer yes or no.'
            extras['word'] = raw['word']
        else:
            instruction = 'Do these two ' + ('questions ask the same thing' if source == 'qqp' else 'sentences have equivalent meaning') + '? Answer yes or no.'
        prompt = instruction + '\n\nFirst: ' + first + '\nSecond: ' + second
    elif source == 'copa':
        premise = context(raw['premise'])
        if raw['question'] not in {'cause', 'effect'}:
            raise ValueError('Unknown COPA direction')
        options = [raw['choice1'], raw['choice2']]
        index = label_index(source, raw)
        answer = options[index]
        labels = [LABELS[source][index]]
        uid = str(raw['idx'])
        prompt = 'Choose the more plausible ' + raw['question'] + '. Give the full option text.\n\nPremise: ' + premise
        prompt += '\nA. ' + options[0] + '\nB. ' + options[1]
        extras.update(choices=options, direction=raw['question'])
    elif source == 'multirc':
        paragraph = context(raw['paragraph'])
        idx = raw['idx']
        identities.append(key('multirc-paragraph', str(idx['paragraph'])))
        uid = ':'.join(str(idx[k]) for k in ('paragraph', 'question', 'answer'))
        answer = 'yes' if label_index(source, raw) else 'no'
        labels = [answer]
        prompt = 'Does the proposed answer correctly answer the question using the passage? Answer yes or no.\n\nPassage: ' + paragraph
        prompt += '\n\nQuestion: ' + raw['question'] + '\nProposed answer: ' + raw['answer']
        extras['original_indices'] = idx
    elif source == 'wsc':
        text = context(raw['text'])
        words = raw['text'].split()
        for i in (1, 2):
            index, span = raw[f'span{i}_index'], raw[f'span{i}_text']
            if index < 0 or index >= len(words) or not span:
                raise RejectedRecord('invalid_coreference_span')
        uid = str(raw['idx'])
        answer = 'yes' if label_index(source, raw) else 'no'
        labels = [answer]
        prompt = 'Does the second marked expression refer to the first? Answer yes or no.\n\nPassage: ' + text
        prompt += '\nFirst expression: ' + raw['span1_text'] + ' (word index ' + str(raw['span1_index']) + ', zero-based)'
        prompt += '\nSecond expression: ' + raw['span2_text'] + ' (word index ' + str(raw['span2_index']) + ', zero-based)'
        extras['original_spans'] = {k: raw[k] for k in ('span1_index', 'span2_index', 'span1_text', 'span2_text')}
    elif source == 'go_emotions':
        text = context(raw['text'])
        if not raw['labels'] or any(not isinstance(i, int) or not 0 <= i < len(EMOTIONS) for i in raw['labels']):
            raise RejectedRecord('invalid_emotion_labels')
        labels = [EMOTIONS[i] for i in sorted(set(raw['labels']))]
        uid = raw['id']
        answer = '; '.join(labels)
        prompt = 'List all annotated emotions expressed in this comment, separated by semicolons.\nAllowed labels: ' + ', '.join(EMOTIONS) + '\n\nComment: ' + text
    elif source == 'medqa':
        question = raw['question'].strip()
        context(question)
        checks.append(key('question', question))
        options = raw['options']
        if set(options) != set('ABCD') or raw['answer_idx'] not in options or options[raw['answer_idx']] != raw['answer']:
            raise RejectedRecord('medical_answer_key_mismatch')
        answer = raw['answer']
        labels = [raw['answer_idx']]
        prompt = 'Answer this medical exam question. Give the full correct option text.\n\nQuestion: ' + question
        prompt += '\n' + '\n'.join(k + '. ' + options[k] for k in 'ABCD')
        extras.update(choices=[options[k] for k in 'ABCD'], original_answer_key=raw['answer_idx'], exam=raw.get('meta_info'))
    elif source == 'logiqa':
        text = context(raw['text'])
        options, index = raw['options'], raw['answer']
        if len(options) != 4 or not isinstance(index, int) or not 0 <= index < len(options):
            raise RejectedRecord('logic_answer_key_mismatch')
        answer, labels, uid = options[index], [str(index)], str(raw['id'])
        prompt = 'Use logical reasoning to answer the question. Give the full correct option text.\n\nPassage: ' + text + '\n\nQuestion: ' + raw['question']
        prompt += '\n' + '\n'.join(f'{chr(65+i)}. {value}' for i, value in enumerate(options))
        extras.update(choices=options, reasoning_types=raw.get('type', {}), human_translated=True)
    elif source == 'samsum':
        dialogue = context(raw['dialogue'])
        identities.append(dialogue_key(dialogue))
        checks.append(dialogue_key(dialogue))
        prompt = 'Summarize the dialogue, preserving the important people, actions, and decisions.\n\nDialogue:\n' + dialogue
        answer, uid = raw['summary'], raw['id']
    else:
        raise ValueError(source)
    if not answer or not answer.strip():
        raise RejectedRecord('empty_answer')
    for value in (prompt, answer):
        if any(token in value for token in ('<bos>', '<eos>', '<question>', '<answer>', '<pad>')):
            raise RejectedRecord('reserved_token_in_original')
    identities += [key(source + '-id', str(uid)), key('prompt', prompt)]
    checks.append(key('prompt', prompt))
    return dict(source=source, original_id=str(uid), original_split='train', variant=0,
                prompt=prompt, answer=answer, language='english', original_labels=labels,
                _identities=identities, _checks=checks, **extras)


def extra_old_keys(row):
    prompt = row['prompt']
    if row.get('source') == 'triviaqa' and 'Question: ' in prompt:
        yield key('context', prompt.rsplit('Question: ', 1)[1])
    for marker, end in [('Dialogue:\n', '\n\nQuestion:'), ('First: ', '\nSecond:'),
                        ('Second: ', '\0'), ('Comment: ', '\0')]:
        if marker in prompt:
            text = prompt.split(marker, 1)[1].split(end, 1)[0]
            yield key('context', clean(text))
            if marker.startswith('Dialogue'):
                yield dialogue_key(text)


def balance_small_holdouts(rows, excluded_groups):
    """Represent every original class in small-source holdouts, moving whole groups."""
    members = defaultdict(list)
    for row in rows:
        if row['group'] not in excluded_groups:
            members[row['group']].append(row)
    changes = []
    for source in ('cb', 'copa', 'wsc'):
        labels = {label for row in rows if row['source'] == source for label in row['original_labels']}
        for split in ('dev', 'confirmation'):
            for label in sorted(labels):
                if any(row['source'] == source and row['split'] == split and label in row['original_labels']
                       for values in members.values() for row in values):
                    continue
                candidates = []
                for group, values in members.items():
                    if all(row['source'] == source and row['split'] == 'train' for row in values):
                        if any(label in row['original_labels'] for row in values):
                            candidates.append(group)
                candidates.sort(key=lambda group: digest('small-holdout-2026-09-11:' + group))
                if len(candidates) < 2:
                    raise ValueError(f'Insufficient independent training groups for {source}/{label}')
                group = candidates[0]
                for row in members[group]:
                    row['split'] = split
                changes.append(dict(source=source, label=label, group=group, previous='train', split=split,
                                    records=len(members[group])))
    return changes


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('base', 'stage', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.nice(10)
    pa.set_cpu_count(1)
    prepare(args.base, args.stage, args.output, profile=sys.modules[__name__])
