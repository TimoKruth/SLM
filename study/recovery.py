"""Prepare a new, blocked continuation using verified independent copies of valid outputs."""
import argparse
import ast
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess

from research.common import read,write,sha,quality

ROOT=Path(__file__).resolve().parents[1]


def model_file(run):
    return Path(run)/read(Path(run)/'latest.json')['checkpoint']/'model.safetensors'


def valid_trial(run,job):
    try:
        run=Path(run);cfg=read(run/'config.json');r=read(run/'result.json')
        folder=run/read(run/'latest.json')['checkpoint'];state=read(folder/'state.json')
        if cfg['study_job']!=job or cfg['model']!=job['parameters']['model']:return False
        if read(folder/'model_config.json')!=cfg['model']:return False
        if r['status']!='completed' or r['checkpoint']!=folder.name:return False
        if r['additional_tokens']<job['target_tokens']:return False
        if state['tokens']!=r['cumulative_tokens'] or r['base_tokens']+r['additional_tokens']!=state['tokens']:return False
        if state['sampler_state']!=r['final_sampler']:return False
        signature=hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest()
        if state['signature']!=signature:return False
        return all((folder/f).is_file() and (folder/f).stat().st_size>0 for f in ['model.safetensors','optimizer.npz','model_config.json'])
    except (OSError,ValueError,KeyError,TypeError):return False


def valid_evaluation(output,model_run,suite):
    try:
        output=Path(output);summary=read(output/'summary.json');quality(summary)
        protocol=read(output/'protocol.json');suite=Path(suite)
        return (protocol.get('partition')=='dev' and summary.get('partition')=='dev'
                and protocol['suite_sha256']==sha(suite) and protocol['checkpoint_sha256']==sha(model_file(model_run))
                and sha(Path(model_run)/'tokenizer.json')==read(suite)['tokenizer_sha256']
                and summary['selected_general']==len(read(suite)['general'])
                and len((output/'results.jsonl').read_text().splitlines())==summary['selected_general'])
    except (OSError,ValueError,KeyError,TypeError):return False


def remaining_budget(plan,state,validation_reserve):
    spent=math.ceil(state.get('total_budget_spent_seconds',state['elapsed_seconds']))
    total=plan.get('original_budget_seconds',plan['budget_seconds'])
    remaining=total-spent-validation_reserve
    if remaining<=0:raise ValueError('Original budget exhausted')
    return spent+validation_reserve,remaining


def clone(source,destination):
    """APFS copy-on-write copies, never writable hardlinks into historical runs."""
    destination.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['/bin/cp','-cR',str(source),str(destination)],check=True)


def numeric_compatibility(old_root):
    files=['slm/model.py','slm/data.py','slm/optimization.py','slm/precision.py','slm/broad_eval.py','slm/inference.py']
    checks={f:sha(ROOT/f)==sha(old_root/f) for f in files}
    trees=[ast.parse((p/'study/trial.py').read_text()) for p in [old_root,ROOT]]
    for name in ['mask_of','make_step','load','step','control']:
        funcs=[next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name==name) for t in trees]
        checks['study.trial.'+name]=ast.dump(funcs[0])==ast.dump(funcs[1])
    if not all(checks.values()):raise ValueError('Numerical code changed; automatic reuse not permitted')
    return checks


def evaluation_limits(original, seconds=None):
    """Change only evaluation wall limits, keeping scoring and token limits intact."""
    limits={key:original[key] for key in ['search_seconds','search_process_seconds',
                                        'confirmation_seconds','confirmation_process_seconds']}
    if seconds is not None:
        if not math.isfinite(seconds) or seconds<=0:
            raise ValueError('Evaluation seconds must be finite and positive')
        for suite in ['search','confirmation']:
            limits[suite+'_seconds']=seconds
            limits[suite+'_process_seconds']=seconds+30
    return limits


def remaining_stage_cap(plan, jobs, imported, evaluated):
    """Upper bound for pending stages, including all later evaluations and controls."""
    return (sum(job['train_seconds']+plan['search_process_seconds']
                for job in jobs if job['id'] not in imported)
            +(len(imported)-len(evaluated))*plan['search_process_seconds']
            +plan['control_seconds']+20
            +4*(plan['long_train_seconds']+2*plan['search_process_seconds'])
            +5*plan['confirmation_process_seconds'])


