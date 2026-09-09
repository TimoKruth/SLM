"""Read-only effect summaries; never interpret missing/failed trials as zero quality."""
from itertools import combinations
from pathlib import Path
from research.common import read,write,quality,contrast,parent_guard


def collect(run):
    out={}
    for p in sorted((run/'trials').glob('*')):
        try:
            cfg=read(p/'config.json');job=cfg['study_job']; result=read(p/'result.json')
            if result['status']!='completed':continue
            q=quality(read(p/'search/summary.json'))
        except (OSError,KeyError,ValueError,TypeError):continue
        out[job['id']]=dict(job=job,result=result,quality=q,path=str(p),model_parameters=cfg['parameters'])
    return out


def effects(rows,parent=None):
    by={(v['job']['phase'],v['job']['name'],v['job']['repetition']):v for v in rows.values()}
    out={}
    for phase,name in sorted({(v['job']['phase'],v['job']['name']) for v in rows.values()}):
        if phase=='interaction':continue
        sample=next(v for v in rows.values() if v['job']['phase']==phase and v['job']['name']==name)
        reference='cold-baseline' if phase=='cold' else ('context-1024-eligible-512' if sample['job']['block']=='context' else 'baseline')
        if name==reference:continue
        try:
            bases=[by[phase,reference,r] for r in range(2)]
            candidates=[by[phase,name,r] for r in range(2)]
        except KeyError:continue
        values=contrast([v['quality'] for v in bases],[v['quality'] for v in candidates])
        values['reference']=reference
        values['phase']=phase
        values['block']=sample['job']['block']
        values['speed_ratios']=[(c['result']['additional_tokens']/c['result']['elapsed_seconds']) /
                                (b['result']['additional_tokens']/b['result']['elapsed_seconds']) for b,c in zip(bases,candidates)]
        if parent is not None and phase=='adaptation' and sample['job']['block']!='context':
            values['parent_guard']=parent_guard(parent,[v['quality'] for v in candidates])
            values['passes_screen']=values['passes_screen'] and values['parent_guard']['passed']
        out[phase+':'+name]=values
    return out


def factorial(rows):
    values=[v for v in rows.values() if v['job']['phase']=='interaction']
    if len(values)!=16:return dict(status='incomplete',completed=len(values),required=16)
    factors=['lr','answer_weight','weight_decay']; highs=[3e-5,2.,.1]; out={}
    for count in [1,2,3]:
        for subset in combinations(range(3),count):
            deltas=[]
            for repeat in range(2):
                total=0.
                for row in values:
                    if row['job']['repetition']!=repeat:continue
                    p=row['job']['parameters'];sign=1
                    for i in subset:sign*=1 if p[factors[i]]==highs[i] else -1
                    total+=sign*row['quality']['accuracy']
                deltas.append(total/(2**(3-count)))
            out[' x '.join(factors[i] for i in subset)]=dict(accuracy_contrasts=deltas,mean=sum(deltas)/2,
                   interpretation='High-minus-low; interactions are differences of differences, averaged over remaining factors.')
    return dict(status='completed',effects=out)


