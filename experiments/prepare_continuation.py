"""Clone frozen end checkpoints and prepare the authorized serial 2 x 3h extension."""
import json
import math
import shutil
import subprocess
from datetime import datetime,timedelta
from pathlib import Path
from slm.train import atomic_json
from slm.campaign import digest
from slm.prepare import digest as value_digest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/size-continuation-2026-09-09'


def signature(config, manifest):
    base=value_digest(json.dumps(dict(config=config['model'],manifest=digest(manifest),batch_size=config['batch_size'],weights=config['source_weights_by_sequence'],seed=config['seed']),sort_keys=True))
    if config['schedule_tokens'] or config['snapshot_tokens']:
        base=value_digest(json.dumps(dict(base_signature=base,schedule_tokens=config['schedule_tokens'],snapshot_tokens=config['snapshot_tokens']),sort_keys=True))
    return base


def prepare():
    previous=ROOT/'runs/size-campaign-2026-09-08'
    old=json.loads((previous/'plan.json').read_text())
    assert json.loads((previous/'status.json').read_text())['status']=='completed'
    assert json.loads((ROOT/'data/v4-broad-corrected-2026-09-08/audit.json').read_text())['status']=='passed'
    frozen_root=Path('/Users/timokruth/Projekte/SLM-evaluation-prep')
    for name,h in old['sha256'].items():
        assert digest(frozen_root/name)==h, name
    # Keep the numerical training path byte-identical to the three-hour parents.
    for file in ['slm/train.py','slm/model.py','slm/data.py','slm/optimization.py','slm/inference.py','slm/broad_eval.py']:
        assert digest(ROOT/file)==digest(frozen_root/file),file
    OUT.mkdir(exist_ok=False)
    shutil.copy2(previous/'suite.json',OUT/'suite.json')
    now=datetime.now().astimezone();admission=(now+timedelta(hours=10)).isoformat()
    conditions=dict(recorded_at=now.isoformat(),performance_mode='User-reported reduced performance for lower noise; settings unchanged by assistant',
        power_settings_at_preparation=subprocess.check_output(['pmset','-g','custom'],text=True),
        execution='Serial 27m then 97m; each continues its latest three-hour checkpoint for 10800 additional seconds',
        comparison_rule='Use cumulative active budgets (3h + 3h), new token deltas and actual system-resource timestamps. Overnight pause is not training time.',
        limitation='Same historical power setting is not proof of identical temperature/background load. GPU values are system-wide.')
    atomic_json(OUT/'RUN_CONDITIONS.json',conditions)
    jobs=[];comparisons=[];frozen=[]
    for size in ['27m','97m']:
        parent=ROOT/f'runs/size-{size}-2026-09-08-3h';run=ROOT/f'runs/size-{size}-2026-09-09-plus3h'
        cfg=json.loads((parent/'config.json').read_text());pointer=json.loads((parent/'latest.json').read_text())
        state=json.loads((parent/pointer['checkpoint']/'state.json').read_text())
        assert cfg['dtype']=='float32' and cfg['execution']=='compiled'
        assert state['signature']==signature(cfg,ROOT/cfg['data']/'manifest.json')
        assert set(cfg['snapshot_tokens'])<=set(state['token_snapshots'])
        run.mkdir(exist_ok=False)
        shutil.copytree(parent/pointer['checkpoint'],run/pointer['checkpoint'])
        for name in ['latest.json','config.json','tokenizer.json','data_manifest.json','best.json','best.safetensors']:
            shutil.copy2(parent/name,run/name)
        copied={}
        for path in (parent/pointer['checkpoint']).iterdir():
            if path.is_file():
                target=run/pointer['checkpoint']/path.name
                assert digest(target)==digest(path)
                copied[str(path.relative_to(ROOT))]=digest(path);frozen.append(path)
        inherited_lr=3e-4*(.1+.9*.5*(1+math.cos(math.pi*min(1,state['tokens']/cfg['schedule_tokens']))))
        lineage=dict(parent_run=str(parent.relative_to(ROOT)),parent_checkpoint=pointer['checkpoint'],starting_step=state['step'],starting_tokens=state['tokens'],
            parent_hashes=copied,state_preserved_exactly=True,optimizer_and_sampler_preserved=True,signature=state['signature'],initial_learning_rate=inherited_lr,
            prior_training_seconds=10800,additional_training_seconds=10800,cloned_at=now.isoformat(),
            note='Independent file copies; historical checkpoint untouched. Counters and token-based learning-rate clock remain cumulative. Best is retained for history, latest is the primary endpoint.')
        atomic_json(run/'parent.json',lineage);atomic_json(run/'RUN_CONDITIONS.json',conditions)
        atomic_json(run/'status.json',dict(status='prepared',resumed_from=str(parent/pointer['checkpoint']),starting_step=state['step'],starting_tokens=state['tokens']))
        original_job=next(j for j in old['jobs'] if j['name']==size+'-training')
        jobs.append(dict(name=size+'-training',module='slm.train',run=str(run.relative_to(ROOT)),args=original_job['args'],training_seconds=10800,timeout_seconds=10920,admission_until=admission))
        jobs.append(dict(name=size+'-final',module='slm.broad_eval',run=str(run.relative_to(ROOT)),args=['--suite',str((OUT/'suite.json').relative_to(ROOT)),
            '--output',str((run/'broad-eval').relative_to(ROOT)),'--maximum','256','--max-seconds','900','--answer-loss','--checkpoint','latest'],timeout_seconds=960,admission_until=admission))
        comparisons.append(dict(name=size,parent=str(parent.relative_to(ROOT)),run=str(run.relative_to(ROOT))))
        frozen += [run/'parent.json',parent/'config.json',parent/'latest.json',parent/'tokenizer.json',parent/'broad-eval/summary.json',parent/'broad-eval/results.jsonl']
    plan=dict(created_at=now.isoformat(),implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),comparison_kind='size_continuation',
        control_run=old['control_run'],control_wait_until=(now+timedelta(minutes=5)).isoformat(),jobs=jobs,comparisons=comparisons,
        evaluation_preparation=old['evaluation_preparation'],snapshot_tokens=[],
        protocol=dict(authorization='User on 2026-09-09 requested continuing both last three-hour runs from latest point for three more hours each.',
          training_sources=32,data_version=4,training_seconds_per_stage=10800,total_active_seconds_per_model=21600,checkpoint='latest, not best',
          precision='Original FP32, unchanged',learning_rate='Original cosine token clock to 100M with floor 3e-5; no reset or warmup restart',
          evaluation='Same 886 internal tasks, same 256-token generation, answer loss, executable code tests and WikiSQL proxy. No external tests.',
          expected_inference='Compare improvement within each model from 3h to 6h and difference between sizes. Not equal-token work or an optimized schedule for each size.',
          no_automatic_extension=True),sha256={})
    frozen += [p for folder in ['slm','slm_perf','experiments','future_eval'] for p in (ROOT/folder).glob('*.py')]
    frozen += [ROOT/'run_slm.py',ROOT/'run_defaults.json',OUT/'suite.json',ROOT/'runs/size-campaign-2026-09-08/data-families/manifest.json',
        ROOT/'data/v4-broad-corrected-2026-09-08/audit.json',ROOT/old['evaluation_preparation']/'audit.json',ROOT/old['evaluation_preparation']/'wikisql-tables.json']
    plan['sha256']={str(p.relative_to(ROOT)):digest(p) for p in frozen}
    atomic_json(OUT/'plan.json',plan);atomic_json(OUT/'status.json',dict(status='prepared',additional_training_seconds_total=21600))
    print(json.dumps(dict(campaign=str(OUT),models=comparisons,authorized=True)))

if __name__=='__main__':prepare()
