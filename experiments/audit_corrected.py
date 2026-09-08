"""Audit corrected broad corpus and discrete classes against pinned original train bytes."""
import argparse,hashlib,json,zipfile
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from experiments.prepare_broad import sha,converted as broad_convert
from slm.prepare import normal,convert as original_convert
from slm.prepare_v2 import converted as expanded_convert
from slm.breadth import SOURCE_FAMILY
from future_eval.metrics import LABELS

ORIGINAL={'boolq','hellaswag','piqa','winogrande','arc'}
EXPANDED={'openbookqa','commonsenseqa','qasc','quartz','quarel','race','snli','aqua_rat'}
BROAD={'social_i_qa','cosmos_qa','dream','wiqa','anli','scitail'}


def fingerprint(text):return hashlib.sha256(normal(text).encode()).digest()


def label(source,row):
    if source=='boolq':return 'yes' if row['answer'] else 'no'
    if source in {'snli','anli'}:return ['entailment','neutral','contradiction'][row['label']] if row['label'] in [0,1,2] else None
    if source=='scitail':return {'entails':'entailment','neutral':'neutral'}[row['label']]
    if source=='wiqa':return row['answer_label'].replace('_',' ')
    if source in {'hellaswag','piqa','cosmos_qa'}:return str(int(row['label']))
    if source=='social_i_qa':return str(int(row['label'])-1)
    if source=='winogrande':return str(int(row['answer'])-1)
    if source in {'arc','openbookqa','commonsenseqa','qasc','quartz'}:return str(row['choices']['label'].index(row['answerKey']))
    if source=='quarel':return str(row['answer_index'])
    if source=='race':return str(ord(row['answer'])-65)
    if source=='aqua_rat':return str(ord(row['correct'])-65)
    if source=='dream':return str(row['choice'].index(row['answer']))


def expected_answer(source, row):
    """Read the target directly from raw fields, independently of converter output."""
    if source in LABELS:return label(source,row)
    if source=='hellaswag':return row['endings'][int(row['label'])]
    if source=='piqa':return row['sol1'] if int(row['label'])==0 else row['sol2']
    if source=='winogrande':return row['option'+str(row['answer'])]
    if source in {'arc','openbookqa','commonsenseqa','qasc','quartz'}:
        answer=row['choices']['text'][row['choices']['label'].index(row['answerKey'])]
        return row['fact1']+' '+row['fact2']+'\nAnswer: '+answer if source=='qasc' else answer
    if source=='quarel':return ['A','B'][row['answer_index']]
    if source=='race':return row['options'][ord(row['answer'])-65]
    if source=='aqua_rat':return row['rationale']+'\nAnswer: '+row['options'][ord(row['correct'])-65]
    if source=='social_i_qa':return row['answer'+chr(64+int(row['label']))]
    if source=='cosmos_qa':return row['answer'+str(row['label'])]
    if source=='dream':return row['answer']
    raise ValueError(source)


