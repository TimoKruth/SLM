"""No-GPU tests for admission, immutable plans and stop/deadline handling."""
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
import pytest
from slm import campaign


def test_changed_frozen_input_stops_before_launch(tmp_path,monkeypatch):
    f=tmp_path/'source.py'
    f.write_text('original')
    monkeypatch.setattr(campaign,'ROOT',tmp_path)
    plan={'sha256':{'source.py':campaign.digest(f)},'jobs':[]}
    campaign.validate_plan(plan)
    f.write_text('changed')
    with pytest.raises(ValueError,match='changed'):
        campaign.validate_plan(plan)


def test_stop_and_deadline_do_not_launch_new_work(tmp_path,monkeypatch):
    child=Mock()
    child.poll.return_value=None
    monkeypatch.setattr(campaign,'shutdown',15)
    with pytest.raises(InterruptedError):
        campaign.wait_child(child,tmp_path,float('inf'))
    monkeypatch.setattr(campaign,'shutdown',None)
    with pytest.raises(TimeoutError):
        campaign.wait_child(child,tmp_path,0)


def test_busy_gpu_wait_has_admission_deadline(tmp_path,monkeypatch):
    from slm_perf import __main__ as cli
    monkeypatch.setattr(cli,'active_jobs',lambda:[123])
    job={'name':'train','admission_until':(datetime.now().astimezone()-timedelta(seconds=1)).isoformat()}
    with pytest.raises(TimeoutError,match='admission'):
        campaign.run_job(job,tmp_path,{'jobs':{}})


def test_idle_gpu_still_honors_stop_and_admission(tmp_path,monkeypatch):
    from slm_perf import __main__ as cli
    monkeypatch.setattr(cli,'active_jobs',lambda:[])
    monkeypatch.setattr(campaign,'shutdown',None)
    job={'name':'train','admission_until':(datetime.now().astimezone()-timedelta(seconds=1)).isoformat()}
    with pytest.raises(TimeoutError,match='admission'):
        campaign.run_job(job,tmp_path,{'jobs':{}})
    (tmp_path/'STOP').touch()
    with pytest.raises(InterruptedError):
        campaign.run_job(job,tmp_path,{'jobs':{}})
