"""Build immutable broad data views from pinned original train splits only."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil

import numpy as np
import pyarrow.parquet as pq
from tokenizers import Tokenizer
from slm.breadth import FAMILIES, sampling_weights
from slm.prepare import digest, normal, partition, text_of

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def context_key(prompt):
    """Compare exact source-independent contexts across old/new partition boundaries."""
    for start, end in [('Passage: ', '\n\nQuestion:'), ('Premise: ', '\nHypothesis:'),
                       ('Background: ', '\nSituation:'), ('Context: ', '\n\nQuestion:')]:
        if start in prompt:
            return digest(normal(prompt.split(start, 1)[1].split(end, 1)[0]))
    return None


def sql_query(raw):
    """Render original WikiSQL structured labels as quoted, single-table SQLite SQL."""
    table, spec = raw['table'], raw['sql']
    quote = lambda s: '"' + str(s).replace('"', '""') + '"'
    headers = table['header']
    selected = quote(headers[spec['sel']])
    agg = ['', 'MAX', 'MIN', 'COUNT', 'SUM', 'AVG'][spec['agg']]
    if agg:
        selected = agg + '(' + selected + ')'
    conditions = []
    c = spec['conds']
    if len({len(c[k]) for k in ['column_index', 'operator_index', 'condition']}) != 1:
        raise ValueError('Mismatched SQL conditions')
    for index, operator, value in zip(c['column_index'], c['operator_index'], c['condition']):
        op = ['=', '>', '<'][operator]
        value = "'" + str(value).replace("'", "''") + "'"
        conditions.append(f'{quote(headers[index])} {op} {value}')
    return f'SELECT {selected} FROM data' + (' WHERE ' + ' AND '.join(conditions) if conditions else '')


def converted(source, raw, uid):
    """Retain original answers, with document/dialogue/table grouping for holdouts."""
    options, extras = None, {}
    if source in {'social_i_qa', 'cosmos_qa'}:
        context = raw['context']
        if source == 'social_i_qa':
            options = [raw['answer' + c] for c in 'ABC']
            label = int(raw['label']) - 1
        else:
            options = [raw[f'answer{i}'] for i in range(4)]
            label = raw['label']
        if not 0 <= label < len(options):
            raise ValueError('Invalid choice')
        prompt = 'Answer the question using the context.\n\nContext: ' + context + '\n\nQuestion: ' + raw['question']
        answer, group = options[label], context
    elif source == 'quoref':
        context = raw['context']
        prompt = 'Answer the question using the passage.\n\nPassage: ' + context + '\n\nQuestion: ' + raw['question']
        answer, group = raw['answers']['text'][0], raw.get('url') or context
        extras['answers'] = raw['answers']['text']
    elif source == 'wiqa':
        context = '\n'.join(raw['question_para_step'])
        prompt = 'Predict the effect of this change.\n\nProcess:\n' + context + '\n\nQuestion: ' + raw['question_stem']
        options = raw['choices']['text']
        answer, group = raw['answer_label'].replace('_', ' '), 'wiqa:' + str(raw['metadata_para_id'])
        if answer not in options:
            raise ValueError('Invalid WIQA label')
    elif source == 'dream':
        context = '\n'.join(raw['dialogue'])
        prompt = 'Answer the question using the dialogue.\n\nDialogue:\n' + context + '\n\nQuestion: ' + raw['question']
        options, answer, group = raw['choice'], raw['answer'], 'dialogue:' + raw['dialogue_id']
        if answer not in options:
            raise ValueError('Invalid dialogue answer')
    elif source in {'anli', 'scitail'}:
        options = ['entailment', 'neutral', 'contradiction'] if source == 'anli' else ['entailment', 'neutral']
        answer = options[raw['label']] if source == 'anli' else raw['label']
        if source == 'scitail' and answer == 'entails':
            answer = 'entailment'
        if answer not in options:
            raise ValueError('Invalid entailment label')
        prompt = 'Classify the hypothesis as ' + ', '.join(options[:-1]) + ', or ' + options[-1] + '.\n\nPremise: ' + raw['premise'] + '\nHypothesis: ' + raw['hypothesis']
        group = raw['premise']
        options = None
    elif source == 'wikisql':
        table = raw['table']
        schema = ', '.join('"' + h.replace('"', '""') + '" ' + ('REAL' if t == 'real' else 'TEXT') for h, t in zip(table['header'], table['types']))
        prompt = 'Write a SQL query. Output SQL only.\n\nSchema:\ndata(' + schema + ')\n\nQuestion: ' + raw['question']
        answer, group = sql_query(raw), 'wikisql-table:' + table['id']
    else:
        raise ValueError(source)
    if options:
        prompt += '\n' + '\n'.join(f'{chr(65+i)}. {a}' for i, a in enumerate(options))
        extras['choices'] = options
    group = digest(normal(group))
    return dict(source=source, original_id=str(raw.get('uid', raw.get('id', uid))), variant=0,
                group=group, split=partition(group), prompt=prompt, answer=answer, original_split='train', **extras)


def prepare(output, base, stage, version=3):
    """Preserve v2 files and splits, excluding new groups that overlap old content."""
    if output.exists():
        raise ValueError(f'Refuse to overwrite {output}')
    output.mkdir(parents=True)
    old = json.loads((base / 'manifest.json').read_text())
    candidate = json.loads((stage / 'manifest.json').read_text())
    contexts, prompts = set(), set()
    for line in (base / 'records.jsonl').open():
        r = json.loads(line)
        prompts.add(digest(normal(r['prompt'])))
        key = context_key(r['prompt'])
        if key:
            contexts.add(key)
    new, bad_groups, seen, rejected = [], set(), set(prompts), Counter()
    for name, meta in candidate['sources'].items():
        assert meta['original_split'] == 'train'
        for file in meta['files']:
            path = stage / 'raw' / name / file['path']
            if sha(path) != file['sha256']:
                raise ValueError(f'Changed raw file: {path}')
            if 'train' not in file['path'] or any(x in file['path'] for x in ['test', 'validation']):
                raise ValueError('Only original training splits are allowed')
            for batch in pq.ParquetFile(path).iter_batches(batch_size=512):
                for raw in batch.to_pylist():
                    try:
                        row = converted(name, raw, digest(json.dumps(raw, sort_keys=True)))
                    except (KeyError, IndexError, ValueError, TypeError):
                        rejected[name + '.conversion'] += 1
                        continue
                    key = digest(normal(row['prompt']))
                    if key in prompts or context_key(row['prompt']) in contexts:
                        bad_groups.add(row['group'])
                    if key in seen:
                        rejected[name + '.duplicate_prompt'] += 1
                        continue
                    seen.add(key)
                    new.append(row)
        print('converted', name, flush=True)
    new = [r for r in new if r['group'] not in bad_groups]
    rejected['new_groups_overlapping_original_content'] = len(bad_groups)
    tok = Tokenizer.from_file(str(base / 'tokenizer.json'))
    shutil.copy2(base / 'tokenizer.json', output / 'tokenizer.json')
    for name in old['derived_files_sha256']:
        (output / name).symlink_to((base / name).resolve())
    counts = dict(old['counts'])
    index, stats, groups, handles = defaultdict(list), defaultdict(Counter), defaultdict(set), {}
    for name in candidate['sources']:
        for split in ['train', 'dev']:
            for suffix in ['bin', 'mask.bin']:
                handles[(name, split, suffix)] = (output / f'{name}.{split}.{suffix}').open('wb')
    with (output / 'records.jsonl').open('w') as out:
        with (base / 'records.jsonl').open() as src:
            shutil.copyfileobj(src, out)
        for offset in range(0, len(new), 512):
            rows = new[offset:offset+512]
            for row, encoding in zip(rows, tok.encode_batch([text_of(r) for r in rows])):
                key = (row['source'], row['split'])
                ids = encoding.ids
                if len(ids) > 1024:
                    stats[key]['excluded_over_1024'] += 1
                    continue
                index[key].append((stats[key]['tokens'], len(ids)))
                mask = np.ones(len(ids), dtype=np.uint8)
                mask[:ids.index(tok.token_to_id('<answer>'))+1] = 0
                np.asarray(ids, dtype=np.uint16).tofile(handles[(*key, 'bin')])
                mask.tofile(handles[(*key, 'mask.bin')])
                stats[key]['tokens'] += len(ids)
                stats[key]['records'] += 1
                groups[key].add(row['group'])
                out.write(json.dumps(row, ensure_ascii=False) + '\n')
    for f in handles.values():
        f.close()
    for name in candidate['sources']:
        for split in ['train', 'dev']:
            key = (name, split)
            np.save(output / f'{name}.{split}.index.npy', np.asarray(index[key], dtype=np.int64).reshape(-1, 2))
            counts['.'.join(key)] = dict(stats[key], groups=len(groups[key]))
            if not stats[key]['records']:
                raise ValueError(f'No usable records: {key}')
        if groups[(name, 'train')] & groups[(name, 'dev')]:
            raise ValueError('Group leakage')
    sources = {**old['sources'], **candidate['sources']}
    weights = sampling_weights(sources)
    evaluation = {name: 1.0 for name in weights if counts.get(name+'.dev', {}).get('records', 0)}
    derived = {p.name: sha(p) for p in output.iterdir() if p.suffix in {'.bin', '.npy'}}
    manifest = dict(old, version=version, sources=sources, counts=counts, source_weights=weights,
                    evaluation_weights=evaluation, families=FAMILIES, rejections=dict(rejected),
                    parent_manifest_sha256=sha(base/'manifest.json'), candidate_manifest_sha256=sha(stage/'manifest.json'),
                    records_sha256=sha(output/'records.jsonl'), derived_files_sha256=derived,
                    decontamination_status='Original v2 examples and partitions unchanged. New documents/dialogues/tables/premises grouped before split. Whole new groups with exact prompts or extracted contexts matching v2 excluded. New exact prompts deduplicated. No comprehensive semantic or near-duplicate cross-source guarantee. External final tests remain closed.')
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('DATA_READY', len(sources), sum(v.get('records', 0) for k,v in counts.items() if k.endswith('.train')), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--version', type=int, default=3)
    args = parser.parse_args()
    prepare(ROOT / args.output, ROOT/'data/v2', ROOT/'data/candidates-wave3-2026-09-07', version=args.version)


if __name__ == '__main__':
    main()
