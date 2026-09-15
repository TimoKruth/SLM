"""Prepare the explicitly authorized 90-minute saved-checkpoint comparison, CPU only."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from experiments.run_parameter_confirmation import sha, read, write, validate_plan


def prepare(project, code, run, origin):
    assert not run.exists(), 'Do not overwrite an existing run'
    # Only CPU data helpers are loaded from the already committed preparation code.
    sys.path.insert(0, str(project))
    import experiments
    experiments.__path__.append(str(project/"experiments"))
    from experiments.prepare_fresh_parameter_confirmation import content_keys, suite_paths, rows_of_suite
    base = project/'runs/parameter-confirmation-refresh-2026-09-15'
    audit = read(base/'coverage-audit.json'); provenance = read(base/'provenance.json')
    assert audit['data_coverage_complete'] and audit['tasks']==1360 and audit['scored_tasks']==1280
    inputs = {}
    for path, expected in provenance['inputs'].items():
        assert sha(path)==expected, 'Preparation input changed: '+path
        inputs[path]=expected
    assert sha(base/'confirmation-suite.json') == audit['suite_sha256']
    suite = read(base/'confirmation-suite.json')
    groups = {r['group'] for r in suite['general']}
    keys = set().union(*(content_keys(r) for r in suite['general']))
    assert len(groups)==1360
    reservations = []
    for path in suite_paths(project):
        if path == (base/'confirmation-suite.json').resolve():continue
        other = rows_of_suite(read(path))
        assert not groups & {r['group'] for r in other}, 'New reservation group overlap: '+str(path)
        assert not keys & set().union(*(content_keys(r) for r in other if 'prompt' in r)), 'New reservation content overlap: '+str(path)
        inputs[str(path)] = sha(path); reservations.append(str(path))
    # No original preparation STOP is removed; independent copies are used throughout.
    run.mkdir(parents=True)
    for name in ['checkpoints','conditions','logs','evaluations']: (run/name).mkdir()
    def register(path):inputs[str(path)]=sha(path);return path
    def copy(source,target):
        register(source);shutil.copy2(source,target);register(target)
        assert inputs[str(source)] == inputs[str(target)]
    copy(base/'confirmation-suite.json', run/'confirmation-suite.json')
    for path in [base/'coverage-audit.json',base/'provenance.json',base/'verification.json']:register(path)
    jobs=[];campaign=project/'runs/long-horizon-round2-resume-2026-09-14'
    definitions=[('parent',None)]+[(c,o) for o in (0,1) for c in 'AD']
    for condition,order in definitions:
        identifier='parent' if condition=='parent' else f'r{order}-{condition}-75M'
        source=(project/'runs/size-27m-2026-09-09-plus3h' if condition=='parent' else
                campaign/'trials'/f'long-round2-r{order}-{condition}'/'token-075000000')
        weight=source/('checkpoint-0135594/model.safetensors' if condition=='parent' else 'model.safetensors')
        snapshot=dict(additional_tokens=None,step=135594) if condition=='parent' else read(register(source/'snapshot.json'))
        shadow=run/'checkpoints'/identifier;shadow.mkdir();(shadow/'checkpoint').mkdir()
        for name in ['config.json','tokenizer.json']:copy(source/name,shadow/name)
        copy(weight,shadow/'checkpoint/model.safetensors');write(shadow/'latest.json',{'checkpoint':'checkpoint'});register(shadow/'latest.json')
        assert sha(shadow/'tokenizer.json') == suite['tokenizer_sha256']
        assert read(shadow/'config.json')['model'] == read(run/'checkpoints/parent/config.json')['model']
        if condition=='parent':assert sha(weight)=='245f44c7187df9532ff9612e3bdc3ad73c2426cd4b67d1ced3dab14c3c6b1f25'
        else:register(source.parent/'RUN_CONDITIONS.json')
        paths=[str(base/'confirmation-suite.json'),str(run/'confirmation-suite.json'),str(weight)]+[str(p) for p in shadow.rglob('*') if p.is_file()]
        if condition!='parent':paths.append(str(source/'snapshot.json'))
        jobs.append(dict(id=identifier,condition=condition,order=order,endpoint='parent' if condition=='parent' else '75M',
                         additional_tokens=snapshot['additional_tokens'],step=snapshot['step'], source=str(source),
                         source_checkpoint=str(weight),shadow=str(shadow),checkpoint_sha256=sha(weight),input_paths=paths))
    register(campaign/'RUN_CONDITIONS.json')
    register(project/'runs/size-27m-2026-09-09-plus3h/RUN_CONDITIONS.json')
    conditions=dict(recorded_at=datetime.now().astimezone().isoformat(),power_source=subprocess.check_output(['pmset','-g','batt'],text=True),
                    power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),
                    monitoring='light',powerwatch_unchanged=True,scope='Saved checkpoint quality only; no throughput inference or training')
    assert 'AC Power' in conditions['power_source']
    write(run/'RUN_CONDITIONS.json',conditions);register(run/'RUN_CONDITIONS.json')
    # The execution worktree derives from the frozen numerical code, not an active training branch.
    for name in subprocess.check_output(['git','ls-files'],cwd=code,text=True).splitlines():
        if name.endswith('.py') or name in ['run_defaults.json','pyproject.toml']:
            register(code/name)
    deadline=origin+5400
    plan=dict(mode='evaluation_only',code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=code,text=True).strip(),
              numerical_base_commit='4c30196',controller_sha256=sha(code/'experiments/run_parameter_confirmation.py'),
              budget_origin=datetime.fromtimestamp(origin).astimezone().isoformat(),budget_origin_unix=origin,
              deadline_unix=deadline,deadline=datetime.fromtimestamp(deadline).astimezone().isoformat(),total_budget_seconds=5400,
              max_seconds_per_evaluation=600,maximum_generated_tokens=256,preparation_seconds_cap=1200,
              evaluation_seconds_cap=3300,analysis_seconds_cap=900,jobs=jobs,inputs=inputs,
              hypothesis='At matched 75M additional-token exposure, D improves family-macro free-answer accuracy over A and the unchanged parent.',
              gates=dict(minimum_gain_vs_A_per_order=.02,strictly_positive_vs_parent_per_order=True,
                         maximum_mean_family_regression_vs_each_reference=.05,automatic_adoption=False),
              selection='All four preselected 75M A/D checkpoints, no outcome-based checkpoint selection. Historical 50M/time-end diagnostics are not part of this decision.',
              uncertainty='5000 paired group resamples within source, fixed two data orders; exploratory intervals, not independent initializations or external transfer.')
    validate_plan(plan)
    write(run/'plan.json',plan)
    write(run/'AUTHORIZATION.json',dict(user_instruction='Start the comparison',proposal='Five saved models at matched 75M, evaluation only, maximum 90 minutes including preparation and reporting.',
                                      automatic_adoption=False,automatic_extension=False,automatic_retry=False,created=conditions['recorded_at']))
    write(run/'PREPARATION_CHECKS.json',dict(source_suite_sha256=audit['suite_sha256'],prior_input_hashes_checked=len(provenance['inputs']),
                                            reservation_suites_checked=len(reservations),selected_overlap=0,reservations=reservations,
                                            elapsed_preparation_seconds=time.time()-origin,script_sha256=sha(Path(__file__))))
    assert time.time()-origin < 1200, 'Preparation cap exceeded'
    print(json.dumps(dict(run=str(run),jobs=len(jobs),inputs=len(inputs),deadline=plan['deadline'],preparation_seconds=time.time()-origin),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['project','code','run']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--budget-origin',required=True)
    a=p.parse_args();prepare(a.project.resolve(),a.code.resolve(),a.run.resolve(),datetime.fromisoformat(a.budget_origin).timestamp())
