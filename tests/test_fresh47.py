from copy import deepcopy
import json
from pathlib import Path
import pytest

from fresh47.campaign import validate, authorized, train_args
from fresh47.prepare import sha


def plan():
    return dict(schema='fresh47.random.v1',source_count=47,initialization='random',parent_checkpoint=None,
                optimizer_initialization='new',forward_precision='fp32',total_seconds=21600,
                phase_seconds=dict(preflight=900,training=16200,evaluation=3600,report=900),
                automatic_retry=False,automatic_adoption=False,data='/new/data',seed=20260916,schedule_tokens=200000000,
                model=dict(vocab_size=16384,dim=512,layers=6,heads=8,hidden=1368,context=1024))


def test_preparation_stop_blocks_start_even_with_authorization(tmp_path):
    p=plan();(tmp_path/'plan.json').write_text(json.dumps(p));(tmp_path/'STOP').touch()
    (tmp_path/'AUTHORIZATION.json').write_text(json.dumps(dict(start_authorized=True)))
    with pytest.raises(ValueError,match='STOP'):authorized(tmp_path,p)


def test_missing_or_mismatched_authorization_cannot_start(tmp_path):
    p=plan();(tmp_path/'plan.json').write_text(json.dumps(p))
    with pytest.raises(ValueError,match='missing'):authorized(tmp_path,p)
    (tmp_path/'AUTHORIZATION.json').write_text(json.dumps(dict(start_authorized=True,plan_sha256='wrong')))
    with pytest.raises(ValueError,match='match'):authorized(tmp_path,p)


def test_fresh_command_has_no_resume_or_parent_and_preserves_cap():
    p=plan();validate(p);args=train_args(p,Path('/new/run'),'2030-01-01T00:00:00+00:00')
    assert '--resume' not in args and not any('checkpoint' in x for x in args if not x.startswith('--'))
    assert args[args.index('--data')+1]=='/new/data'
    assert args[args.index('--dim')+1]=='512'
    bad=deepcopy(p);bad['parent_checkpoint']='legacy'
    with pytest.raises(AssertionError):validate(bad)
    bad=deepcopy(p);bad['phase_seconds']['training']+=1
    with pytest.raises(AssertionError):validate(bad)


def test_existing_status_prevents_budget_reset(tmp_path):
    p=plan();(tmp_path/'plan.json').write_text(json.dumps(p))
    (tmp_path/'AUTHORIZATION.json').write_text(json.dumps(dict(start_authorized=True,plan_sha256=sha(tmp_path/'plan.json'))))
    authorized(tmp_path,p)
    (tmp_path/'status.json').write_text('{"status":"paused"}')
    with pytest.raises(ValueError,match='reset the budget'):authorized(tmp_path,p)


def test_launcher_accepts_fresh_supervisor_and_retains_monitoring():
    from run_slm import command
    from slm_perf.__main__ import SUPERVISOR_MODULES, GPU_MODULES
    from slm_perf.instrument import MODULES, transformed
    args=command(['--run','runs/fresh','--module','fresh47.campaign','--dry-run'])
    assert args[args.index('--mode')+1]=='light' and args[-1]=='--dry-run'
    assert 'fresh47.campaign' in MODULES & SUPERVISOR_MODULES
    assert 'fresh47.campaign' not in GPU_MODULES
    path=Path(__file__).resolve().parents[1]/'fresh47/campaign.py'
    transformed(path.read_text(),str(path),'fresh47.campaign')


@pytest.mark.parametrize('failed_phase',[None,'final-confirmation'])
def test_supervisor_completes_both_endpoints_or_pauses_without_retry(tmp_path,monkeypatch,failed_phase):
    """Exercise orchestration with fake children: no model, device or real subprocess."""
    import sys
    import fresh47.campaign as campaign
    import slm_perf.__main__ as launcher
    import slm_perf.gpu_lease as leases
    data=tmp_path/'data';data.mkdir()
    for split in ['dev','confirmation']:(data/f'{split}-suite.json').write_text('{"general":[{},{}]}')
    run=tmp_path/'run';run.mkdir();p=plan();p.update(data=str(data),inputs={})
    (run/'plan.json').write_text(json.dumps(p))
    (run/'AUTHORIZATION.json').write_text(json.dumps(dict(start_authorized=True,plan_sha256=sha(run/'plan.json'))))
    calls=[]
    class FakeLease:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def child_options(self):return {}
    class Child:
        pid=98765
        returncode=0
        def poll(self):return self.returncode
        def wait(self,**kwargs):return self.returncode
        def terminate(self):pass
    def popen(args,**kwargs):
        child=Child()
        if args[0]=='/usr/bin/caffeinate':return child
        module=args[args.index('--module')+1];calls.append(module)
        if module=='slm.train':
            folder=Path(args[args.index('--run')+1]);folder.mkdir()
            (folder/'status.json').write_text('{"status":"completed","reason":"deadline","tokens":100}')
        else:
            folder=Path(args[args.index('--output')+1]);folder.mkdir(parents=True)
            if folder.name==failed_phase:child.returncode=1;return child
            (folder/'summary.json').write_text(json.dumps(dict(evaluated_general=2,answer_loss=dict(examples=2),deadline_reached=False,by_source={},mean_source_accuracy_by_family={})))
        return child
    monkeypatch.setattr(leases,'GPULease',FakeLease)
    monkeypatch.setattr(launcher,'active_jobs',lambda:[])
    monkeypatch.setattr(campaign.subprocess,'Popen',popen)
    monkeypatch.setattr(campaign.subprocess,'check_output',lambda *a,**k:'AC Power')
    monkeypatch.setattr(campaign.signal,'signal',lambda *a:None)
    monkeypatch.setattr(sys,'argv',['campaign','--run',str(run)])
    if failed_phase:
        with pytest.raises(RuntimeError,match='failed'):campaign.main()
        assert (run/'STOP').exists() and not (run/'RESULT.json').exists()
    else:
        campaign.main()
        assert json.loads((run/'RESULT.json').read_text())['automatic_adoption'] is False
    status=json.loads((run/'status.json').read_text())
    assert status['status']==('paused' if failed_phase else 'completed')
    assert status['budget_spent_seconds']<p['total_seconds']
    assert calls==['slm.train','slm.broad_eval','slm.broad_eval']
