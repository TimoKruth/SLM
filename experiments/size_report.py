"""Offline, capability-wise report for a frozen model-size campaign."""
import json
from collections import Counter
from pathlib import Path
from slm.breadth import FAMILIES
from slm.train import atomic_json
from future_eval.metrics import sql_compare


def read(path):return json.loads(Path(path).read_text())


def rows(path):return [json.loads(s) for s in Path(path).read_text().splitlines()]


def details(run, evaluation, majority, tables):
    summary=read(evaluation/'summary.json');answers=rows(evaluation/'results.jsonl')
    baselines={}
    for source,label in majority.items():
        subset=[r for r in answers if r['source']==source]
        baselines[source]=dict(train_only_prediction=label,scored=len(subset),
            baseline_correct=sum(r['expected'].strip().casefold()==label for r in subset),
            model_correct=sum(r.get('correct',False) for r in subset))
    sql=[]
    for row in answers:
        if row['source']=='wikisql':
            value=sql_compare(row['generated'],row['expected'],tables[row['id']]) if row['id'] in tables else {'status':'missing_table'}
            sql.append(dict(id=row['id'],**value))
    return dict(summary=summary,train_majority_baselines=baselines,wikisql_execution_proxy=sql,
        empty_outputs=sum(not r['generated'].strip() for r in answers),
        token_limits=sum(r['stop_reason']=='token_limit' for r in answers),
        qa_mean_f1={s:sum(r['token_f1'] for r in answers if r['source']==s)/sum(r['source']==s for r in answers)
                    for s in {r['source'] for r in answers if 'token_f1' in r}})


