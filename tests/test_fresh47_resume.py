"""CPU-only continuation admission and fake-child orchestration checks."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import pytest
import fresh47.resume as resume
from fresh47.prepare import sha


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat()


@pytest.fixture
def prepared(tmp_path):
    run=tmp_path/'run';run.mkdir();model=run/'model';model.mkdir()
    data=tmp_path/'data';data.mkdir()
    for split in ['dev','confirmation']:
        (data/f'{split}-suite.json').write_text('{"general":[{},{}]}')
    plan=dict(schema='fresh47.random.v1',source_count=47,initialization='random',parent_checkpoint=None,
              optimizer_initialization='new',forward_precision='fp32',total_seconds=86400,
              phase_seconds=dict(preflight=900,training=81000,evaluation=3600,report=900),
              automatic_retry=False,automatic_adoption=False,data=str(data),seed=20260916,schedule_tokens=200000000,
              model=dict(vocab_size=16384,dim=768,layers=12,heads=12,hidden=2048,context=1024),inputs={})
    now=time.time();started=iso(now-30000);deadline=iso(now+56400);until=iso(now+51000)
    (run/'plan.json').write_text(json.dumps(plan))
    (run/'status.json').write_text(json.dumps(dict(status='paused',phase='training',started=started,deadline=deadline,budget_spent_seconds=27000)))
    (run/'STOP').write_text('Paused')
    (model/'config.json').write_text(json.dumps(dict(until=until)))
    checkpoint='checkpoint-0088459';cp=model/checkpoint;cp.mkdir()
    for name in ['model.safetensors','optimizer.npz','state.json','model_config.json']:
        (cp/name).write_text('{}')
    (model/'latest.json').write_text(json.dumps(dict(checkpoint=checkpoint)))
    paths=['status.json','STOP','model/config.json','model/latest.json']+[str(p.relative_to(run)) for p in cp.iterdir()]
    request=run/'RESUME.json'
    request.write_text(json.dumps(dict(resume_authorized=True,plan_sha256=sha(run/'plan.json'),controller_sha256=sha(Path(resume.__file__)),
          resume_inputs={p:sha(run/p) for p in paths},original_started=started,deadline=deadline,training_until=until,checkpoint=checkpoint)))
    return run,plan,request


def test_preserves_absolute_budget_and_cutoff(prepared):
    run,plan,request=prepared
    auth,state,deadline,until=resume.continuation(run,plan,request)
    assert deadline-datetime.fromisoformat(state['started']).timestamp()==86400
    assert until==datetime.fromisoformat(auth['training_until']).timestamp()
    assert deadline-time.time()<56401
    with pytest.raises(ValueError,match='remaining training'):
        resume.continuation(run,plan,request,now=until)


@pytest.mark.parametrize('kind',['checkpoint','consumed','deadline','cutoff'])
def test_rejects_tamper_replay_or_extension(prepared,kind):
    run,plan,request=prepared
    auth=json.loads(request.read_text())
    if kind=='checkpoint':
        (run/'model'/auth['checkpoint']/'optimizer.npz').write_text('changed')
    elif kind=='consumed':request.with_suffix('.consumed.json').write_text('{}')
    else:
        auth['deadline' if kind=='deadline' else 'training_until']=iso(time.time()+200000)
        request.write_text(json.dumps(auth))
    with pytest.raises(ValueError):resume.continuation(run,plan,request)
    assert (run/'STOP').exists()


@pytest.mark.parametrize('failure',[None,'train','final-confirmation'])
def test_resume_pipeline_never_resets_budget_or_retries(prepared,monkeypatch,failure):
    run,plan,request=prepared
    original=json.loads((run/'status.json').read_text())
    auth=json.loads(request.read_text());calls=[]
    import slm_perf.__main__ as launcher
    import slm_perf.gpu_lease as leases
    class Lease:
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
        module=args[args.index('--module')+1];calls.append(args)
        if module=='slm.train':
            assert '--resume' in args
            assert args[args.index('--until')+1]==auth['training_until']
            (run/'model/status.json').write_text(json.dumps(dict(status='completed',reason='deadline',step=90000,tokens=170000000)))
            if failure=='train':child.returncode=1
        else:
            out=Path(args[args.index('--output')+1]);out.mkdir(parents=True)
            if out.name==failure:child.returncode=1;return child
            (out/'summary.json').write_text(json.dumps(dict(evaluated_general=2,answer_loss=dict(examples=2),deadline_reached=False,by_source={},mean_source_accuracy_by_family={})))
        return child
    monkeypatch.setattr(leases,'GPULease',Lease)
    monkeypatch.setattr(launcher,'active_jobs',lambda:[])
    monkeypatch.setattr(resume.subprocess,'Popen',popen)
    monkeypatch.setattr(resume.subprocess,'check_output',lambda *a,**k:'AC Power')
    import psutil,shutil
    from types import SimpleNamespace
    monkeypatch.setattr(psutil,'virtual_memory',lambda:SimpleNamespace(available=32*1024**3))
    monkeypatch.setattr(shutil,'disk_usage',lambda *a:SimpleNamespace(free=32*1024**3))
    monkeypatch.setattr(sys,'argv',['resume','--run',str(run),'--authorization',str(request)])
    if failure:
        with pytest.raises(RuntimeError,match='failed'):resume.main()
        assert (run/'STOP').exists() and not (run/'RESULT.json').exists()
    else:
        resume.main()
        assert json.loads((run/'RESULT.json').read_text())['inputs_unchanged']
        assert len(calls)==3
    current=json.loads((run/'status.json').read_text())
    assert current['deadline']==original['deadline'] and current['started']==original['started']
    assert current['budget_spent_seconds']>=30000
    assert request.with_suffix('.consumed.json').exists()
    assert request.with_suffix('.prior-stop.txt').exists()
    assert sum(a[a.index('--module')+1]=='slm.train' for a in calls)==1
