"""Offline report from completed pilot artifacts; does not import MLX."""
import argparse,json,math,statistics
from pathlib import Path


def summarize(run):
    run=Path(run)
    r=json.loads((run/'results.json').read_text())
    p=json.loads((run/'protocol.json').read_text())
    trials=[json.loads(line) for line in (run/'trials.jsonl').read_text().splitlines()]
    supervisor=json.loads((run/'supervisor.json').read_text())
    assert r['status']==supervisor['status']=='completed'
    assert supervisor['elapsed_seconds']<=p['budget_seconds']
    labels={'random_first':'Erstes Zufallsnetz','random_selected':'Ausgewähltes Zufallsnetz','trained_families':'Training: Fähigkeitsgruppen','trained_sources':'Training: Quellen'}
    c=r['comparison'];projection=r['projections_three_hours']
    lines=['# Zufallsnetz-Stichprobe vom 8. September 2026','',
        f"Abgeschlossen in **{supervisor['elapsed_seconds']/60:.2f} Minuten**, einschließlich Aufwärmen, Suche, Kontrollen und Monitoring-Abschluss; Budgetobergrenze 20 Minuten. **{r['candidates']} vollständig neu initialisierte Modelle** mit jeweils {r['parameters']:,} Parametern geprüft. Kein Gewichtstraining innerhalb dieser Stichprobe.",'',
        '## Gemessener Durchsatz','',
        '| Prüfung | Sekunden pro Netz | Netze in drei Stunden |','|---|---:|---:|',
        f"| Nur Initialisierung (Median) | {r['median_initialization_seconds']:.4f} | — |",
        f"| Initialisierung + 30 Auswahlaufgaben, einschließlich Such-Verwaltung | {r['mean_search_seconds_per_candidate']:.3f} | {projection['fast_selection_candidates_before_final_controls']:,} |",
        f"| Initialisierung + {p['teacher_full_examples']} Referenzaufgaben | {r['median_initialization_seconds']+c['random_selected']['full_teacher']['seconds']:.2f} | {projection['full_teacher_candidates']:,} |",
        f"| {p['full_examples']} freie Antworten, aus {len(p['generation_probes'])} Aufgaben hochgerechnet | {projection['full_generation_seconds_per_candidate_extrapolated']:.1f} | {projection['full_generation_candidates_from_small_probe']:,} |",'',
        f"Suchphase: {r['search_wall_seconds']:.2f} Sekunden; {60/r['mean_search_seconds_per_candidate']:.1f} Kandidaten/Minute. Median der synchronisierten Referenzprüfung allein: {r['median_selection_seconds']:.3f} Sekunden.",
        'Die Drei-Stunden-Zahlen sind serielle Durchsatzprojektionen vor zusätzlichen Abschlusskontrollen, keine Erfolgswahrscheinlichkeiten. Die freie Generierung ist nur eine grobe Hochrechnung aus einer kleinen, nach Fähigkeitsgruppen begrenzten Probe.', '',
        '## Qualität auf denselben Kontrollen','',
        '| Modell | Antwort-Loss auf 30 Kontrollen ↓ | Freie Antworten: korrekt / bewertbar | Tokenlimit / 13 |','|---|---:|---:|---:|']
    for name,label in labels.items():
        v=c[name];g=v['generation']
        lines.append(f"| {label} | {v['control']['answer_loss']:.4f} | {g['correct']} / {g['scored']} | {g['token_limits']} / {g['examples']} |")
    lines += ['',f"Auswahl-Loss aller Zufallsnetze: {min(t['selection']['answer_loss'] for t in trials):.4f} bis {max(t['selection']['answer_loss'] for t in trials):.4f}; Mittelwert {statistics.mean(t['selection']['answer_loss'] for t in trials):.4f}. Gewinner-Seed: {json.loads((run/'winner.json').read_text())['seed']}. Gleichverteilung über 16.384 Tokens hätte einen Loss von ln(16.384) = {math.log(16384):.4f}.", '',
        f"Auf allen {p['teacher_full_examples']} passenden Referenzaufgaben: Zufallsgewinner {c['random_selected']['full_teacher']['answer_loss']:.4f}, trainiertes Quellenmodell {c['trained_sources']['full_teacher']['answer_loss']:.4f}. Diese größere Auswertung enthält die Auswahlaufgaben und ist nicht unabhängig.", '',
        'Die 30 Auswahl- und 30 Kontrollaufgaben wurden vorab gruppengetrennt festgelegt; alle stammen aus Original-Trainingssplits von 30 Benchmark-Quellen. SciTail ist ausgeschlossen. Die freie Antwortprobe umfasst 13 Aufgaben; nicht automatisch bewertbare Aufgaben zählen nicht als falsch. Eine kleine Kontrollprobe kann keine umfassende Fähigkeitseinschätzung liefern.', '',
        'Teacher Forcing gibt die richtigen vorherigen Antworttokens vor. Ein kleinerer Loss allein belegt keine selbstständige Problemlösung. Die trainierten Checkpoints wurden früher anhand von Entwicklungs-Loss ausgewählt und stammen aus der fehlerhaften SciTail-Datenversion. Der Vergleich ist beschreibend; die externen Abschlusstests werden nicht angefasst.', '',
        '## Betriebsbedingungen und nächster Versuch','',
        f"MLX-Spitzenspeicher: {r['mlx_peak_gb']:.3f} GB. Kein paralleler SLM-GPU-Lauf; keine Änderung der Leistungseinstellung. Der Nutzer meldete reduzierte Leistung zur Geräuschbegrenzung. Betriebssystemeinstellungen sind als Momentaufnahme in `power-settings.txt` abgelegt. Zeit und Speicher sind keine Messung von Energiebedarf oder GPU-Auslastung.", '',
        f"Der ausgewählte Zufallskandidat erzeugte auf {sum(not row['generated'].strip() for row in c['random_selected']['generation']['rows'])} von {len(p['generation_probes'])} Aufgaben ausschließlich Leerraum. Seine Loss-Verbesserung liefert damit keinen Nachweis nutzbarer Fähigkeiten. Für diese unabhängige Vollgewichts-Zufallssuche empfehle ich derzeit keinen Drei-Stunden-Lauf; korrigiertes Training hat Vorrang.", '',
        'Ein größerer Zufallssuchlauf wird nicht automatisch gestartet. Ein Qualitätsvorteil auf den getrennten Kontrollen müsste belastbar bestätigt werden, bevor längeres Neuwürfeln als Lernstrategie begründet wäre. Für einen sauberen neuen Trainingsvergleich müssen zunächst die SciTail-Daten korrigiert und erneut geprüft werden.', '',
        'Protokoll: `protocol.json`; Einzelkandidaten: `trials.jsonl`; vollständige Kontrollantworten und Referenz-Loss: `controls.json`; Zahlen und Projektionen: `results.json`; Zeitbegrenzung: `supervisor.json`; Monitoring: `performance/`. Methodik und Forschung: `random_search/README.md` im Branch `codex/evaluation-preparation`.', '']
    (run/'REPORT.md').write_text('\n'.join(lines))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True)
    summarize(p.parse_args().run)
