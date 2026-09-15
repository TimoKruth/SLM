"""CPU-only reference quarantine and pinned, evaluation-only validation collection."""
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import shutil
from urllib.request import urlopen

import numpy as np
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
from experiments.analyze_parameters import digest

SOURCES = {
    'arc': ('allenai/ai2_arc', '210d026faf9955653af8916fad021475a3f00453', '210d026faf9955653af8916fad021475a3f00453',
            ['ARC-Easy/validation-00000-of-00001.parquet', 'ARC-Challenge/validation-00000-of-00001.parquet']),
    'quarel': ('community-datasets/quarel', '52be7f062d2c13d401a9e53b6963d8fbcc4abeb4', '52be7f062d2c13d401a9e53b6963d8fbcc4abeb4',
               ['data/validation-00000-of-00001.parquet']),
    'dream': ('dataset-org/dream', '78b128b6aa3ac08913a19a3c71064bf23206bdf6', 'ca4c45feaf089ecfc37579eb2c594375f70dbfd5',
              ['plain_text/validation/0000.parquet']),
    'quoref': ('allenai/quoref', '0823a60bbacda6cb6d2d58dcd7647b0ca053ffaf', '41fed5bc359f81c2f28259e6572cd1f9aab26e29',
               ['default/validation/0000.parquet']),
}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def reference_policy(project):
    paths = [project/'next_run/manual_findings.json',
             project/'results/2026-09-15/parameter-error-analysis/manual-review.json']
    findings = []
    for path in paths:
        for row in json.loads(path.read_text()):
            category = row.get('category', row.get('manual_category', ''))
            if category.startswith('reference_'):
                findings.append(dict(source=row['source'], original_id=str(row['id']), category=category,
                                     reason=row.get('finding', row.get('manual_note')), evidence=str(path)))
    return findings, {str(p): digest(p) for p in paths}


def quarantine(project, output):
    if output.exists():
        raise ValueError('Refuse to overwrite data version')
    base = project/'data/v4-broad-corrected-2026-09-08'
    parent = json.loads((base/'manifest.json').read_text())
    assert digest(base/'records.jsonl') == parent['records_sha256']
    findings, inputs = reference_policy(project)
    flagged = {(r['source'], r['original_id']) for r in findings}
    groups, found = set(), set()
    for line in (base/'records.jsonl').open():
        row = json.loads(line); key = (row['source'], str(row['original_id']))
        if key in flagged:
            groups.add(row['group']); found.add(key)
    assert found == flagged, 'Unresolved reviewed IDs'
    output.mkdir(parents=True)
    removed, positions, counts, group_counts = [], defaultdict(list), Counter(), defaultdict(set)
    before_train, after_train = __import__('hashlib').sha256(), __import__('hashlib').sha256()
    with (output/'records.jsonl').open('wb') as target:
        for line in (base/'records.jsonl').open('rb'):
            row = json.loads(line); key = row['source']+'.'+row['split']
            if row['split'] == 'train': before_train.update(line)
            # Positions refer to per-source token indices, including excluded rows.
            if row['group'] in groups:
                positions[key].append(counts[key]); removed.append({k: row[k] for k in ['source','split','original_id','variant','group']})
            else:
                target.write(line); group_counts[key].add(row['group'])
                if row['split'] == 'train': after_train.update(line)
            counts[key] += 1
    updated_counts = dict(parent['counts'])
    for key, stats in parent['counts'].items():
        assert counts[key] == stats.get('records', 0), key
        filenames = [key+'.bin', key+'.mask.bin', key+'.index.npy']
        for name in filenames:
            assert digest(base/name) == parent['derived_files_sha256'][name]
        if key not in positions:
            for name in filenames: shutil.copy2(base/name, output/name)
        else:
            indices = np.load(base/(key+'.index.npy'))
            drop = set(positions[key]); new_index = []; offset = 0
            with (base/(key+'.bin')).open('rb') as tokens, (base/(key+'.mask.bin')).open('rb') as masks, \
                 (output/(key+'.bin')).open('wb') as out_tokens, (output/(key+'.mask.bin')).open('wb') as out_masks:
                for i, (start, length) in enumerate(indices):
                    if i in drop: continue
                    start, length = int(start), int(length)
                    tokens.seek(start*2); masks.seek(start)
                    token_bytes, mask_bytes = tokens.read(length*2), masks.read(length)
                    assert len(token_bytes)==length*2 and len(mask_bytes)==length
                    out_tokens.write(token_bytes); out_masks.write(mask_bytes)
                    new_index.append((offset, length)); offset += length
            np.save(output/(key+'.index.npy'), np.asarray(new_index, dtype=np.int64).reshape(-1, 2))
            updated_counts[key] = dict(stats, records=len(new_index), tokens=offset, groups=len(group_counts[key]))
        for name in filenames:
            if key not in positions: assert digest(output/name) == parent['derived_files_sha256'][name]
    shutil.copy2(base/'tokenizer.json', output/'tokenizer.json')
    assert digest(output/'tokenizer.json') == parent['tokenizer']['sha256']
    # This derivative must never introduce original validation records into training.
    manifest = dict(parent, data_revision='reference-quarantine-1-2026-09-15',
                    counts=updated_counts, records_sha256=digest(output/'records.jsonl'),
                    parent_manifest_sha256=digest(base/'manifest.json'), parent_data=str(base),
                    derived_files_sha256={p.name: digest(p) for p in output.iterdir() if p.suffix in {'.bin','.npy'}},
                    quarantine_policy='Remove whole reviewed groups, including ambiguous references. No invented replacement labels. All retained record bytes, order, splits, token IDs and masks preserved. Original validation material is evaluation-only and stored separately.')
    write(output/'manifest.json', manifest)
    audit = dict(status='prepared_not_adopted', findings=findings, removed=removed,
                 removed_records=len(removed), removed_groups=len(groups),
                 removed_by_split=dict(Counter(r['split'] for r in removed)),
                 removed_by_source=dict(Counter(r['source'] for r in removed)),
                 before_training_records=sum(v['records'] for k,v in parent['counts'].items() if k.endswith('.train')),
                 after_training_records=sum(v['records'] for k,v in updated_counts.items() if k.endswith('.train')),
                 before_training_stream_sha256=before_train.hexdigest(), after_training_stream_sha256=after_train.hexdigest(),
                 historical_records_sha256=digest(base/'records.jsonl'), new_records_sha256=manifest['records_sha256'],
                 input_reviews=inputs, manifest_sha256=digest(output/'manifest.json'), script_sha256=digest(Path(__file__)))
    assert audit['historical_records_sha256'] == parent['records_sha256']
    for path, expected in inputs.items(): assert digest(Path(path)) == expected
    write(output/'audit.json', audit)
    print(json.dumps({k:v for k,v in audit.items() if k not in {'findings','removed','input_reviews'}},indent=2), flush=True)


