"""No GPU work: failure injection, provenance checks, budget and retry boundaries."""
from pathlib import Path
import sys
import pytest
from research.common import write,read,sha
from study.safety import failure_kind,archive_failed_output,RecoverableStop,retry_seconds
from study.recovery import remaining_budget,valid_evaluation,evaluation_limits,remaining_stage_cap

GPU_HANG = ('libc++abi: terminating due to uncaught exception of type std::runtime_error: '
            '[METAL] Command buffer execution failed: Caused GPU Hang Error '
            '(00000003:kIOGPUCommandBufferCallbackErrorHang)')


@pytest.mark.parametrize('message',[GPU_HANG,'Caused GPU Hang Error',
                                    'kIOGPUCommandBufferCallbackErrorHang'])
def test_native_gpu_hang_uses_bounded_infrastructure_recovery(message):
    assert failure_kind(message)=='gpu_service'


@pytest.mark.parametrize('message',[
    'libc++abi: terminating due to uncaught exception of type std::runtime_error: invalid configuration',
    'SIGABRT (exit -6)',
    '[METAL] Command buffer execution failed: invalid resource',
])
def test_unrelated_native_abort_is_not_assumed_to_be_gpu_hang(message):
    assert failure_kind(message)=='trial_failure'


def test_infrastructure_is_not_a_model_quality_failure():
    assert failure_kind('Unable to reach MTLCompilerService. Broken pipe')=='gpu_service'
    assert failure_kind('Unable to reach MTLCompilerService. Reentrancy avoided')=='gpu_service'
    assert failure_kind('Available RAM below 6 GiB')=='memory'
    assert failure_kind('Nonfinite objective or gradient')=='numerical_trial_failure'
    assert failure_kind('ValueError: invalid configuration')=='trial_failure'


def test_no_budget_reset_on_second_recovery():
    old=dict(budget_seconds=86400)
    spent,remaining=remaining_budget(old,{'elapsed_seconds':6666.1948},120)
    assert (spent,remaining)==(6787,79613)
    spent2,remaining2=remaining_budget(dict(budget_seconds=remaining,original_budget_seconds=86400),
                                      dict(elapsed_seconds=100,total_budget_spent_seconds=spent+100),0)
    assert remaining2==remaining-100
    assert retry_seconds(360,35,1000)==325
    assert retry_seconds(360,35,40)==25
    assert retry_seconds(360,361,1000)==0


def test_longer_evaluation_caps_count_every_pending_stage_without_changing_original():
    original=dict(search_seconds=110,search_process_seconds=120,
                  confirmation_seconds=80,confirmation_process_seconds=90)
    limits=evaluation_limits(original,600)
    assert limits==dict(search_seconds=600,search_process_seconds=630,
                        confirmation_seconds=600,confirmation_process_seconds=630)
    assert original['search_seconds']==110
    assert evaluation_limits(original)==original
    plan=dict(limits,control_seconds=120,long_train_seconds=2100)
    jobs=[dict(id='saved',train_seconds=360),dict(id='pending',train_seconds=1200)]
    cap=remaining_stage_cap(plan,jobs,['saved'],[])
    assert cap==1200+630+630+120+20+4*(2100+2*630)+5*630
    assert remaining_stage_cap(plan,jobs,['saved'],['saved'])==cap-630


@pytest.mark.parametrize('seconds',[0,-1,float('nan'),float('inf')])
def test_invalid_evaluation_budget_rejected(seconds):
    with pytest.raises(ValueError,match='finite and positive'):
        evaluation_limits(dict(search_seconds=110,search_process_seconds=120,
                               confirmation_seconds=80,confirmation_process_seconds=90),seconds)


def test_evaluation_timeout_pauses_before_any_training(tmp_path,monkeypatch):
    import study.campaign as campaign
    run=tmp_path/'run';run.mkdir()
    write(run/'plan.json',dict(budget_seconds=2000,reuse_completed=True,
          parent=str(tmp_path/'parent'),control_seconds=30,search_seconds=600,
          search_process_seconds=630,jobs=['must-not-start'],deferred={}))
    write(run/'initial-inputs.json',{});write(run/'frozen-inputs.json',{})
    modules=[]
    class FakeProcess:
        pid=900
        def __init__(self,cmd,**kwargs):
            self.returncode=0
            if '--module' not in cmd:return
            module=cmd[cmd.index('--module')+1];modules.append(module)
            target=Path(cmd[cmd.index('--run')+1])
            if module=='study.trial':
                assert '--control-only' in cmd
                write(target/'control.json',{'passed':True})
            elif module=='slm.broad_eval':
                self.returncode=1
                output=Path(cmd[cmd.index('--output')+1])
                write(output/'protocol.json',{'partial':True})
                kwargs['stdout'].write('TimeoutError: Reference-loss evaluation exceeded deadline\n')
        def poll(self):return self.returncode
        def wait(self,timeout=None):return self.returncode
        def terminate(self):self.returncode=-15
        def kill(self):self.returncode=-9
    monkeypatch.setattr(campaign.subprocess,'Popen',FakeProcess)
    monkeypatch.setattr(campaign.time,'sleep',lambda _:None)
    monkeypatch.setattr(campaign.signal,'signal',lambda *a:None)
    monkeypatch.setattr(sys,'argv',['study.campaign','--run',str(run)])
    with pytest.raises(SystemExit):campaign.main()
    state=read(run/'status.json')
    assert state['status']=='paused_infrastructure'
    assert state['stages'][-1]['failure_kind']=='evaluation_timeout'
    assert state.get('gpu_recovery_attempts',0)==0
    assert modules==['study.health','study.trial','slm.broad_eval']
    assert (run/'STOP').exists() and (run/'parent-search/protocol.json').exists()


