"""Materialize the bounded design now; select fresh confirmation only after prior GPU work."""
import argparse
from collections import defaultdict, Counter
from datetime import datetime
import json
from pathlib import Path
import random
import subprocess

from research.common import read, write, sha
from research.prepare import select
from slm.breadth import FAMILIES
from .design import designs, plan_budget, validate

ROOT=Path(__file__).resolve().parents[1]


def initial(run):
    if (run/'plan.json').exists():raise ValueError('Plan exists')
    groups=designs(FAMILIES)
    if plan_budget(groups)>86100:raise ValueError('Stage caps exceed 24 hours minus reserve')
    parent=(ROOT/'runs/size-27m-2026-09-09-plus3h').resolve()
    data=(ROOT/'runs/size-campaign-2026-09-08/data-families').resolve()
    jobs=[]
    for phase,settings in groups.items():
        for repetition in range(2):
            ordered=list(settings)
            random.Random(202609900+repetition).shuffle(ordered)
            baseline='cold-baseline' if phase=='cold' else 'baseline'
            ordered.sort(key=lambda c:c['name']!=baseline)
            for c in ordered:
                validate(c['parameters'])
                job=dict(c,phase=phase,repetition=repetition,
                         data_seed={'adaptation':202609201,'cold':202609301,'interaction':202609401}[phase]+repetition,
                         model_seed=202609601+repetition,
                         target_tokens=3000000 if phase=='cold' else 1500000,
                         train_seconds=1200 if phase=='cold' else 360)
                job['id']=f"{phase}-r{repetition}-{c['name']}"
                write(run/'jobs'/f"{job['id']}.json",job)
                jobs.append(job['id'])
    plan=dict(version=1,budget_seconds=86400,maximum_stage_seconds=plan_budget(groups),
              created=datetime.now().astimezone().isoformat(),jobs=jobs,
              parent=str(parent),parent_checkpoint=read(parent/'latest.json')['checkpoint'],data=str(data),
              data_manifest_sha256=sha(data/'manifest.json'),
              prerequisite=str((ROOT/'runs/research-round2-2026-09-09').resolve()),
              preparation_seconds=600,control_seconds=120,search_seconds=110,search_process_seconds=120,
              confirmation_seconds=80,confirmation_process_seconds=90,
              long_target_tokens=15000000,long_train_seconds=2100,
              selection='Among completed adaptation (not context/cold) variants, require both paired accuracy gains >=2pp, '
                        'no average family decline >5pp, and no loss/accuracy decline against unchanged parent in either repetition. '
                        'Rank passing status then mean accuracy gain then reference answer loss. '
                        'Even if none passes, take best exploratory contender into paired 15M-token replication. '
                        'Long confirmation uses fresh groups, two new data seeds and unchanged-parent control; never auto-adopt.',
              limits='Finite sampled levels, local short-horizon effects; no universal parameter knowledge. '
                     'Architecture changes also change parameter count. Context changes packing; use matched eligible subset. '
                     'Initializations repeated only in cold block. Final external tests closed.',
              deferred={'tokenizer_vocab':'Needs separate train-only tokenizer/data-version audit and common-example/byte comparison; not varied in this campaign.',
                        'optimizer_family':'AdamW only; WD=0 tests Adam-like decay removal, not a tuned comparison to SGD/Muon.',
                        'architecture_components':'Activation/norm/RoPE/dropout/tied embeddings remain fixed; not inferred from size variations.',
                        'decode_settings':'Evaluation protocol held fixed; no tuning on reference answers.',
                        'system_power':'User noise-limited power setting preserved, not a tuning factor.',
                        'io_cadence':'Existing light monitoring/checkpoint policy held fixed for comparisons.'},
              code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    write(run/'plan.json',plan)
    code=[ROOT/p for p in subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines() if p.endswith(('.py','.json','.md'))]
    code += [run/'plan.json',*sorted((run/'jobs').glob('*.json'))]
    write(run/'initial-inputs.json',{str(p):sha(p) for p in code})
    return plan


def suites(run,plan):
    """CPU-only grouped holdout creation inside the campaign's time budget."""
    from tokenizers import Tokenizer
    from slm.prepare import text_of
    prior=[ROOT/'runs/research-pilot-2026-09-09/confirmation-suite.json',
           ROOT/'runs/research-round2-2026-09-09/confirmation-suite.json']
    historical=read(ROOT/'runs/size-campaign-2026-09-08/suite.json')
    search=read(ROOT/'runs/research-round2-2026-09-09/search-suite.json')
    write(run/'search-suite.json',search)
    blocked={r['group'] for r in historical['general']}
    blocked.update(r['group'] for p in prior for r in read(p)['general'])
    bad={(r['source'],r['id']) for r in read(ROOT/'next_run/manual_findings.json') if r['manual_category'].startswith('reference_')}
    pool=defaultdict(list);train=set()
    tokenizer=Tokenizer.from_file(str(Path(plan['parent'])/'tokenizer.json'))
    with (ROOT/'data/v4-broad-corrected-2026-09-08/records.jsonl').open() as f:
        for line in f:
            row=json.loads(line)
            if row['split']=='train':train.add(row['group'])
            elif row['group'] not in blocked and (row['source'],row['original_id']) not in bad:
                if len(tokenizer.encode(text_of(row)).ids)<=1024:pool[row['source']].append(row)
    rows=[]
    for source in sorted(pool):rows+=select(pool[source],8,'study-24h-20260909',blocked|{r['group'] for r in rows})
    if train.intersection(r['group'] for r in rows+search['general']):raise ValueError('Training overlap')
    if blocked.intersection(r['group'] for r in rows):raise ValueError('Prior dev-group overlap')
    suite={**search,'general':rows,'code':[],'memorization':[],
           'protocol':'Fresh internal confirmation groups excluding historic general suite and both pilot confirmations. '
                      'Original train split only; prior inline dev-loss exposure possible. Not an external held-out benchmark.'}
    write(run/'confirmation-suite.json',suite)
    write(run/'suite-audit.json',dict(search=dict(Counter(r['source'] for r in search['general'])),
                                    confirmation=dict(Counter(r['source'] for r in rows)),train_overlap=0,prior_confirmation_overlap=0))
    write(run/'RUN_CONDITIONS.json',dict(recorded_at=datetime.now().astimezone().isoformat(),
          performance_mode='User-reported reduced power for noise; unchanged',
          power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),
          power_source=subprocess.check_output(['pmset','-g','batt'],text=True)))
    frozen=read(run/'initial-inputs.json')
    parent=Path(plan['parent']);data=Path(plan['data'])
    files=[*list((parent/plan['parent_checkpoint']).glob('*')),parent/'latest.json',parent/'config.json',parent/'tokenizer.json']
    files += [p for p in data.iterdir() if p.is_file() and p.name.endswith(('.bin','.npy','.json'))]
    files += [run/p for p in ['search-suite.json','confirmation-suite.json','suite-audit.json','RUN_CONDITIONS.json']]
    files += prior
    frozen.update({str(p):sha(p) for p in files})
    write(run/'frozen-inputs.json',frozen)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--suites-only',action='store_true');a=p.parse_args()
    run=Path(a.run).resolve();run.mkdir(parents=True,exist_ok=True)
    if a.suites_only:suites(run,read(run/'plan.json'))
    else:
        plan=initial(run)
        print(json.dumps(dict(jobs=len(plan['jobs']),maximum_stage_seconds=plan['maximum_stage_seconds']),indent=2))


if __name__=='__main__':main()
