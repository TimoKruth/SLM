"""GPU throughput pilot; one serial process and no trained random candidates."""
import argparse
from collections import defaultdict,Counter
from datetime import datetime
import hashlib,json,math
from pathlib import Path
import statistics,time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def split_tasks(rows):
    """Freeze selection/control groups before seeing any candidate model outputs."""
    by_source=defaultdict(list)
    for row in rows:
        if row['source']!='scitail':by_source[row['source']].append(row)
    selection=[];control=[]
    for source,pool in sorted(by_source.items()):
        pool=sorted(pool,key=lambda r:hashlib.sha256(('random-pilot-20260908:'+r['group']).encode()).hexdigest())
        if len(pool)<2:raise ValueError('Need two independent groups: '+source)
        if pool[0]['group']==pool[1]['group']:raise ValueError('Group overlap')
        selection.append(pool[0])
    selection_groups={r['group'] for r in selection}
    for source,pool in sorted(by_source.items()):
        pool=sorted(pool,key=lambda r:hashlib.sha256(('random-pilot-20260908:'+r['group']).encode()).hexdigest())
        available=[r for r in pool if r['group'] not in selection_groups]
        if not available:raise ValueError('No disjoint control group: '+source)
        control.append(available[0])
    return selection,control


def encode_rows(rows,tok,context):
    """Mask only answer targets; retain complete records rather than truncating labels."""
    import numpy as np
    encoded=[]
    for r in rows:
        text='<bos><question>\n'+r['prompt']+'\n<answer>\n'+r['answer']+'<eos>\n'
        ids=tok.encode(text).ids
        if len(ids)>context:raise ValueError('Reference exceeds context: '+r['source']+':'+r['original_id'])
        start=ids.index(tok.token_to_id('<answer>'))+1
        mask=np.zeros((1,len(ids)-1),dtype=np.float32);mask[:,max(0,start-1):]=1
        encoded.append((r,np.array([ids[:-1]],dtype=np.int32),np.array([ids[1:]],dtype=np.int32),mask))
    return encoded


def teacher_score(model,encoded,deadline):
    """Synchronized forward-only loss, equally weighted by source."""
    import mlx.core as mx
    import mlx.nn as nn
    values=defaultdict(list);tokens=0;start=time.perf_counter()
    for row,x,y,mask in encoded:
        if time.time()>=deadline:raise TimeoutError('Teacher-score deadline')
        loss=nn.losses.cross_entropy(model(mx.array(x)),mx.array(y),reduction='none')
        value=(mx.sum(loss*mx.array(mask))/mx.sum(mx.array(mask))).item()
        if not math.isfinite(value):raise ValueError('Nonfinite loss')
        values[row['source']].append(float(value));tokens+=x.size
    return dict(answer_loss=statistics.mean(statistics.mean(v) for v in values.values()),
        source_loss={s:statistics.mean(v) for s,v in values.items()},seconds=time.perf_counter()-start,
        examples=sum(len(v) for v in values.values()),processed_tokens=tokens)


def fresh_model(config,seed):
    import mlx.core as mx
    from slm.model import LanguageModel
    mx.random.seed(seed);start=time.perf_counter();model=LanguageModel(config)
    mx.eval(model.parameters());model.eval()
    return model,time.perf_counter()-start