def collect(output):
    if (output/'manifest.json').exists():
        raise ValueError('Refuse to overwrite completed collection')
    output.mkdir(parents=True, exist_ok=True)
    collected = {}
    for name, (repo, source_rev, data_rev, paths) in SOURCES.items():
        folder = output/'raw'/name; folder.mkdir(parents=True, exist_ok=True)
        meta = json.load(urlopen(f'https://huggingface.co/api/datasets/{repo}/revision/{source_rev}', timeout=30))
        data_meta = json.load(urlopen(f'https://huggingface.co/api/datasets/{repo}/revision/{data_rev}', timeout=30))
        assert meta['sha'] == source_rev and data_meta['sha'] == data_rev
        write(folder/'metadata.json', meta); write(folder/'data_revision.json', data_meta)
        card = Path(hf_hub_download(repo, 'README.md', repo_type='dataset', revision=source_rev, local_dir=folder))
        entries = []
        for namepath in paths:
            assert ('/validation/' in namepath or Path(namepath).name.startswith('validation-'))
            assert not any(part in namepath for part in ['train', 'test'])
            path = Path(hf_hub_download(repo, namepath, repo_type='dataset', revision=data_rev, local_dir=folder))
            parquet = pq.ParquetFile(path)
            entries.append(dict(path=namepath, sha256=digest(path), bytes=path.stat().st_size,
                                rows=parquet.metadata.num_rows, columns=parquet.schema_arrow.names,
                                url=f'https://huggingface.co/datasets/{repo}/resolve/{data_rev}/{namepath}'))
        collected[name] = dict(repo=repo, source_revision=source_rev, data_revision=data_rev,
                               original_split='validation', purpose='evaluation_only',
                               license_metadata=meta.get('cardData',{}).get('license'),
                               card_sha256=digest(card), files=entries)
        print(name, sum(e['rows'] for e in entries), 'validation rows collected', flush=True)
    write(output/'manifest.json', dict(sources=collected, used_in_training=False,
                                      original_test_splits_loaded=False, collector_sha256=digest(Path(__file__))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['quarantine','collect'])
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); os.nice(10)
    if args.action == 'quarantine': quarantine(args.project.resolve(), args.output.resolve())
    else: collect(args.output.resolve())
