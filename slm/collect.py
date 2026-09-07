"""Collect additional original benchmark train splits in a separate staging area."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen

from huggingface_hub import hf_hub_download
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'data/candidates-2026-09-07'
# One canonical configuration per benchmark: no duplicate raw/tokenized or all/high/middle copies.
SOURCES = {
 'sciq': ('allenai/sciq', 'data/', 'Naturwissenschaftliches Textverständnis', '2c94ad3e1aafab77146f384e23536f97a4849815'),
 'openbookqa': ('allenai/openbookqa', 'additional/', 'Naturwissenschaftliches Schlussfolgern', '388097ea7776314e93a529163e0fea805b8a6454'),
 'commonsenseqa': ('tau/commonsense_qa', 'data/', 'Alltagswissen', '94630fe30dad47192a8546eb75f094926d47e155'),
 'qasc': ('allenai/qasc', 'data/', 'Zwei unterstützende Fakten kombinieren', 'a34ba204eb9a33b919c10cc08f4f1c8dae5ec070'),
 'quartz': ('allenai/quartz', 'data/', 'Qualitative physikalische Beziehungen', '28c1dbb56caf81799296cb17892fa73402e23464'),
 'quarel': ('community-datasets/quarel', 'data/', 'Qualitatives Schlussfolgern', '52be7f062d2c13d401a9e53b6963d8fbcc4abeb4'),
 'ropes': ('allenai/ropes', 'plain_text/', 'Wissen auf beschriebene Situationen anwenden', 'd59f1e2ee2b423d7c6ba71edd47fceb4158b07dd'),
 'drop': ('ucinlp/drop', 'data/', 'Rechnen und Vergleichen anhand von Texten', '95cda593fae71b60b5b19f82de3fcf3298c1239c'),
 'hotpotqa': ('hotpotqa/hotpot_qa', 'distractor/', 'Fragen über mehrere Dokumente', '1908d6afbbead072334abe2965f91bd2709910ab'),
 'race': ('ehovy/race', 'all/', 'Leseverständnis aus Prüfungsaufgaben', '2fec9fd81f1dc971569a9b729c43f2f0e6436637'),
 'snli': ('stanfordnlp/snli', 'plain_text/', 'Folgerung, Widerspruch und neutrale Aussagen', 'cdb5c3d5eed6ead6e5a341c8e56e669bb666725b'),
 'aqua_rat': ('deepmind/aqua_rat', 'raw/', 'Mathematik mit menschlichen Lösungsbegründungen', '33301c6a050c96af81f63cad5562cb5363e88971'),
 'spider': ('xlangai/spider', 'spider/', 'SQL aus Text und Datenbankschema', '0c350918f3f29ec754f1181c65cdce76cd6c133c'),
 'code_contests': ('deepmind/code_contests', 'data/', 'Wettbewerbsprogrammierung mit Referenzcode', '802411c3010cb00d1b05bad57ca77365a3c699d6'),
}
EXCLUDED_FAMILIES = ['LiveCodeBench', 'IFBench', 'IFEval', 'IF-RLVR', 'BIG-Bench', 'BBH', 'BBEH']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch(name):
    repo, prefix, purpose, revision = SOURCES[name]
    folder = STAGE / 'raw' / name
    folder.mkdir(parents=True, exist_ok=True)
    meta = json.load(urlopen(f'https://huggingface.co/api/datasets/{repo}/revision/{revision}', timeout=60))
    assert meta['sha'] == revision
    (folder / 'metadata.json').write_text(json.dumps(meta, indent=2))
    paths = sorted(f['rfilename'] for f in meta['siblings'] if f['rfilename'].startswith(prefix+'train-') and f['rfilename'].endswith('.parquet'))
    assert paths
    card = hf_hub_download(repo, 'README.md', repo_type='dataset', revision=revision, local_dir=folder)
    def download_file(filename):
        assert not re.search(r'(^|/)(test|valid|validation|dev)[/-]', filename)
        path = Path(hf_hub_download(repo, filename, repo_type='dataset', revision=revision, local_dir=folder))
        count = pq.ParquetFile(path).metadata.num_rows
        item = dict(path=filename, sha256=sha(path), bytes=path.stat().st_size, rows=count)
        print(f'{name}: {filename} ({count} train rows)', flush=True)
        return item
    with ThreadPoolExecutor(max_workers=min(4, len(paths))) as pool:
        files = list(pool.map(download_file, paths))
    total = sum(f['rows'] for f in files)
    manifest = dict(name=name, repo=repo, url=f'https://huggingface.co/datasets/{repo}', purpose=purpose, revision=revision, original_split='train', canonical_config=prefix.rstrip('/'), original_train_rows=total, license_metadata=meta.get('cardData',{}).get('license'), card_sha256=sha(card), files=files, status='downloaded_original_train_only', external_evaluation_splits_downloaded=False)
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return name, manifest



def fetch_spider_schemas():
    folder = STAGE / 'raw/spider'
    revision = 'b7b5b8c890cd30e35427348bb9eb8c6d1350ca7c'
    url = f'https://raw.githubusercontent.com/taoyds/spider/{revision}/evaluation_examples/examples/tables.json'
    body = urlopen(url, timeout=60).read()
    schema_sha = hashlib.sha256(body).hexdigest()
    assert schema_sha == '61bb20aa401f03164e2d7f3b16509b7b5f79cc9c943ca7bd159046df1159e2ed'
    train_ids = set(pq.read_table(folder/'spider/train-00000-of-00001.parquet', columns=['db_id']).column('db_id').to_pylist())
    selected = [row for row in json.loads(body) if row['db_id'] in train_ids]
    missing = sorted(train_ids - {row['db_id'] for row in selected})
    assert not missing, missing
    path = folder/'train_schemas.json'
    path.write_text(json.dumps(selected, indent=2))
    meta = dict(repo='taoyds/spider', revision=revision, url=url, original_schema_file_sha256=schema_sha, training_database_count=len(train_ids), stored_training_schemas=len(selected), missing_training_schemas=missing, stored_file=path.name, stored_sha256=sha(path), note='Only schema metadata for database IDs present in the downloaded train partition retained. No evaluation questions or SQL targets loaded.')
    (folder/'schema_manifest.json').write_text(json.dumps(meta,indent=2))
    return meta


def write_catalog(result):
    lines = ['# Benchmark-Sammlung für spätere Trainings', '',
             f"Stand: {result['created']}", '',
             f"**{result['additional_sources']} zusätzliche Originalquellen lokal gesammelt; zusammen mit den bisherigen zehn sind das {result['total_collected_sources']} Benchmark-Datensätze im Bestand.** Trainiert wurde weiterhin ausschließlich mit den ursprünglichen zehn.", '',
             f"Zusätzliche Rohdaten: {result['additional_original_train_rows']:,} Zeilen in Original-Trainingsanteilen; {result['downloaded_bytes']/1e9:.2f} GB Parquet-Dateien. Das sind weder deduplizierte Aufgaben noch fertige Trainingspaare. Eine Zeile kann viele Referenzprogramme enthalten.", '',
             '| Quelle | Schwerpunkt | Original-Trainingszeilen | Lizenz laut Metadaten |',
             '| --- | --- | ---: | --- |']
    for name, m in result['sources'].items():
        license_value = m['license_metadata'] or ['nicht angegeben']
        if isinstance(license_value, list):
            license_value = ', '.join(license_value)
        lines.append(f"| [{name}]({m['url']}) | {m['purpose']} | {m['original_train_rows']:,} | {license_value} |")
    lines += ['', '**Was tatsächlich gesammelt wurde**', '',
              'Ausschließlich originale `train`-Parquet-Dateien, zusätzlich Dataset Cards und Metadaten. Pro Benchmark nur eine kanonische Konfiguration, beispielsweise RACE `all`, HotpotQA `distractor` und AQuA-RAT `raw`. Revisionen sind im Downloader festgelegt; Dateiprüfsummen, Zeilenzahlen und Splitnamen stehen im Manifest. Die Daten liegen getrennt vom eingefrorenen ersten Trainingskorpus unter `data/candidates-2026-09-07/`. Sie wurden noch nicht in Modell- oder Tokenizertraining eingebaut.', '',
              '**Vor dem nächsten Training**', '',
              '- CodeContests zuerst auf ursprüngliche korrekte Python-3-Referenzen reduzieren und nach Aufgaben gruppieren. Falsche Lösungen, andere Programmiersprachen und generierte Unit-Tests werden keine Lernziele. Gegen APPS und die reservierten Entwicklungsaufgaben nach Problemherkunft, Text und Code-AST deduplizieren.',
              '- Spider: Zusätzlich sind die Schemata sämtlicher 140 Trainingsdatenbanken in `raw/spider/train_schemas.json` gesammelt; Quelle und Prüfsummen stehen in `schema_manifest.json`. Frage und Schema zusammen in den Prompt aufnehmen, Entwicklungsgruppen nach Datenbank anlegen.',
              '- SNLI nach Ausgangssatz, RACE nach Artikel und die kontextgebundenen QA-Datensätze nach Dokumenten/Herkunft gruppieren. Ungültige Labels und leere Antworten entfernen. Große Quellen wie SNLI dürfen die Mischung nicht dominieren.',
              '- Originale Begründungen nutzen, sofern vorhanden; keine neuen Lehrerantworten erzeugen. Lizenz- und Herkunftsdetails aus den gespeicherten Cards übernehmen. Nichtkommerzielle bzw. unklare Bedingungen bleiben sichtbar.',
              '- Exakte und ungefähre Dublettenprüfung, Abgleich gegen bestehende Entwicklungsgruppen sowie Ermittlung vollständiger Beispiele innerhalb der gewählten Kontextlänge. Erst danach ist die tatsächlich nutzbare Trainingsmenge bekannt.', '',
              'LiveCodeBench, IFBench, BBEH sowie die ausgeschlossenen verwandten Familien IFEval, IF-RLVR, BIG-Bench und BBH sind nicht Teil dieser Sammlung. Es wurden keine Test- oder Validierungsdateien heruntergeladen. Interne Unit-Test-Felder innerhalb von CodeContests-Trainingsaufgaben sind etwas anderes als der Benchmark-Testsplit; auch diese Felder werden nicht als Trainingsantworten verwendet. Ein umfassender semantischer Kontaminationsnachweis liegt weiterhin nicht vor.', '',
              '**Reproduzieren**', '',
              '```sh', '.venv/bin/python -m slm.collect', '```', '',
              'Manifest: `data/candidates-2026-09-07/manifest.json`. Je Quelle unter `raw/<name>/`: `metadata.json`, `manifest.json`, `README.md` und die festgelegten Original-Trainingsdateien.', '']
    (ROOT / 'BENCHMARKS.md').write_text('\n'.join(lines))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sources', nargs='+', choices=sorted(SOURCES), default=list(SOURCES))
    args = p.parse_args()
    STAGE.mkdir(parents=True, exist_ok=True)
    manifests, failures = {}, {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {name: pool.submit(fetch, name) for name in args.sources}
        for name, future in futures.items():
            try:
                _, manifests[name] = future.result()
            except Exception as e:
                failures[name] = f'{type(e).__name__}: {e}'
                print(f'FAILED {name}: {failures[name]}', flush=True)
    # Retain manifests of sources from earlier successful invocations.
    for file in (STAGE/'raw').glob('*/manifest.json'):
        item = json.loads(file.read_text()); manifests[item['name']] = item
    result = dict(created=datetime.now().astimezone().isoformat(), status='collected' if not failures else 'partial', sources=manifests, failures=failures, excluded_evaluation_families=EXCLUDED_FAMILIES, original_training_sources=10, additional_sources=len(manifests), total_collected_sources=10+len(manifests), additional_original_train_rows=sum(m['original_train_rows'] for m in manifests.values()), downloaded_bytes=sum(f['bytes'] for m in manifests.values() for f in m['files']), used_in_training=False, note='Staged originals; row counts are not deduplicated tasks, model tokens or final training counts. No benchmark test/validation splits downloaded. CodeContests train records contain per-problem unit-test fields, which must not become training targets.')
    if 'spider' in manifests:
        result['spider_training_schemas'] = fetch_spider_schemas()
    result['collector_sha256'] = sha(__file__)
    (STAGE/'collector.py').write_text(Path(__file__).read_text())
    (STAGE/'manifest.json').write_text(json.dumps(result,indent=2))
    write_catalog(result)
    print(json.dumps({k:v for k,v in result.items() if k!='sources'}, indent=2), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
