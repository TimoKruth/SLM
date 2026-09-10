from pathlib import Path
import copy
import json
import sys
import pytest
from research.common import read,write
from long_study.protocol import signature,phase_for_elapsed,validate_plan,differences


def plan():
    return dict(jobs=[str(i) for i in range(8)],budget_seconds=85400,previous_budget_spent_seconds=1000,
                control_seconds=120,report_seconds=600,parent_checkpoint='checkpoint-1',
                parent_weights_sha256='a',data_manifest_sha256='b')


def test_wall_endpoint_is_time_based_with_reserved_checkpoint_time():
    assert phase_for_elapsed(7139,7200,60)=='train'
    assert phase_for_elapsed(7140,7200,60)=='checkpoint'
    assert phase_for_elapsed(100,7200,60)=='train'
    with pytest.raises(ValueError):phase_for_elapsed(0,60,60)


def test_budget_charges_probe_and_all_evaluations():
    p=plan();assert validate_plan(p)==8*7200+33*630+120+600
    for changes in [dict(budget_seconds=86400),dict(budget_seconds=78000,previous_budget_spent_seconds=8400),dict(jobs=['x']*8)]:
        with pytest.raises(ValueError):validate_plan(dict(p,**changes))


def test_resume_signature_covers_job_parent_data_and_precision():
    p=plan();j=dict(parameters=dict(precision='fp32',lr=3e-5),train_seconds=7200)
    s=signature(p,j)
    for k in ['parent_checkpoint','parent_weights_sha256','data_manifest_sha256']:
        assert signature(dict(p,**{k:'changed'}),j)!=s
    for change in [dict(parameters=dict(precision='bf16',lr=3e-5)),dict(train_seconds=14400)]:
        assert signature(p,dict(j,**change))!=s


def test_failed_gpu_stage_resumes_checkpoint_once_without_budget_reset(tmp_path,monkeypatch):
    from long_study.campaign import Runner
    from study.safety import RecoverableStop
    run=tmp_path/'campaign';run.mkdir();write(run/'frozen-inputs.json',{})
    target=run/'trials'/'first';write(target/'latest.json',{'checkpoint':'checkpoint-1'})
    r=Runner(run,{},dict(stages=[]),10000,[]);calls=[];ticks=iter([100.,120.,140.,150.])
    monkeypatch.setattr('long_study.campaign.time.monotonic',lambda:next(ticks))
    monkeypatch.setattr('long_study.campaign.time.sleep',lambda _:None)
    def attempt(name,module,target,args,seconds):
        calls.append((name,module,args,seconds))
        return (module=='study.health'),{'failure_kind':'gpu_service'}
    monkeypatch.setattr(r,'attempt',attempt)
    with pytest.raises(RecoverableStop,match='Retry failed'):
        r.job('first','long_study.trial',target,[],7200)
    assert len(calls)==3 and calls[1][1]=='study.health'
    assert '--resume' in calls[2][2]
    assert float(calls[2][2][-1])<7200 and calls[2][3]<7200
    assert (target/'latest.json').exists() and r.state['gpu_recovery_attempts']==1


def test_timeout_never_triggers_gpu_retry(tmp_path,monkeypatch):
    from long_study.campaign import Runner
    from study.safety import RecoverableStop
    write(tmp_path/'frozen-inputs.json',{})
    r=Runner(tmp_path,{},dict(stages=[]),10000,[]);calls=[]
    def fail(*args):calls.append(args);return False,{'failure_kind':'evaluation_timeout'}
    monkeypatch.setattr(r,'attempt',fail)
    with pytest.raises(RecoverableStop,match='evaluation_timeout'):r.job('eval','slm.broad_eval',tmp_path,[],630)
    assert len(calls)==1


def test_stop_blocks_before_campaign_status_or_child(tmp_path,monkeypatch):
    from long_study.campaign import main
    write(tmp_path/'plan.json',plan());(tmp_path/'STOP').write_text('stop')
    monkeypatch.setattr(sys,'argv',['long_study.campaign','--run',str(tmp_path)])
    monkeypatch.setattr('long_study.campaign.subprocess.Popen',lambda *a,**k:pytest.fail('Child started'))
    with pytest.raises(ValueError,match='STOP'):main()
    assert not (tmp_path/'status.json').exists()


def test_report_preserves_all_four_cells_and_interaction(tmp_path):
    from long_study.report import report
    jobs=[]
    for repetition in range(2):
        for c,acc in zip('ABCD',[.2,.3,.4,.6]):
            name=f'{repetition}{c}';jobs.append(name)
            write(tmp_path/'jobs'/(name+'.json'),dict(repetition=repetition,condition=c))
            write(tmp_path/'trials'/name/'confirmation/summary.json',dict(selected_general=2,evaluated_general=2,
                 deadline_reached=False,answer_loss=dict(examples=2,macro_source_answer_loss=1),
                 mean_source_accuracy_by_family={'f':acc}))
    write(tmp_path/'plan.json',dict(jobs=jobs))
    report(tmp_path,dict(status='running',phase='evaluation'))
    result=read(tmp_path/'contrasts.json')
    assert result['final_confirmation:interaction'][0]['accuracy']==pytest.approx(.1)
    assert len(result['final_confirmation:B-A'])==2


def test_new_modules_use_monitoring_and_gpu_admission():
    from run_slm import command
    from slm_perf.__main__ import GPU_MODULES
    from slm_perf.instrument import MODULES
    assert 'long_study.trial' in GPU_MODULES
    assert {'long_study.trial','long_study.campaign'}<=MODULES
    cmd=command(['--run','test','--module','long_study.trial'])
    assert cmd[cmd.index('--mode')+1]=='light'
