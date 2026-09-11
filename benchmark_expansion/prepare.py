"""Build a separate, audited future mixture; never launch training or read final tests."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import unicodedata

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from tokenizers import Tokenizer

from benchmark_expansion.fetch import sha
from slm.breadth import EXPANSION_FAMILIES, sampling_weights
from slm.prepare import digest, text_of

ADMITTED = ('triviaqa', 'tydiqa', 'tabmwp')
LANGUAGES = {'arabic', 'bengali', 'english', 'finnish', 'indonesian',
             'korean', 'russian', 'swahili', 'telugu'}


def norm(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def key(kind, text):
    return kind + ':' + digest(norm(text))


def convert(source, raw, uid=None):
    """Preserve canonical answers; retain original aliases/solutions as metadata."""
    question = raw['question'].strip()
    if not question:
        raise ValueError('Empty question')
    extra = {}
    if source == 'triviaqa':
        uid = raw['question_id']
        answer = raw['answer']['value']
        prompt = 'Answer this factual question with a short answer.\n\nQuestion: ' + question
        identities = [key('triviaqa-id', uid), key('question', question)]
        extra = dict(aliases=raw['answer']['aliases'], question_source=raw['question_source'])
        # Aliases are retained for review, not promoted to training targets.
        language = 'english'
        checks = [key('question', question)]
    elif source == 'tydiqa':
        uid = raw['id']
        language = uid.split('-', 1)[0]
        if language not in LANGUAGES:
            raise ValueError('Unknown TyDiQA language')
        context, title = raw['context'], raw['title']
        answers, starts = raw['answers']['text'], raw['answers']['answer_start']
        if not answers or len(answers) != len(starts):
            raise ValueError('Missing/misaligned answer spans')
        if any(start < 0 for start in starts):
            raise ValueError('Negative answer offset')
        if any(not answer or answer not in context for answer in answers):
            raise ValueError('Original answer text missing from passage')
        offsets_match = all(context[start:start+len(answer)] == answer for answer, start in zip(answers, starts))
        answer = answers[0]
        prompt = 'Answer using a span from the passage in its original language.\n\nPassage: ' + context + '\n\nQuestion: ' + question
        identities = [key('context', context), key('article', title), key('tydiqa-id', uid)]
        # Title grouping intentionally also connects exact cross-language titles.
        checks = [key('context', context), key('article', title),
                  'base-group:' + digest('article:' + title)]
        extra = dict(answers=answers, title=title, answer_starts=starts,
                     original_answer_offsets_match=offsets_match, answer_text_verified=True)
    elif source == 'tabmwp':
        if raw['split'] != 'train':
            raise ValueError('Non-training TabMWP row')
        table = raw['table']
        if not table.strip():
            raise ValueError('Missing text table')
        answer = str(raw['answer'])
        choices = raw.get('choices')
        if choices and answer not in choices:
            raise ValueError('Choice label mismatch')
        prompt = 'Answer the question using the table. Give only the final answer, including the unit when provided.\n\nTable title: ' + (raw.get('table_title') or '') + '\nTable:\n' + table + '\n\nQuestion: ' + question
        if choices:
            prompt += '\nChoices: ' + '; '.join(choices)
        unit = raw.get('unit') or ''
        if unit:
            prompt += '\nUnit: ' + unit
            answer += ' ' + unit
        identities = [key('table', table), key('tabmwp-id', str(uid))]
        checks = [key('table', table)]
        language = 'english'
        extra = dict(choices=choices, unit=unit, canonical_answer=str(raw['answer']),
                     answer_type=raw['ans_type'], grade=raw['grade'],
                     original_solution=raw['solution'])
    else:
        raise ValueError(source)
    if not str(answer).strip():
        raise ValueError('Empty answer')
    identities.append(key('prompt', prompt))
    checks.append(key('prompt', prompt))
    return dict(source=source, original_id=str(uid), original_split='train', variant=0,
                prompt=prompt, answer=str(answer), language=language,
                _identities=identities, _checks=checks, **extra)


def original_rows(stage, source):
    if source == 'tabmwp':
        yield from json.loads((stage/source/'train.json').read_text()).items()
    else:
        for batch in pq.ParquetFile(stage/source/'train.parquet').iter_batches(batch_size=256):
            for raw in batch.to_pylist():
                yield None, raw


def group_rows(rows):
    """Union connected identifiers, full prompts, documents and tables before splitting."""
    parent = list(range(len(rows)))
    def find(i):
        while i != parent[i]:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    owners = {}
    for i, row in enumerate(rows):
        for identity in row['_identities']:
            if identity in owners:
                a, b = find(i), find(owners[identity])
                parent[max(a, b)] = min(a, b)
            else:
                owners[identity] = i
    names = {}
    for i, row in enumerate(rows):
        root = find(i)
        names[root] = min(names.get(root, min(row['_identities'])), min(row['_identities']))
    for i, row in enumerate(rows):
        row['group'] = digest(names[find(i)])
        bucket = int(digest('expansion-2026-09-11:' + row['group'])[:8], 16) % 100
        row['split'] = 'dev' if bucket < 5 else 'confirmation' if bucket < 10 else 'train'


def old_keys(row):
    """Source-independent exact overlap checks; not a semantic decontamination claim."""
    prompt = row['prompt']
    yield key('prompt', prompt)
    yield 'base-group:' + row['group']
    for start, end in [('Passage: ', '\n\nQuestion:'), ('Premise: ', '\nHypothesis:'),
                       ('Context: ', '\n\nQuestion:'), ('Background: ', '\nSituation:')]:
        if start in prompt:
            yield key('context', prompt.split(start, 1)[1].split(end, 1)[0])
    if 'Question: ' in prompt:
        yield key('question', prompt.rsplit('Question: ', 1)[1].split('\n', 1)[0])
    else:
        # Most old context-free QA converters put the question after an instruction.
        yield key('question', prompt.split('\n\n', 1)[-1].split('\n', 1)[0])
    if row.get('title'):
        yield key('article', row['title'])


def screen_tatqa(stage, tok):
    records = json.loads((stage/'tatqa/train.json').read_text())
    types, scales = Counter(), Counter()
    lengths = []
    for raw in records:
        context = '\n'.join(' | '.join(row) for row in raw['table']['table'])
        context += '\n' + '\n'.join(p['text'] for p in raw['paragraphs'])
        for q in raw['questions']:
            types[q['answer_type']] += 1
            scales[q['scale']] += 1
            answer = '; '.join(q['answer']) if isinstance(q['answer'], list) else str(q['answer'])
            row = dict(prompt='Answer using the table and paragraphs.\n\n' + context + '\nQuestion: ' + q['question'],
                       answer=answer + (' ' + q['scale'] if q['scale'] else ''))
            lengths.append(len(tok.encode(text_of(row)).ids))
    return dict(status='screened_not_admitted', questions=len(lengths), context_groups=len(records),
                within_1024=sum(n <= 1024 for n in lengths), answer_types=dict(types), scales=dict(scales),
                reason='Original raw file has table/paragraph UUIDs, but no report identifiers. Report-level grouping and numeric reference review remain pending; no TAT-QA training files emitted.')


def prepare(base, stage, output):
    if output.exists():
        raise ValueError('Refuse to overwrite existing output')
    old = json.loads((base/'manifest.json').read_text())
    if old.get('version') != 4 or len(old['sources']) != 32:
        raise ValueError('Expected corrected v4 parent with 32 sources')
    provenance = json.loads((stage/'manifest.json').read_text())
    for source, meta in provenance['sources'].items():
        if meta['original_split'] != 'train':
            raise ValueError('Non-training source')
        for entry in meta['files']:
            if sha(stage/source/entry['path']) != entry['sha256']:
                raise ValueError('Staged source integrity failure')
    if sha(base/'tokenizer.json') != old['tokenizer']['sha256']:
        raise ValueError('Changed parent tokenizer')
    tok = Tokenizer.from_file(str(base/'tokenizer.json'))
    if tok.get_vocab_size() > 65536:
        raise ValueError('Tokenizer cannot be represented as uint16')
    rows, raw_counts, reference_audit = [], Counter(), Counter()
    for source in ADMITTED:
        for uid, raw in original_rows(stage, source):
            # Fail closed on malformed classes/spans instead of silently discarding them.
            row = convert(source, raw, uid)
            rows.append(row)
            if source == 'tydiqa':
                reference_audit['tydiqa.original_offsets_match' if row['original_answer_offsets_match']
                                else 'tydiqa.original_offsets_mismatch_text_verified'] += 1
            raw_counts[source] += 1
        print('converted', source, raw_counts[source], flush=True)
    group_rows(rows)
    candidate_keys = {check for row in rows for check in row['_checks']}
    overlap = set()
    parent_records_hash = hashlib.sha256()
    with (base/'records.jsonl').open() as stream:
        for line in stream:
            parent_records_hash.update(line.encode())
            overlap.update(candidate_keys.intersection(old_keys(json.loads(line))))
    if parent_records_hash.hexdigest() != old['records_sha256']:
        raise ValueError('Changed parent records')
    bad_groups = {row['group'] for row in rows if overlap.intersection(row['_checks'])}
    seen_answers, conflicts = {}, set()
    for row in rows:
        prompt = key('prompt', row['prompt'])
        if prompt in seen_answers and seen_answers[prompt] != norm(row['answer']):
            conflicts.add(row['group'])
        seen_answers[prompt] = norm(row['answer'])
    output.mkdir(parents=True)
    (output/'STOP').write_text('Prepared data only. No training or queue is authorized by this preparation.\n')
    shutil.copy2(base/'tokenizer.json', output/'tokenizer.json')
    # Reuse immutable parent arrays. Verify each before exposing it in the new view.
    for name, expected in old['derived_files_sha256'].items():
        if sha(base/name) != expected:
            raise ValueError('Changed parent array: ' + name)
        (output/name).symlink_to((base/name).resolve())
    stats, rejected, lengths, groups = defaultdict(Counter), Counter(), defaultdict(list), defaultdict(set)
    indices, handles, seen = defaultdict(list), {}, set()
    for source in ADMITTED:
        for split in ('train', 'dev'):
            for suffix in ('bin', 'mask.bin'):
                handles[source, split, suffix] = (output/f'{source}.{split}.{suffix}').open('wb')
    try:
        with (output/'records.jsonl').open('w') as records, (output/'confirmation.jsonl').open('w') as confirmation:
            with (base/'records.jsonl').open() as original:
                shutil.copyfileobj(original, records)
            for row in rows:
                source, split = row['source'], row['split']
                prompt = key('prompt', row['prompt'])
                reason = ('overlap_group' if row['group'] in bad_groups else
                          'conflicting_reference_group' if row['group'] in conflicts else
                          'duplicate_prompt' if prompt in seen else None)
                if reason:
                    rejected[source + '.' + reason] += 1
                    continue
                seen.add(prompt)
                ids = tok.encode(text_of(row)).ids
                lengths[source + '.' + row['language']].append(len(ids))
                if len(ids) > 1024:
                    rejected[source + '.over_1024.' + row['language']] += 1
                    continue
                if ids.count(tok.token_to_id('<answer>')) != 1:
                    raise ValueError('Embedded answer delimiter')
                row.pop('_identities')
                row.pop('_checks')
                row['tokens'] = len(ids)
                groups[source, split].add(row['group'])
                stats[source, split]['records'] += 1
                stats[source, split]['tokens'] += len(ids)
                stats[source, split]['language.' + row['language']] += 1
                if split == 'confirmation':
                    confirmation.write(json.dumps(row, ensure_ascii=False) + '\n')
                    continue
                offset = stats[source, split]['tokens'] - len(ids)
                indices[source, split].append((offset, len(ids)))
                mask = np.ones(len(ids), dtype=np.uint8)
                mask[:ids.index(tok.token_to_id('<answer>')) + 1] = 0
                np.asarray(ids, dtype=np.uint16).tofile(handles[source, split, 'bin'])
                mask.tofile(handles[source, split, 'mask.bin'])
                records.write(json.dumps(row, ensure_ascii=False) + '\n')
    finally:
        for handle in handles.values():
            handle.close()
    counts = dict(old['counts'])
    for source in ADMITTED:
        for split in ('train', 'dev', 'confirmation'):
            if not stats[source, split]['records']:
                raise ValueError(f'Empty source partition: {source}/{split}')
            for other in ('train', 'dev', 'confirmation'):
                if split != other and groups[source, split] & groups[source, other]:
                    raise ValueError('Group leakage')
            if split != 'confirmation':
                np.save(output/f'{source}.{split}.index.npy', np.asarray(indices[source, split], dtype=np.int64))
                counts[source + '.' + split] = dict(stats[source, split], groups=len(groups[source, split]))
    sources = {**old['sources'], **{s: provenance['sources'][s] for s in ADMITTED}}
    weights = sampling_weights(sources, families=EXPANSION_FAMILIES)
    audit = dict(raw_counts=dict(raw_counts), reference_audit=dict(reference_audit), rejections=dict(rejected),
                 new_counts={'.'.join(k): dict(v, groups=len(groups[k])) for k, v in stats.items()},
                 overlap_keys=len(overlap), overlapping_groups=len(bad_groups), conflicting_groups=len(conflicts),
                 lengths={k: dict(measured=len(v), within_1024=sum(n <= 1024 for n in v),
                                  median=float(np.median(v)), p95=float(np.percentile(v, 95)), maximum=max(v)) for k, v in lengths.items()},
                 tatqa=screen_tatqa(stage, tok),
                 limitations=['Exact normalized prompts, questions, extracted contexts and available article groups checked against all retained v4 train/dev records. No comprehensive near-duplicate, translated-document or semantic cross-benchmark audit.',
                              'Internal holdouts are drawn from original train splits; they are not official scores or external transfer tests.',
                              'TriviaQA canonical values are training targets. Original aliases can contain noisy references and require review before alias-aware scoring.',
                              'TabMWP original solutions may refer to unseen visual highlighting; they are metadata, not training targets.',
                              'TyDiQA original offsets are preserved and mismatches counted. Every original answer text is verified as an exact substring; offsets are not training targets and are not repaired.',
                              'Language coverage and family sampling are not proof of acquired knowledge. No new model trained.'])
    (output/'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    manifest = dict(old, version=5, status='prepared_not_started', activated=False, sources=sources,
                    counts=counts, families=EXPANSION_FAMILIES, source_weights=weights,
                    evaluation_weights={s: 1.0 for s in sources if counts.get(s+'.dev', {}).get('records')},
                    parent_directory=str(base.resolve()), parent_manifest_sha256=sha(base/'manifest.json'),
                    candidate_manifest_sha256=sha(stage/'manifest.json'),
                    records_sha256=sha(output/'records.jsonl'), confirmation_sha256=sha(output/'confirmation.jsonl'),
                    audit_sha256=sha(output/'audit.json'),
                    derived_files_sha256={p.name: sha(p) for p in sorted(output.iterdir()) if p.suffix in {'.bin', '.npy'}},
                    decontamination_status=audit['limitations'][0], external_tests_loaded=False)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(audit, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    for name in ('base', 'stage', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.nice(10)
    pa.set_cpu_count(1)
    prepare(args.base, args.stage, args.output)


if __name__ == '__main__':
    main()
