"""Produce a local morning report and bounded qualitative development samples."""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from .train import atomic_json

ROOT = Path(__file__).resolve().parents[1]


def report(run, sample=False, until=None):
    config = json.loads((run / 'config.json').read_text())
    data = (ROOT / config.get('data', 'data')).resolve()
    state = json.loads((run / 'status.json').read_text())
    manifest = json.loads((run / 'data_manifest.json').read_text())
    events = []
    for line in (run / 'metrics.jsonl').read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    dev = [e for e in events if e['event'] == 'development']
    train = [e for e in events if e['event'] == 'train']
    samples = []
    if sample and (run / 'latest.json').exists():
        import mlx.core as mx
        mx.set_memory_limit(8 * 1024 ** 3)
        mx.set_cache_limit(512 * 1024 ** 2)
        from tokenizers import Tokenizer
        from .model import LanguageModel, ModelConfig
        from .train import generate, evaluate
        deadline = datetime.fromisoformat(until).timestamp() if until else time.time() + 180
        model = LanguageModel(ModelConfig(**config['model']))
        folder = run / json.loads((run / 'latest.json').read_text())['checkpoint']
        model.load_weights(str(folder / 'model.safetensors'))
        tok = Tokenizer.from_file(str(run / 'tokenizer.json'))
        if deadline - time.time() > 60:
            final_dev = evaluate(model, data, config['model']['context'], config['batch_size'], deadline=deadline)
            if len(final_dev) == len(manifest.get('evaluation_weights', manifest['sources'])):
                event = {'event': 'development', 'time': datetime.now().astimezone().isoformat(), 'step': state.get('step', 0), 'tokens': state.get('tokens', 0), 'sources': final_dev, 'macro_answer_loss': sum(v['answer_loss'] for v in final_dev.values()) / len(final_dev), 'best': False, 'is_external_benchmark': False, 'phase': 'final_report'}
                dev.append(event)
                with (run / 'metrics.jsonl').open('a') as f:
                    f.write(json.dumps(event) + '\n')
        per_source = {}
        chosen = []
        for line in (data / 'records.jsonl').open():
            row = json.loads(line)
            if row['split'] != 'dev' or per_source.get(row['source'], 0) >= 2:
                continue
            chosen.append(row)
            per_source[row['source']] = per_source.get(row['source'], 0) + 1
            if len(chosen) == len(manifest['sources']) * 2:
                break
        for row in chosen:
            if time.time() >= deadline:
                break
            prediction = generate(model, tok, row['prompt'], max_tokens=128, deadline=deadline)
            samples.append(dict(source=row['source'], original_id=row['original_id'], prompt=row['prompt'], expected=row['answer'], generated=prediction, generation='greedy; at most 128 new tokens; not executed or scored'))
        atomic_json(run / 'samples.json', samples)
    counts = manifest['counts']
    lines = [
        '**Lokaler Trainingslauf — Bericht**', '',
        f"Erstellt: {datetime.now().astimezone().isoformat()}", '',
        f"Status: **{state['status']}**. Grund: `{state.get('reason', state.get('error', 'laufend'))}`.", '',
        f"Modell: {config['parameters']:,} Parameter, zufällige Initialisierung, MLX auf M1 Max, FP32.",
        f"Verarbeitet: {state.get('tokens', 0):,} Trainingstokens in {state.get('step', 0):,} Optimizer-Schritten.", '',
        '**Datenbasis**', '',
        '| Datensatz | Trainingspaare | Trainingstokens | Entwicklungspaare |',
        '| --- | ---: | ---: | ---: |',
    ]
    for source in manifest['sources']:
        tr, va = counts[source + '.train'], counts[source + '.dev']
        lines.append(f"| {source} | {tr.get('records',0):,} | {tr.get('tokens',0):,} | {va.get('records',0):,} |")
    lines.extend(['', 'Mehrere Referenzlösungen zählen als mehrere Paare derselben Aufgabe. Daten stammen ausschließlich aus Original-Trainingsanteilen; Entwicklungsgruppen sind vor dem Training reserviert; zusätzliche Ausschlüsse und Quellen ohne Entwicklungssplit stehen im Datenmanifest. Der Tokenizer wurde ohne Entwicklungsdaten gelernt.', '', '**Lernverlauf**', ''])
    if manifest.get('code_overlap_filter'):
        lines.insert(lines.index('**Lernverlauf**'), f"Zusätzlich wurden {manifest['code_overlap_filter']['excluded_development_records']} Entwicklungsvarianten wegen einer strukturgleichen Code-Lösung im Training ausgeschlossen.")
    if train:
        lines.extend([f"Erste protokollierte Trainings-Loss: {train[0]['loss']:.4f}; letzte: {train[-1]['loss']:.4f}. Die Batches unterscheiden sich, daher ist dieser Vergleich nur eine grobe Orientierung.", f"Letzter gemessener Durchsatz: {train[-1]['tokens_per_second']:.0f} Tokens/s; MLX-Spitzenspeicher: {max(e['mlx_peak_gb'] for e in train):.2f} GB.", ''])
    if dev:
        lines.extend(['| Quelle | Antwort-Loss am Anfang | Antwort-Loss bei letzter Entwicklungsmessung |', '| --- | ---: | ---: |'])
        for source in manifest['sources']:
            a, b = dev[0]['sources'].get(source), dev[-1]['sources'].get(source)
            if a and b:
                lines.append(f"| {source} | {a['answer_loss']:.4f} | {b['answer_loss']:.4f} |")
    lines.extend(['', '**Interpretation**', '', 'Das ist ein lokaler Pilot. Sinkende Loss zeigt, dass das Modell statistische Regelmäßigkeiten lernt; sie beweist noch keine allgemeine Coding-Kompetenz oder Transfer auf neue Benchmark-Familien. Entwicklungs-Loss nutzt kleine feste Stichproben und die bekannten Aufgabenformate. Die drei Abschlusstests LiveCodeBench, IFBench und BBEH wurden nicht geladen oder verwendet.', '', 'Bekannte Grenzen: begrenzte Datenmischung; lange Beispiele über 1.024 Tokens für das Modell ausgeschlossen; mehrere Code-Lösungen pro Aufgabe; keine umfassende semantische Kontaminationsprüfung; ausführbare Code-Ergebnisse werden gegebenenfalls separat unter `code-eval/` dokumentiert. HellaSwag enthält hier ausschließlich die positive Fortsetzung. PIQAs Datenlizenz ist in der verwendeten HF-Metadatenquelle nicht spezifiziert; es erfolgt keine Veröffentlichung der Daten oder Gewichte.', '', '**Dateien**', '', '- `latest.json`: letzter vollständiger, fortsetzbarer Checkpoint.', '- `best.json` / `best.safetensors`: nach Entwicklungs-Loss ausgewählte Gewichte.', '- `metrics.jsonl`: Verlauf einschließlich Startmessung und Entwicklungswerten.', '- `samples.json`: qualitative Antworten auf reservierte Entwicklungsaufgaben, falls erzeugt; Code wurde nicht ausgeführt.', '- `config.json` / `data_manifest.json`: Konfiguration, Datenrevisionen und Prüfsummen.', '', 'Nächster Schritt: ausführbare Code-Diagnose des besten Checkpoints durchführen und mit dem vorherigen Lauf vergleichen. Die Abschlusstests bleiben bis zur Festlegung aller Vergleichsläufe geschlossen.', ''])
    (run / 'REPORT.md').write_text('\n'.join(lines))
    return run / 'REPORT.md'


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run', required=True)
    p.add_argument('--sample', action='store_true')
    p.add_argument('--until')
    args = p.parse_args()
    print(report((ROOT / args.run).resolve(), args.sample, args.until))
