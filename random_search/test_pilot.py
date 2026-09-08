import json
from pathlib import Path
import pytest
from .pilot import split_tasks,encode_rows


def test_split_excludes_scitail_and_disjoins_groups():
    rows=[{'source':s,'group':s+str(i),'original_id':str(i)} for s in ['a','b','scitail'] for i in range(4)]
    a,b=split_tasks(rows)
    assert {r['source'] for r in a}=={'a','b'}
    assert not {r['group'] for r in a}&{r['group'] for r in b}
    assert split_tasks(list(reversed(rows)))==(a,b)


def test_missing_control_is_rejected():
    with pytest.raises(ValueError):split_tasks([{'source':'a','group':'a'}])


def test_masks_only_answer_targets():
    from tokenizers import Tokenizer,models,pre_tokenizers
    t=Tokenizer(models.WordLevel({'[UNK]':0},unk_token='[UNK]'))
    t.add_special_tokens(['<bos>','<question>','<answer>','<eos>']);t.pre_tokenizer=pre_tokenizers.Whitespace()
    row=dict(source='x',original_id='1',prompt='question text',answer='answer text')
    _,x,y,m=encode_rows([row],t,30)[0]
    assert m.shape==y.shape==x.shape and m.sum()>0 and (m==0).sum()>0
    assert all(m[0,i]==0 for i,v in enumerate(y[0]) if v==t.token_to_id('<answer>'))
    with pytest.raises(ValueError):encode_rows([row],t,2)


def test_pilot_uses_light_and_gpu_admission():
    from run_slm import command
    from slm_perf.__main__ import GPU_MODULES
    cmd=command(['--module','random_search.pilot','--run','runs/pilot'])
    assert cmd[cmd.index('--mode')+1]=='light'
    assert 'random_search.pilot' in GPU_MODULES


def test_real_selection_covers_all_valid_sources():
    from tokenizers import Tokenizer
    suite=Path('runs/eval-preparation-2026-09-07/after-campaign/suite-v2.json')
    if not suite.exists():pytest.skip('Local prepared dataset unavailable')
    rows=json.loads(suite.read_text())['general'];tok=Tokenizer.from_file('data/v3-broad/tokenizer.json')
    fitting=[]
    for row in rows:
        try:encode_rows([row],tok,1024);fitting.append(row)
        except ValueError:pass
    a,b=split_tasks(fitting)
    assert len(a)==len(b)==30
    assert not {r['group'] for r in a}&{r['group'] for r in b}


def test_seed_reproducibility_and_forward_preserves_weights():
    import time
    import numpy as np
    import mlx.core as mx
    from mlx.utils import tree_flatten
    from slm.model import ModelConfig
    from .pilot import fresh_model,teacher_score
    with mx.stream(mx.cpu):
        config=ModelConfig(vocab_size=16,dim=8,layers=1,heads=2,hidden=16,context=8)
        model,_=fresh_model(config,13)
        before={k:np.array(v) for k,v in tree_flatten(model.parameters())}
        x=np.array([[1,2,3]],dtype=np.int32);mask=np.ones_like(x,dtype=np.float32)
        result=teacher_score(model,[({'source':'s'},x,x,mask)],time.time()+30)
        assert np.isfinite(result['answer_loss'])
        assert all(np.array_equal(before[k],np.array(v)) for k,v in tree_flatten(model.parameters()))
        same,_=fresh_model(config,13)
        assert all(np.array_equal(before[k],np.array(v)) for k,v in tree_flatten(same.parameters()))
        other,_=fresh_model(config,14)
        assert any(not np.array_equal(before[k],np.array(v)) for k,v in tree_flatten(other.parameters()))
