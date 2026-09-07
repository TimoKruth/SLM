from datetime import datetime,timedelta
import json
import sys
import pytest


def test_gpu_benchmark_refuses_live_training(monkeypatch,tmp_path):
    from experiments.performance import benchmark
    monkeypatch.setattr(benchmark,'active_slm_jobs',lambda:[123])
    monkeypatch.setattr(sys,'argv',['benchmark','--run',str(tmp_path),'--output',str(tmp_path/'out')])
    with pytest.raises(RuntimeError,match='Live SLM'):benchmark.main()
    assert not (tmp_path/'out').exists()


def test_changed_source_cancels_deferred_benchmark(monkeypatch,tmp_path):
    from experiments.performance import after_run
    run=tmp_path/'run';out=tmp_path/'out';run.mkdir();out.mkdir()
    (run/'status.json').write_text(json.dumps({'status':'completed'}));(run/'supervisor.json').write_text(json.dumps({'phase':'finished'}))
    (tmp_path/'code.py').write_text('changed')
    (out/'plan.json').write_text(json.dumps({'queue_deadline':(datetime.now().astimezone()+timedelta(hours=1)).isoformat(),'source_sha256':{'code.py':'original'}}))
    monkeypatch.setattr(after_run,'ROOT',tmp_path);monkeypatch.setattr(after_run,'RUN',run);monkeypatch.setattr(after_run,'OUT',out);monkeypatch.setattr(after_run,'active_slm_jobs',lambda:[])
    after_run.main()
    assert json.loads((out/'status.json').read_text())['status']=='skipped_source_changed'


def test_expired_queue_does_not_launch(monkeypatch,tmp_path):
    from experiments.performance import after_run
    out=tmp_path/'out';out.mkdir();(out/'plan.json').write_text(json.dumps({'queue_deadline':(datetime.now().astimezone()-timedelta(seconds=1)).isoformat(),'source_sha256':{}}))
    monkeypatch.setattr(after_run,'OUT',out)
    after_run.main()
    assert json.loads((out/'status.json').read_text())['status']=='expired_without_gpu_benchmark'
