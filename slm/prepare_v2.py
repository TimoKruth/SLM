"""Expanded benchmark-only corpus, preserving original development reservations."""
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import warnings

import numpy as np
import pyarrow.parquet as pq
from tokenizers import Tokenizer
from .prepare import ROOT, digest, normal, text_of, code_key
from .collect import STAGE, sha

OUT = ROOT/'data/v2'
CODE = {'apps','mbpp','code_contests'}
WEIGHTS = dict(apps=.23,mbpp=.03,code_contests=.18,spider=.04,gsm8k=.08,math=.07,aqua_rat=.06,squad=.04,boolq=.015,hellaswag=.025,piqa=.025,winogrande=.02,arc=.015,sciq=.015,openbookqa=.01,commonsenseqa=.015,qasc=.015,quartz=.01,quarel=.01,ropes=.015,drop=.025,hotpotqa=.025,race=.02,snli=.025)


def reference_solutions(solutions, limit=8):
    out, seen = [], set()
    for value in sorted(solutions, key=lambda x: (len(x), x)):
        key = code_key(value)
        if key and key not in seen:
            out.append(value); seen.add(key)
        if len(out)==limit: break
    return out


def shingle_keys(text):
    words = re.findall(r'\w+', text.lower())
    return {digest(' '.join(words[i:i+5]))[:16] for i in range(max(0,len(words)-4))}


class CodeOverlap:
    """Near-duplicate candidate retrieval; exact Jaccard confirmation, not a proof of semantic independence."""
    def __init__(self):
        self.shingles=[]; self.index=defaultdict(set)
    def add(self,text):
        keys=shingle_keys(text); i=len(self.shingles); self.shingles.append(keys)
        for key in sorted(keys)[:16]: self.index[key].add(i)
    def overlaps(self,text):
        keys=shingle_keys(text)
        candidates=set().union(*(self.index.get(key,set()) for key in sorted(keys)[:16]))
        return any(len(keys & self.shingles[i])/max(1,len(keys | self.shingles[i])) >= .8 for i in candidates)


