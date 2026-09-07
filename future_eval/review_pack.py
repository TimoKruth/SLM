"""Generate blinded forms for open-answer review; no invented automatic quality scores."""
import hashlib,json
from pathlib import Path


def build(suite_path,inputs,output):
    tasks={(r['source'],r['original_id']):r for r in json.loads(Path(suite_path).read_text())['general']}
    forms=[];key={}
    for path in inputs:
        for line in Path(path).read_text().splitlines():
            r=json.loads(line)
            if r['source'] not in {'hellaswag','piqa'}:continue
            uid=hashlib.sha256((str(path)+'\0'+r['source']+'\0'+r['id']).encode()).hexdigest()[:16]
            forms.append(dict(review_id=uid,prompt=tasks[(r['source'],r['id'])]['prompt'],response=r['generated'],
                reference_one_possible_answer=r['expected'],scores={'task_fulfilment':None,'context_consistency':None,'practical_or_narrative_coherence':None,'repetition':None},
                rationale=None,reviewer=None,reviewed_at=None))
            key[uid]=dict(file=str(path),source=r['source'],id=r['id'])
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'forms.jsonl').exists():raise ValueError('Do not overwrite review forms')
    (output/'forms.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in sorted(forms,key=lambda x:x['review_id'])))
    (output/'unblind-key.json').write_text(json.dumps(key,indent=2)+'\n')
    (output/'RUBRIC.md').write_text('''# Offene Antworten: getrennte qualitative Prüfung

Die 24 vorhandenen Antworten sind nach einer deterministischen ID gemischt; Modellnamen stehen nur im separaten Zuordnungsschlüssel. Stil kann die Herkunft trotzdem verraten.

Aufgabenerfüllung, Kontexttreue und praktische/narrative Schlüssigkeit jeweils mit 0 (fehlt/falsch), 1 (teilweise) oder 2 (erfüllt) bewerten. Wiederholung separat: 0 keine, 1 störend, 2 dominierend. Für jede Antwort kurze überprüfbare Begründung, Reviewer und Datum angeben. Unklare Fälle unbewertet lassen und begründen. Die Referenz ist eine mögliche Antwort; Wortlautgleichheit ist kein Qualitätsmaß.

Keine Bewertung ist vorausgefüllt. Für belastbarere Aussagen zwei unabhängige Bewertungen und dokumentierte Klärung von Abweichungen einplanen. Agentengestützte Bewertungen als solche kennzeichnen. Diese Formulare sind zusätzliche Entwicklungsdiagnostik, kein offizieller Benchmark-Score.
''')
    return len(forms)
