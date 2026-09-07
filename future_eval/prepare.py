"""Idle-only CPU preparation: train baselines, larger dev suite, sampled overlap and SQL."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import time
from .metrics import LABELS,sql_compare


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def priority(row):
    return hashlib.sha256((row['source']+'\0'+row['group']).encode()).hexdigest()


def retain(pool,row,limit):
    """Deterministic bounded distinct-group sample, independent of model outputs/labels."""
    key=priority(row)
    if key in pool:return
    if len(pool)<limit:pool[key]=row
    elif key<max(pool):
        del pool[max(pool)];pool[key]=row


def shingles(text):
    words=re.findall(r'\w+',text.casefold())
    return {tuple(words[i:i+5]) for i in range(len(words)-4)}


def near_duplicates(training, development):
    """Candidate retrieval by rare hash shingles, verified by Jaccard; sampled, not exhaustive."""
    import zlib
    inverted=defaultdict(list);features=[]
    for row in training:
        ss=shingles(row['prompt']);features.append(ss)
        if len(ss)<20:continue
        for value in sorted({zlib.crc32(' '.join(s).encode()) for s in ss})[:4]:
            inverted[value].append(len(features)-1)
    matches=[]
    for row in development:
        ss=shingles(row['prompt'])
        if len(ss)<20:continue
        candidates=set()
        for value in sorted({zlib.crc32(' '.join(s).encode()) for s in ss})[:4]:candidates.update(inverted[value])
        for i in sorted(candidates):
            overlap=len(ss&features[i])/len(ss|features[i])
            if overlap>=.85:
                other=training[i]
                matches.append(dict(dev_source=row['source'],dev_id=row['original_id'],train_source=other['source'],train_id=other['original_id'],jaccard=overlap))
    return matches


def scan(base, per_source, cutoff):
    from tokenizers import Tokenizer
    tok=Tokenizer.from_file(str(base/'tokenizer.json'))
    records_hash=hashlib.sha256()
    counts=Counter();labels=defaultdict(Counter);train=defaultdict(dict);dev=defaultdict(dict)
    length_stats=defaultdict(Counter);group_labels=defaultdict(set)
    for n,line in enumerate((base/'records.jsonl').open()):
        if n%10000==0 and time.time()>=cutoff:raise TimeoutError('Preparation time budget reached')
        records_hash.update(line.encode())
        row=json.loads(line);source=row['source'];split=row['split'];counts[(source,split)]+=1
        if row.get('original_split')!='train':raise ValueError('Unexpected original non-train record')
        if row.get('variant',0)!=0:continue
        if split=='train':
            if source in LABELS:
                label=row['answer'].strip().casefold()
                # Count each original task/label once; repeated variants cannot dominate.
                key=(row['original_id'],label)
                if key not in group_labels[source]:labels[source][label]+=1;group_labels[source].add(key)
            retain(train[source],row,512)
        elif split=='dev':
            prompt_len=len(tok.encode('<bos><question>\n'+row['prompt']+'\n<answer>\n').ids)
            answer_len=len(tok.encode(row['answer']).ids)
            length_stats[source]['rows']+=1
            length_stats[source]['prompt_tokens']+=prompt_len
            length_stats[source]['answer_tokens']+=answer_len
            if prompt_len+answer_len>1024:length_stats[source]['full_reference_over_context']+=1
            if answer_len>256:length_stats[source]['reference_over_256_generation_tokens']+=1
            if prompt_len>768:
                length_stats[source]['prompt_leaves_under_256_tokens']+=1
                continue
            bucket=0 if prompt_len<=256 else (1 if prompt_len<=512 else 2)
            retain(dev[(source,bucket)],row,per_source)
    expected=json.loads((base/'manifest.json').read_text()).get('records_sha256')
    if expected and records_hash.hexdigest()!=expected:raise ValueError('Records checksum mismatch')
    selected=[]
    for source in sorted({key[0] for key in dev}):
        buckets=[sorted(dev[(source,b)].items()) for b in range(3)]
        groups=set()
        while len(groups)<per_source and any(buckets):
            for pool in buckets:
                if pool and len(groups)<per_source:
                    _,row=pool.pop(0)
                    if row['group'] not in groups:groups.add(row['group']);selected.append(row)
    majority={s:sorted(c.items(),key=lambda x:(-x[1],x[0]))[0][0] for s,c in labels.items() if c}
    return dict(counts={'.'.join(k):v for k,v in counts.items()},label_counts={s:dict(c) for s,c in labels.items()},majority=majority,
                selected=selected,training_sample=[r for pool in train.values() for r in pool.values()],length_stats=dict(length_stats))


def prepare(base, out, suite_path, cutoff, per_source=32):
    result=scan(base,per_source,cutoff)
    metadata=json.loads((base/'manifest.json').read_text())
    result['prior_filter_counts']={name:{k:v for k,v in values.items() if 'exclud' in k or 'reject' in k} for name,values in metadata.get('counts',{}).items() if isinstance(values,dict)}
    old=json.loads(suite_path.read_text())
    if sha(base/'tokenizer.json')!=old['tokenizer_sha256']:raise ValueError('Tokenizer mismatch')
    rows=result.pop('selected');training=result.pop('training_sample')
    result['sampled_near_duplicates']=near_duplicates(training,rows)
    result['near_duplicate_scope']=dict(train_sample=len(training),dev_sample=len(rows),threshold=.85,
        limitation='Bounded deterministic sample, four shingle keys; false negatives possible. No semantic or complete contamination clearance.')
    suite=dict(version=2,general=rows,memorization=[],code=old['code'],tokenizer_sha256=old['tokenizer_sha256'],
        data_manifest_sha256=sha(base/'manifest.json'),protocol='Future internal development only; up to 32 distinct groups/source, round-robin across three prompt-length strata. Prompt leaves 256 tokens; report long-reference exclusions. Not substituted into the current A/B campaign.')
    (out/'suite-v2.json').write_text(json.dumps(suite,ensure_ascii=False)+'\n')
    result['selected_per_source']=dict(Counter(r['source'] for r in rows))
    comparisons={}
    for name in ['broad-baseline-2026-09-07','broad-families-2026-09-07-3h','broad-sources-2026-09-07-3h']:
        path=base.parents[1]/'runs'/name/'broad-eval/results.jsonl'
        if not path.exists():continue
        values=[json.loads(l) for l in path.read_text().splitlines()];summary={}
        for source,majority in result['majority'].items():
            subset=[r for r in values if r['source']==source]
            if subset:summary[source]=dict(prediction_learned_only_from_train=majority,n=len(subset),
                baseline_correct=sum(r['expected'].strip().casefold()==majority for r in subset),model_correct=sum(r.get('correct',False) for r in subset))
        comparisons[name]=summary
    result['train_majority_comparison']=comparisons
    from .analyze import analyze
    result['post_campaign_error_summary']={name:analyze(base.parents[1]/'runs'/name/'broad-eval')['by_source'] for name in comparisons}
    # Read only the pinned WikiSQL original training parquet, after the campaign is idle.
    import pyarrow.parquet as pq
    stage=base.parent/'candidates-wave3-2026-09-07';meta=json.loads((stage/'manifest.json').read_text())['sources']['wikisql']
    tables={};wanted={r['original_id'] for r in old['general']+rows if r['source']=='wikisql'}
    for item in meta['files']:
        path=stage/'raw/wikisql'/item['path']
        if meta['original_split']!='train' or sha(path)!=item['sha256']:raise ValueError('WikiSQL source check failed')
        for batch in pq.ParquetFile(path).iter_batches(batch_size=128,use_threads=False):
            if time.time()>=cutoff:raise TimeoutError('Preparation time budget reached')
            for raw in batch.to_pylist():
                uid=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()
                if uid in wanted:tables[uid]=raw['table']
    (out/'wikisql-tables.json').write_text(json.dumps(tables,ensure_ascii=False)+'\n')
    sql=[]
    for name in comparisons:
        path=base.parents[1]/'runs'/name/'broad-eval/results.jsonl'
        for line in path.read_text().splitlines():
            row=json.loads(line)
            if row['source']=='wikisql':
                status=sql_compare(row['generated'],row['expected'],tables[row['id']]) if row['id'] in tables else {'status':'missing_original_table'}
                sql.append(dict(run=name,id=row['id'],**status))
    result['sql_diagnostics']=sql
    (out/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (out/'REPORT.md').write_text('# Vorbereitung nach der Kampagne\n\n'+f"Neue Entwicklungsauswahl: {len(rows)} Aufgaben. Train-only-Mehrheitsregeln, Kontextlängen, begrenzte Dublettenprüfung und SQL-Diagnosen: `audit.json`.\n\nDiese Auswahl ersetzt nicht die eingefrorene A/B-Auswertung. Dublettentreffer benötigen Prüfung; keine vollständige semantische Freigabe. SQL ist ein SQLite-Proxy auf einer Originaltabelle, kein offizieller Score.\n")


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--data',default='data/v3-broad');p.add_argument('--suite',default='data/broad-checks-2026-09-07/suite.json');p.add_argument('--seconds',type=int,default=1200);p.add_argument('--per-source',type=int,default=32)
    a=p.parse_args()
    from slm_perf.__main__ import active_jobs
    if active_jobs():raise RuntimeError('Heavy preparation waits until GPU jobs are idle')
    out=Path(a.run);out.mkdir(parents=True,exist_ok=True)
    if (out/'audit.json').exists() or (out/'suite-v2.json').exists():raise ValueError('Do not overwrite preparation')
    os.nice(10)
    prepare(Path(a.data).resolve(),out,Path(a.suite),time.time()+a.seconds,a.per_source)
    print('Future suite and diagnostics prepared; current run inputs unchanged.')

if __name__=='__main__':main()