def test_eval_retry_never_moves_parent_weights(tmp_path):
    parent=tmp_path/'historical-parent';parent.mkdir();(parent/'model').write_text('weights')
    run=tmp_path/'new';out=run/'partial';out.mkdir(parents=True);(out/'results.jsonl').write_text('partial')
    archive=archive_failed_output(run,'slm.broad_eval',parent,['--output',str(out)],'job')
    assert (archive/'results.jsonl').exists() and (parent/'model').read_text()=='weights'
    with pytest.raises(RecoverableStop,match='outside'):
        archive_failed_output(run,'study.trial',parent,[],'job2')


def test_evaluation_reuse_requires_exact_model_suite_and_complete_rows(tmp_path):
    model=tmp_path/'model';out=tmp_path/'eval';model.mkdir();out.mkdir()
    write(model/'latest.json',{'checkpoint':'.'});(model/'model.safetensors').write_bytes(b'weights')
    (model/'tokenizer.json').write_bytes(b'tokenizer')
    suite=tmp_path/'suite.json';write(suite,{'general':[{}],'tokenizer_sha256':sha(model/'tokenizer.json')})
    write(out/'summary.json',dict(partition='dev',selected_general=1,evaluated_general=1,deadline_reached=False,
                                  answer_loss={'examples':1,'macro_source_answer_loss':1},mean_source_accuracy_by_family={'f':.5}))
    write(out/'protocol.json',dict(partition='dev',suite_sha256=sha(suite),checkpoint_sha256=sha(model/'model.safetensors')))
    (out/'results.jsonl').write_text('{}\n')
    assert valid_evaluation(out,model,suite)
    (model/'model.safetensors').write_bytes(b'changed')
    assert not valid_evaluation(out,model,suite)


@pytest.mark.parametrize('probe_fails',[False,True])
@pytest.mark.parametrize('error,exit_code',[
    ('Unable to reach MTLCompilerService',1),
    (GPU_HANG,-6),
])
def test_real_supervisor_stops_cascade_and_preserves_pending_work(tmp_path,monkeypatch,probe_fails,error,exit_code):
    import study.campaign as campaign
    from study.design import BASE
    run=tmp_path/'run';run.mkdir()
    plan=dict(budget_seconds=1000,reuse_completed=True,previous_budget_spent_seconds=10,
              parent=str(tmp_path/'parent'),control_seconds=30,search_seconds=10,search_process_seconds=20,
              confirmation_seconds=10,confirmation_process_seconds=20,jobs=['first','second'],deferred={})
    write(run/'plan.json',plan);write(run/'initial-inputs.json',{});write(run/'frozen-inputs.json',{})
    for name in plan['jobs']:
        write(run/'jobs'/(name+'.json'),dict(id=name,parameters=BASE,train_seconds=100,target_tokens=100))
    modules=[];trial_calls=[]
    class FakeProcess:
        pid=900
        def __init__(self,cmd,**kwargs):
            self.returncode=0
            if '--module' not in cmd:return
            module=cmd[cmd.index('--module')+1];target=Path(cmd[cmd.index('--run')+1]);modules.append(module)
            if module=='study.health' and 'health-recovery' in str(target) and probe_fails:
                self.returncode=exit_code;kwargs['stdout'].write(error+'\n')
            elif module=='study.trial' and '--control-only' in cmd:
                write(target/'control.json',{'passed':True})
            elif module=='slm.broad_eval':
                output=Path(cmd[cmd.index('--output')+1])
                write(output/'summary.json',dict(selected_general=1,evaluated_general=1,deadline_reached=False,
                      answer_loss={'examples':1,'macro_source_answer_loss':1},mean_source_accuracy_by_family={'f':.5}))
            elif module=='study.trial':
                trial_calls.append(cmd);target.mkdir(parents=True,exist_ok=True)
                (target/'partial').write_text('failed attempt retained')
                self.returncode=exit_code;kwargs['stdout'].write(error+'\n')
        def poll(self):return self.returncode
        def wait(self,timeout=None):return self.returncode
        def terminate(self):self.returncode=-15
        def kill(self):self.returncode=-9
    monkeypatch.setattr(campaign.subprocess,'Popen',FakeProcess)
    monkeypatch.setattr(campaign.time,'sleep',lambda _:None)
    monkeypatch.setattr(campaign.signal,'signal',lambda *a:None)
    monkeypatch.setattr(sys,'argv',['study.campaign','--run',str(run)])
    with pytest.raises(SystemExit):campaign.main()
    assert read(run/'status.json')['status']=='paused_infrastructure'
    failed=[s for s in read(run/'status.json')['stages'] if s['status']=='failed']
    assert all(s['failure_kind']=='gpu_service' and s['exit_code']==exit_code for s in failed)
    assert (run/'STOP').exists()
    assert len(trial_calls)==(1 if probe_fails else 2)
    assert all('first.json' in cmd[cmd.index('--job')+1] for cmd in trial_calls)
    if not probe_fails:
        assert '--wall-seconds' in trial_calls[1]
        assert (run/'attempts/first/output/partial').exists()
