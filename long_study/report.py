"""Read-only contrasts for the preregistered 2x2 block; no winner adoption."""
from pathlib import Path
from research.common import read,write,quality,parent_guard
from .protocol import differences


def report(run,state):
    run=Path(run);plan=read(run/'plan.json');rows={};curves={}
    for identifier in plan['jobs']:
        job=read(run/'jobs'/(identifier+'.json'));trial=run/'trials'/identifier
        for endpoint,suffix in [('15M','token-015000000/search'),('50M','token-050000000/search'),
                                ('final_search','search'),('final_confirmation','confirmation')]:
            try:q=quality(read(trial/suffix/'summary.json'))
            except (OSError,ValueError,KeyError):continue
            rows[(job['repetition'],job['condition'],endpoint)]=q
        try:curves[identifier]=read(trial/'result.json')
        except OSError:pass
    contrasts={}
    for endpoint in ['15M','50M','final_search','final_confirmation']:
        for a,b in [('A','B'),('C','D'),('A','C'),('B','D')]:
            values=[]
            for r in range(2):
                if (r,a,endpoint) in rows and (r,b,endpoint) in rows:
                    values.append(dict(repetition=r,**differences(rows[r,a,endpoint],rows[r,b,endpoint])))
            contrasts[endpoint+':'+b+'-'+a]=values
        interaction=[]
        for r in range(2):
            if all((r,c,endpoint) in rows for c in 'ABCD'):
                interaction.append(dict(repetition=r,
                    accuracy=(rows[r,'D',endpoint]['accuracy']-rows[r,'C',endpoint]['accuracy'])-
                             (rows[r,'B',endpoint]['accuracy']-rows[r,'A',endpoint]['accuracy'])))
        contrasts[endpoint+':interaction']=interaction
    write(run/'contrasts.json',contrasts)
    rows_json=[dict(repetition=r,condition=c,endpoint=e,**q) for (r,c,e),q in rows.items()]
    write(run/'quality.json',rows_json)
    assessment={}
    try:parent=quality(read(run/'parent-confirmation/summary.json'))
    except (OSError,ValueError,KeyError):parent=None
    if parent:
        for a,b in [('A','B'),('C','D'),('A','C'),('B','D')]:
            if not all((r,c,'final_confirmation') in rows for r in range(2) for c in [a,b]):continue
            values=contrasts['final_confirmation:'+b+'-'+a]
            guard=parent_guard(parent,[rows[r,b,'final_confirmation'] for r in range(2)])
            families={k:sum(v['families'][k] for v in values)/2 for k in values[0]['families']}
            assessment[b+'-'+a]=dict(accuracy_deltas=[v['accuracy'] for v in values],mean_family_deltas=families,
                parent_guard=guard,passes_preregistered_thresholds=all(v['accuracy']>=.02 for v in values)
                and min(families.values())>=-.05 and guard['passed'],automatic_adoption=False)
    write(run/'assessment.json',assessment)
    lines=['# Langer 2×2-Vergleich','',f"Status: {state['status']}; Phase: {state.get('phase')}",
           '', 'Interne Aufgaben, zwei Datenreihenfolgen desselben Elternmodells. Keine externe Transfer- oder Signifikanzbehauptung.',
           'CPU-EvoNN-Überlappung und Leistungsmodus gehören zu den Betriebsbedingungen; gleiche Zeit bedeutet nicht gleiche Tokens.',
           '', '| Lauf | Status | Zusätzliche Tokens | Gemessene aktive Sekunden |', '| --- | --- | ---: | ---: |']
    for name,r in curves.items():lines.append(f"| {name} | {r['status']} | {r['additional_tokens']} | {r['elapsed_seconds']:.1f} |")
    lines+=['','## Qualität','','| Seedfolge | Bedingung | Endpunkt | Genauigkeit | Antwortloss |','| --- | --- | --- | ---: | ---: |']
    for r in rows_json:lines.append(f"| {r['repetition']} | {r['condition']} | {r['endpoint']} | {r['accuracy']:.2%} | {r['answer_loss']:.4f} |")
    lines+=['','Alle direkten Kontraste und Wechselwirkungen: contrasts.json. Fehlende Zeit-/Tokenstände werden nicht imputiert. Keine automatische Modellübernahme.']
    (run/'REPORT.md').write_text('\n'.join(lines)+'\n')
