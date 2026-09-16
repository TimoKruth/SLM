"""CPU-only fresh 47-source data/tokenizer preparation; never initializes a model."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
import numpy as np
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders
from slm.breadth import BENCHMARK47_FAMILIES, sampling_weights, EVALUATION_SOURCE_FAMILY
from slm.prepare import SPECIAL, text_of


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def rank(group):return hashlib.sha256(('fresh47-20260916:'+group).encode()).hexdigest()

def rows(base):
    for name in ['records.jsonl','confirmation.jsonl']:
        with (base/name).open() as f:
            for line in f:yield json.loads(line)


def prepare(base,output,policy):
    assert not output.exists(), 'Use a new data version'
    meta=json.loads((base/'manifest.json').read_text());assert len(meta['sources'])==47
    expected={**meta['derived_files_sha256'],'records.jsonl':meta['records_sha256'],
              'confirmation.jsonl':meta['confirmation_sha256'],'tokenizer.json':meta['tokenizer']['sha256'],
              'audit.json':meta['audit_sha256'],**meta.get('parent_suites_sha256',{})}
    for name,digest in expected.items():assert sha(base/name)==digest,name
    exclusions=json.loads(policy.read_text());badids={(r['source'],r['original_id']) for r in exclusions}
    blocked=set();dev_groups=defaultdict(set);fixed_confirmation=set();original_labels=defaultdict(set)
    for row in rows(base):
        assert row['original_split']=='train'
        if (row['source'],str(row['original_id'])) in badids:blocked.add(row['group'])
        if row['split']=='dev':dev_groups[row['source']].add(row['group'])
        elif row['split']=='confirmation':fixed_confirmation.add(row['source'])
        if row['split']=='train':original_labels[row['source']].update(row.get('original_labels',[]))
    # Keep all original training memberships. Divide legacy dev groups into dev/confirmation;
    # preserve already separated confirmation partitions for the 15 expansion sources.
    repartition={}
    for source,groups in sorted(dev_groups.items()):
        if source in fixed_confirmation:continue
        for i,group in enumerate(sorted(groups-blocked,key=rank)):
            repartition.setdefault(group,'dev' if i%2==0 else 'confirmation')
    def accepted():
        for row in rows(base):
            if row['group'] in blocked:continue
            if any(t in row['prompt'] or t in row['answer'] for t in SPECIAL):continue
            row=dict(row)
            if row['split']=='dev' and row['source'] not in fixed_confirmation:row['split']=repartition[row['group']]
            yield row
    output.mkdir(parents=True)
    (output/'STOP').write_text('Data preparation only. No model training or evaluation authorized by this artifact.\n')
    tokenizer=Tokenizer(models.BPE());tokenizer.pre_tokenizer=pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder=decoders.ByteLevel()
    trainer=trainers.BpeTrainer(vocab_size=16384,min_frequency=2,special_tokens=SPECIAL,
                               initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),show_progress=False)
    tokenizer_input=hashlib.sha256();tokenizer_records=0
    def train_texts():
        nonlocal tokenizer_records
        for row in accepted():
            if row['split']=='train':
                value=text_of(row);tokenizer_input.update((value+'\n').encode());tokenizer_records+=1;yield value
    print('Training fresh train-only tokenizer',flush=True)
    tokenizer.train_from_iterator(train_texts(),trainer=trainer)
    tokenizer.save(str(output/'tokenizer.json'));assert sha(output/'tokenizer.json')!=meta['tokenizer']['sha256']
    print('Tokenizer complete',tokenizer_records,flush=True)
    handles={};indices=defaultdict(list);counts=defaultdict(Counter);groups=defaultdict(set);labels=defaultdict(set)
    candidates=defaultdict(list);filtered=Counter();samples=defaultdict(list)
    for source in meta['sources']:
        for split in ['train','dev']:
            for suffix in ['bin','mask.bin']:handles[source,split,suffix]=(output/f'{source}.{split}.{suffix}').open('wb')
    files={split:(output/('confirmation.jsonl' if split=='confirmation' else 'records.jsonl')).open('w') for split in ['train','confirmation']}
    def encode_batch(batch):
        encoded=tokenizer.encode_batch([text_of(r) for r in batch])
        for row,encoding in zip(batch,encoded):
            key=row['source'],row['split'];ids=encoding.ids
            if len(ids)>1024:filtered['.'.join(key)+'.over_context']+=1;continue
            assert 2<=len(ids)<=1024 and max(ids)<65536
            # Source records may carry lengths from the previous tokenizer.
            row.pop('tokens',None)
            counts[key]['records']+=1;groups[key].add(row['group']);labels[key].update(row.get('original_labels',[]))
            if row['split']!='confirmation':
                indices[key].append((counts[key]['tokens'],len(ids)))
                mask=np.ones(len(ids),dtype=np.uint8);mask[:ids.index(tokenizer.token_to_id('<answer>'))+1]=0
                np.asarray(ids,dtype=np.uint16).tofile(handles[*key,'bin']);mask.tofile(handles[*key,'mask.bin'])
                counts[key]['tokens']+=len(ids)
                if len(samples[key])<16:samples[key].append((len(indices[key])-1,row))
            files['confirmation' if row['split']=='confirmation' else 'train'].write(json.dumps(row,ensure_ascii=False)+'\n')
            if row['split'] in ['dev','confirmation']:
                prompt='<bos><question>\n'+row['prompt']+'\n<answer>\n'
                if len(tokenizer.encode(prompt).ids)+256<=1024:candidates[key].append(row)
    batch=[]
    for row in accepted():
        batch.append(row)
        if len(batch)==256:encode_batch(batch);batch=[]
    if batch:encode_batch(batch)
    for f in [*handles.values(),*files.values()]:f.close()
    for source in meta['sources']:
        for split in ['train','dev']:
            key=source,split
            np.save(output/f'{source}.{split}.index.npy',np.asarray(indices[key],dtype=np.int64).reshape(-1,2))
    # Group separation is checked globally, not only within sources.
    global_groups={split:set().union(*(v for (s,p),v in groups.items() if p==split)) for split in ['train','dev','confirmation']}
    assert not global_groups['train']&global_groups['dev'] and not global_groups['train']&global_groups['confirmation']
    assert not global_groups['dev']&global_groups['confirmation']
    assert all(counts[s,'train']['records']>0 for s in meta['sources'])
    for source,values in original_labels.items():assert values<=labels[source,'train'],('Lost training label',source)
    suites={};coverage={};tokenizer_sha=sha(output/'tokenizer.json')
    for split in ['dev','confirmation']:
        chosen=[]
        for source in sorted(meta['sources']):
            selected=[];seen=set()
            for row in sorted(candidates[source,split],key=lambda r:(rank(r['group']),str(r['original_id']),r.get('variant',0))):
                if row['group'] in seen:continue
                selected.append(row);seen.add(row['group'])
                if len(selected)==32:break
            chosen.extend(selected);coverage[source+'.'+split]=dict(selected=len(selected),eligible_groups=len({r['group'] for r in candidates[source,split]}),family=EVALUATION_SOURCE_FAMILY[source])
        assert len({r['group'] for r in chosen})==len(chosen)
        suite=dict(version=1,tokenizer_sha256=tokenizer_sha,general=chosen,code=[],memorization=[],
                   protocol='Fresh random-initialization campaign on 47 sources. Preserved original train membership; grouped dev/confirmation. New train-only tokenizer. Up to 32 groups per source, all references fit context plus 256 generation tokens. HotpotQA training-only due shared-document grouping; no external benchmark or functional-code claims.')
        write(output/f'{split}-suite.json',suite);suites[split]=dict(tasks=len(chosen),sha256=sha(output/f'{split}-suite.json'))
    # Independent re-encoding samples plus full file/index shape and hash verification.
    sample_count=0
    for (source,split),sample in samples.items():
        idx=np.load(output/f'{source}.{split}.index.npy');t=np.memmap(output/f'{source}.{split}.bin',dtype=np.uint16,mode='r');m=np.memmap(output/f'{source}.{split}.mask.bin',dtype=np.uint8,mode='r')
        assert len(idx)==counts[source,split]['records'] and len(t)==len(m)==counts[source,split]['tokens']
        assert idx[0,0]==0 and np.all(idx[1:,0]==idx[:-1,0]+idx[:-1,1]) and idx[-1].sum()==len(t)
        for position,row in sample:
            ids=tokenizer.encode(text_of(row)).ids;offset,length=map(int,idx[position]);assert t[offset:offset+length].tolist()==ids
            boundary=ids.index(tokenizer.token_to_id('<answer>'))+1;assert m[offset:offset+length].tolist()==[0]*boundary+[1]*(len(ids)-boundary)
            sample_count+=1
    counts_out={s+'.'+p:dict(v,groups=len(groups[s,p])) for (s,p),v in counts.items()}
    manifest=dict(version=7,status='prepared_not_started',sources=meta['sources'],families=BENCHMARK47_FAMILIES,
                  tokenizer=dict(vocab_size=tokenizer.get_vocab_size(),sha256=tokenizer_sha,trained_on='Only new campaign training membership from v6 original-train records; no dev/confirmation/validation/test text.',training_records=tokenizer_records,training_text_stream_sha256=tokenizer_input.hexdigest()),
                  counts=counts_out,max_record_tokens=1024,source_weights=sampling_weights(meta['sources'],families=BENCHMARK47_FAMILIES),
                  evaluation_weights={s:1. for s in meta['sources'] if counts[s,'dev']['records']},
                  records_sha256=sha(output/'records.jsonl'),confirmation_sha256=sha(output/'confirmation.jsonl'),
                  derived_files_sha256={p.name:sha(p) for p in output.iterdir() if p.suffix in {'.bin','.npy'}},
                  lineage=dict(parent_manifest_sha256=sha(base/'manifest.json'),parent_records_sha256=meta['records_sha256'],parent_confirmation_sha256=meta['confirmation_sha256']),
                  original_validation_or_test_in_training=False,external_tests_loaded=False,
                  limitations=['Inherits v6 admitted pool and its original-tokenizer length filtering; not a reconstruction of discarded raw rows.',
                               'Exact/group audit inherited from v6; not full semantic or near-duplicate independence.',
                               'HotpotQA has no direct holdout; some other sources have fewer than 32 held-out groups.',
                               'Historical scores are deprecated and not baselines for this fresh model.'])
    write(output/'manifest.json',manifest)
    from slm.data import Sampler
    for split in ['train','dev']:
        sampler=Sampler(output,split=split,seed=20260916)
        for source in sampler.names:
            x,y,mask,answer=sampler.batch(2,source);assert mask.sum()>0 and answer.sum()>0
    audit=dict(status='ready_for_prepared_campaign_only',model_initialized=False,training_started=False,
               created=datetime.now().astimezone().isoformat(),sources=47,families=13,
               quarantined_groups=len(blocked),reference_policy_sha256=sha(policy),filtered=dict(filtered),coverage=coverage,suites=suites,
               counts=counts_out,training_records=sum(v['records'] for k,v in counts_out.items() if k.endswith('.train')),
               token_and_mask_samples_verified=sample_count,group_overlap=0,manifest_sha256=sha(output/'manifest.json'),
               script_sha256=sha(Path(__file__)),self_contained_files=not any(p.is_symlink() for p in output.iterdir()))
    write(output/'READY.json',audit);print(json.dumps({k:v for k,v in audit.items() if k not in ['coverage','counts','filtered']},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['base','output','policy']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();os.nice(10);prepare(a.base.resolve(),a.output.resolve(),a.policy.resolve())