def converted(name,r,schemas):
    sid=str(r.get('id',r.get('query_id',r.get('name',''))))
    q = r.get('question',r.get('question_stem',''))
    group = q
    if name=='sciq':
        p='Answer the question using the passage.\n\nPassage: '+r['support']+'\n\nQuestion: '+q
        a=r['correct_answer'];group=r['support'] or q
    elif name in ['openbookqa','commonsenseqa','qasc','quartz']:
        choices=r['choices']; a=choices['text'][choices['label'].index(r['answerKey'])]
        p='Answer this question.\n\n'+q+'\n'+'\n'.join(f'{l}. {t}' for l,t in zip(choices['label'],choices['text']))
        if name=='quartz':p='Use this knowledge: '+r['para']+'\n\n'+p;group=r['para_id']
        if name=='qasc':a=r['fact1']+' '+r['fact2']+'\nAnswer: '+a
    elif name=='quarel':
        # Original options are embedded in the question. Preserve their explicit A/B interface.
        p='Choose the correct option, A or B.\n\n'+q;a=['A','B'][r['answer_index']]
    elif name=='ropes':
        p='Answer using the background and situation.\n\nBackground: '+r['background']+'\nSituation: '+r['situation']+'\nQuestion: '+q
        a=r['answers']['text'][0];group=r['background']
    elif name=='drop':
        p='Answer the question using the passage.\n\nPassage: '+r['passage']+'\n\nQuestion: '+q
        a='; '.join(r['answers_spans']['spans']);group=r['section_id']
    elif name=='hotpotqa':
        # All original distractor paragraphs retained, never select context using the answer.
        context='\n\n'.join(title+': '+''.join(sentences) for title,sentences in zip(r['context']['title'],r['context']['sentences']))
        p='Answer the question using the passages.\n\n'+context+'\n\nQuestion: '+q;a=r['answer']
        # The exact question is the task group. Shared-document overlap is separately marked in manifest.
        group=q
    elif name=='race':
        p='Answer the question using the passage.\n\nPassage: '+r['article']+'\n\nQuestion: '+q+'\n'+'\n'.join(f'{chr(65+i)}. {v}' for i,v in enumerate(r['options']))
        a=r['options'][ord(r['answer'])-65];group=r['article'];sid=r['example_id']+':'+digest(q)[:12]
    elif name=='snli':
        if r['label'] not in [0,1,2]: return None
        p='Classify the hypothesis as entailment, neutral, or contradiction.\n\nPremise: '+r['premise']+'\nHypothesis: '+r['hypothesis']
        a=['entailment','neutral','contradiction'][r['label']];group=r['premise']
    elif name=='aqua_rat':
        p='Solve this math problem and explain your calculation.\n\n'+q+'\n'+'\n'.join(r['options'])
        if r['correct'] not in 'ABCDE' or len(r['correct'])!=1:return None
        a=r['rationale']+'\nAnswer: '+r['options'][ord(r['correct'])-65]
    elif name=='spider':
        schema=schemas[r['db_id']]
        tables=[]
        for i,t in enumerate(schema['table_names_original']):
            cols=[f'{col} {kind}' for (table,col),kind in zip(schema['column_names_original'],schema['column_types']) if table==i]
            tables.append(t+'('+', '.join(cols)+')')
        foreign=[]
        for aidx,bidx in schema['foreign_keys']:
            ta,ca=schema['column_names_original'][aidx];tb,cb=schema['column_names_original'][bidx]
            foreign.append(f'{schema["table_names_original"][ta]}.{ca} = {schema["table_names_original"][tb]}.{cb}')
        p='Write a SQL query. Output SQL only.\n\nSchema:\n'+'\n'.join(tables)+'\nForeign keys: '+'; '.join(foreign)+'\n\nQuestion: '+q
        a=r['query'];group=r['db_id']
    elif name=='code_contests':
        q=r['description'];p='Write a Python 3 program that solves this problem. Output code only.\n\n'+q
        answers=reference_solutions([v for lang,v in zip(r['solutions']['language'],r['solutions']['solution']) if lang==3])
        return sid,p,answers,q
    else:raise ValueError(name)
    return sid,p,[a],group


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'manifest.json').exists(), 'Refuse to overwrite frozen v2 data'
    source_manifest=json.loads((STAGE/'manifest.json').read_text())
    schemas={r['db_id']:r for r in json.loads((STAGE/'raw/spider/train_schemas.json').read_text())}
    # Original MBPP/APPS interface metadata; never show test assertions or reference bodies in prompts.
    interfaces={}
    for raw in pq.read_table(ROOT/'data/raw/mbpp/full/train-00000-of-00001.parquet').to_pylist():
        tree=ast.parse(raw['test_list'][0]);calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        defined={node.name for node in ast.parse(raw['code']).body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
        calls=[node for node in calls if node.func.id in defined]
        if calls: interfaces[('mbpp',str(raw['task_id']))]=calls[0].func.id
    for line in (ROOT/'data/raw/apps/train.jsonl').open():
        raw=json.loads(line);io=json.loads(raw['input_output'] or '{}', parse_int=str)
        if io.get('fn_name'):interfaces[('apps',str(raw['id']))]=io['fn_name']
    rows=[];prompts=set();old_train_code=set();old_dev_code=set();overlap=CodeOverlap();reject=Counter()
    for line in (ROOT/'data/records.jsonl').open():
        row=json.loads(line)
        fn=interfaces.get((row['source'],row['original_id']))
        if fn:row['prompt']+='\n\nRequired function name: '+fn
        rows.append(row);prompts.add(digest(normal(row['prompt'])))
        if row['source'] in CODE:
            key=code_key(row['answer'])
            if key:(old_dev_code if row['split']=='dev' else old_train_code).add(key)
            if row['variant']==0:overlap.add(row['prompt'].split('\n\n',1)[-1].split('\n\nStarter code:')[0].split('\n\nRequired function name:')[0])
    old_count=len(rows)
    old_dev_groups={r['group'] for r in rows if r['split']=='dev'}
    old_questions=set()
    for r in rows:
        body=r['prompt'].split('\n\n',1)[-1].split('\n\nRequired function name:')[0]
        if 'Question: ' in body:body=body.rsplit('Question: ',1)[-1]
        if r['source']=='arc':body=body.split('\n',1)[0]
        body=body.split('\n\nStarter code:')[0].split('\nOptions:')[0]
        old_questions.add(digest(normal(body)))
    for name,meta in source_manifest['sources'].items():
        n=0
        for file in meta['files']:
            path=STAGE/'raw'/name/file['path']
            if sha(path)!=file['sha256']:raise ValueError(f'Corrupt source: {path}')
            columns=['name','description','solutions'] if name=='code_contests' else None
            for batch in pq.ParquetFile(path).iter_batches(batch_size=32 if name=='code_contests' else 512,columns=columns):
                for raw in batch.to_pylist():
                    n+=1
                    question=raw.get('question',raw.get('question_stem',raw.get('description','')))
                    if question and digest(normal(question)) in old_questions:
                        reject[name+'.duplicate_original_question']+=1;continue
                    if name=='hotpotqa' and any(digest('article:'+title) in old_dev_groups or digest('article:'+title.replace(' ','_')) in old_dev_groups for title in raw['context']['title']):
                        reject[name+'.original_dev_article_overlap']+=1;continue
                    try: value=converted(name,raw,schemas)
                    except (KeyError,ValueError,IndexError) as e:
                        raise ValueError(f'Invalid conversion {name}:{n}: {e}') from e
                    if value is None:reject[name+'.invalid_label']+=1;continue
                    sid,p,answers,g=value
                    if not answers or not all(a and a.strip() for a in answers):reject[name+'.empty_answer']+=1;continue
                    key=digest(normal(p))
                    if key in prompts:reject[name+'.duplicate_prompt']+=1;continue
                    if name=='code_contests' and overlap.overlaps(g):reject[name+'.near_duplicate_existing_code_task']+=1;continue
                    group=digest(name+':'+normal(g));split='dev' if int(digest('expanded-v2:'+group)[:8],16)%100<5 else 'train'
                    if name=='code_contests':
                        keys={code_key(a) for a in answers}
                        if keys & old_dev_code or (split=='dev' and keys & old_train_code):reject[name+'.reference_overlap_original_partition']+=1;continue
                        overlap.add(g)
                    prompts.add(key)
                    for i,a in enumerate(answers):rows.append(dict(source=name,original_id=sid or str(n-1),variant=i,group=group,split=split,prompt=p,answer=a,original_split='train'))
        print(name,n,'original rows processed; total pairs',len(rows),flush=True)
    # Preserve old reservations. Remove new training groups that collide with any dev code reference.
    dev_keys={code_key(r['answer']) for r in rows if r['source'] in CODE and r['split']=='dev'};dev_keys.discard(None)
    bad={r['group'] for r in rows[old_count:] if r['source'] in CODE and r['split']=='train' and code_key(r['answer']) in dev_keys}
    rows=[r for r in rows if r['group'] not in bad]
    reject['new_training_groups_sharing_dev_code']=len(bad)
    # Keep all HotpotQA in training: its shared documents make a cheap task split insufficient.
    # This source is monitored through other QA dev families, not through a leaky per-question holdout.
    for r in rows:
        if r['source']=='hotpotqa':r['split']='train'
    shutil.copy2(ROOT/'data/tokenizer.json',OUT/'tokenizer.json')
    tok=Tokenizer.from_file(str(OUT/'tokenizer.json'))
    stats=defaultdict(Counter);groups=defaultdict(set);indices=defaultdict(list);handles={}
    for name in WEIGHTS:
        for split in ['train','dev']:
            for suffix in ['bin','mask.bin']:handles[(name,split,suffix)]=(OUT/f'{name}.{split}.{suffix}').open('wb')
    with (OUT/'records.jsonl').open('w') as out:
        for start in range(0,len(rows),512):
            batch=rows[start:start+512]
            for row,encoding in zip(batch,tok.encode_batch([text_of(r) for r in batch])):
                key=(row['source'],row['split']);ids=encoding.ids
                if len(ids)>1024:stats[key]['excluded_over_1024']+=1;continue
                offset=stats[key]['tokens'];indices[key].append((offset,len(ids)))
                mask=np.ones(len(ids),dtype=np.uint8);mask[:ids.index(tok.token_to_id('<answer>'))+1]=0
                np.asarray(ids,dtype=np.uint16).tofile(handles[(*key,'bin')]);mask.tofile(handles[(*key,'mask.bin')])
                stats[key]['records']+=1;stats[key]['tokens']+=len(ids);groups[key].add(row['group']);out.write(json.dumps(row,ensure_ascii=False)+'\n')
    for handle in handles.values():handle.close()
    for name in WEIGHTS:
        for split in ['train','dev']:np.save(OUT/f'{name}.{split}.index.npy',np.asarray(indices[(name,split)],dtype=np.int64).reshape(-1,2))
    for name in WEIGHTS:
        assert stats[(name,'train')]['tokens']>1025,name
        assert groups[(name,'train')].isdisjoint(groups[(name,'dev')]),name
    eval_weights={n:w for n,w in WEIGHTS.items() if stats[(n,'dev')]['tokens']>1025}
    original=json.loads((ROOT/'data/manifest.json').read_text())
    manifest=dict(version=2,sources={**original['sources'],**source_manifest['sources']},counts={'.'.join(k):dict(v,groups=len(groups[k])) for k,v in stats.items()},tokenizer=dict(vocab_size=tok.get_vocab_size(),sha256=sha(OUT/'tokenizer.json'),trained_on='Frozen original v1 train-only tokenizer; not retrained'),max_record_tokens=1024,source_weights=WEIGHTS,evaluation_weights=eval_weights,rejections=dict(reject),original_manifest_sha256=sha(ROOT/'data/manifest.json'),candidate_manifest_sha256=sha(STAGE/'manifest.json'),records_sha256=sha(OUT/'records.jsonl'),external_tests_loaded=False,excluded_evaluation_families=source_manifest['excluded_evaluation_families'],decontamination_status='Original development groups preserved. Exact new prompts and original question duplicates excluded; HotpotQA matching original reserved SQuAD article titles excluded. Code task near-duplicate retrieval via bottom-16 five-word shingles, Jaccard >=0.8; identical Python AST reference overlaps filtered by whole task. No full semantic or external test audit. HotpotQA has no internal dev split due document sharing.',derived_files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.suffix in ['.bin','.npy']})
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest['counts'],indent=2),flush=True);print('DATA_READY',flush=True)


if __name__=='__main__':main()
