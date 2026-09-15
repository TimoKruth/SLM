"""Prepare larger diagnostic coverage and reserve fresh metadata; CPU-only, no evaluation."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from tokenizers import Tokenizer
if __package__:
    from .analyze_parameters import digest, scorer
else:
    from analyze_parameters import digest, scorer


def rank(row, salt):
    return hashlib.sha256((salt+'|'+row['source']+'|'+row['group']+'|'+str(row['original_id'])+'|'+str(row.get('variant',0))).encode()).hexdigest()


def select_groups(rows, quota, salt, excluded=()):
    used=set(excluded); selected=[]
    for row in sorted(rows, key=lambda row: rank(row, salt)):
        if row['group'] not in used:
            selected.append(row); used.add(row['group'])
            if len(selected)==quota:break
    return selected


def prepare(project, output, scorer_path, review_path):
    project=project.resolve(); output=output.resolve()
    assert not output.exists()
    hashes={}
    def read(path):
        hashes[str(path)]=digest(path); return json.loads(path.read_text())
    campaign=project/'runs/long-horizon-round2-resume-2026-09-14'
    coverage=read(project/'runs/parameter-error-analysis-2026-09-15-verified/analysis.json')['coverage']['confirmation']
    targets={r['source']:64 if r['scored'] else 16 for r in coverage}
    scored_sources={r['source'] for r in coverage if r['scored']}
    family={r['source']:r['family'] for r in coverage}
    # All existing local SLM campaign suite files, deduplicated through worktree symlinks.
    paths=set(p.resolve() for w in project.parent.glob('SLM*') for p in (w/'runs').glob('*/*suite.json'))
    blocked=set(); suite_files=[]
    for path in sorted(paths):
        suite=read(path)
        if not isinstance(suite,dict) or 'general' not in suite:continue
        for part in ['general','code','memorization']:
            blocked.update(r['group'] for r in suite.get(part,[]) if 'group' in r)
        suite_files.append(str(path))
    # Diagnostic tasks come only from suites of explicitly completed campaigns,
    # never from another thread's prepared but unopened confirmation tasks.
    opened=set()
    consumed=[('size-campaign-2026-09-08','suite.json'),
              ('research-pilot-2026-09-09','confirmation-suite.json'),
              ('research-round2-2026-09-09','confirmation-suite.json'),
              ('parameter-study-timeout-recovery-2026-09-10','confirmation-suite.json'),
              ('long-horizon-resume-2026-09-10','confirmation-suite.json'),
              ('long-horizon-round2-resume-2026-09-14','confirmation-suite.json')]
    for directory,name in consumed:
        folder=project/'runs'/directory
        status=read(folder/'status.json'); assert status['status']=='completed',directory
        old=read(folder/name)
        opened.update(r['group'] for r in old['general'])
    assert opened<=blocked
    prior=read(project/'next_run/manual_findings.json'); reviews=read(review_path)
    excluded={(r['source'],str(r['id'])) for r in prior if r['manual_category'].startswith('reference_')}
    excluded.update((r['source'],str(r['id'])) for r in reviews if r['category'].startswith('reference_'))
    tok_path=project/'runs/size-27m-2026-09-09-plus3h/tokenizer.json'
    hashes[str(tok_path)]=digest(tok_path); tokenizer=Tokenizer.from_file(str(tok_path))
    hashes[str(scorer_path)]=digest(scorer_path); final=scorer(scorer_path)['final_answer']
    pools={'opened':defaultdict(list),'fresh':defaultdict(list)}; train=set(); failures=defaultdict(Counter)
    records=project/'data/v4-broad-corrected-2026-09-08/records.jsonl'
    stream_hash=hashlib.sha256()
    with records.open('rb') as stream:
        for line in stream:
            stream_hash.update(line); row=json.loads(line)
            if row['split']=='train':train.add(row['group']);continue
            if row['split']!='dev' or row['source'] not in targets:continue
            source=row['source']
            if (source,str(row['original_id'])) in excluded:
                failures[source]['known_reference_issue']+=1;continue
            prompt='<bos><question>\n'+row['prompt']+'\n<answer>\n'
            if len(tokenizer.encode(prompt+row['answer']+'<eos>\n').ids)>1024:
                failures[source]['reference_over_context']+=1;continue
            # Full 256-token generation allowance must fit without prompt truncation.
            if len(tokenizer.encode(prompt).ids)+256>1024:
                failures[source]['prompt_without_full_generation_room']+=1;continue
            if source in {'gsm8k','math','aqua_rat','qasc'} and final(row['answer'],source) is None:
                failures[source]['reference_unparseable']+=1;continue
            if row['group'] in opened:
                pools['opened'][source].append(row)
            elif row['group'] not in blocked:
                pools['fresh'][source].append(row)
    hashes[str(records)]=stream_hash.hexdigest()
    diagnostic=[]; fresh=[]; audit={}
    for source, quota in sorted(targets.items()):
        opened_rows=[r for r in pools['opened'][source] if r['group'] not in train]
        fresh_rows=[r for r in pools['fresh'][source] if r['group'] not in train]
        selected=select_groups(opened_rows,quota,'parameter-diagnostic-v1-20260915',{r['group'] for r in diagnostic})
        diagnostic.extend(selected)
        unique=select_groups(fresh_rows,len(fresh_rows)+1,'parameter-fresh-reserve-v1-20260915',{r['group'] for r in fresh})
        fresh.extend(unique)
        audit[source]=dict(family=family[source],scored=source in scored_sources,target_per_suite=quota,
                           diagnostic_available_groups=len({r['group'] for r in opened_rows}),diagnostic_selected=len(selected),
                           fresh_available_groups=len(unique),confirmation_deficit=max(0,quota-len(unique)),
                           filter_counts=dict(failures[source]))
    dg={r['group'] for r in diagnostic}; fg={r['group'] for r in fresh}
    assert len(dg)==len(diagnostic) and len(fg)==len(fresh)
    assert not dg&train and not fg&train and not fg&blocked and not dg&fg
    assert dg<=opened
    output.mkdir(parents=True)
    (output/'STOP').write_text('Evaluation preparation only. No training or model evaluation launched.\n')
    template=read(campaign/'confirmation-suite.json')
    suite=dict(template,general=diagnostic,code=[],memorization=[],protocol='Expanded diagnostic suite from already-opened internal dev groups. Not fresh confirmation or external transfer. Same 25-source coverage as round2 confirmation. One task per group; context plus 256 generation tokens fits; original references and scorer retained, known reference issues excluded for this new diagnostic only.')
    (output/'diagnostic-suite.json').write_text(json.dumps(suite,indent=2)+'\n')
    metadata=[{k:r[k] for k in ['source','original_id','variant','group','split']} for r in fresh]
    (output/'fresh-reserve-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    ready=all(r['diagnostic_selected']==r['target_per_suite'] for r in audit.values())
    confirmation_possible=all(not r['confirmation_deficit'] for r in audit.values())
    result=dict(status='diagnostic_prepared_confirmation_incomplete' if ready else 'coverage_limited_preparation',
                diagnostic_ready=ready,confirmation_ready=False,confirmation_quota_possible=confirmation_possible,
                diagnostic_tasks=len(diagnostic),diagnostic_scored=sum(r['source'] in scored_sources for r in diagnostic),
                fresh_reserved_groups=len(fresh),coverage=audit,training_group_overlap=0,opened_fresh_group_overlap=0,
                diagnostic_fresh_group_overlap=0,excluded_suite_files=suite_files,diagnostic_consumed_suites=consumed,
                diagnostic_suite_sha256=digest(output/'diagnostic-suite.json'),fresh_metadata_sha256=digest(output/'fresh-reserve-metadata.json'),
                limitation='Fresh reserve is metadata only; no new confirmation answers or model scores inspected. Existing v4 dev loss may have exposed fresh groups historically. New training comparison, token endpoint and selection rule remain unspecified; no confirmation suite declared ready. Original official external tests remain unopened.')
    (output/'coverage-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    for path,h in hashes.items():assert digest(Path(path))==h
    (output/'provenance.json').write_text(json.dumps(dict(inputs=hashes,script_sha256=digest(Path(__file__))),indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['project','output','scorer','reviews']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prepare(a.project,a.output,a.scorer,a.reviews)
