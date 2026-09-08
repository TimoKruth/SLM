"""Admission screening of staged original training splits, not mixture conversion."""
import json
from collections import Counter
import pyarrow.parquet as pq
from tokenizers import Tokenizer
from next_run.prepare import ROOT, OUT, sha

def main():
    base=ROOT/'data/candidates-next-2026-09-08';tok=Tokenizer.from_file(str(ROOT/'data/v4-broad-corrected-2026-09-08/tokenizer.json'))
    tat=json.loads((base/'tatqa/train.json').read_text());texts=[];types=Counter();scales=Counter();groups=set()
    for record in tat:
        groups.add(record['table']['uid'])
        context='\n'.join(' | '.join(row) for row in record['table']['table'])+'\n'+'\n'.join(p['text'] for p in record['paragraphs'])
        for q in record['questions']:
            types[q['answer_type']]+=1;scales[q['scale']]+=1
            texts.append('<bos><task>Answer using the table and paragraphs.\n'+context+'\n'+q['question']+'<answer>'+str(q['answer'])+' '+q['scale']+'<eos>')
    lengths=[len(x.ids) for x in tok.encode_batch(texts)]
    table=pq.read_table(base/'multinli/train.parquet',columns=['premise','hypothesis','label','promptID','pairID','genre'])
    rows=table.to_pylist();labels=Counter(r['label'] for r in rows)
    features=json.loads(table.schema.metadata[b'huggingface'])['info']['features'];names=features['label']['names']
    assert set(labels)<=set(range(len(names)))
    sample=rows[::max(1,len(rows)//10000)]
    nli_lengths=[len(x.ids) for x in tok.encode_batch(['<bos><task>Classify the hypothesis as entailment, neutral, or contradiction.\n\nPremise: '+r['premise']+'\nHypothesis: '+r['hypothesis']+'<answer>'+names[r['label']]+'<eos>' for r in sample])]
    report=dict(status='screened_not_admitted',activated=False,training_sources_remain=32,
      tatqa=dict(questions=len(texts),table_groups=len(groups),answer_types=dict(types),scales=dict(scales),within_1024=sum(n<=1024 for n in lengths),length_measured=len(lengths),max_tokens=max(lengths),
        dataset_license='CC BY 4.0 according to pinned README',grouping='Whole table and originating financial report where identifiable, before any internal split',
        pending=['Preserve numeric scale and derivation semantics','Group related tables by source report where possible','Check exact and near overlap with existing data','Preserve CC BY 4.0 dataset attribution (separate from MIT code license)']),
      multinli=dict(records=len(rows),labels={names[k]:v for k,v in labels.items()},genres=dict(Counter(r['genre'] for r in rows)),premise_groups=len({r['premise'].strip() for r in rows}),prompt_groups=len({r['promptID'] for r in rows}),unique_ids=len({r['pairID'] for r in rows}),length_sample=len(sample),sample_within_1024=sum(n<=1024 for n in nli_lengths),sample_max_tokens=max(nli_lengths),
        license_note='OANC terms plus per-fiction-work CC BY/CC BY-SA/public-domain conditions; pinned README retained',grouping='Connected groups by promptID and normalized premise before split',pending=['Full token-length audit','Cross-source premise overlap, especially SNLI/ANLI','Deduplication and group audit','Does not add a new ability family']),
      provenance_manifest_sha256=sha(base/'manifest.json'))
    (base/'screening.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
