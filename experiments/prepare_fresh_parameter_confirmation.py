"""Prepare sealed, outcome-free confirmation material; never train or evaluate models."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re

import pyarrow.parquet as pq
from tokenizers import Tokenizer
from experiments.analyze_parameters import digest, scorer
from experiments.prepare_broad import converted as broad_convert
from experiments.prepare_parameter_evaluation import rank
from experiments.refresh_parameter_data import SOURCES, reference_policy, write
from slm.prepare import convert, normal, digest as text_digest
from slm.prepare_v2 import converted as expanded_convert

SALT = 'parameter-confirmation-refresh-v1-20260915'


def normalized(text):
    return ' '.join(re.findall(r'\w+', text.casefold()))


def content_parts(row):
    prompt = row['prompt']
    parts = [('prompt', prompt)]
    for start, end in [('Passage: ', '\n\nQuestion:'), ('Premise: ', '\nHypothesis:'),
                       ('Background: ', '\nSituation:'), ('Context: ', '\n\nQuestion:'),
                       ('Dialogue:\n', '\n\nQuestion:'), ('Process:\n', '\n\nQuestion:')]:
        if start in prompt:
            parts.append(('context', prompt.split(start, 1)[1].split(end, 1)[0]))
            return parts
    # For question-only tasks compare the question independently of instructions/options.
    if row['source'] in {'arc','quarel','openbookqa','commonsenseqa','qasc','aqua_rat','gsm8k','math'}:
        body = prompt.rsplit('\n\n', 1)[-1].split('\n', 1)[0]
        body = re.split(r'\s*\(A\)', body, maxsplit=1)[0]
        parts.append(('question', body))
    return parts


def content_keys(row):
    return {kind+':'+text_digest(normalized(body)) for kind, body in content_parts(row) if normalized(body)}


def validation_record(source, raw, uid, provenance):
    if source == 'arc':
        assert raw['answerKey'] in raw['choices']['label']
        row = convert(source, [raw])[0][0]
        assert row['answer'] == raw['choices']['text'][raw['choices']['label'].index(raw['answerKey'])]
        row['reference_label'] = raw['answerKey']
    elif source == 'quarel':
        assert raw['answer_index'] in (0, 1)
        sid, prompt, answers, group = expanded_convert(source, raw, {})
        row = dict(source=source, original_id=sid, variant=0, prompt=prompt, answer=answers[0],
                   group=text_digest(source+':'+normal(group)))
        assert row['answer'] == ('A' if raw['answer_index'] == 0 else 'B')
        row['reference_label'] = row['answer']
    else:
        row = broad_convert(source, raw, uid)
        if source == 'dream':
            assert row['answer'] in raw['choice']
            row['reference_label'] = str(raw['choice'].index(raw['answer']))
        else:
            assert row['answer'] in raw['answers']['text']
            assert len(raw['answers']['text']) == len(raw['answers']['answer_start'])
            for answer, start in zip(raw['answers']['text'], raw['answers']['answer_start']):
                assert raw['context'][start:start+len(answer)] == answer, 'Invalid extractive reference span'
            title = raw.get('title', '')
            row['overlap_group_aliases'] = [text_digest('article:'+title), text_digest('article:'+title.replace(' ', '_'))] if title else []
    row.update(split='confirmation', original_split='validation', original_config=provenance['path'].split('/')[0],
               original_id='validation:'+str(row['original_id']), provenance=provenance)
    return row


def suite_paths(project):
    return sorted({p.resolve() for worktree in project.parent.glob('SLM*')
                   for p in (worktree/'runs').rglob('*suite*.json')})


def rows_of_suite(value):
    if not isinstance(value, dict): return []
    return [row for part in ['general','code','memorization'] for row in value.get(part, []) if isinstance(row, dict) and 'group' in row]


def prepare(project, stage, output, scorer_path):
    assert not output.exists(), 'Refuse to overwrite preparation'
    inputs = {}
    def read(path):
        inputs[str(path)] = digest(path)
        return json.loads(path.read_text())
    coverage = read(project/'runs/parameter-error-analysis-2026-09-15-verified/analysis.json')['coverage']['confirmation']
    targets = {r['source']:64 if r['scored'] else 16 for r in coverage}
    scored_sources = {r['source'] for r in coverage if r['scored']}
    family = {r['source']:r['family'] for r in coverage}
    policies, hashes = reference_policy(project); inputs.update(hashes)
    excluded_ids = {(r['source'], r['original_id']) for r in policies}
    tokenizer_path = project/'runs/size-27m-2026-09-09-plus3h/tokenizer.json'
    inputs[str(tokenizer_path)] = digest(tokenizer_path)
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    inputs[str(scorer_path)] = digest(scorer_path); frozen_score = scorer(scorer_path)
    pools = defaultdict(list); failures = defaultdict(Counter)
    def admit(row):
        source = row['source']
        prompt = '<bos><question>\n'+row['prompt']+'\n<answer>\n'
        if not row['answer'].strip(): failures[source]['empty_reference'] += 1; return
        if len(tokenizer.encode(prompt+row['answer']+'<eos>\n').ids)>1024:
            failures[source]['reference_over_context'] += 1; return
        if len(tokenizer.encode(prompt).ids)+256>1024:
            failures[source]['prompt_without_generation_room'] += 1; return
        if source in {'gsm8k','math','aqua_rat','qasc'} and frozen_score['final_answer'](row['answer'], source) is None:
            failures[source]['unparseable_reference'] += 1; return
        pools[source].append(row)
    blocked_groups, reserved_rows = set(), []
    initial_suites = suite_paths(project)
    for path in initial_suites:
        rows = rows_of_suite(read(path))
        blocked_groups.update(r['group'] for r in rows); reserved_rows.extend(rows)
    # Reserve references independently of ID formatting, retaining the old raw dataset unchanged.
    records = project/'data/v4-broad-corrected-2026-09-08/records.jsonl'
    stream_hash = hashlib.sha256()
    for line in records.open('rb'):
        stream_hash.update(line); row = json.loads(line)
        if (row['source'], str(row['original_id'])) in excluded_ids: blocked_groups.add(row['group'])
        if row['split'] != 'dev' or row['source'] not in targets or row['source'] in SOURCES: continue
        if row['group'] in blocked_groups: failures[row['source']]['reserved_group'] += 1; continue
        admit(row)
    inputs[str(records)] = stream_hash.hexdigest()
    manifest = read(stage/'manifest.json')
    for source, meta in manifest['sources'].items():
        assert source in SOURCES and meta['original_split'] == 'validation' and meta['purpose'] == 'evaluation_only'
        for item in meta['files']:
            path = stage/'raw'/source/item['path']; inputs[str(path)] = digest(path)
            assert inputs[str(path)] == item['sha256']
            for batch in pq.ParquetFile(path).iter_batches(batch_size=256, use_threads=False):
                for raw in batch.to_pylist():
                    try:
                        row = validation_record(source, raw, text_digest(json.dumps(raw, sort_keys=True)),
                                                dict(repo=meta['repo'], revision=meta['data_revision'], path=item['path'], sha256=item['sha256']))
                    except (AssertionError, IndexError, KeyError, ValueError, TypeError):
                        failures[source]['invalid_original_label_or_span'] += 1; continue
                    admit(row)
    candidates = [r for rows in pools.values() for r in rows]
    key_groups, aliases = defaultdict(set), defaultdict(set)
    candidate_groups = {r['group'] for r in candidates}
    for row in candidates:
        for key in content_keys(row): key_groups[key].add(row['group'])
        for group in [row['group']]+row.get('overlap_group_aliases', []): aliases[group].add(row['group'])
    reasons = defaultdict(set)
    def block(row, reason):
        matches = set(aliases.get(row['group'], ()))
        for key in content_keys(row): matches.update(key_groups.get(key, ()))
        for group in matches: reasons[group].add(reason)
    for row in reserved_rows: block(row, 'existing_or_reserved_suite')
    for group in blocked_groups & candidate_groups: reasons[group].add('reserved_or_reference_group')
    # Includes every historical/prepared corpus, not just the actively trained v4 lineage.
    corpora = sorted({p.resolve() for w in project.parent.glob('SLM*') for p in (w/'data').rglob('records.jsonl')})
    scanned, duplicate_hashes = [], {}
    for path in corpora:
        # The new derivative is independently verified; other copies still get recorded.
        expected = digest(path); inputs[str(path)] = expected
        if expected in duplicate_hashes:
            scanned.append(dict(path=str(path), sha256=expected, identical_to=duplicate_hashes[expected])); continue
        duplicate_hashes[expected] = str(path)
        h = hashlib.sha256(); n = 0
        for line in path.open('rb'):
            h.update(line); row = json.loads(line)
            if row.get('split') == 'train': block(row, 'training_group_or_content'); n += 1
        assert h.hexdigest() == expected
        scanned.append(dict(path=str(path), sha256=expected, training_rows=n))
        print('Overlap checked', path.name, path.parent.name, n, flush=True)
    # Recheck reservations created concurrently before selecting/finalizing this suite.
    final_suites = suite_paths(project)
    for path in final_suites:
        if path not in initial_suites:
            for row in rows_of_suite(read(path)): block(row, 'existing_or_reserved_suite')
    selected = []; used_groups, used_keys = set(), set(); audit = {}
    for source, quota in sorted(targets.items()):
        usable = [r for r in pools[source] if r['group'] not in reasons]
        count = 0
        for row in sorted(usable, key=lambda r: rank(r, SALT)):
            keys = content_keys(row)
            if row['group'] in used_groups or keys & used_keys: continue
            selected.append(row); used_groups.add(row['group']); used_keys.update(keys); count += 1
            if count == quota: break
        audit[source] = dict(family=family[source], scored=source in scored_sources, quota=quota,
                             eligible_groups=len({r['group'] for r in usable}), selected=count, deficit=max(0, quota-count),
                             selected_original_splits=dict(Counter(r['original_split'] for r in selected if r['source']==source)),
                             reference_labels=dict(Counter(r['reference_label'] for r in selected if r['source']==source and 'reference_label' in r)),
                             filters=dict(failures[source]),
                             overlapping_groups=dict(Counter(reason for group in {r['group'] for r in pools[source]} for reason in reasons.get(group, ()))))
    assert all(a['deficit'] == 0 for a in audit.values()), json.dumps(audit, indent=2)
    assert len(selected) == 1360 and len(used_groups) == 1360
    assert sum(r['source'] in scored_sources for r in selected) == 1280
    assert not (used_groups & reasons.keys())
    output.mkdir(parents=True)
    (output/'STOP').write_text('Data preparation only; no model evaluation, training, scheduler, or launch authorization.\n')
    template = read(project/'runs/long-horizon-round2-resume-2026-09-14/confirmation-suite.json')
    suite = dict(template, general=selected, code=[], memorization=[],
                 protocol='Sealed data preparation. 64 groups per scored source, 16 per unscored source. ARC/DREAM/QuaRel/Quoref use original validation only; others use unconsumed internal v4 dev. Original validation is never training data. Fixed hash selection, frozen strict scorer, no model outputs. Future hypothesis/selection/endpoints/budget must be fixed before execution. Internal dev may have been exposed via dev loss; no external transfer claim.')
    write(output/'confirmation-suite.json', suite)
    result = dict(status='data_prepared_execution_not_authorized', data_coverage_complete=True, execution_ready=False,
                  tasks=len(selected), scored_tasks=1280, source_count=len(targets), coverage=audit,
                  original_split_counts=dict(Counter(r['original_split'] for r in selected)),
                  selection_salt=SALT, suite_sha256=digest(output/'confirmation-suite.json'),
                  selected_training_or_reserved_group_or_exact_content_overlap=0,
                  exclusion_suite_count=len(final_suites), exclusion_corpora=scanned,
                  limitation='Exact normalized prompts, extracted contexts/dialogues/questions and document group aliases checked across all discovered corpora and suites. This is not comprehensive semantic/near-duplicate decontamination. Internal dev tasks may have appeared in dev loss. No model scores generated or inspected; future comparison and budget not yet specified. Original test splits and reserved external final benchmarks remain unopened.')
    write(output/'coverage-audit.json', result)
    for path, expected in inputs.items(): assert digest(Path(path)) == expected, path
    assert set(suite_paths(project)) - {output/'confirmation-suite.json'} == set(final_suites), 'Reservations changed; rerun before use'
    write(output/'provenance.json', dict(inputs=inputs, script_sha256=digest(Path(__file__)),
                                       converter_sha256={str(p):digest(p) for p in [Path('slm/prepare.py'),Path('slm/prepare_v2.py'),Path('experiments/prepare_broad.py')]}))
    print(json.dumps({k:v for k,v in result.items() if k not in {'coverage','exclusion_corpora'}},indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['project','stage','output','scorer']: p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args(); os.nice(10)
    prepare(args.project.resolve(), args.stage.resolve(), args.output.resolve(), args.scorer.resolve())
