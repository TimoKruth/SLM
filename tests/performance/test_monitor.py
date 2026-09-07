import ast
import json
from pathlib import Path
import types

import pytest
from slm_perf.runtime import Monitor
from slm_perf.instrument import transformed, MODULES, ROOT
from slm_perf.report import comparison


def test_nested_spans_account_without_double_counting(tmp_path):
    now=[0]
    m=Monitor(tmp_path,clock=lambda:now[0])
    with m.span('root'):
        now[0]+=10
        with m.span('child'):now[0]+=20
        now[0]+=30
    data=m.result('completed')
    assert data['phases']['root']['inclusive_seconds']==60/1e9
    assert data['phases']['root']['self_seconds']==40/1e9
    assert data['phases']['root/child']['self_seconds']==20/1e9
    assert sum(v['self_seconds'] for v in data['phases'].values())==pytest.approx(60/1e9)


def test_exception_propagates_and_records_elapsed(tmp_path):
    m=Monitor(tmp_path)
    with pytest.raises(ValueError,match='original'):
        with m.span('failure'):raise ValueError('original')
    assert not m.stack
    assert m.result('failed')['phases']['failure']['count']==1


def test_write_failure_disables_measurement_without_failing_workload(tmp_path,monkeypatch):
    m=Monitor(tmp_path,flush_seconds=.000001)
    def fail(*args,**kwargs):raise OSError('disk unavailable')
    monkeypatch.setattr(Path,'write_text',fail)
    m.flush('running')
    assert m.disabled
    assert m.call('work',lambda:42)==42
    assert m.errors


def test_transform_preserves_control_flow_returns_and_arguments(tmp_path):
    source='''
def main(value):
    """Keep docs."""
    try:
        if value < 0: raise ValueError(value)
        return value + 7
    finally:
        cleanup.append(value)
'''
    m=Monitor(tmp_path)
    code,_=transformed(source,'fixture.py','fixture')
    ns={'_slm_perf':m,'cleanup':[]}
    exec(code,ns)
    assert ns['main'].__doc__=='Keep docs.'
    assert ns['main'](2)==9
    with pytest.raises(ValueError):ns['main'](-1)
    assert ns['cleanup']==[2,-1]
    assert m.result('completed')['phases']['fixture.main']['count']==2


def test_all_supported_sources_compile_without_execution():
    for name in MODULES:
        path=ROOT/(name.replace('.','/')+'.py')
        if path.exists():transformed(path.read_text(),str(path),name)


def test_histograms_and_trace_memory_are_bounded(tmp_path):
    m=Monitor(tmp_path,mode='detail');m.max_trace_events=10;m.start_detail()
    for _ in range(100):
        with m.span('same'):pass
    m.finish()
    assert len(m.trace)<=10 and m.trace_dropped==90
    assert len(m.stats)==1
    assert m.stats['same'].percentile(.95)<=m.stats['same'].maximum/1e9
    assert (tmp_path/'python-functions.json').exists()


def test_warmup_excluded_from_steady_phase(tmp_path):
    m=Monitor(tmp_path,warmup_steps=2)
    for _ in range(5):
        with m.span('slm.train.main.step'):pass
    assert m.stats['slm.train.main.step.warmup'].count==2
    assert m.stats['slm.train.main.step.steady'].count==3


def test_compare_rejects_different_data_and_mode(tmp_path):
    m=Monitor(tmp_path)
    m.metadata={'workload':{'manifest':'a'},'environment':{'machine':'x'}}
    a=m.result('completed');b=json.loads(json.dumps(a))
    b['metadata']['workload']['manifest']='b';b['mode']='detail'
    out=comparison(a,b)
    assert not out['comparable']
    assert set(out['mismatches'])=={'mode','metadata.workload'}


def test_active_job_guard_before_output_or_mlx_import(tmp_path,monkeypatch):
    from slm_perf import __main__ as cli
    monkeypatch.setattr(cli,'active_jobs',lambda:[123])
    args=types.SimpleNamespace(module='slm.train',mode='light',output=str(tmp_path/'never'))
    with pytest.raises(RuntimeError,match='active'):cli.launch(args)
    assert not (tmp_path/'never').exists()


def test_off_executes_original_entry_point(tmp_path,monkeypatch):
    from slm_perf import __main__ as cli
    monkeypatch.setattr(cli,'active_jobs',lambda:[])
    seen=[]
    def execute(*args):seen.append(args);raise SystemExit(0)
    monkeypatch.setattr(cli.os,'execv',execute)
    args=types.SimpleNamespace(module='slm.train',mode='off',target=['--','--run','example'])
    with pytest.raises(SystemExit):cli.launch(args)
    assert seen[0][1][1:]==['-m','slm.train','--run','example']
    assert not list(tmp_path.iterdir())