def prepare(old,run,reserve=120,repaired_evaluation=None,evaluation_seconds=None):
    if run.exists():raise ValueError('Use a new continuation directory')
    state=read(old/'status.json');original=read(old/'plan.json')
    limits=evaluation_limits(original,evaluation_seconds)
    if state['status'] not in ['stopped','invalid','paused_infrastructure','completed_with_failures']:
        raise ValueError('Original campaign must be stopped')
    if state.get('frozen_inputs_unchanged') is not True:raise ValueError('Original input integrity not verified')
    original_hashes=read(old/'frozen-inputs.json')
    for p,h in original_hashes.items():
        if sha(p)!=h:raise ValueError('Original input changed: '+p)
    old_root=Path('/Users/timokruth/Projekte/SLM-parameter-study')
    compatibility=numeric_compatibility(old_root)
    spent,remaining=remaining_budget(original,state,reserve)
    run.mkdir(parents=True)
    imported=[];evaluated=[];repaired=[]
    for filename in ['search-suite.json','confirmation-suite.json','suite-audit.json']:
        shutil.copy2(old/filename,run/filename)
    clone(old/'jobs',run/'jobs')
    for identifier in original['jobs']:
        job=read(old/'jobs'/(identifier+'.json'));source=old/'trials'/identifier
        if not valid_trial(source,job):continue
        destination=run/'trials'/identifier;destination.mkdir(parents=True)
        for filename in ['config.json','result.json','status.json','latest.json','tokenizer.json','RUN_CONDITIONS.json']:
            clone(source/filename,destination/filename)
        pointer=read(source/'latest.json')['checkpoint'];clone(source/pointer,destination/pointer)
        if not valid_trial(destination,job):raise ValueError('Copied trial validation failed')
        imported.append(identifier)
        if valid_evaluation(source/'search',source,old/'search-suite.json'):
            clone(source/'search',destination/'search');evaluated.append(identifier)
        elif repaired_evaluation is not None and valid_evaluation(repaired_evaluation,source,old/'search-suite.json'):
            clone(repaired_evaluation,destination/'search');evaluated.append(identifier);repaired.append(identifier)
    if not valid_evaluation(old/'parent-search',Path(original['parent']),old/'search-suite.json'):
        raise ValueError('Original parent evaluation not reusable')
    clone(old/'parent-search',run/'parent-search')
    conditions=dict(recorded_at=datetime.now().astimezone().isoformat(),
          performance_mode='User-reported reduced power for noise; unchanged',
          power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),
          power_source=subprocess.check_output(['pmset','-g','batt'],text=True),
          previous_conditions=read(old/'RUN_CONDITIONS.json'))
    write(run/'RUN_CONDITIONS.json',conditions)
    plan=dict(original,reuse_completed=True,recovered_from=str(old),
              original_budget_seconds=original.get('original_budget_seconds',original['budget_seconds']),
              previous_budget_spent_seconds=spent,budget_seconds=remaining,
              validation_reserve_seconds=reserve,created=datetime.now().astimezone().isoformat(),
              code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    plan.update(limits)
    plan['maximum_remaining_stage_seconds']=remaining_stage_cap(
        plan,[read(run/'jobs'/(i+'.json')) for i in original['jobs']],imported,evaluated)
    if plan['maximum_remaining_stage_seconds']+60>remaining:
        (run/'STOP').write_text('Preparation failed: pending stage caps exceed remaining budget.\n')
        raise ValueError('Pending stage caps exceed remaining original budget')
    write(run/'plan.json',plan)
    audit=dict(imported_training=imported,imported_evaluations=evaluated,repaired_evaluations=repaired,
               pending_training=len(original['jobs'])-len(imported),
               pending_evaluation_only=sorted(set(imported)-set(evaluated)),
               numeric_compatibility=compatibility,old_elapsed_seconds=state['elapsed_seconds'],
               charged_previous_seconds=spent,remaining_seconds=remaining,validation_reserve_seconds=reserve,
               evaluation_limits_before=evaluation_limits(original),evaluation_limits_after=limits)
    write(run/'recovery-audit.json',audit)
    frozen=dict(original_hashes)
    files=[ROOT/p for p in subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines() if p.endswith(('.py','.md','.json'))]
    files += [p for p in run.rglob('*') if p.is_file()]
    for p in files:frozen[str(p)]=sha(p)
    write(run/'initial-inputs.json',frozen);write(run/'frozen-inputs.json',frozen)
    (run/'STOP').write_text('Prepared only. Explicit user instruction required to start.\n')
    write(run/'READY.json',dict(status='prepared_paused',training_started=False,**audit))
    return audit


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--from-run',required=True);parser.add_argument('--run',required=True)
    parser.add_argument('--repaired-evaluation')
    parser.add_argument('--evaluation-seconds',type=float)
    args=parser.parse_args();print(json.dumps(prepare(Path(args.from_run).resolve(),Path(args.run).resolve(),
                       repaired_evaluation=Path(args.repaired_evaluation).resolve() if args.repaired_evaluation else None,
                       evaluation_seconds=args.evaluation_seconds),indent=2))


if __name__=='__main__':main()
