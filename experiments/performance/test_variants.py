import mlx.core as mx
import numpy as np
import pytest
from mlx.utils import tree_flatten
from slm.model import LanguageModel,ModelConfig
from experiments.performance.variants import cached_forward,tokens_greedy,make_training_step


@pytest.fixture(autouse=True)
def cpu_only():
    old=mx.default_device();mx.set_default_device(mx.cpu)
    yield
    mx.set_default_device(old)


def model():
    mx.random.seed(991)
    return LanguageModel(ModelConfig(vocab_size=128,dim=32,layers=2,heads=4,hidden=64,context=64))


def test_cached_prefill_and_chunked_logits_match_reference():
    m=model();ids=mx.array([[1,2,3,4,5,6,7,8]])
    expected=np.array(m(ids));a,cache=cached_forward(m,ids[:,:3]);b,cache=cached_forward(m,ids[:,3:6],cache);c,cache=cached_forward(m,ids[:,6:],cache)
    np.testing.assert_allclose(np.concatenate([np.array(a),np.array(b),np.array(c)],axis=1),expected,rtol=2e-5,atol=2e-6)
    assert cache[0][0].shape[2]==8


def test_greedy_cache_and_fresh_request_are_identical():
    m=model();a=tokens_greedy(m,[1,2,3,4],12);b=tokens_greedy(m,[1,2,3,4],12,cached=True)
    assert a==b
    assert tokens_greedy(m,[7,8],8)==tokens_greedy(m,[7,8],8,cached=True)


def test_cache_cannot_silently_roll_positions():
    m=model();_,c=cached_forward(m,mx.ones((1,63),dtype=mx.int32))
    with pytest.raises(ValueError):cached_forward(m,mx.ones((1,2),dtype=mx.int32),c)


def test_compilation_preserves_updates_and_learning_rate_changes():
    a,b=model(),model();fa,oa,sa=make_training_step(a);fb,ob,sb=make_training_step(b,compiled=True)
    for i in range(5):
        x=mx.array([[1,2+i,3,4]],dtype=mx.int32);y=mx.array([[2+i,3,4,5]],dtype=mx.int32);mask=mx.array([[1.,1.,1.,0.]])
        lr=mx.array(3e-4/(i+1));la,ga=fa(x,y,mask,lr);lb,gb=fb(x,y,mask,lr);mx.eval(sa,sb,la,lb,ga,gb)
        np.testing.assert_allclose(np.array(la),np.array(lb),rtol=1e-5,atol=1e-6)
    for (_,va),(_,vb) in zip(tree_flatten(a.parameters()),tree_flatten(b.parameters())):
        np.testing.assert_allclose(np.array(va),np.array(vb),rtol=3e-4,atol=2e-6)
    assert int(oa.step.item())==int(ob.step.item())==5
