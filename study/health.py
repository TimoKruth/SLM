"""Small bounded GPU probe. No project model or optimizer state is changed."""
import argparse
import math
from pathlib import Path
import time
from research.common import write


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True)
    parser.add_argument('--seconds',type=float,default=5);args=parser.parse_args()
    if not 0<args.seconds<=30:raise ValueError('Health probe must be bounded to <=30 seconds')
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    from slm.model import LanguageModel,ModelConfig
    from slm.optimization import make_training_step
    mx.set_default_device(mx.gpu);mx.set_memory_limit(1024**3);mx.set_cache_limit(64*1024**2)
    started=time.monotonic();checks=[];iterations=0
    try:
        mx.random.seed(21)
        for dtype in [mx.float32,mx.bfloat16]:
            a=mx.random.normal((64,64)).astype(dtype);b=a@a.T
            value=float(mx.mean(b.astype(mx.float32)).item())
            if not math.isfinite(value):raise FloatingPointError('Nonfinite GPU matrix result')
            checks.append(str(dtype))
        model=LanguageModel(ModelConfig(vocab_size=64,dim=32,layers=1,heads=4,hidden=64,context=32))
        opt=optim.AdamW(3e-5,bias_correction=True);update=make_training_step(model,opt)
        while iterations<2 or time.monotonic()-started<args.seconds:
            x=mx.random.randint(0,64,(2,32));y=mx.random.randint(0,64,(2,32))
            loss,norm=update(x,y,mx.ones((2,32)),mx.array(3e-5))
            mx.eval(model.parameters(),opt.state,loss,norm)
            if not math.isfinite(float(loss.item())):raise FloatingPointError('Nonfinite compiled update')
            # Different inference lengths exercise the compiler path that failed historically.
            length=3+iterations%27
            value=float(mx.mean(model(x[:,:length])).item())
            if not math.isfinite(value):raise FloatingPointError('Nonfinite inference')
            iterations+=1
        write(Path(args.run)/'health.json',dict(passed=True,checks=checks,iterations=iterations,
              elapsed_seconds=time.monotonic()-started,device=mx.metal.device_info()['device_name']))
    except BaseException as exc:
        write(Path(args.run)/'health.json',dict(passed=False,error=repr(exc),checks=checks,iterations=iterations,
              elapsed_seconds=time.monotonic()-started));raise


if __name__=='__main__':main()
