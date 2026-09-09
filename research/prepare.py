"""CPU-only suite selection and immutable input manifest, before any trial outcome."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
from pathlib import Path
import subprocess

from .common import read, write, sha

ROOT = Path(__file__).resolve().parents[1]


def select(rows, count, salt, blocked=()):
    groups = set(blocked)
    out = []
    for row in sorted(rows, key=lambda r: hashlib.sha256(
            (salt + r['source'] + r['group'] + r['original_id']).encode()).hexdigest()):
        if row['group'] not in groups:
            out.append(row)
            groups.add(row['group'])
            if len(out) == count:
                break
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', required=True)
    p.add_argument('--profile', choices=['pilot', 'followup'], default='pilot')
    args = p.parse_args()
    run = Path(args.run).resolve()
    followup = args.profile == 'followup'
    prior_confirmation_path = ROOT / 'runs/research-pilot-2026-09-09/confirmation-suite.json'
    if (run / 'plan.json').exists():
        raise ValueError('Use a new campaign directory')
    run.mkdir(parents=True, exist_ok=True)
    parent = ROOT / 'runs/size-27m-2026-09-09-plus3h'
    data = ROOT / 'runs/size-campaign-2026-09-08/data-families'
    historical = read(ROOT / 'runs/size-campaign-2026-09-08/suite.json')
    questionable = {(r['source'], r['id']) for r in read(ROOT / 'next_run/manual_findings.json')
                    if r['manual_category'].startswith('reference_')}
    eligible = lambda r: (r['source'], r['original_id']) not in questionable
    pool = defaultdict(list)
    for row in historical['general']:
        if eligible(row):
            pool[row['source']].append(row)
    search = []
    for source in sorted(pool):
        search += select(pool[source], 16 if followup else 8, 'research-search-round2-20260909' if followup else 'research-search-20260909', [r['group'] for r in search])
    blocked = {r['group'] for r in historical['general']}
    for row in historical.get('code', []):
        if 'group' in row:
            blocked.add(row['group'])
    prior_groups = {r['group'] for r in read(prior_confirmation_path)['general']} if followup else set()
    blocked.update(prior_groups)
    train_groups, fresh = set(), defaultdict(list)
    import json
    from tokenizers import Tokenizer
    from slm.prepare import text_of
    tokenizer = Tokenizer.from_file(str(parent / 'tokenizer.json'))
    with (ROOT / 'data/v4-broad-corrected-2026-09-08/records.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['split'] == 'train':
                train_groups.add(row['group'])
            elif row['group'] not in blocked and eligible(row):
                if len(tokenizer.encode(text_of(row)).ids) <= 1024:
                    fresh[row['source']].append(row)
    confirmation = []
    for source in sorted(fresh):
        confirmation += select(fresh[source], 8, 'research-confirm-round2-20260909' if followup else 'research-confirm-20260909',
                               blocked | {r['group'] for r in confirmation})
    assert not train_groups.intersection(r['group'] for r in search + confirmation)
    assert not {r['group'] for r in search}.intersection(r['group'] for r in confirmation)
    assert not prior_groups.intersection(r['group'] for r in confirmation)
    for name, rows in [('search', search), ('confirmation', confirmation)]:
        write(run / f'{name}-suite.json', dict(version=1, general=rows, memorization=[], code=[],
              tokenizer_sha256=sha(parent / 'tokenizer.json'),
              data_manifest_sha256=sha(data / 'manifest.json'),
              protocol='Internal dev from original train splits. Frozen before outcomes; grouped separation from training. '
                       'Confirmation excludes all historic general-suite groups and this search; followup also excludes the prior pilot confirmation. '
                       'Not an untouched external test. '
                       'Some dev examples may have contributed to previous inline dev-loss measurements. '
                       'Code, SQL and narrative functional quality are not scored in this bounded screen.'))
    write(run / 'suite-audit.json', dict(search= dict(Counter(r['source'] for r in search)),
          confirmation=dict(Counter(r['source'] for r in confirmation)),
          training_group_overlap=0, search_confirmation_group_overlap=0,
          prior_confirmation_group_overlap=0, profile=args.profile,
          excluded_questionable_references=sorted(questionable)))
    trials = [dict(name=name, learning_rate=lr, answer_weight=weight)
              for name, lr, weight in [('baseline', 3e-5, 1), ('higher-lr', 1e-4, 1), ('answer-weight', 3e-5, 4)]]
    if followup:
        trials = [dict(name=name, learning_rate=lr, answer_weight=weight)
                  for name, lr, weight in [('baseline', 3e-5, 1), ('lower-lr', 1e-5, 1), ('mild-answer-weight', 3e-5, 2)]]
    pointer = read(parent / 'latest.json')['checkpoint']
    plan = dict(version=1, parent=str(parent.resolve()), parent_checkpoint=pointer, data=str(data.resolve()),
                gpu_wall_budget_seconds=3600, control_seconds=40, trial_seconds=360,
                additional_tokens=3000000, evaluation_seconds=120, evaluation_process_seconds=130,
                variants=trials, data_order_seeds=[202609092, 202609093] if followup else [None, 202609091], repetitions=2,
                profile=args.profile, require_parent_guard=followup,
                confirmation_seconds=70 if followup else 120, confirmation_process_seconds=80 if followup else 130,
                precision='fp32', created=datetime.now().astimezone().isoformat(),
                selection='Mean of equally weighted source accuracies within each scored family, then family macro. '
                          'Contender ranked by mean paired accuracy gain; reference answer loss breaks ties. '
                          'Pass requires >=2pp gain in both data-order repetitions and no mean family regression >5pp. '
                          'Repeat criterion on separate confirmation suite. Never auto-promote or extend budget.',
                limitation='Same parent weights and AdamW in every trial. Repetitions vary sampling order, not initialization. '
                           'Small dev suites and short adaptation only: exploratory evidence, not statistical significance or broad transfer.',
                monitoring='light', code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    if followup:
        plan['selection'] += (' Followup additionally requires each contender repetition to match or beat the unchanged parent accuracy '
                              'and reference answer loss on BOTH suites. This is a conservative screening guard, not significance.')
        plan['limitation'] += ' Expanded search reuses historical development tasks; fresh confirmation has disjoint groups from pilot confirmation.'
    write(run / 'plan.json', plan)
    conditions = dict(recorded_at=plan['created'], performance_mode='User-reported reduced performance for lower noise; unchanged by assistant',
                      power_settings=subprocess.check_output(['pmset', '-g', 'custom'], text=True),
                      power_source=subprocess.check_output(['pmset', '-g', 'batt'], text=True),
                      execution='Serial GPU jobs; matched additional token counts within repetition; FP32',
                      resource_history=str((ROOT / 'runs/system-resources/latest.html').resolve()))
    write(run / 'RUN_CONDITIONS.json', conditions)
    paths = [ROOT / s for s in subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
             if s.endswith(('.py', '.json', '.md'))]
    paths += list((parent / pointer).glob('*')) + [parent / 'config.json', parent / 'latest.json', parent / 'tokenizer.json']
    paths += [f for f in data.iterdir() if f.is_file() and (f.name.endswith(('.bin', '.npy', '.json')))]
    if followup:
        paths += [prior_confirmation_path]
    paths += [run / name for name in ['plan.json', 'search-suite.json', 'confirmation-suite.json', 'suite-audit.json', 'RUN_CONDITIONS.json']]
    write(run / 'frozen-inputs.json', {str(f): sha(f) for f in sorted(set(paths))})
    print(json.dumps(dict(run=str(run), search=len(search), confirmation=len(confirmation), plan=plan), indent=2))


if __name__ == '__main__':
    main()
