"""Assemble comparable diagnostics without changing historical scores."""
import json
from collections import Counter,defaultdict
from next_run.prepare import ROOT,OUT
from next_run.analyze import repetition
from slm.broad_eval import score_general

def main():
    answer={};baselines=json.loads((ROOT/'runs/size-eval-preparation-2026-09-08/audit.json').read_text())['majority']
    for label in ['seen-train','matched-dev']:
        suite=json.loads((OUT/f'{label}-suite.json').read_text())
        rows=[json.loads(l) for l in (OUT/label/'results.jsonl').read_text().splitlines()]
        source_loss=json.loads((OUT/label/'answer-loss.json').read_text())['source_answer_loss']
        families=defaultdict(lambda:Counter(total=0,correct=0,scored=0,exact=0,repetition=0,token_limit=0))
        for r in rows:
            if r['source']=='hotpotqa':continue
            v=families[r['family']];v['total']+=1;v['correct']+=int(r.get('correct',False));v['scored']+=int('correct' in r)
            v['exact']+=r['expected'].strip()==r['generated'].strip();v['repetition']+=repetition(r['generated']);v['token_limit']+=r['stop_reason']=='token_limit'
        baseline={}
        for s,value in baselines.items():
            selected=[r for r in suite['general'] if r['source']==s]
            baseline[s]=dict(answer=value,correct=sum(score_general(r,value).get('correct',False) for r in selected),tasks=len(selected))
        loss=sum(v for k,v in source_loss.items() if k!='hotpotqa')/sum(k!='hotpotqa' for k in source_loss)
        answer[label]=dict(paired_sources=31,source_macro_answer_loss=loss,families=dict(families),totals=dict(sum(families.values(),Counter())),majority_baselines=baseline)
    original={(r['source'],r['id']):r for r in map(json.loads,(ROOT/'runs/size-27m-2026-09-08-3h/broad-eval/results.jsonl').read_text().splitlines())}
    probes=[json.loads(l) for l in (OUT/'length-probe/results.jsonl').read_text().splitlines()]
    length=dict(selected=len(probes),scored=sum('correct' in r for r in probes),correct=sum(r.get('correct',False) for r in probes),still_at_limit=sum(r['stop_reason']=='token_limit' for r in probes),repetition=sum(repetition(r['generated']) for r in probes),by_family=dict(Counter(r['family'] for r in probes)),limitation='Selected diagnostic cases; not representative and not a replacement for the fixed 256-token evaluation.')
    findings=json.loads((ROOT/'next_run/manual_findings.json').read_text())
    suspect={(r['source'],r['id']) for r in findings if r['manual_category'] in ['reference_quality_and_invalid_reasoning','reference_quality_and_repetition','reference_question_mismatch','reference_ambiguity']}
    sensitivity={}
    for size in ['27m','97m']:
        rows=[json.loads(l) for l in (ROOT/f'runs/size-{size}-2026-09-08-3h/broad-eval/results.jsonl').read_text().splitlines()]
        kept=[r for r in rows if (r['source'],r['id']) not in suspect]
        sensitivity[size]=dict(correct=sum(r.get('correct',False) for r in kept),scored=sum('correct' in r for r in kept),excluded_tasks=len(rows)-len(kept),posthoc=True)
    result=dict(train_development=answer,length_probe=length,reference_sensitivity=sensitivity,
        conclusions=['Small selected train/dev gap does not indicate strong pure memorization; sample cannot establish a universal cause.',
                     'Long-answer repetition is prominent; merely doubling output budget did not solve these selected cases.',
                     'Internal scores contain questionable original references; historical metrics retained and sensitivity separate.'])
    (OUT/'diagnostic-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
