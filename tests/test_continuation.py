import json
import pytest
from experiments.continuation_report import work_delta


def test_continuation_counts_only_added_work():
    old=dict(step=10,tokens=100,source_tokens={'a':60,'b':40})
    new=dict(step=20,tokens=150,source_tokens={'a':80,'b':70})
    assert work_delta(old,new)==dict(step=10,tokens=50,source_tokens={'a':20,'b':30})
    with pytest.raises(ValueError):work_delta(new,old)
    with pytest.raises(ValueError):work_delta(old,{**new,'tokens':151})


def test_report_keeps_three_and_six_hour_results_separate(tmp_path,monkeypatch):
    from experiments import continuation_report as mod
    monkeypatch.setattr(mod,'__file__',str(tmp_path/'experiments/continuation_report.py'))
    def write(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj))
    write(tmp_path/'prep/audit.json',{'majority':{}});write(tmp_path/'prep/wikisql-tables.json',{})
    comparisons=[]
    for name in ['27m','97m']:
        parent=tmp_path/(name+'-parent');run=tmp_path/name
        cfg={k:1 for k in ['model','seed','batch_size','context','schedule_tokens','snapshot_tokens','max_tokens','execution','dtype','manifest_sha256','source_weights_by_sequence','parameters']}
        for folder,tokens in [(parent,100),(run,150)]:
            write(folder/'config.json',cfg);write(folder/'checkpoint/state.json',dict(step=tokens,tokens=tokens,source_tokens={'snli':tokens},signature=name))
        write(run/'parent.json',{'parent_checkpoint':'checkpoint'});write(run/'latest.json',{'checkpoint':'checkpoint'});write(run/'RUN_CONDITIONS.json',{})
        (run/'metrics.jsonl').write_text('')
        comparisons.append(dict(name=name,parent=parent.name,run=run.name))
    def fake(run,*args):
        before=run.name.endswith('parent');n=2 if before else 3
        summary=dict(by_source={'snli':{'correct':n,'scored':4}},answer_loss={'macro_source_answer_loss':2 if before else 1},mean_source_accuracy_by_family={'entailment':n/4},code_passes_with_stronger_tests=0)
        return dict(summary=summary,wikisql_execution_proxy=[],token_limits=0)
    monkeypatch.setattr(mod,'details',fake)
    out=tmp_path/'report';out.mkdir();mod.report(dict(evaluation_preparation='prep',comparisons=comparisons,protocol={}),out,{'jobs':{}})
    result=json.loads((out/'comparison.json').read_text())
    assert result['runs'][0]['added_work']['tokens']==50
    assert result['runs'][0]['additional_correct']==1
    assert '2/4 → 3/4' in (out/'REPORT.md').read_text()