def audit(base):
    root=base.parent;meta=json.loads((base/'manifest.json').read_text())
    parent=root/'v2';assert sha(parent/'manifest.json')==meta['parent_manifest_sha256']
    assert sha(base/'records.jsonl')==meta['records_sha256']
    assert sha(base/'tokenizer.json')==meta['tokenizer']['sha256']==sha(parent/'tokenizer.json')
    remaining=(parent/'records.jsonl').stat().st_size;prefix=hashlib.sha256()
    with (base/'records.jsonl').open('rb') as f:
        while remaining:
            block=f.read(min(remaining,1024**2));assert block;prefix.update(block);remaining-=len(block)
    assert prefix.hexdigest()==sha(parent/'records.jsonl')
    for name,expected in meta['derived_files_sha256'].items():assert sha(base/name)==expected,name
    raw_classes=defaultdict(Counter);references=defaultdict(dict);raw_counts={};raw_invalid=Counter()
    for source,sm in meta['sources'].items():
        assert sm['original_split']=='train';n=0
        if source=='piqa':
            path=root/'raw/piqa/source.zip';assert sha(path)==sm['archive_sha256']
            with zipfile.ZipFile(path) as z:
                rr=z.read('physicaliqa-train-dev/train.jsonl').decode().splitlines()
                ll=z.read('physicaliqa-train-dev/train-labels.lst').decode().splitlines();assert len(rr)==len(ll)
                batches=[[dict(json.loads(r),label=int(l)) for r,l in zip(rr,ll)]]
        else:
            files=[]
            for item in sm['files']:
                assert 'train' in item['path'] and not any(x in item['path'] for x in ['test','validation'])
                candidates=[p/'raw'/source/item['path'] for p in [root,root/'candidates-2026-09-07',root/'candidates-wave3-2026-09-07']]
                path=next(p for p in candidates if p.exists());assert sha(path)==item['sha256'],str(path);files.append(path)
            def raw_batches():
                for path in files:
                    if path.suffix=='.parquet':
                        if source not in ORIGINAL|EXPANDED|BROAD:
                            yield [None]*pq.ParquetFile(path).metadata.num_rows
                        else:
                            for batch in pq.ParquetFile(path).iter_batches(batch_size=512,use_threads=False):yield batch.to_pylist()
                    else:
                        # No code/reference parsing needed for the source row count.
                        with path.open() as f:
                            for line in f:
                                if line.strip():yield [None]
            batches=raw_batches()
        for batch in batches:
            for raw in batch:
                n+=1
                if source not in ORIGINAL|EXPANDED|BROAD:continue
                value=label(source,raw)
                if value is None:raw_invalid[source]+=1;continue
                raw_classes[source][value]+=1
                if source in ORIGINAL:
                    rows,_=original_convert(source,[raw]);row=rows[0];prompt,answer=row['prompt'],row['answer']
                elif source in EXPANDED:
                    _,prompt,answers,_=expanded_convert(source,raw,{});answer=answers[0]
                else:
                    row=broad_convert(source,raw,str(n));prompt,answer=row['prompt'],row['answer']
                assert fingerprint(answer)==fingerprint(expected_answer(source,raw)), ('Converter answer differs from original target',source)
                references[source].setdefault(fingerprint(prompt),set()).add((value,fingerprint(answer)))
        raw_counts[source]=n
        if 'original_train_rows' in sm:assert n==sm['original_train_rows'],source
        print('RAW_CHECKED',source,n,flush=True)
    counts=Counter();groups=defaultdict(set);prompts=defaultdict(set);classes=defaultdict(Counter)
    top=defaultdict(Counter);labels=defaultdict(Counter);unmatched=Counter();empty=Counter()
    for line in (base/'records.jsonl').open():
        row=json.loads(line);s,split=row['source'],row['split'];assert row['original_split']=='train'
        counts[(s,split)]+=1;groups[split].add(row['group']);key=fingerprint(row['prompt']);prompts[split].add(key)
        if not row['answer'].strip() or not row['prompt'].strip():empty[s]+=1
        if len(row['answer'])<=80:top[(s,split)][row['answer']]+=1
        if s in LABELS:labels[(s,split)][row['answer'].strip().casefold()]+=1
        if s in references:
            possible=references[s].get(key,set());actual=fingerprint(row['answer'])
            matched={cl for cl,answer in possible if answer==actual}
            if not matched:unmatched[s]+=1
            else:
                # Ambiguous identical choices may have multiple source positions; do not invent a unique label.
                for cl in matched:classes[(s,split)][cl]+=1
    assert not empty,empty;assert not unmatched,unmatched
    assert groups['train'].isdisjoint(groups['dev']);assert prompts['train'].isdisjoint(prompts['dev'])
    assert {s for s,split in counts if split=='train'}==set(SOURCE_FAMILY)
    missing={s:sorted(set(v)-set(classes[(s,'train')])) for s,v in raw_classes.items() if set(v)-set(classes[(s,'train')])}
    assert not missing,missing
    details={}
    for s in meta['sources']:
        details[s]={'raw_rows':raw_counts[s],'raw_classes':dict(raw_classes[s]),'invalid_original_labels':raw_invalid[s],'splits':{}}
        for split in ['train','dev']:
            c=counts[(s,split)];assert c==meta['counts'].get(s+'.'+split,{}).get('records',0),(s,split)
            idx=np.load(base/f'{s}.{split}.index.npy');assert len(idx)==c
            if c:
                assert int(idx[:,1].max())<=1024 and int(idx[:,1].min())>=2
                assert idx[0,0]==0 and np.all(idx[1:,0]==idx[:-1,0]+idx[:-1,1])
                size=int(idx[-1].sum());assert (base/f'{s}.{split}.bin').stat().st_size==2*size
                assert (base/f'{s}.{split}.mask.bin').stat().st_size==size
            details[s]['splits'][split]={'records':c,'classes':dict(classes[(s,split)]),'label_counts':dict(labels[(s,split)]),'top_short_answers':top[(s,split)].most_common(5),'context_exclusions':meta['counts'].get(s+'.'+split,{}).get('excluded_over_1024',0)}
    result={'status':'passed','sources':details,'exact_group_overlap':0,'exact_prompt_overlap':0,'missing_original_training_classes':missing,'retained_choice_answer_mismatches':dict(unmatched),'original_v2_records_preserved_byte_for_byte':True,'all_derived_hashes_valid':True,'external_final_tests_loaded':False,'limits':['Original discrete labels checked against retained prompts/answers for 19 sources; ambiguous identical choices may count in multiple positions.','Open-response sources have row, provenance, index, context and nonempty checks; no exhaustive semantic correctness audit.','Exact grouping and prompt checks are exhaustive; semantic near-duplicate clearance is not claimed.','HotpotQA intentionally has no own development split.','Context filtering and original class imbalance are reported, not automatically rebalanced.']}
    (base/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print('CORRECTED_AUDIT_PASSED',sum(v for (s,p),v in counts.items() if p=='train'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);audit(Path(p.parse_args().data))
