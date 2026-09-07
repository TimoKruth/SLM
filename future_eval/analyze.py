"""Read existing small evaluation artifacts; no model, tokenizer, or GPU work."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
from .metrics import LABELS,error_tags,wilson


def analyze(directory):
    rows=[json.loads(s) for s in (directory/'results.jsonl').read_text().splitlines()]
    by_source={};reviews=[]
    for source in sorted({r['source'] for r in rows}):
        subset=[r for r in rows if r['source']==source]
        scored=[r for r in subset if 'correct' in r and r.get('reference_parseable',True)]
        correct=sum(r['correct'] for r in scored)
        tags=Counter()
        for row in subset:
            diag=error_tags(row);tags.update(diag['tags'])
            reviews.append(dict(row,diagnostics=diag))
        item=dict(generated=len(subset),scored=len(scored),correct=correct,wilson_95=wilson(correct,len(scored)),
                  observed_tags=dict(tags),output_distribution=dict(Counter(r['generated'] for r in subset)) if source in LABELS else None)
        if source in LABELS:
            # These fixed policies do NOT choose the most frequent development answer.
            fixed={label:sum(r['expected'].strip().casefold()==label for r in subset) for label in LABELS[source]}
            item.update(fixed_label_policy_hits=fixed,uniform_random_expected_hits=len(subset)/len(LABELS[source]),
                        train_majority_baseline='Pending train-only full-corpus counts after campaign; never fit on dev labels.')
        by_source[source]=item
    return dict(by_source=by_source,rows=reviews,notes='Tags describe symptoms, not inferred internal causes. Wilson intervals are exploratory item-level intervals, not a family-transfer confidence interval.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--inputs',nargs='+',required=True)
    a=p.parse_args();out=Path(a.run);out.mkdir(parents=True,exist_ok=True)
    if (out/'analysis.json').exists():raise ValueError('Do not overwrite prior analysis')
    result={str(Path(name)):analyze(Path(name)) for name in a.inputs}
    (out/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    lines=['# Fehleranalyse vorhandener Antworten','','Automatische Tags beschreiben beobachtbare Symptome. Sie beweisen weder Verständnis noch die interne Ursache eines Fehlers. Die eingefrorenen Erfolgsscores werden nicht geändert.','']
    for name,r in result.items():
        lines += ['## '+name,'','| Quelle | Korrekt / bewertet | 95%-Intervall, grob | Beobachtete Symptome |','| --- | ---: | --- | --- |']
        for source,s in r['by_source'].items():
            ci=s['wilson_95']; interval='n/a' if ci is None else f'{ci[0]:.0%}–{ci[1]:.0%}'
            lines.append(f"| {source} | {s['correct']}/{s['scored']} | {interval} | {s['observed_tags']} |")
        lines += ['','Feste Label-Strategien (jeweils vorab definierte Antworten, keine auf Entwicklung gelernte Mehrheitsregel):','']
        for source,s in r['by_source'].items():
            if 'fixed_label_policy_hits' in s:
                lines.append(f"- {source}: {s['fixed_label_policy_hits']}; gleichverteiltes Raten erwartet {s['uniform_random_expected_hits']:.1f}/{s['generated']}.")
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    hashes={str(Path(n)/'results.jsonl'):hashlib.sha256((Path(n)/'results.jsonl').read_bytes()).hexdigest() for n in a.inputs}
    (out/'inputs.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print('Analyzed',sum(len(r['rows']) for r in result.values()),'existing answers; no model executed.')

if __name__=='__main__':main()
