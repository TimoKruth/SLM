"""Verify the prepared data and freeze small internal suites, without model execution."""
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer

from benchmark_expansion.fetch import sha
from benchmark_expansion.prepare import ADMITTED
from slm.data import Sampler
from slm.prepare import digest, text_of


def verify(directory):
    manifest = json.loads((directory/'manifest.json').read_text())
    audit = json.loads((directory/'audit.json').read_text())
    for name, expected in {**manifest['derived_files_sha256'], 'records.jsonl': manifest['records_sha256'],
                           'confirmation.jsonl': manifest['confirmation_sha256'], 'audit.json': manifest['audit_sha256'],
                           'tokenizer.json': manifest['tokenizer']['sha256']}.items():
        if sha(directory/name) != expected:
            raise ValueError('Artifact changed: ' + name)
    tok = Tokenizer.from_file(str(directory/'tokenizer.json'))
    arrays = {}
    for source in ADMITTED:
        for split in ('train', 'dev'):
            prefix = directory/f'{source}.{split}'
            arrays[source, split] = (np.memmap(str(prefix)+'.bin', dtype=np.uint16, mode='r'),
                                     np.memmap(str(prefix)+'.mask.bin', dtype=np.uint8, mode='r'),
                                     np.load(str(prefix)+'.index.npy'))
    counts, positions, group_splits, selected = Counter(), Counter(), {}, defaultdict(list)
    for filename in ('records.jsonl', 'confirmation.jsonl'):
        with (directory/filename).open() as stream:
            for line in stream:
                row = json.loads(line)
                if row['source'] not in ADMITTED:
                    continue
                source, split = row['source'], row['split']
                if row['original_split'] != 'train':
                    raise ValueError('Non-training source row')
                if row['group'] in group_splits and group_splits[row['group']] != split:
                    raise ValueError('Partition overlap')
                group_splits[row['group']] = split
                counts[source, split] += 1
                ids = tok.encode(text_of(row)).ids
                if not 0 < len(ids) <= 1024:
                    raise ValueError('Record length violation')
                if split != 'confirmation':
                    tokens, masks, index = arrays[source, split]
                    offset, length = index[positions[source, split]]
                    positions[source, split] += 1
                    if length != len(ids) or tokens[offset:offset+length].tolist() != ids:
                        raise ValueError('Serialized tokens differ from original record')
                    start = ids.index(tok.token_to_id('<answer>')) + 1
                    if masks[offset:offset+length].tolist() != [0]*start + [1]*(length-start):
                        raise ValueError('Answer mask mismatch')
                if split in ('dev', 'confirmation'):
                    selected[split, source, row['language']].append(row)
    for source in ADMITTED:
        retained = sum(counts[source, split] for split in ('train', 'dev', 'confirmation'))
        excluded = sum(v for k, v in audit['rejections'].items() if k.startswith(source+'.'))
        if retained + excluded != audit['raw_counts'][source]:
            raise ValueError('Original-row reconciliation failed: ' + source)
        for split in ('train', 'dev'):
            if counts[source, split] != manifest['counts'][source+'.'+split]['records']:
                raise ValueError('Manifest count mismatch')
            tokens, masks, index = arrays[source, split]
            if len(tokens) != len(masks) or len(index) != counts[source, split]:
                raise ValueError('Array shape mismatch')
            if int(index[-1, 0] + index[-1, 1]) != len(tokens):
                raise ValueError('Trailing/missing token data')
    for split in ('train', 'dev'):
        sampler = Sampler(directory, split=split)
        for source in sampler.names:
            x, y, real, answers = sampler.batch(1, source=source)
            if x.shape != (1, 1024) or not real.sum() or not answers.sum():
                raise ValueError('Sampler smoke check failed: ' + source)
    suites = {}
    for split in ('dev', 'confirmation'):
        examples = []
        for (partition, source, language), candidates in sorted(selected.items()):
            if partition != split:
                continue
            candidates.sort(key=lambda r: digest(r['group'] + ':' + r['original_id']))
            seen = set()
            for row in candidates:
                if row['group'] in seen:
                    continue
                # Preserve at least 128 prompt-generation positions with the fixed context.
                if len(tok.encode('<bos><question>\n' + row['prompt'] + '\n<answer>\n').ids) > 896:
                    continue
                examples.append(row)
                seen.add(row['group'])
                if len(seen) == 16:
                    break
        suite = dict(tokenizer_sha256=manifest['tokenizer']['sha256'], general=examples, memorization=[], code=[],
                     protocol=dict(partition=split, origin='Grouped internal holdout from original training splits',
                                   maximum_per_source_language=16, external_tests_loaded=False,
                                   metric='original_answer_exact_proxy', max_new_tokens=128,
                                   report_by=['source', 'family', 'language'],
                                   limitation='Canonical TriviaQA reference only, strict TabMWP text/unit matching, no official benchmark claims.'))
        filename = f'{split}-suite.json'
        path = directory/filename
        content = json.dumps(suite, indent=2, ensure_ascii=False) + '\n'
        if path.exists() and path.read_text() != content:
            raise ValueError('Refuse to change an existing suite')
        path.write_text(content)
        suites[filename] = dict(examples=len(examples), sha256=sha(path))
    result = dict(status='verified_preparation_only', training_started=False, sources=35,
                  new_records={'.'.join(k): v for k,v in counts.items()},
                  checked='All new token sequences/masks, raw-row reconciliation, group separation, artifact hashes and all-source CPU sampler batches.',
                  suites=suites, manifest_sha256=sha(directory/'manifest.json'))
    (directory/'READY.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.nice(10)
    verify(parser.parse_args().data)