def report(run,state):
    rows=collect(run)
    parent=read(run/'parent-quality.json') if (run/'parent-quality.json').exists() else None
    e=effects(rows,parent)
    write(run/'effects.json',e);write(run/'interactions.json',factorial(rows))
    duration={}
    for identifier,v in rows.items():
        if v['job']['phase']!='long':continue
        try:
            snapshot=quality(read(Path(v['path'])/'token-001500000/search/summary.json'))
            duration[identifier]=dict(accuracy_delta=v['quality']['accuracy']-snapshot['accuracy'],
                                      answer_loss_delta=v['quality']['answer_loss']-snapshot['answer_loss'],
                                      interpretation='Same trajectory at ~1.5M and ~15M added tokens, fixed search suite.')
        except (OSError,KeyError,ValueError):pass
    write(run/'duration-effects.json',duration)
    lines=['# Systematische Parameterstudie (24h-Budget)','',f"Status: {state['status']}; Phase: {state.get('phase','—')}",'',
           'Gültig ausgewertete Läufe: '+str(len(rows))+'. Alle fehlenden oder fehlgeschlagenen Läufe bleiben unbewertet.',
           'Vergleiche gelten nur für die gemessenen Stufen, Trainingsdauer und Ausgangsmodelle. Zwei Datenreihenfolgen sind keine unabhängigen Initialisierungen. '
           'Der Architekturblock hat zwei neue Initialisierungen je Konfiguration. Keine Signifikanz- oder externe Transferbehauptung.',
           'Referenz-Antwortloss wird über alle Quellen gemittelt. Generative Genauigkeit ist das Familien-Makro der bewertbaren Quellen; '
           'funktionale Code-/SQL- und offene Textqualität sind hier nicht umfassend bewertet.', '',
           '| Phase / Variante | Wiederholung | Parameter | Tokens | Sekunden | Tokens/s | GPU-Spitze (GB) | Genauigkeit | Antwortloss |',
           '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    if parent:lines.append(f"| Unverändertes Elternmodell | — | 27294208 | 0 | — | — | — | {parent['accuracy']:.2%} | {parent['answer_loss']:.4f} |")
    for v in rows.values():
        j,r,q=v['job'],v['result'],v['quality']
        lines.append(f"| {j['phase']} / {j['name']} | {j['repetition']} | {v['model_parameters']} | {r['additional_tokens']} | {r['elapsed_seconds']:.1f} | "
                     f"{r['additional_tokens']/r['elapsed_seconds']:.0f} | {r['peak_gpu_gb']:.2f} | {q['accuracy']:.2%} | {q['answer_loss']:.4f} |")
    lines+=['','## Gepaarte Effekte','','| Vergleich | Genauigkeitsänderung je Wiederholung (pp) | Mittlere Antwortloss-Änderung |',
            '| --- | --- | ---: |']
    for name,v in e.items():
        deltas=', '.join(f'{d*100:+.2f}' for d in v['accuracy_deltas'])
        lines.append(f"| {name} gegen {v['reference']} | {deltas} | {v['mean_answer_loss_delta']:+.4f} |")
    lines+=['','Details je Fähigkeitsgruppe und Durchsatz: effects.json; vollständige 2×2×2-Wechselwirkungen: interactions.json.',
            'Gepaarte Lernkurve derselben langen Trajektorien bei 1,5M/15M Zusatz-Tokens: duration-effects.json.',
            'Kontextvergleiche verwenden dieselben auf 512 Tokens begrenzten Originalbeispiele, ändern aber deren Packung. '
            'Größere globale Batches ändern Zahl der Updates und Token-Überschuss am Endpunkt. '
            'Architekturvergleiche ändern teilweise zugleich die Parameterzahl; keine isolierte Kapazitätsaussage.']
    if (run/'selection.json').exists():lines+=['','Auswahl für längere Prüfung: '+str(read(run/'selection.json'))]
    if (run/'confirmation.json').exists():lines+=['','Längere Gegenprüfung: '+str(read(run/'confirmation.json'))]
    failed=[s for s in state.get('stages',[]) if s['status']=='failed']
    if failed:
        lines+=['','## Fehlgeschlagene Stufen','']
        lines += [f"- {s['name']}: {s.get('error','Prozessfehler')}; Exit {s.get('cleanup_exit_code',s.get('exit_code'))}. Siehe Stufenlog." for s in failed]
    plan=read(run/'plan.json')
    lines+=['','## Noch nicht untersucht','']+[f'- {k}: {v}' for k,v in plan['deferred'].items()]
    lines+=['','Kein automatischer Modellwechsel oder weiterer Lauf nach Budgetende. Ein STOP im Kampagnenverzeichnis beendet die Arbeit.']
    if state.get('error'):lines+=['','Fehler/Abbruch: '+state['error']]
    (run/'REPORT.md').write_text('\n'.join(lines)+'\n')
