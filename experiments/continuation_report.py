"""Compare the frozen three-hour parents with their separate three-hour continuations."""
from collections import Counter
from pathlib import Path
from .size_report import read, rows, details
from slm.breadth import FAMILIES
from slm.train import atomic_json


def work_delta(parent, final):
    delta = {key: final[key] - parent[key] for key in ('step', 'tokens')}
    if any(value < 0 for value in delta.values()):
        raise ValueError('Continuation counters precede parent')
    sources = {s: final.get('source_tokens', {}).get(s, 0) - parent.get('source_tokens', {}).get(s, 0)
               for s in set(final.get('source_tokens', {})) | set(parent.get('source_tokens', {}))}
    if any(v < 0 for v in sources.values()) or sum(sources.values()) != delta['tokens']:
        raise ValueError('Source-token deltas disagree with continuation work')
    return dict(**delta, source_tokens=sources)


def counts(summary):
    sources = summary['by_source'].values()
    return dict(correct=sum(s['correct'] for s in sources), scored=sum(s['scored'] for s in sources))


def report(plan, out, progress):
    root = Path(__file__).resolve().parents[1]
    prep = root / plan['evaluation_preparation']
    audit, tables = read(prep / 'audit.json'), read(prep / 'wikisql-tables.json')
    data = []
    for item in plan['comparisons']:
        run, parent = root / item['run'], root / item['parent']
        lineage = read(run / 'parent.json')
        state = read(run / read(run / 'latest.json')['checkpoint'] / 'state.json')
        parent_state = read(parent / lineage['parent_checkpoint'] / 'state.json')
        config, before_config = read(run / 'config.json'), read(parent / 'config.json')
        stable = ['model', 'seed', 'batch_size', 'context', 'schedule_tokens', 'snapshot_tokens',
                  'max_tokens', 'execution', 'dtype', 'manifest_sha256', 'source_weights_by_sequence']
        if any(config[k] != before_config[k] for k in stable) or state['signature'] != parent_state['signature']:
            raise ValueError('Continuation changed frozen training settings')
        before = details(parent, parent / 'broad-eval', audit['majority'], tables)
        after = details(run, run / 'broad-eval', audit['majority'], tables)
        delta = work_delta(parent_state, state)
        b, a = counts(before['summary']), counts(after['summary'])
        if b['scored'] != a['scored']:
            raise ValueError('Different scored task counts')
        data.append(dict(name=item['name'], parent=item['parent'], run=item['run'], parameters=config['parameters'],
                         parent_state=parent_state, final_state=state, added_work=delta,
                         before=before, after=after, before_counts=b, after_counts=a,
                         additional_correct=a['correct'] - b['correct'],
                         development_curve=rows(run / 'metrics.jsonl'),
                         conditions=read(run / 'RUN_CONDITIONS.json')))
    result = dict(runs=data, protocol=plan['protocol'], progress=progress,
                  scope='Internal development; six hours cumulative active budgets in two sessions, not six uninterrupted wall-clock hours. One seed, fixed order and changed operating time limit causal conclusions.')
    atomic_json(out / 'comparison.json', result)
    lines = ['# Modellgröße und längeres Training: 3 → 6 Stunden', '',
             result['scope'], '',
             'Je Modell drei zusätzliche Stunden vom letzten vollständigen Endcheckpoint; Modellgewichte, AdamW und Sampler fortgesetzt. Unveränderte FP32-Architektur, Daten und 100M-Token-Lernratenkurve. Keine neuen Daten oder BF16-Optimierung.', '',
             '| Modell | Tokens vorher | Tokens zusätzlich | Tokens gesamt | Korrekt 3h → 6h | Antwort-Loss 3h → 6h |',
             '|---|---:|---:|---:|---:|---:|']
    for d in data:
        lines.append(f"| {d['name']} | {d['parent_state']['tokens']:,} | {d['added_work']['tokens']:,} | {d['final_state']['tokens']:,} | {d['before_counts']['correct']}/{d['before_counts']['scored']} → {d['after_counts']['correct']}/{d['after_counts']['scored']} | {d['before']['summary']['answer_loss']['macro_source_answer_loss']:.3f} → {d['after']['summary']['answer_loss']['macro_source_answer_loss']:.3f} |")
    lines += ['', '| Fähigkeit | Klein 3h | Klein 6h | Groß 3h | Groß 6h |', '|---|---:|---:|---:|---:|']
    for family in FAMILIES:
        cells = []
        for d in data:
            for stage in ('before', 'after'):
                v = d[stage]['summary']['mean_source_accuracy_by_family'].get(family)
                cells.append('unbewertet' if v is None else f'{v:.1%}')
        lines.append('| ' + family + ' | ' + ' | '.join(cells) + ' |')
    for d in data:
        lines += ['', '## ' + d['name'], '',
                  f"Zusätzliche korrekte Antworten: {d['additional_correct']}. Tokens/s inklusive Start, Prüfungen und Checkpoints im Zusatzbudget: {d['added_work']['tokens']/10800:.0f}.",
                  f"Code bestanden: {d['before']['summary']['code_passes_with_stronger_tests']} → {d['after']['summary']['code_passes_with_stronger_tests']}.",
                  f"WikiSQL-Ausführungsproxy: {dict(Counter(v['status'] for v in d['before']['wikisql_execution_proxy']))} → {dict(Counter(v['status'] for v in d['after']['wikisql_execution_proxy']))}.",
                  f"Tokenlimits: {d['before']['token_limits']} → {d['after']['token_limits']}."]
    lines += ['', '## Interpretation', '',
              'Der Zugewinn von Stunde 3 bis 6 wird je Größe separat ausgewiesen. Bei gleichem Zeitbudget bleibt die tatsächlich gesehene Tokenmenge verschieden. Das kleine Modell startet bereits auf der Lernratenuntergrenze 3e-5; das große folgt seiner unveränderten Kurve ab etwa 38,5M Tokens. Der Versuch misst diese konkrete Fortsetzung, nicht eine größenunabhängig optimale Lernrate.',
              'Betriebsbedingungen und PowerWatch-Verlauf ergänzen die Messungen. Die Pause zwischen den Sitzungen ist keine Trainingszeit. Mehrheitsregeln, ausführbare Tests und Quellenergebnisse stehen im JSON. Historische Referenzmängel bleiben dieselben; die interne Suite ist kein externer Transferbeleg.',
              'Keine automatische weitere Verlängerung.']
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n')
