"""Freeze broad development tasks, a tiny train-only learning control, and data views."""
import argparse
from collections import Counter, defaultdict
import heapq
import json
from pathlib import Path
import shutil

import numpy as np
from tokenizers import Tokenizer
from experiments.prepare_broad import sha
from slm.breadth import sampling_weights, SOURCE_FAMILY
from slm.prepare import digest, text_of
from slm.code_eval import load_tasks

ROOT = Path(__file__).resolve().parents[1]
EXTRA_CASES = {
    '1125': [{'input':'5\n2 2\n3 7\n11 13\n999 1001\n1000000 1000000\n',
              'output':'4\n21\n143\n999999\n1000000000000\n'}],
    '1409': [{'input':'11\n1\n2\n3\n4\n5\n7\n8\n15\n16\n31\n1000000\n',
              'output':'1\n1\n2\n1\n2\n3\n1\n4\n1\n5\n7\n'}],
}


def build(base, out):
    if out.exists():
        raise ValueError('Refuse to overwrite checks')
    out.mkdir(parents=True)
    meta = json.loads((base/'manifest.json').read_text())
    tok = Tokenizer.from_file(str(base/'tokenizer.json'))
    candidates = defaultdict(list)
    seen_groups, code_prompts = set(), {}
    for line in (base/'records.jsonl').open():
        row = json.loads(line)
        if row['split'] == 'dev' and row['source'] in {'apps', 'mbpp'}:
            code_prompts[(row['source'], row['original_id'])] = row['prompt']
        if row.get('variant', 0) != 0:
            continue
        key = (row['source'], row['split'])
        group = (*key, row['group'])
        if group in seen_groups:
            continue
        if row['split'] == 'train' and (len(row['answer']) > 350 or len(row['prompt']) > 2400):
            continue
        seen_groups.add(group)
        priority = (len(row['prompt']) + 3*len(row['answer'])) if row['split']=='train' else int(digest(row['group'])[:12], 16)
        heap = candidates[key]
        item = (-priority, row['original_id'], row)
        if len(heap) < 24:
            heapq.heappush(heap, item)
        elif priority < -heap[0][0]:
            heapq.heapreplace(heap, item)
    selected = {'train': [], 'dev': []}
    for (source, split), heap in sorted(candidates.items()):
        wanted = 4 if split == 'train' else 6
        for _, _, row in sorted(heap, key=lambda x:-x[0]):
            if len(tok.encode(text_of(row)).ids) > 1024:
                continue
            selected[split].append(row)
            wanted -= 1
            if wanted == 0:
                break
    # The same frozen tasks evaluate both broad mixture candidates.
    tasks, exclusions = load_tasks()
    for task in tasks:
        task['prompt'] = code_prompts.get((task['source'], task['id']), task['prompt'])
        task['original_case_count'] = len(task['cases'])
        extra = EXTRA_CASES.get(task['id'], []) if task['source']=='apps' else []
        task['cases'] = task['cases'] + extra
        task['extra_case_count'] = len(extra)
        task['coverage'] = 'additional_boundary_inputs' if extra else ('multiple_original_cases' if len(task['cases'])>1 else 'single_original_case_only')
    suite = dict(version=1, data_manifest_sha256=sha(base/'manifest.json'), tokenizer_sha256=sha(base/'tokenizer.json'),
                 general=selected['dev'], memorization=selected['train'], code=tasks, code_exclusions=exclusions,
                 protocol='Frozen internal development only. Broad generative metrics and exact answer diagnostics; narrative generation reported separately. Code test inputs hidden from prompts. Training-control recall is not generalization. No external final benchmarks loaded.')
    (out/'suite.json').write_text(json.dumps(suite, ensure_ascii=False)+'\n')
    control = out/'control-data'
    control.mkdir()
    shutil.copy2(base/'tokenizer.json', control/'tokenizer.json')
    stats, derived, indices = defaultdict(Counter), {}, defaultdict(list)
    handles = {}
    for source in meta['sources']:
        for split in ['train', 'dev']:
            for suffix in ['bin', 'mask.bin']:
                handles[(source,split,suffix)] = (control/f'{source}.{split}.{suffix}').open('wb')
    with (control/'records.jsonl').open('w') as f:
        for split, rows in selected.items():
            for row in rows:
                key = (row['source'], split)
                ids = tok.encode(text_of(row)).ids
                indices[key].append((stats[key]['tokens'], len(ids)))
                mask = np.ones(len(ids), dtype=np.uint8)
                mask[:ids.index(tok.token_to_id('<answer>'))+1] = 0
                np.asarray(ids,dtype=np.uint16).tofile(handles[(*key,'bin')])
                mask.tofile(handles[(*key,'mask.bin')])
                stats[key]['tokens'] += len(ids)
                stats[key]['records'] += 1
                f.write(json.dumps(row,ensure_ascii=False)+'\n')
    for f in handles.values():
        f.close()
    for key in handles:
        if key[2] == 'bin':
            np.save(control/f'{key[0]}.{key[1]}.index.npy', np.asarray(indices[key[:2]],dtype=np.int64).reshape(-1,2))
    train_sources = {name for name in meta['sources'] if stats[(name,'train')]['records']}
    if train_sources != set(meta['sources']):
        raise ValueError(f'Control missing sources: {set(meta["sources"])-train_sources}')
    control_meta = dict(meta, counts={'.'.join(k):dict(v) for k,v in stats.items()},
                        records_sha256=sha(control/'records.jsonl'), source_weights=sampling_weights(train_sources),
                        evaluation_weights={name:1 for name in train_sources if stats[(name,'dev')]['records']},
                        derived_files_sha256={p.name:sha(p) for p in control.iterdir() if p.suffix in {'.bin','.npy'}},
                        purpose='Tiny learning control: repeated original training tasks, with separately held-out dev tasks.')
    (control/'manifest.json').write_text(json.dumps(control_meta,indent=2)+'\n')
    for mode in ['families','sources']:
        view = out/f'data-{mode}'
        view.mkdir()
        for p in base.iterdir():
            if p.name != 'manifest.json':
                (view/p.name).symlink_to(p.resolve())
        view_meta = dict(meta, source_weights=sampling_weights(meta['sources'],mode), sampling_mode=mode,
                         parent_manifest_sha256=sha(base/'manifest.json'))
        (view/'manifest.json').write_text(json.dumps(view_meta,indent=2)+'\n')
    print('CHECKS_READY', {split:dict(Counter(r['source'] for r in rows)) for split,rows in selected.items()}, flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    build(ROOT/a.data, ROOT/a.output)


if __name__=='__main__':
    main()
