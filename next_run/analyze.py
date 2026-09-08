"""Non-destructive error diagnostics of frozen answers, with explicit heuristic flags."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from slm.broad_eval import normalize, score_general
from next_run.prepare import ROOT, OUT

def repetition(text):
    words=text.casefold().split()
    if len(words)<20:return False
    grams=Counter(tuple(words[i:i+4]) for i in range(len(words)-3))
    return max(grams.values(),default=0)>=5 or bool(re.search(r'(.{3,40}?)\1{5,}',text))

def flags(row):
    return dict(token_limit=row.get('stop_reason')=='token_limit',repetition=repetition(row['generated']),
                empty=not row['generated'].strip(),incorrect=row.get('correct') is False,
                unscored='correct' not in row)

def main():
    suite=json.loads((ROOT/'runs/size-campaign-2026-09-08/suite.json').read_text())
    tasks={(r['source'],r['original_id']):r for r in suite['general']}
    report={};manual=[];probes=[]
    for size in ['27m','97m']:
        rows=[json.loads(line) for line in (ROOT/f'runs/size-{size}-2026-09-08-3h/broad-eval/results.jsonl').read_text().splitlines()]
        families=defaultdict(Counter)
        for r in rows:
            families[r['family']].update({k:int(v) for k,v in flags(r).items()});families[r['family']]['total']+=1
        report[size]=dict(families=dict(families),totals=dict(sum(families.values(),Counter())),flags_overlap=True)
        if size=='27m':
            for family in sorted(families):
                subset=[r for r in rows if r['family']==family]
                selected=[]
                for predicate in [lambda r:r.get('correct') is True,lambda r:flags(r)['token_limit'],lambda r:r.get('correct') is False and not repetition(r['generated']),lambda r:repetition(r['generated'])]:
                    candidate=next((r for r in subset if r not in selected and predicate(r)),None)
                    if candidate:selected.append(candidate)
                for r in selected:
                    task=tasks[(r['source'],r['id'])]
                    manual.append(dict(**r,prompt=task['prompt'],flags=flags(r)))
            limited=[r for r in rows if flags(r)['token_limit']]
            for repeating in [False,True]:
                chosen=sorted([r for r in limited if repetition(r['generated'])==repeating],key=lambda r:(r['family'],r['source'],r['id']))[:8]
                probes.extend(tasks[(r['source'],r['id'])] for r in chosen)
    (OUT/'error-flags.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'manual-sample.json').write_text(json.dumps(manual,ensure_ascii=False,indent=2)+'\n')
    (OUT/'length-probe-suite.json').write_text(json.dumps({**suite,'general':probes,'code':[],'memorization':[],
      'protocol':'Diagnostic selected 16 token-limit cases, half repetition heuristic positive. 512-token rerun; not a new official score.'},ensure_ascii=False)+'\n')
    print(json.dumps({s:r['totals'] for s,r in report.items()}));print('Manual cases',len(manual),'length probes',len(probes))

if __name__=='__main__':main()
