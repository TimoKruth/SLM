"""Reports and guarded comparisons. Inclusive child times are never summed."""
import json
from pathlib import Path


def render(data):
    lines = ['# Performance-Messung', '',f"Status: {data['status']}; Modus: {data['mode']}; Prozesszeit: {data['elapsed_seconds']:.3f} s.",
             f"Trainingstokens im Messfenster: {data['training_tokens_delta']:,}; einschließlich Start, Entwicklung und Checkpoints: {data['end_to_end_tokens_per_second']:.1f} Tokens/s.",
             '', 'Alle Zeiten sind Host-Wall-Zeiten. GPU-Arbeit ist an bestehenden eval/item/save-Grenzen enthalten. Graph-Aufbau ist keine GPU-Kernelzeit. Inklusive Zeiten enthalten Kindphasen und dürfen nicht addiert werden.',
             '', '| Phase | Aufrufe | Inklusiv s | Eigenzeit s | Eigenanteil | Mittel ms | p95 ca. ms |', '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name,row in sorted(data['phases'].items(),key=lambda pair:pair[1]['self_seconds'],reverse=True):
        share=100*row['self_seconds']/max(data['elapsed_seconds'],1e-9)
        lines.append(f"| {name} | {row['count']} | {row['inclusive_seconds']:.6f} | {row['self_seconds']:.6f} | {share:.2f} % | {row['mean_seconds']*1000:.3f} | {row['p95_seconds_approx']*1000:.3f} |")
    lines += ['',f"Geschätzte Hook-Buchhaltung: {data['hook_bookkeeping_seconds_estimate']:.6f} s; Monitoring-Dateiausgabe: {data['monitor_io_seconds']:.6f} s. Das ist keine vollständige Overhead-Messung; dafür ist ein A/B-Versuch erforderlich.",
              f"Aufwärmphase: erste {data['warmup_steps']} Schritte gesondert. p50/p95 verwenden konstante Speicherbelegung und ca. 5 % Histogrammauflösung.",
              '', 'Metadaten, Quellcode-Prüfsummen, instrumentierte Stellen und Zähler: `timings.json`. Bei detail zusätzlich Python-Funktionsprofil und eine begrenzte Host-Timeline. Nicht ausgeführte Pfade wurden nicht vermessen.']
    if data['errors']: lines += ['', 'Monitoring-Fehler: '+repr(data['errors'])]
    if data.get('children'):
        lines += ['', '## Teilprozesse', '', 'Die Wartezeit des Supervisors enthält die Laufzeiten seiner Kinder. Diese Berichte deshalb nicht zum Supervisor addieren.']
        for child in data['children']:
            lines.append(f"- {child['module']}: [{Path(child['output']).name}]({child['output']}/REPORT.md)")
    return '\n'.join(lines)+'\n'


def comparison(a,b):
    mismatches=[]
    for field in ['schema','mode','warmup_steps','flush_seconds','detail_limit_seconds']:
        if a.get(field)!=b.get(field): mismatches.append(field)
    for field in ['workload','environment']:
        if not a.get('metadata',{}).get(field) or a['metadata'][field]!=b.get('metadata',{}).get(field):
            mismatches.append('metadata.'+field)
    if a.get('metadata',{}).get('monitoring_source_sha256')!=b.get('metadata',{}).get('monitoring_source_sha256'):
        mismatches.append('metadata.monitoring_source_sha256')
    if a['status']!='completed' or b['status']!='completed': mismatches.append('incomplete_run')
    if not a.get('observed_training_steps') or not b.get('observed_training_steps'):
        # Non-training programs can still compare phase means, but have no step speed claim.
        note='Kein vollständiger Trainingsschritt-Vergleich verfügbar.'
    else: note='Lernratenzeitplan und Auswertungsfrequenz zusätzlich beachten; ein längerer Lauf verändert den Anteil einmaliger Arbeiten.'
    def rollup(data):
        result={}
        for path,row in data['phases'].items():
            leaf=path.rsplit('/',1)[-1]
            if leaf.endswith('.step.steady'):
                result[leaf]=dict(row)
        return result
    aa,bb=rollup(a),rollup(b)
    phases=[]
    for name in sorted(set(aa)&set(bb)):
        old,new=aa[name]['mean_seconds'],bb[name]['mean_seconds']
        phases.append(dict(phase=name,baseline_seconds=old,candidate_seconds=new,speedup=old/new if new else None))
    changed_sources=a.get('metadata',{}).get('source_sha256')!=b.get('metadata',{}).get('source_sha256')
    return dict(comparable=not mismatches,mismatches=mismatches,source_changed=changed_sources,steady_training=phases,note=note,
                added_phases=sorted(set(b['phases'])-set(a['phases'])),removed_phases=sorted(set(a['phases'])-set(b['phases'])),
                phase_deltas=[dict(phase=p,baseline_mean_seconds=a['phases'][p]['mean_seconds'],candidate_mean_seconds=b['phases'][p]['mean_seconds'],
                                   delta_percent=100*(b['phases'][p]['mean_seconds']/a['phases'][p]['mean_seconds']-1) if a['phases'][p]['mean_seconds'] else None)
                              for p in sorted(set(a['phases'])&set(b['phases']))])


def write_report(directory):
    directory=Path(directory)
    (directory/'REPORT.md').write_text(render(json.loads((directory/'timings.json').read_text())))
