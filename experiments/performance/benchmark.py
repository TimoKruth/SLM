"""Bounded GPU benchmark. Refuses to compete with live SLM training/evaluation."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time
import psutil

ROOT=Path(__file__).resolve().parents[2]


def active_slm_jobs():
    found=[]
    for p in psutil.process_iter(['pid','cmdline']):
        try:
            args=p.info['cmdline'] or []
            if any(x in args for x in ['slm.train','slm.report','slm.code_eval','slm.interface_eval']):found.append(p.info['pid'])
        except (psutil.AccessDenied,psutil.NoSuchProcess):pass
    return found


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    if active_slm_jobs():raise RuntimeError('Live SLM GPU job present; benchmark refused')
    import mlx.core as mx
    import numpy as np
    from slm.model import LanguageModel,ModelConfig
    from slm.data import Sampler
    from experiments.performance.variants import make_training_step,tokens_greedy
    run=(ROOT/args.run).resolve();out=(ROOT/args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    config=json.loads((run/'config.json').read_text());checkpoint=run/'best.safetensors'
    mx.set_default_device(mx.gpu);mx.set_memory_limit(12*1024**3);mx.set_cache_limit(512*1024**2)
    def model():
        m=LanguageModel(ModelConfig(**config['model']));m.load_weights(str(checkpoint));mx.eval(m.parameters());return m
    sampler=Sampler(Path(config['data']),context=config['model']['context'],seed=719)
    batches=[sampler.batch(2) for _ in range(20)]
    actual_tokens=sum(int(b[2].sum()) for b in batches[5:])
    measured=[]
    # Alternate order to reduce warm-cache / temperature order effects.
    for repeat in range(3):
        for compiled in ([False,True] if repeat%2==0 else [True,False]):
            m=model();fn,opt,state=make_training_step(m,compiled=compiled)
            mx.eval(state);losses=[];warm_start=time.perf_counter();started=None
            for i,batch in enumerate(batches):
                if i==5:warm_seconds=time.perf_counter()-warm_start;started=time.perf_counter()
                x,y,mask=[mx.array(b) for b in batch[:3]]
                loss,norm=fn(x,y,mask,mx.array(3e-4/(1+i/20)));mx.eval(state,loss,norm);losses.append(float(loss.item()))
            elapsed=time.perf_counter()-started
            record=dict(kind='training',compiled=compiled,repeat=repeat,seconds=elapsed,nonpadding_tokens=actual_tokens,tokens_per_second=actual_tokens/elapsed,warmup_including_compile_seconds=warm_seconds,losses=losses)
            measured.append(record);print(json.dumps(record),flush=True)
            del m,fn,opt,state;gc.collect();mx.clear_cache()
    reference=next(r['losses'] for r in measured if not r['compiled'])
    equivalent=all(np.allclose(r['losses'],reference,rtol=1e-4,atol=1e-5) for r in measured)
    m=model();m.eval()
    # Synthetic fixed token IDs: equal length and fixed work, not a quality evaluation.
    ids=[1]+[5+(i*17)%(config['model']['vocab_size']-5) for i in range(255)]
    generations=[]
    for repeat in range(3):
        for cached in ([False,True] if repeat%2==0 else [True,False]):
            tokens_greedy(m,ids,4,cached=cached)
            started=time.perf_counter();tokens=tokens_greedy(m,ids,64,cached=cached);elapsed=time.perf_counter()-started
            record=dict(kind='inference',cached=cached,repeat=repeat,seconds=elapsed,new_tokens=64,tokens_per_second=64/elapsed,tokens=tokens)
            generations.append(record);print(json.dumps(record),flush=True)
    cache_equal=all(r['tokens']==generations[0]['tokens'] for r in generations)
    eager=statistics.median(r['tokens_per_second'] for r in measured if not r['compiled']);compiled=statistics.median(r['tokens_per_second'] for r in measured if r['compiled'])
    plain=statistics.median(r['tokens_per_second'] for r in generations if not r['cached']);cached=statistics.median(r['tokens_per_second'] for r in generations if r['cached'])
    result=dict(status='completed',checkpoint=str(checkpoint),checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),parameters=config['parameters'],training_loss_trajectories_equivalent=bool(equivalent),greedy_tokens_identical=cache_equal,training_speedup=compiled/eager,inference_speedup=cached/plain,training=measured,inference=generations,notes='FP32, same frozen weights and real preloaded batches. Three alternating repetitions; five warmup and fifteen timed training steps. Compilation/warmup reported separately. Inference 256-token synthetic prompt plus 64 forced decode steps, including prefill. No production pipeline change or quality-score claim.')
    (out/'results.json').write_text(json.dumps(result,indent=2))
    lines=['# GPU-Performancevergleich', '',f"Kompilierter Trainingsschritt: {compiled/eager:.2f}× gegenüber eager; Loss-Verläufe innerhalb der Toleranz: {equivalent}.",f"KV-Cache bei Generierung: {cached/plain:.2f}×; greedy Tokenfolgen identisch: {cache_equal}.", '',result['notes'], '', 'Keine automatische Übernahme in Training oder Evaluation. Vor einer Übernahme müssen Checkpoint-Wiederaufnahme und reale Aufgaben auf dem jeweiligen Kandidaten geprüft werden.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    if not equivalent or not cache_equal:raise SystemExit(2)


if __name__=='__main__':main()
