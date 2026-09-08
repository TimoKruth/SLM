"""Reconstruct actual training exposure and freeze matched diagnostic samples."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from tokenizers import Tokenizer
from slm.data import Sampler
from slm.prepare import text_of

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'runs/next-preparation-2026-09-08'
RUN = ROOT/'runs/size-27m-2026-09-08-3h'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

class ObservedTokens:
    def __init__(self, values, seen): self.values,self.seen=values,seen
    def __getitem__(self, key):
        self.seen[key.start]+=1
        return self.values[key]

def main():
    OUT.mkdir(exist_ok=True)
    if (OUT/'seen-train-suite.json').exists():
        raise FileExistsError('Frozen diagnostic suites already exist; choose a new output version')
    config=json.loads((RUN/'config.json').read_text())
    data=ROOT/config['data']
    sampler=Sampler(data,seed=config['seed'],context=config['context'])
    seen={s:Counter() for s in sampler.names}
    for s in sampler.names:sampler.tokens[s]=ObservedTokens(sampler.tokens[s],seen[s])
    target=json.loads((RUN/'token-010000000/snapshot.json').read_text())
    totals=Counter();tokens=0;answer_tokens=0
    for _ in range(target['step']):
        b=sampler.batch(config['batch_size']);tokens+=int(b[2].sum());answer_tokens+=int(b[3].sum());totals.update(sampler.last_batch_source_tokens)
    assert tokens==target['tokens'] and dict(totals)==target['source_tokens'], 'Replay differs from frozen snapshot'
    wanted={}
    for s,counts in seen.items():
        index=np.load(data/f'{s}.train.index.npy')
        rank=sorted(counts,key=lambda offset:hashlib.sha256(f'20260908:{s}:{offset}'.encode()).hexdigest())[:64]
        offsets={int(start):i for i,(start,length) in enumerate(index)}
        wanted[s]={offsets[o]:o for o in rank}
    pools=defaultdict(list);ordinal=Counter()
    with (data/'records.jsonl').open() as f:
        for line in f:
            row=json.loads(line)
            if row['split']!='train':continue
            s=row['source'];i=ordinal[s];ordinal[s]+=1
            if i in wanted[s]:
                row['exposure_first_10m']=seen[s][wanted[s][i]]
                row['training_token_offset']=wanted[s][i]
                pools[s].append(row)
    tok=Tokenizer.from_file(str(RUN/'tokenizer.json'))
    for s,rows in pools.items():
        for row in rows:
            ids=tok.encode(text_of(row)).ids;o=row['training_token_offset']
            assert ids==list(sampler.tokens[s].values[o:o+len(ids)]), 'Record/index mismatch'
    old=json.loads((ROOT/'runs/size-campaign-2026-09-08/suite.json').read_text())
    train=[];dev=[];pairs=[]
    # Deterministic greedy length matching, without looking at model responses.
    for s in sorted(pools):
        available=[r for r in old['general'] if r['source']==s]
        selected=pools[s][:8]
        for row in selected:
            train.append(row)
            if not available:continue
            lengths=lambda r:(len(tok.encode(r['prompt']).ids),len(tok.encode(r['answer']).ids))
            a,b=lengths(row)
            match=min(available,key=lambda r:abs(lengths(r)[0]-a)+2*abs(lengths(r)[1]-b))
            available.remove(match);dev.append(match)
            pairs.append(dict(source=s,train_id=row['original_id'],dev_id=match['original_id'],train_lengths=[a,b],dev_lengths=list(lengths(match))))
    assert not {r['group'] for r in train}&{r['group'] for r in dev}
    for name,rows in [('seen-train',train),('matched-dev',dev)]:
        suite={**old,'general':rows,'memorization':rows if name=='seen-train' else [],'code':[],
            'protocol':'Diagnostic original-train exposure versus internal development; deterministic length matching, no outcome selection. Training recall is not generalization.'}
        (OUT/f'{name}-suite.json').write_text(json.dumps(suite,ensure_ascii=False)+'\n')
    (OUT/'sample-audit.json').write_text(json.dumps(dict(replayed_steps=target['step'],replayed_tokens=tokens,identical_source_tokens=True,answer_token_fraction=answer_tokens/tokens,
        train_count=len(train),dev_count=len(dev),train_sources=len(pools),dev_sources=len({r['source'] for r in dev}),pairs=pairs,
        limitation='Deterministic diagnostic sample: first eight record-order entries from a hash-selected pool of 64 seen entries per source, not a representative random sample. Only exposure within first 10M tokens proved; later exposures unknown. Length matching is approximate. HotpotQA has no dev group and is excluded from paired comparison.',
        inputs={str(p):sha(p) for p in [RUN/'config.json',RUN/'token-010000000/snapshot.json',data/'manifest.json',ROOT/'runs/size-campaign-2026-09-08/suite.json']}),indent=2)+'\n')
    print(json.dumps(dict(train=len(train),dev=len(dev),replay_tokens=tokens,answer_token_fraction=answer_tokens/tokens)))

if __name__=='__main__':main()
