import numpy as np
from next_run.analyze import repetition, flags
from next_run.prepare import ObservedTokens
from collections import Counter

def test_repetition_and_missing_correctness():
    assert repetition('red blue green yellow '*12)
    assert not repetition('A short useful answer.')
    assert flags({'generated':'abc','stop_reason':'special_token'})['unscored']

def test_exposure_records_only_consumed_slices():
    c=Counter();p=ObservedTokens(np.arange(20),c)
    np.testing.assert_equal(p[3:7],[3,4,5,6]);p[3:7]
    assert c=={3:2}

def test_mixed_master_parameters_and_gradients():
    import mlx.core as mx
    import mlx.nn as nn
    from mlx.utils import tree_flatten
    from next_run.performance import MixedModel
    from slm.model import LanguageModel,ModelConfig,loss_fn
    # CPU only: no interference with monitored GPU evaluations.
    with mx.stream(mx.cpu):
        cfg=ModelConfig(vocab_size=32,dim=16,layers=1,heads=2,hidden=32,context=8)
        mx.random.seed(1);base=LanguageModel(cfg);mixed=MixedModel(cfg)
        mixed.load_weights(tree_flatten(base.parameters()))
        x=mx.array([[1,2,3,4]],dtype=mx.int32);mask=mx.ones(x.shape)
        a=loss_fn(base,x,x,mask);b,g=nn.value_and_grad(mixed,loss_fn)(mixed,x,x,mask)
        mx.eval(a,b,g)
        assert abs(a.item()-b.item())<.02
        assert all(v.dtype==mx.float32 for _,v in tree_flatten(mixed.parameters()))
        assert all(v.dtype==mx.float32 and mx.all(mx.isfinite(v)).item() for _,v in tree_flatten(g))

def test_performance_launcher_monitored_and_locked():
    import run_slm
    from slm_perf.__main__ import GPU_MODULES
    from slm_perf.instrument import MODULES
    command=run_slm.command(['--run','runs/probe','--module','next_run.performance'])
    assert command[command.index('--mode')+1]=='light'
    assert 'next_run.performance' in GPU_MODULES & MODULES

def test_historical_fp32_signature_and_precision_resume_guard():
    from slm.train import training_signature
    args=({'dim':16},'abc',2,{'snli':1.0},42,100,[10])
    legacy='93b012761bf32e220d5394664613e07eac2bd469ba35c24b61a598081706baf9'
    assert training_signature(*args)==legacy
    assert training_signature(*args,forward_precision='fp32')==legacy
    assert training_signature(*args,forward_precision='bf16')!=legacy
