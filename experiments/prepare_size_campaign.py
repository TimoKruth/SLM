"""Freeze the corrected data, protocol and serial 2 x 3-hour size comparison."""
import json,subprocess
from datetime import datetime,timedelta
from pathlib import Path
from experiments.prepare_broad import sha
from slm.breadth import sampling_weights

ROOT=Path(__file__).resolve().parents[1]


def prepare():
    data=ROOT/'data/v4-broad-corrected-2026-09-08'
    evaluation=ROOT/'runs/size-eval-preparation-2026-09-08'
    audit=json.loads((data/'audit.json').read_text());assert audit['status']=='passed'
    prep=json.loads((evaluation/'audit.json').read_text());assert not prep['sampled_near_duplicates']
    smoke=ROOT/'runs/size-preflight-2026-09-08'
    assert json.loads((smoke/'status.json').read_text())['reason']=='step_limit'
    checked=json.loads((smoke/'token-000010000/evaluation/summary.json').read_text())
    assert not checked['deadline_reached'] and checked['evaluated_general']==checked['selected_general']
    assert checked['answer_loss']['examples']==checked['selected_general']
    assert checked['code_evaluated']+sum(checked['code_exclusions'].values())==2
    out=ROOT/'runs/size-campaign-2026-09-08';out.mkdir(exist_ok=False)
    view=out/'data-families';view.mkdir()
    meta=json.loads((data/'manifest.json').read_text())
    for p in data.iterdir():
        if p.name!='manifest.json':(view/p.name).symlink_to(p.resolve())
    meta.update(source_weights=sampling_weights(meta['sources'],'families'),sampling_mode='families',
        view_parent_manifest_sha256=sha(data/'manifest.json'))
    (view/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
    suite=json.loads((evaluation/'suite-v2.json').read_text())
    suite['protocol']='Frozen corrected internal development for model-size comparison: 32 training sources, 31 with own development groups; 886 generative tasks and separate executable code tasks. Original train splits only. No external final tests. Same tasks for both models and fixed-token snapshots.'
    (out/'suite.json').write_text(json.dumps(suite,ensure_ascii=False)+'\n')
    now=datetime.now().astimezone();admission=(now+timedelta(hours=12)).isoformat()
    conditions=dict(recorded_at=now.isoformat(),performance_mode='User-reported reduced performance for lower noise',
        exact_setting='Unknown; pmset snapshots additionally recorded at each training start',
        changes_made_to_system_settings=False,execution='Serial, small model first; fixed order is a comparison limitation',
        comparison_rule='Report actual tokens, source exposure and wall time; time/memory are not energy or GPU-utilization measurements.')
    (out/'RUN_CONDITIONS.json').write_text(json.dumps(conditions,indent=2)+'\n')
    snapshots=[10000000,20000000,30000000]
    jobs=[];comparisons=[]
    for name,dim,layers,heads,hidden in [('27m',512,6,8,1368),('97m',768,12,12,2048)]:
        run=Path(f'runs/size-{name}-2026-09-08-3h');(ROOT/run).mkdir(exist_ok=False)
        (ROOT/run/'RUN_CONDITIONS.json').write_text(json.dumps(conditions,indent=2)+'\n')
        trainargs=['--data',str(view.relative_to(ROOT)),'--execution','compiled','--seed','20260906','--steps','1000000','--max-tokens','1000000000000',
            '--dim',str(dim),'--layers',str(layers),'--heads',str(heads),'--hidden',str(hidden),'--context','1024','--batch-size','2',
            '--checkpoint-seconds','600','--eval-seconds','1800','--schedule-tokens','100000000','--snapshot-tokens',*map(str,snapshots)]
        jobs.append(dict(name=name+'-training',module='slm.train',run=str(run),args=trainargs,training_seconds=10800,timeout_seconds=10920,admission_until=admission))
        def evaluation_job(stage,target_run,output,checkpoint,optional=False):
            args=['--suite',str((out/'suite.json').relative_to(ROOT)),'--output',str(output),'--maximum','256','--max-seconds','900','--answer-loss','--checkpoint',checkpoint]
            if optional:args.append('--skip-code')
            return dict(name=stage,module='slm.broad_eval',run=str(target_run),args=args,timeout_seconds=960,admission_until=admission,optional_snapshot=optional)
        jobs.append(evaluation_job(name+'-final',run,run/'broad-eval','latest'))
        for target in snapshots:
            sr=run/f'token-{target:09d}'
            jobs.append(evaluation_job(f'{name}-tokens-{target}',sr,sr/'evaluation','best',True))
        comparisons.append(dict(name=name,run=str(run)))
    plan=dict(created_at=now.isoformat(),implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),comparison_kind='model_size',control_run='runs/broad-control-2026-09-07',
        control_wait_until=(now+timedelta(minutes=5)).isoformat(),jobs=jobs,comparisons=comparisons,snapshot_tokens=snapshots,
        evaluation_preparation=str(evaluation.relative_to(ROOT)),budget='2 x 10800 seconds training; final checkpoint cleanup outside deadline; separate bounded evaluations (900 seconds each). No continuation or random search.',
        protocol=dict(data_version=4,training_sources=32,general_tasks=len(suite['general']),code_tasks=len(suite['code']),
            primary_checkpoint='latest after three-hour budget; not whichever development checkpoint wins',
            sampling='Equal family probability, equal source probability within family; token exposure reported separately',
            mixture_selection_reason='Previous corrected 670-item comparison tied; family balancing retained for breadth, not chosen on external tests.',
            learning_rate='AdamW peak 3e-4, 100-step warmup, shared cosine token clock to 100 million tokens, floor 3e-5; wall deadline only stops training',
            matched_work='First completed step crossing each fixed token threshold; save actual tokens, steps and per-source exposure',
            boundaries='One seed each and fixed serial order. Internal development only. Code and SQL execution proxies separate from answer matching. No exhaustive semantic overlap guarantee.',
            data_fixes=['SciTail entails -> entailment','WIQA no_effect -> no effect']),sha256={})
    files=[p for folder in ['slm','slm_perf','experiments','future_eval'] for p in (ROOT/folder).glob('*.py')]
    files += [ROOT/'run_slm.py',ROOT/'run_defaults.json',data/'manifest.json',data/'audit.json',view/'manifest.json',out/'suite.json',evaluation/'audit.json',evaluation/'wikisql-tables.json',ROOT/'runs/broad-control-2026-09-07/recall-before/summary.json',ROOT/'runs/broad-control-2026-09-07/recall-after/summary.json']
    plan['sha256']={str(p.relative_to(ROOT)):sha(p) for p in files}
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (out/'status.json').write_text(json.dumps({'status':'prepared','training_seconds':21600},indent=2)+'\n')
    print('SIZE_CAMPAIGN_READY',out)

if __name__=='__main__':prepare()
