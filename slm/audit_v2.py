"""Verify frozen partitions and records against manifest before the six-hour run."""
import json
from collections import Counter
from datetime import datetime
from .prepare_v2 import OUT,CODE,ROOT
from .prepare import code_key,digest,normal
from .collect import sha


def main():
    m=json.loads((OUT/'manifest.json').read_text())
    old_dev={json.loads(line)['group'] for line in (ROOT/'data/records.jsonl').open() if json.loads(line)['split']=='dev'}
    groups={'train':set(),'dev':set()};prompts={'train':set(),'dev':set()};codes={'train':set(),'dev':set()};counts=Counter()
    for line in (OUT/'records.jsonl').open():
        r=json.loads(line);s=r['split'];assert r['original_split']=='train'
        groups[s].add(r['group']);prompts[s].add(digest(normal(r['prompt'])));counts[(r['source'],s)]+=1
        if r['source'] in CODE:
            key=code_key(r['answer']);assert key;codes[s].add(key)
    assert groups['train'].isdisjoint(groups['dev'])
    assert groups['train'].isdisjoint(old_dev)
    assert prompts['train'].isdisjoint(prompts['dev'])
    assert codes['train'].isdisjoint(codes['dev'])
    assert sha(OUT/'records.jsonl')==m['records_sha256']
    for (name,split),count in counts.items():assert count==m['counts'][name+'.'+split]['records']
    result=dict(time=datetime.now().astimezone().isoformat(),source_count=len(m['sources']),train_pairs=sum(v for (n,s),v in counts.items() if s=='train'),dev_pairs=sum(v for (n,s),v in counts.items() if s=='dev'),train_tokens=sum(v.get('tokens',0) for k,v in m['counts'].items() if k.endswith('.train')),group_overlap=0,original_development_groups_in_training=0,exact_prompt_overlap=0,python_ast_overlap=0,records_sha256=m['records_sha256'],manifest_sha256=sha(OUT/'manifest.json'),semantic_audit_complete=False)
    (OUT/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
