"""CPU-only preparation; writes STOP and freezes inputs before any campaign starts."""
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
import copy
import json
import math
import subprocess

from research.common import read,write,sha
from research.prepare import select
from .protocol import validate_plan

ROOT=Path(__file__).resolve().parents[1]


def fresh_suite(run,parent,search):
    from tokenizers import Tokenizer
    from slm.prepare import text_of
    paths=sorted((ROOT/'runs').glob('*/confirmation-suite.json'))
    paths+=[ROOT/'runs/size-campaign-2026-09-08/suite.json']
    blocked={r['group'] for r in search['general']}
    for path in paths:blocked.update(r['group'] for r in read(path)['general'])
    bad={(r['source'],r['id']) for r in read(ROOT/'next_run/manual_findings.json') if r['manual_category'].startswith('reference_')}
    tokenizer=Tokenizer.from_file(str(parent/'tokenizer.json'))
    pool=defaultdict(list);train=set()
    records=ROOT/'data/v4-broad-corrected-2026-09-08/records.jsonl'
    with records.open() as stream:
        for line in stream:
            row=json.loads(line)
            if row['split']=='train':train.add(row['group'])
            elif row['group'] not in blocked and (row['source'],row['original_id']) not in bad:
                if len(tokenizer.encode(text_of(row)).ids)<=1024:pool[row['source']].append(row)
    selected={};used=set(blocked)
    for source in sorted(pool):
        selected[source]=select(pool[source],8,'long-horizon-20260910',used)
        used.update(r['group'] for r in selected[source])
    rows=[]
    for index in range(8):
        for source in sorted(selected):
            if index<len(selected[source]) and len(rows)<200:rows.append(selected[source][index])
    if len(rows)!=200:raise ValueError('Insufficient fresh tasks; review suite before training')
    if train.intersection(r['group'] for r in rows) or blocked.intersection(r['group'] for r in rows):
        raise ValueError('Fresh suite overlaps previous or training groups')
    suite=dict(search,general=rows,code=[],memorization=[],protocol='Fresh internal grouped confirmation, excludes prior confirmations and search groups; possible historical inline dev-loss exposure. Not external transfer.')
    write(run/'confirmation-suite.json',suite)
    write(run/'suite-audit.json',dict(examples=len(rows),sources=dict(Counter(r['source'] for r in rows)),
          train_overlap=0,previous_group_overlap=0,blocked_groups=len(blocked),excluded_suites=[str(p) for p in paths],
          records_sha256=sha(records)))
    return [*paths,records,ROOT/'next_run/manual_findings.json']


def prepare(run,design_path,charged_seconds,concurrency_report):
    if run.exists():raise ValueError('Use a new campaign directory')
    design=read(design_path);run.mkdir(parents=True)
    (run/'STOP').write_text('Prepared; explicit authorized start handled separately.\n')
    parent=Path(design['parent']);data=Path(design['data'])
    if read(parent/'latest.json')['checkpoint']!=design['parent_checkpoint']:raise ValueError('Parent changed')
    if sha(data/'manifest.json')!=design['data_manifest_sha256']:raise ValueError('Data changed')
    old=ROOT/'runs/parameter-study-timeout-recovery-2026-09-10'
    search=read(old/'search-suite.json');write(run/'search-suite.json',search)
    references=fresh_suite(run,parent,search)
    configs={c['id']:c['parameters'] for c in design['configurations']}
    jobs=[]
    for entry in design['runs']:
        job=dict(id=entry['id'],condition=entry['condition'],repetition=entry['repetition'],
                 parameters=copy.deepcopy(configs[entry['condition']]),data_seed=entry['data_seed'],model_seed=2026091010,
                 train_seconds=7200,checkpoint_seconds=300,checkpoint_reserve_seconds=60,
                 snapshot_tokens=[15000000,30000000,50000000,75000000,100000000,150000000])
        write(run/'jobs'/(job['id']+'.json'),job);jobs.append(job['id'])
    spent=math.ceil(charged_seconds)
    plan=dict(version=1,parent=str(parent),parent_checkpoint=design['parent_checkpoint'],
              parent_weights_sha256=sha(parent/design['parent_checkpoint']/'model.safetensors'),
              data=str(data),data_manifest_sha256=design['data_manifest_sha256'],jobs=jobs,
              original_budget_seconds=86400,previous_budget_spent_seconds=spent,budget_seconds=86400-spent,
              control_seconds=120,report_seconds=600,evaluation_seconds=600,evaluation_process_seconds=630,
              original_design=str(design_path),original_design_sha256=sha(design_path),
              concurrency_report=str(concurrency_report),concurrency_report_sha256=sha(concurrency_report),
              code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    plan['maximum_stage_seconds']=validate_plan(plan)
    write(run/'plan.json',plan)
    write(run/'RUN_CONDITIONS.json',dict(recorded_at=datetime.now().astimezone().isoformat(),
          performance_mode='User-authorized high performance with concurrent EvoNN CPU campaign; overlap recorded per stage',
          power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),
          power_source=subprocess.check_output(['pmset','-g','batt'],text=True)))
    files=[ROOT/p for p in subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines() if p.endswith(('.py','.json','.md'))]
    files += [p for p in (parent/plan['parent_checkpoint']).iterdir() if p.is_file()]
    files += [parent/'latest.json',parent/'tokenizer.json',parent/'config.json',Path(design_path),Path(concurrency_report),*references]
    files += [p for p in data.iterdir() if p.is_file() and p.suffix in ['.bin','.npy','.json']]
    files += [p for p in run.rglob('*') if p.is_file() and p.name!='STOP']
    write(run/'frozen-inputs.json',{str(p.resolve()):sha(p) for p in files})
    write(run/'READY.json',dict(status='prepared',jobs=8,maximum_evaluations=33,remaining_seconds=plan['budget_seconds']))
    return plan
