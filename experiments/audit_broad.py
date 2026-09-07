"""Audit exact split separation, pinned bytes and retained source coverage."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from experiments.prepare_broad import sha
from slm.prepare import digest, normal
from slm.breadth import SOURCE_FAMILY


def main():
    base, parent = Path('data/v3-broad'), Path('data/v2')
    meta=json.loads((base/'manifest.json').read_text())
    assert sha(parent/'manifest.json')==meta['parent_manifest_sha256']
    assert sha(base/'records.jsonl')==meta['records_sha256']
    assert sha(base/'tokenizer.json')==meta['tokenizer']['sha256']==sha(parent/'tokenizer.json')
    remaining=(parent/'records.jsonl').stat().st_size
    prefix=hashlib.sha256()
    with (base/'records.jsonl').open('rb') as f:
        while remaining:
            block=f.read(min(remaining,1024*1024))
            assert block
            prefix.update(block)
            remaining-=len(block)
    assert prefix.hexdigest()==sha(parent/'records.jsonl')
    for filename, expected in meta['derived_files_sha256'].items():
        assert sha(base/filename)==expected, filename
    groups={'train':set(),'dev':set()}
    prompts={'train':set(),'dev':set()}
    counts=Counter()
    for line in (base/'records.jsonl').open():
        row=json.loads(line)
        assert row['original_split']=='train'
        groups[row['split']].add(row['group'])
        prompts[row['split']].add(digest(normal(row['prompt'])))
        counts[(row['source'],row['split'])]+=1
    assert groups['train'].isdisjoint(groups['dev'])
    assert prompts['train'].isdisjoint(prompts['dev'])
    assert {source for source,split in counts if split=='train'}==set(SOURCE_FAMILY)
    for (source,split),count in counts.items():
        assert count==meta['counts'][source+'.'+split]['records']
    report=dict(status='passed',sources=32,counts={'.'.join(k):v for k,v in counts.items()},
                exact_group_overlap=0,exact_prompt_overlap=0,original_v2_records_preserved_byte_for_byte=True,
                tokenizer_unchanged=True,all_derived_hashes_valid=True,external_final_tests_loaded=False,
                limitations='No complete semantic/near-duplicate audit. HotpotQA has no own development partition; narrative/SQL execution metrics remain incomplete.')
    (base/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('AUDIT_PASSED',sum(v for (s,p),v in counts.items() if p=='train'),flush=True)


if __name__=='__main__':
    main()