def generate_probe(model,tok,rows,deadline):
    from slm.inference import greedy_generate
    from slm.broad_eval import score_general
    begin=time.perf_counter();output=[]
    for row in rows:
        if time.time()>=deadline:raise TimeoutError('Generation deadline')
        response=greedy_generate(model,tok,row['prompt'],256,deadline=deadline)
        if response['stop_reason']=='deadline':raise TimeoutError('Generation incomplete')
        output.append(dict(source=row['source'],id=row['original_id'],**response,**score_general(row,response['generated'])))
    scored=[r for r in output if 'correct' in r and r.get('reference_parseable',True)]
    return dict(seconds=time.perf_counter()-begin,examples=len(rows),generated_tokens=sum(r['generated_tokens'] for r in output),
        correct=sum(r['correct'] for r in scored),scored=len(scored),token_limits=sum(r['stop_reason']=='token_limit' for r in output),rows=output)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--budget-seconds',type=int,default=1200);p.add_argument('--search-seconds',type=int,default=300);p.add_argument('--max-candidates',type=int,default=256)
    p.add_argument('--suite',default='runs/eval-preparation-2026-09-07/after-campaign/suite-v2.json')
    a=p.parse_args()
    if not 60<=a.budget_seconds<=1200 or not 1<=a.search_seconds<a.budget_seconds or a.max_candidates<2:p.error('Invalid pilot budget')
    out=Path(a.run);out.mkdir(parents=True,exist_ok=True)
    if (out/'protocol.json').exists():raise ValueError('New pilot output required')
    begin=time.time();deadline=begin+a.budget_seconds
    import mlx.core as mx
    from tokenizers import Tokenizer
    from slm.model import ModelConfig
    from slm.breadth import SOURCE_FAMILY
    from slm.train import atomic_json
    import gc
    mx.set_default_device(mx.gpu);mx.set_memory_limit(12*1024**3);mx.set_cache_limit(512*1024**2)
    suite=json.loads(Path(a.suite).read_text());base=Path('runs/broad-sources-2026-09-07-3h')
    cfg=json.loads((base/'config.json').read_text());config=ModelConfig(**cfg['model'])
    tok=Tokenizer.from_file(str(base/'tokenizer.json'))
    assert sha(base/'tokenizer.json')==suite['tokenizer_sha256']
    full=[r for r in suite['general'] if r['source']!='scitail']
    # Some reference encodings differ by terminal newlines; explicitly report exclusions.
    fitting=[];excluded=[]
    for row in full:
        try:encode_rows([row],tok,config.context);fitting.append(row)
        except ValueError:excluded.append({'source':row['source'],'id':row['original_id'],'reason':'full_reference_exceeds_context'})
    selection,control=split_tasks(fitting)
    probes=[];families=Counter()
    for row in control:
        family=SOURCE_FAMILY[row['source']]
        if families[family]<2:probes.append(row);families[family]+=1
    select_encoded=encode_rows(selection,tok,config.context);control_encoded=encode_rows(control,tok,config.context)
    full_encoded=encode_rows(fitting,tok,config.context)
    protocol=dict(created_at=datetime.now().astimezone().isoformat(),model=cfg['model'],budget_seconds=a.budget_seconds,search_seconds=a.search_seconds,
        suite_sha256=sha(a.suite),tokenizer_sha256=sha(base/'tokenizer.json'),pilot_sha256=sha(__file__),initialization='Same production normal initialization; different seeds, no optimizer or weight updates.',
        selection=selection,control=control,generation_probes=probes,full_examples=len(full),teacher_full_examples=len(fitting),teacher_exclusions=excluded,
        selection_metric='Lowest equally source-weighted teacher-forced answer loss on selection tasks only.',
        caveats=['Control answers are not consulted until the winning seed is fixed.','All tasks are internal development from original benchmark train splits; they are not pristine external tests.','Teacher forcing supplies earlier reference tokens and is not free-answer correctness.','Prior trained checkpoints already used development loss for selection; comparisons are descriptive, not a fresh controlled training experiment.','Exact reduced-power setting remains user reported; no power or GPU utilization measurement is inferred from time/memory.'])
    atomic_json(out/'protocol.json',protocol)
    trials=[];best=None
    # Warm kernels before candidate timing; this seed does not participate in selection.
    warm,_=fresh_model(config,2026090799);teacher_score(warm,select_encoded,deadline);del warm;gc.collect();mx.clear_cache()
    search_start=time.time();search_until=min(deadline-180,search_start+a.search_seconds)
    for i in range(a.max_candidates):
        if time.time()>=search_until and len(trials)>=2:break
        if (out/'STOP').exists():raise InterruptedError('Requested stop')
        seed=2026090800+i;start=time.perf_counter();model,init=fresh_model(config,seed)
        score=teacher_score(model,select_encoded,deadline)
        row=dict(index=i,seed=seed,initialization_seconds=init,selection=score,total_seconds=time.perf_counter()-start)
        trials.append(row)
        if best is None or score['answer_loss']<best['selection']['answer_loss']:best=row
        with (out/'trials.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        atomic_json(out/'status.json',dict(status='searching',candidates=len(trials),best_seed=best['seed'],best_selection_loss=best['selection']['answer_loss']))
        print('CANDIDATE',len(trials),round(row['total_seconds'],3),round(score['answer_loss'],5),flush=True)
        del model;gc.collect();mx.clear_cache()
    search_wall=time.time()-search_start
    # Freeze the winner BEFORE any holdout evaluation, without changing its weights.
    atomic_json(out/'winner.json',best)
    comparison={}
    refs=[('random_first',trials[0]['seed'],None),('random_selected',best['seed'],None),
          ('trained_families',None,Path('runs/broad-families-2026-09-07-3h/best.safetensors')),
          ('trained_sources',None,Path('runs/broad-sources-2026-09-07-3h/best.safetensors'))]
    for name,seed,path in refs:
        if (out/'STOP').exists():raise InterruptedError('Requested stop')
        atomic_json(out/'status.json',dict(status='checking_controls',model=name,candidates=len(trials)))
        model,init=fresh_model(config,seed if seed is not None else 991)
        if path is not None:model.load_weights(str(path));mx.eval(model.parameters())
        value={'seed':seed,'initialization_seconds':init,'checkpoint_sha256':sha(path) if path else None,
               'control':teacher_score(model,control_encoded,deadline),
               'generation':generate_probe(model,tok,probes,deadline)}
        if name in {'random_selected','trained_sources'}:
            value['full_teacher']=teacher_score(model,full_encoded,deadline)
        comparison[name]=value
        atomic_json(out/'controls.json',comparison)
        print('CONTROL',name,'loss',value['control']['answer_loss'],'generation',value['generation']['correct'],'/',value['generation']['scored'],flush=True)
        del model;gc.collect();mx.clear_cache()
    selected=comparison['random_selected'];init_median=statistics.median(r['initialization_seconds'] for r in trials)
    fast=search_wall/len(trials)
    full_teacher=init_median+selected['full_teacher']['seconds']
    extrapolated_gen=init_median+selected['generation']['seconds']/len(probes)*len(full)
    results=dict(status='completed',parameters=cfg['parameters'],
        candidates=len(trials),search_wall_seconds=search_wall,mean_search_seconds_per_candidate=fast,
        median_initialization_seconds=init_median,median_selection_seconds=statistics.median(r['selection']['seconds'] for r in trials),
        seed_selection_loss_range=[min(r['selection']['answer_loss'] for r in trials),max(r['selection']['answer_loss'] for r in trials)],
        comparison=comparison,projections_three_hours={'fast_selection_candidates_before_final_controls':int(10800/fast),'full_teacher_candidates':int(10800/full_teacher),
            'full_generation_candidates_from_small_probe':int(10800/extrapolated_gen),'full_generation_seconds_per_candidate_extrapolated':extrapolated_gen,
            'caveat':'Serial throughput estimate at current conditions, not probability of finding a good model. Generation extrapolation uses a small capability-balanced probe; full-corpus runtime may differ.'},
        elapsed_seconds=time.time()-begin,mlx_peak_gb=mx.get_peak_memory()/1e9)
    atomic_json(out/'results.json',results);atomic_json(out/'status.json',dict(status='completed',candidates=len(trials),elapsed_seconds=results['elapsed_seconds']))
    print('PILOT_COMPLETE',json.dumps({k:v for k,v in results.items() if k!='comparison'}),flush=True)

if __name__=='__main__':main()