def report(plan, out, progress):
    root=Path(__file__).resolve().parents[1]
    prep=root/plan['evaluation_preparation'];audit=read(prep/'audit.json');tables=read(prep/'wikisql-tables.json')
    data=[]
    for item in plan['comparisons']:
        run=root/item['run'];pointer=read(run/'latest.json');state=read(run/pointer['checkpoint']/'state.json')
        metrics=rows(run/'metrics.jsonl');config=read(run/'config.json')
        snapshots={}
        for target in plan['snapshot_tokens']:
            snapshot=run/f'token-{target:09d}'
            if (snapshot/'evaluation/summary.json').exists():
                snapshots[str(target)]=dict(state=read(snapshot/'snapshot.json'),**details(snapshot,snapshot/'evaluation',audit['majority'],tables))
        data.append(dict(name=item['name'],run=item['run'],config=config,final_state={k:state[k] for k in ['step','tokens','source_tokens']},
            training_status=read(run/'status.json'),development_curve=[m for m in metrics if m['event']=='development'],
            final=details(run,run/'broad-eval',audit['majority'],tables),snapshots=snapshots,
            conditions=read(run/'RUN_CONDITIONS.json')))
    signatures=['manifest_sha256','source_weights_by_sequence','seed','batch_size','context','schedule_tokens','max_tokens','execution','dtype']
    mismatches=[key for key in signatures if data[0]['config'][key]!=data[1]['config'][key]]
    if mismatches:raise ValueError('Model comparison inputs differ: '+str(mismatches))
    matched={}
    for key in sorted(set(data[0]['snapshots'])&set(data[1]['snapshots']),key=int):
        states=[d['snapshots'][key]['state'] for d in data]
        matched[key]=dict(tokens=[s['tokens'] for s in states],steps=[s['step'] for s in states],
            identical_work=all(states[0][k]==states[1][k] for k in ['tokens','step','source_tokens']))
    result=dict(runs=data,matched_tokens=matched,protocol=plan['protocol'],
        quality_scope='Internal development, one seed and fixed serial order; no external family-transfer measurement or definitive size ranking.',
        source_mismatches=mismatches,progress=progress)
    atomic_json(out/'comparison.json',result)
    names=[d['name'] for d in data]
    lines=['# Größenvergleich: korrigiertes breites Benchmark-Training','',
        'Je drei Stunden ab Startfreigabe; Initialisierung, Datenprüfung im Trainer, Validierung und Checkpoints zählen zum Zeitbudget. Auswertungen folgen separat. Gleiche Daten, Sampling, Seed, Kontext, Batchgröße und tokenbasierte Lernratenkurve; Modellgröße und dadurch erreichter Durchsatz unterscheiden sich.','',
        '| Modell | Parameter | Trainings-Tokens | Schritte |','|---|---:|---:|']
    for d in data:lines.append(f"| {d['name']} | {d['config']['parameters']:,} | {d['final_state']['tokens']:,} | {d['final_state']['step']:,} |")
    lines+=['','## Nach drei Stunden: letzte Modellstände','',
        '| Fähigkeit | '+names[0]+' Genauigkeit / Loss | '+names[1]+' Genauigkeit / Loss |','|---|---:|---:|']
    def cell(summary,family):
        accuracy=summary['mean_source_accuracy_by_family'].get(family)
        loss=summary['answer_loss']['family_answer_loss'].get(family)
        return ('unbewertet' if accuracy is None else f'{accuracy:.1%}')+' / '+('n/a' if loss is None else f'{loss:.3f}')
    for family in FAMILIES:lines.append('| '+family+' | '+' | '.join(cell(d['final']['summary'],family) for d in data)+' |')
    lines+=['','Genauigkeit ist das Mittel der automatisch bewertbaren Quellen im Bereich; unterschiedliche Metriken bleiben getrennt. Loss nutzt richtige vorherige Antworttokens. Narrative Antworten, SQL und Programmcode werden nicht als normale Antwortgenauigkeit ausgegeben. HotpotQA hat keinen eigenen Entwicklungssplit.','',
        '## Vergleich bei ähnlicher Tokenzahl','']
    for target,item in matched.items():
        lines += [f"### Ziel {int(target):,} Tokens",'',f"Tatsächlich: {item['tokens']}; identische Schritte und Quellen-Tokenzahlen: {item['identical_work']}.",'',
            '| Fähigkeit | '+names[0]+' Genauigkeit / Loss | '+names[1]+' Genauigkeit / Loss |','|---|---:|---:|']
        for family in FAMILIES:lines.append('| '+family+' | '+' | '.join(cell(d['snapshots'][target]['summary'],family) for d in data)+' |')
    if not matched:lines.append('Kein gemeinsamer Token-Zwischenstand innerhalb des Zeitbudgets; keine Hochrechnung als Messergebnis.')
    lines+=['','## Einfache Vergleichswerte und ausführbare Aufgaben','']
    for d in data:
        lines += ['### '+d['name'],'','| Quelle | Modell korrekt | Trainings-Mehrheitsregel korrekt | Aufgaben |','|---|---:|---:|---:|']
        for source,b in d['final']['train_majority_baselines'].items():lines.append(f"| {source} | {b['model_correct']} | {b['baseline_correct']} | {b['scored']} |")
        summary=d['final']['summary']
        lines += ['',f"Code: {summary['code_statuses']}; bestanden mit stärkerer Testabdeckung: {summary['code_passes_with_stronger_tests']}. WikiSQL-Ausführungsdiagnosen: {dict(Counter(v['status'] for v in d['final']['wikisql_execution_proxy']))}.",f"Leere Antworten: {d['final']['empty_outputs']}; Tokenlimits: {d['final']['token_limits']}.",'']
    lines += ['## Grenzen','',
        'Ein Seed je Größe und feste Reihenfolge erlauben keine belastbare allgemeine Rangfolge. Die gemeldete reduzierte Leistung bleibt bestehen; tatsächliche Betriebssystemeinstellungen wurden vor jedem Training protokolliert. Stromverbrauch und freie GPU-Kapazität wurden nicht gemessen. Quellenverteilungen, Entwicklungs-Lernkurven und Einzelmetriken stehen in `comparison.json`. SciTail und WIQA stammen hier aus der korrigierten Version; historische Ergebnisse wurden nicht überschrieben.','',
        'Keine automatische Verlängerung. Einen längeren Lauf erst anhand von Lernkurven, freier Antwortqualität, Mehrheitsregeln und Ressourcenaufwand auswählen. Externe Abschlusstests bleiben geschlossen.','']
    (out/'REPORT.md').write_text('\n'.join(lines))
