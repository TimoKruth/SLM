"""CPU-only scientific/control tests for the 24h study. No performance measurements."""
import copy
import numpy as np
import pytest
import mlx.core as mx
import mlx.optimizers as optim
from mlx.utils import tree_flatten
from study.design import BASE,designs,plan_budget,validate,lr_at
from study.trial import mask_of,make_step
from study.report import factorial
from study.campaign import exposure_key
from slm.model import LanguageModel,ModelConfig
from slm.optimization import make_training_step
from slm.breadth import FAMILIES


@pytest.fixture(autouse=True)
def cpu():
    old=mx.default_device();mx.set_default_device(mx.cpu)
    yield
    mx.set_default_device(old)


def tiny():
    mx.random.seed(91)
    return LanguageModel(ModelConfig(vocab_size=32,dim=16,layers=1,heads=2,hidden=32,context=8))


def assert_close(a,b):
    aa,bb=dict(tree_flatten(a)),dict(tree_flatten(b))
    assert aa.keys()==bb.keys()
    for k in aa:np.testing.assert_allclose(np.array(aa[k]),np.array(bb[k]),rtol=5e-4,atol=3e-6,err_msg=k)


@pytest.mark.parametrize('prompt,answer',[(1.,1.),(1.,.5),(0.,1.),(1.,4.)])
def test_accumulation_matches_single_batch_with_unequal_token_counts(prompt,answer):
    a,b=tiny(),tiny()
    oa,ob=[optim.AdamW(3e-5,betas=[.9,.95],weight_decay=.1,bias_correction=True) for _ in range(2)]
    pa={**BASE,'execution':'eager','prompt_weight':prompt,'answer_weight':answer}
    pb={**pa,'microbatch':1,'accumulation':2}
    fa,fb=make_step(a,oa,pa),make_step(b,ob,pb)
    x=mx.array([[1,2,3,4],[2,3,0,0]]);y=mx.array([[2,3,4,5],[3,4,0,0]])
    real=np.array([[1.,1.,1.,1.],[1.,1.,0.,0.]],dtype=np.float32)
    answer_mask=np.array([[0.,0.,1.,1.],[0.,1.,1.,1.]],dtype=np.float32)
    mask=mx.array(mask_of(real,answer_mask,pa))
    for _ in range(3):
        la,na=fa(x,y,mask,mx.array(3e-5));lb,nb=fb(x,y,mask,mx.array(3e-5))
        mx.eval(a.parameters(),b.parameters(),oa.state,ob.state,la,lb)
        np.testing.assert_allclose(np.array(la),np.array(lb),rtol=1e-5,atol=1e-6)
    assert_close([a.parameters(),oa.state],[b.parameters(),ob.state])


def test_default_step_matches_production():
    a,b=tiny(),tiny();oa,ob=[optim.AdamW(3e-5,betas=[.9,.95],weight_decay=.1,bias_correction=True) for _ in range(2)]
    fa=make_training_step(a,oa,compiled=False);fb=make_step(b,ob,{**BASE,'execution':'eager'})
    x=mx.array([[1,2],[2,3]]);y=mx.array([[2,3],[3,4]]);mask=mx.ones((2,2))
    for _ in range(2):
        la,_=fa(x,y,mask,mx.array(3e-5));lb,_=fb(x,y,mask,mx.array(3e-5))
        mx.eval(a.parameters(),b.parameters(),oa.state,ob.state,la,lb)
    assert_close([a.parameters(),oa.state],[b.parameters(),ob.state])


def test_finite_space_budget_and_valid_levels():
    groups=designs(FAMILIES)
    assert {k:len(v) for k,v in groups.items()}=={'adaptation':37,'cold':12,'interaction':8}
    assert plan_budget(groups)==85530<86400
    for values in groups.values():
        assert len({v['name'] for v in values})==len(values)
        for v in values:validate(v['parameters'])
    with pytest.raises(ValueError,match='Architecture'):
        validate({**BASE,'model':{**BASE['model'],'layers':8}})


def test_schedule_and_context_controls():
    assert lr_at(BASE,0,1000,0)==BASE['lr']
    p={**BASE,'schedule':'cosine'}
    assert lr_at(p,1000,1000,0)==pytest.approx(BASE['lr']*.1)
    assert lr_at({**BASE,'warmup_steps':100},0,1000,0)==pytest.approx(BASE['lr']/100)
    p={**BASE,'train_context':512}
    with pytest.raises(ValueError,match='eligible'):validate(p)


def test_factorial_recovers_interaction_without_claiming_independence():
    configurations=designs(FAMILIES)['interaction'];rows={}
    for repeat in range(2):
        for c in configurations:
            p=c['parameters'];a=1 if p['lr']==3e-5 else -1;b=1 if p['answer_weight']==2 else -1
            q=.5+.02*a+.03*b+.04*a*b
            key=f'{repeat}-{c["name"]}'
            rows[key]=dict(job={**c,'phase':'interaction','repetition':repeat},quality={'accuracy':q})
    r=factorial(rows)
    assert r['effects']['lr']['mean']==pytest.approx(.04)
    assert r['effects']['lr x answer_weight']['mean']==pytest.approx(.16)
    rows.pop(next(iter(rows)))
    assert factorial(rows)['status']=='incomplete'


def test_exposure_groups_only_compare_identical_sampling_setups():
    j=dict(phase='adaptation',repetition=0,target_tokens=1500000,parameters=BASE)
    assert exposure_key(j)==exposure_key({**j,'parameters':{**BASE,'lr':1e-5,'precision':'bf16'}})
    assert exposure_key(j)==exposure_key({**j,'parameters':{**BASE,'microbatch':1,'accumulation':2}})
    assert exposure_key(j)!=exposure_key({**j,'parameters':{**BASE,'mixture':'sources'}})


def test_campaign_refuses_budget_reset_before_any_child_launch(tmp_path,monkeypatch):
    from study.campaign import main
    from research.common import write
    import sys
    write(tmp_path/'plan.json',{})
    write(tmp_path/'status.json',{'status':'stopped'})
    monkeypatch.setattr(sys,'argv',['study.campaign','--run',str(tmp_path)])
    with pytest.raises(ValueError,match='budget cannot reset'):main()
