"""GPU checkpoint-resume validation for the isolated mixed-precision candidate."""
import json
from pathlib import Path
import numpy as np
import mlx.core as mx
from mlx.utils import tree_flatten
from next_run.performance import MixedModel
from next_run.prepare import ROOT
from slm.model import ModelConfig
from slm.data import Sampler
from slm.train import checkpoint, restore
from experiments.performance.variants import make_training_step

def validate(out):
    src=ROOT/'runs/size-27m-2026-09-08-3h';cfg=json.loads((src/'config.json').read_text())
    saved=src/json.loads((src/'latest.json').read_text())['checkpoint']/'model.safetensors'
    mx.set_default_device(mx.gpu);mx.set_memory_limit(12*1024**3);mx.set_cache_limit(512*1024**2)
    def make():
        m=MixedModel(ModelConfig(**cfg['model']));m.load_weights(str(saved))
        fn,opt,state=make_training_step(m,compiled=True)
        sampler=Sampler(ROOT/cfg['data'],seed=991,context=1024)
        return m,fn,opt,state,sampler
    def step(fn,state,sampler,i):
        b=sampler.batch(2);x,y,mask=[mx.array(v) for v in b[:3]]
        loss,norm=fn(x,y,mask,mx.array(3e-5));mx.eval(state,loss,norm)
        return float(loss.item())
    m,fn,opt,state,s=make();a=[step(fn,state,s,i) for i in range(12)]
    expected=dict(tree_flatten([m.parameters(),opt.state]));expected={k:np.array(v) for k,v in expected.items()};rng=s.rng.bit_generator.state
    m,fn,opt,state,s=make();b=[step(fn,state,s,i) for i in range(6)]
    folder=out/'resume-check';folder.mkdir(exist_ok=False)
    checkpoint(folder,m,opt,s,dict(step=6,tokens=0))
    m,fn,opt,state,s=make();restored=restore(folder,m,opt,s)
    # restore replaces optimizer state, so rebuild the compiled capture over restored state.
    import mlx.nn as nn
    import mlx.optimizers as optim
    from slm.model import loss_fn
    state=[m.state,opt.state];grad=nn.value_and_grad(m,loss_fn)
    def resumed_update(x,y,mask,lr):
        opt.learning_rate=lr;loss,g=grad(m,x,y,mask);g,n=optim.clip_grad_norm(g,1.);opt.update(m,g);return loss,n
    fn=mx.compile(resumed_update,inputs=state,outputs=state)
    b += [step(fn,state,s,i) for i in range(6,12)]
    actual={k:np.array(v) for k,v in tree_flatten([m.parameters(),opt.state])}
    passed=all(np.allclose(actual[k],v,rtol=5e-4,atol=2e-5) for k,v in expected.items())
    result=dict(status='passed' if passed else 'failed',arrays=len(expected),weights_and_optimizer_close=passed,
        losses_close=bool(np.allclose(a,b,rtol=2e-5,atol=2e-6)),sampler_state_identical=rng==s.rng.bit_generator.state,
        max_absolute_difference=max(float(np.max(np.abs(actual[k]-v))) for k,v in expected.items()),steps=12,split=6,
        master_parameter_dtypes=sorted({str(v.dtype) for _,v in tree_flatten(m.parameters())}),rtol=5e-4,atol=2e-5)
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    assert passed and result['losses_close'] and result['sampler_state_identical']
