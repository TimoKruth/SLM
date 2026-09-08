"""Bounded batch/precision screening; FP32 master weights, unchanged production model."""
import argparse
import gc
import json
import statistics
import subprocess
import time
from datetime import datetime
from pathlib import Path
import numpy as np
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten
from slm.model import LanguageModel, ModelConfig, loss_fn
from slm.data import Sampler
from experiments.performance.variants import make_training_step
from next_run.prepare import ROOT, sha

from slm.precision import MixedModel


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--max-seconds',type=float,default=240);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    out=Path(a.run);out.mkdir(parents=True,exist_ok=True)
    if a.validate_only:
        from next_run.validate_precision import validate
        validate(out)
        return
    src=ROOT/'runs/size-27m-2026-09-08-3h';cfg=json.loads((src/'config.json').read_text())
    checkpoint=src/json.loads((src/'latest.json').read_text())['checkpoint']/'model.safetensors'
    conditions=dict(recorded_at=datetime.now().astimezone().isoformat(),power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),mode='User reduced-performance setting unchanged')
    (out/'RUN_CONDITIONS.json').write_text(json.dumps(conditions,indent=2))
    protocol=dict(variants=['fp32-b1','fp32-b2','fp32-b4','bf16-b2'],repeats=3,warmup_sequences=40,measured_sequences=80,
        precision_loss_rtol=.005,precision_loss_atol=.01,weight_relative_l2_limit=.005,
        order='Forward/reverse/forward',note='Batch variants see identical sequences but different optimizer update counts, so throughput only, not numerical equivalence. BF16 keeps FP32 master weights and optimizer. No automatic adoption.')
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2))
    mx.set_default_device(mx.gpu);mx.set_memory_limit(12*1024**3);mx.set_cache_limit(512*1024**2)
    s=Sampler(ROOT/cfg['data'],seed=20260908,context=1024)
    batches=[s.batch(1) for _ in range(120)]
    arrays=[np.concatenate([b[k] for b in batches],axis=0) for k in range(3)]
    actual_tokens=int(arrays[2][40:].sum());records=[];deadline=time.monotonic()+a.max_seconds
    baseline_weights=None;baseline_loss=None
    for repeat in range(3):
        variants=protocol['variants'] if repeat!=1 else list(reversed(protocol['variants']))
        for variant in variants:
            if time.monotonic()>=deadline:raise TimeoutError('Performance screening deadline')
            batch=int(variant[-1]);mixed=variant.startswith('bf16')
            m=(MixedModel if mixed else LanguageModel)(ModelConfig(**cfg['model']));m.load_weights(str(checkpoint))
            update,opt,state=make_training_step(m,compiled=True);mx.eval(state);mx.reset_peak_memory()
            losses=[];started=time.perf_counter()
            for offset in range(0,120,batch):
                if time.monotonic()>=deadline:raise TimeoutError('Performance screening deadline')
                if offset==40:warm=time.perf_counter()-started;started=time.perf_counter()
                x,y,mask=[mx.array(v[offset:offset+batch]) for v in arrays]
                loss,norm=update(x,y,mask,mx.array(3e-5));mx.eval(state,loss,norm)
                losses.append(float(loss.item()))
            elapsed=time.perf_counter()-started
            weights={k:np.array(v) for k,v in tree_flatten(m.parameters())}
            finite=all(np.isfinite(v).all() for v in weights.values()) and bool(np.isfinite(losses).all())
            rec=dict(variant=variant,repeat=repeat,seconds=elapsed,warmup_seconds=warm,tokens=actual_tokens,tokens_per_second=actual_tokens/elapsed,peak_bytes=mx.get_peak_memory(),finite=finite,losses=losses)
            if variant=='fp32-b2' and repeat==0:baseline_weights=weights;baseline_loss=losses
            if mixed:
                rec['loss_close']=bool(np.allclose(losses,baseline_loss,rtol=.005,atol=.01))
                rec['relative_weight_l2']=float(np.sqrt(sum(np.square(weights[k]-v,dtype=np.float64).sum() for k,v in baseline_weights.items())/sum(np.square(v,dtype=np.float64).sum() for v in baseline_weights.values())))
                rec['short_stability_gate']=finite and rec['loss_close'] and rec['relative_weight_l2']<.005
            records.append(rec);(out/'measurements.json').write_text(json.dumps(records,indent=2));print(variant,repeat,round(rec['tokens_per_second']),finite,flush=True)
            del m,opt,state,update,weights;gc.collect();mx.clear_cache()
    summary={v:dict(median_tokens_per_second=statistics.median(r['tokens_per_second'] for r in records if r['variant']==v),range_tokens_per_second=[min(r['tokens_per_second'] for r in records if r['variant']==v),max(r['tokens_per_second'] for r in records if r['variant']==v)]) for v in protocol['variants']}
    (out/'summary.json').write_text(json.dumps(dict(status='completed',results=summary,checkpoint_sha256=sha(checkpoint),precision_gate=all(r.get('short_stability_gate',True) for r in records),adopted=False,limitation='Short isolated screening only; no long-run quality or checkpoint-resume validation of mixed precision.'),indent=2)+'\n')

if __name__=='__main__':main()
