import json
from pathlib import Path
import pytest


def test_token_schedule_is_independent_of_wall_clock():
    from slm.train import schedule_fraction
    assert schedule_fraction(20,1000,0,100,10,100)==schedule_fraction(20,1000,0,100,90,100)==.2
    assert schedule_fraction(200,1000,0,100,10,100)==1
    assert schedule_fraction(20,1000,0,100,90)==.9


def test_token_snapshots_survive_normal_checkpoint_cleanup_and_do_not_overwrite(tmp_path):
    from slm.train import token_snapshots
    class Model:
        def __init__(self):self.saves=0
        def save_weights(self,path):self.saves+=1;Path(path).write_bytes(b'weights')
    model=Model();(tmp_path/'config.json').write_text('{}');(tmp_path/'tokenizer.json').write_text('{}')
    state={'tokens':9,'step':1}
    token_snapshots(tmp_path,model,state,[10,20]);assert model.saves==0
    state.update(tokens=11,step=2)
    token_snapshots(tmp_path,model,state,[10,20]);assert model.saves==1
    snapshot=tmp_path/'token-000000010'
    assert json.loads((snapshot/'snapshot.json').read_text())['tokens']==11
    assert not list(snapshot.glob('*optimizer*'))
    state.update(tokens=21,step=3)
    token_snapshots(tmp_path,model,state,[10,20]);assert model.saves==2
    # A resume from an older optimizer checkpoint must not overwrite completed snapshots.
    token_snapshots(tmp_path,model,{'tokens':21,'step':3},[10,20]);assert model.saves==2
    assert json.loads((snapshot/'snapshot.json').read_text())['step']==2


def test_reference_loss_masks_question_and_matches_training_answer_targets():
    import time
    import numpy as np
    import mlx.core as mx
    from types import SimpleNamespace
    from slm.broad_eval import reference_loss
    class Tokenizer:
        def token_to_id(self,value):return 2
        def encode(self,text):return SimpleNamespace(ids=[0,1,2,3,4])
    class Model:
        config=SimpleNamespace(context=5)
        def __call__(self,x):
            logits=np.zeros((1,4,5),dtype=np.float32)
            # Wrong predictions on question positions; confident correct answer targets.
            logits[0,0,0]=20;logits[0,1,0]=20
            logits[0,2,3]=20;logits[0,3,4]=20
            return mx.array(logits)
    row=dict(source='boolq',original_id='x',prompt='Question',answer='yes')
    with mx.stream(mx.cpu):
        result=reference_loss(Model(),Tokenizer(),[row],time.time()+30)
    assert result['source_answer_loss']['boolq']<1e-5
    with pytest.raises(TimeoutError):reference_loss(Model(),Tokenizer(),[row],time.time()-1)


def test_missing_token_snapshot_is_skipped_without_launch(tmp_path,monkeypatch):
    from slm import campaign
    monkeypatch.setattr(campaign,'ROOT',tmp_path)
    progress={'jobs':{}}
    campaign.run_job({'name':'optional','run':'absent','optional_snapshot':True},tmp_path,progress)
    assert progress['jobs']['optional']['status']=='skipped'


@pytest.mark.parametrize('different_data',[False,True])
def test_size_report_checks_comparability_and_train_only_baseline(tmp_path,monkeypatch,different_data):
    from experiments import size_report
    monkeypatch.setattr(size_report,'__file__',str(tmp_path/'experiments/size_report.py'))
    def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
    prep=tmp_path/'prep';write(prep/'audit.json',{'majority':{'boolq':'yes'}});write(prep/'wikisql-tables.json',{})
    summary={'mean_source_accuracy_by_family':{'reading_and_extraction':0},'answer_loss':{'family_answer_loss':{'reading_and_extraction':2}},'code_statuses':{},'code_passes_with_stronger_tests':0}
    plan={'evaluation_preparation':'prep','snapshot_tokens':[10],'protocol':{},'comparisons':[{'name':s,'run':s} for s in ['a','b']]}
    for name in ['a','b']:
        run=tmp_path/name
        write(run/'latest.json',{'checkpoint':'checkpoint-0000002'})
        state={'step':2,'tokens':11,'source_tokens':{'boolq':11}}
        write(run/'checkpoint-0000002/state.json',state)
        config={k:1 for k in ['manifest_sha256','source_weights_by_sequence','seed','batch_size','context','schedule_tokens','max_tokens','execution','dtype','parameters']}
        if different_data and name=='b':config['manifest_sha256']=2
        write(run/'config.json',config);write(run/'status.json',{'status':'completed'});write(run/'RUN_CONDITIONS.json',{})
        (run/'metrics.jsonl').write_text('{"event":"development"}\n')
        for evaluation in [run/'broad-eval',run/'token-000000010/evaluation']:
            write(evaluation/'summary.json',summary)
            (evaluation/'results.jsonl').write_text(json.dumps({'source':'boolq','expected':'no','generated':'yes','correct':False,'stop_reason':'special_token'})+'\n')
        write(run/'token-000000010/snapshot.json',state)
    out=tmp_path/'out';out.mkdir()
    if different_data:
        with pytest.raises(ValueError,match='inputs differ'):size_report.report(plan,out,{'jobs':{}})
    else:
        size_report.report(plan,out,{'jobs':{}})
        result=json.loads((out/'comparison.json').read_text())
        assert result['matched_tokens']['10']['identical_work']
        assert result['runs'][0]['final']['train_majority_baselines']['boolq']['baseline_correct']==0
        assert (out/'REPORT.md').exists()
