"""Verify the prepared reference derivative and sealed suite without model execution."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer
from experiments.analyze_parameters import digest, scorer
from experiments.refresh_parameter_data import write
from experiments.prepare_fresh_parameter_confirmation import content_keys
from slm.prepare import text_of


def verify(project, output):
    folder = project/'runs/parameter-confirmation-refresh-2026-09-15'
    assert (folder/'provenance.json').exists(), 'Suite preparation incomplete'
    suite = json.loads((folder/'confirmation-suite.json').read_text())
    validation = [r for r in suite['general'] if r['original_split'] == 'validation']
    val_keys = set().union(*(content_keys(r) for r in validation))
    val_groups = {g for r in validation for g in [r['group']]+r.get('overlap_group_aliases', [])}
    data = project/'data/v4-reference-audited-2026-09-15'
    audit = json.loads((data/'audit.json').read_text())
    manifest = json.loads((data/'manifest.json').read_text())
    parent = Path(manifest['parent_data'])
    assert digest(data/'records.jsonl') == audit['new_records_sha256'] == manifest['records_sha256']
    assert digest(parent/'records.jsonl') == audit['historical_records_sha256']
    excluded = {r['group'] for r in audit['removed']}
    tokenizer = Tokenizer.from_file(str(data/'tokenizer.json'))
    changed = {r['source']+'.'+r['split'] for r in audit['removed']}
    indices = {key: np.load(data/(key+'.index.npy')) for key in changed}
    tokens = {key: np.memmap(data/(key+'.bin'), dtype=np.uint16, mode='r') for key in changed}
    masks = {key: np.memmap(data/(key+'.mask.bin'), dtype=np.uint8, mode='r') for key in changed}
    counts = Counter(); checked = 0; dropped = 0
    with (data/'records.jsonl').open('rb') as actual:
        for line in (parent/'records.jsonl').open('rb'):
            row = json.loads(line)
            if row['split'] == 'dev':
                assert row['group'] not in val_groups and not content_keys(row) & val_keys, 'Original validation overlaps historical v4 dev content'
            if row['group'] in excluded: dropped += 1; continue
            assert actual.readline() == line, 'Retained bytes/order changed'
            key = row['source']+'.'+row['split']
            if key in changed:
                ids = tokenizer.encode(text_of(row)).ids
                start, length = map(int, indices[key][counts[key]])
                assert length == len(ids) and tokens[key][start:start+length].tolist() == ids
                mask = [0]*(ids.index(tokenizer.token_to_id('<answer>'))+1)
                mask += [1]*(len(ids)-len(mask))
                assert masks[key][start:start+length].tolist() == mask
                checked += 1
            counts[key] += 1
        assert actual.read() == b''
    assert dropped == audit['removed_records']
    for key, stats in manifest['counts'].items(): assert counts[key] == stats.get('records', 0), key
    for name, expected in manifest['derived_files_sha256'].items(): assert digest(data/name) == expected
    assert audit['before_training_stream_sha256'] == audit['after_training_stream_sha256']
    assert all(r['split'] == 'dev' for r in audit['removed'])
    result = dict(retained_records_byte_identical=True, retained_records=sum(counts.values()),
                  quarantined_records=dropped, changed_split_records_retokenized_and_mask_checked=checked,
                  checked_derived_files=len(manifest['derived_files_sha256']), train_records_unchanged=True,
                  data_audit_sha256=digest(data/'audit.json'), verifier_sha256=digest(Path(__file__)))
    folder = project/'runs/parameter-confirmation-refresh-2026-09-15'
    if (folder/'provenance.json').exists():
        suite = json.loads((folder/'confirmation-suite.json').read_text())
        coverage = json.loads((folder/'coverage-audit.json').read_text())
        assert digest(folder/'confirmation-suite.json') == coverage['suite_sha256']
        assert len(suite['general']) == 1360 and len({r['group'] for r in suite['general']}) == 1360
        score = scorer(project.parent/'SLM-long-round2/slm/broad_eval.py')['score_general']
        self_scored = Counter()
        for row in suite['general']:
            metrics = score(row, row['answer'])
            if 'correct' in metrics:
                assert metrics['correct'], ('Original reference fails its own scorer',row['source'])
                self_scored[row['source']] += 1
        assert sum(self_scored.values()) == 1280
        assert (folder/'STOP').exists()
        result.update(suite_tasks=1360, original_references_pass_frozen_scorer=1280,
                      selected_validation_configs={source:dict(Counter(r['original_config'] for r in validation if r['source']==source)) for source in sorted({r['source'] for r in validation})},
                      suite_sha256=coverage['suite_sha256'], preparation_only_stop_verified=True, original_validation_overlap_historical_v4_dev=0)
    else:
        raise ValueError('Suite preparation has not completed')
    assert not output.exists()
    write(output, result); print(json.dumps(result, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); os.nice(10); verify(args.project.resolve(), args.output.resolve())
