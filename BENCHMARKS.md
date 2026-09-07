# Benchmark-Sammlung für spätere Trainings

Stand: 7. September 2026, 10:41 Uhr.

**32 Benchmark-Datensätze sind inzwischen gesammelt; 24 werden im laufenden zweiten Versuch verwendet.** Der erste abgeschlossene Lauf nutzte die ursprünglichen zehn. Die folgenden 14 Ergänzungen bilden mit ihnen den Pool für [Lauf 2](LAUF_2.md). Weitere acht Quellen mit 356.312 Original-Trainingszeilen liegen separat für spätere Versuche bereit; deren Katalog und ausstehende Prüfungen stehen in [VORBEREITUNG_3.md](VORBEREITUNG_3.md).

Zusätzliche Rohdaten: 973,732 Zeilen in Original-Trainingsanteilen; 7.94 GB Parquet-Dateien. Das sind weder deduplizierte Aufgaben noch fertige Trainingspaare. Eine Zeile kann viele Referenzprogramme enthalten.

| Quelle | Schwerpunkt | Original-Trainingszeilen | Lizenz laut Metadaten |
| --- | --- | ---: | --- |
| [sciq](https://huggingface.co/datasets/allenai/sciq) | Naturwissenschaftliches Textverständnis | 11,679 | cc-by-nc-3.0 |
| [openbookqa](https://huggingface.co/datasets/allenai/openbookqa) | Naturwissenschaftliches Schlussfolgern | 4,957 | unknown |
| [commonsenseqa](https://huggingface.co/datasets/tau/commonsense_qa) | Alltagswissen | 9,741 | mit |
| [qasc](https://huggingface.co/datasets/allenai/qasc) | Zwei unterstützende Fakten kombinieren | 8,134 | cc-by-4.0 |
| [quartz](https://huggingface.co/datasets/allenai/quartz) | Qualitative physikalische Beziehungen | 2,696 | cc-by-4.0 |
| [quarel](https://huggingface.co/datasets/community-datasets/quarel) | Qualitatives Schlussfolgern | 1,941 | nicht angegeben |
| [ropes](https://huggingface.co/datasets/allenai/ropes) | Wissen auf beschriebene Situationen anwenden | 10,924 | cc-by-4.0 |
| [drop](https://huggingface.co/datasets/ucinlp/drop) | Rechnen und Vergleichen anhand von Texten | 77,400 | cc-by-sa-4.0 |
| [hotpotqa](https://huggingface.co/datasets/hotpotqa/hotpot_qa) | Fragen über mehrere Dokumente | 90,447 | cc-by-sa-4.0 |
| [race](https://huggingface.co/datasets/ehovy/race) | Leseverständnis aus Prüfungsaufgaben | 87,866 | other |
| [snli](https://huggingface.co/datasets/stanfordnlp/snli) | Folgerung, Widerspruch und neutrale Aussagen | 550,152 | cc-by-sa-4.0 |
| [aqua_rat](https://huggingface.co/datasets/deepmind/aqua_rat) | Mathematik mit menschlichen Lösungsbegründungen | 97,467 | apache-2.0 |
| [spider](https://huggingface.co/datasets/xlangai/spider) | SQL aus Text und Datenbankschema | 7,000 | cc-by-sa-4.0 |
| [code_contests](https://huggingface.co/datasets/deepmind/code_contests) | Wettbewerbsprogrammierung mit Referenzcode | 13,328 | cc-by-4.0 |

**Was tatsächlich gesammelt wurde**

Ausschließlich originale `train`-Parquet-Dateien, zusätzlich Dataset Cards und Metadaten. Pro Benchmark nur eine kanonische Konfiguration, beispielsweise RACE `all`, HotpotQA `distractor` und AQuA-RAT `raw`. Revisionen sind im Downloader festgelegt; Dateiprüfsummen, Zeilenzahlen und Splitnamen stehen im Manifest. Die Daten liegen getrennt vom eingefrorenen ersten Trainingskorpus unter `data/candidates-2026-09-07/`. Ihre aufbereiteten Trainingsbeispiele werden im zweiten Lauf verwendet; der ursprüngliche Tokenizer bleibt eingefroren. Die Ergebnisse der Aufbereitung stehen in [LAUF_2.md](LAUF_2.md).

**Vor dem nächsten Training**

- CodeContests zuerst auf ursprüngliche korrekte Python-3-Referenzen reduzieren und nach Aufgaben gruppieren. Falsche Lösungen, andere Programmiersprachen und generierte Unit-Tests werden keine Lernziele. Gegen APPS und die reservierten Entwicklungsaufgaben nach Problemherkunft, Text und Code-AST deduplizieren.
- Spider: Zusätzlich sind die Schemata sämtlicher 140 Trainingsdatenbanken in `raw/spider/train_schemas.json` gesammelt; Quelle und Prüfsummen stehen in `schema_manifest.json`. Frage und Schema zusammen in den Prompt aufnehmen, Entwicklungsgruppen nach Datenbank anlegen.
- SNLI nach Ausgangssatz, RACE nach Artikel und die kontextgebundenen QA-Datensätze nach Dokumenten/Herkunft gruppieren. Ungültige Labels und leere Antworten entfernen. Große Quellen wie SNLI dürfen die Mischung nicht dominieren.
- Originale Begründungen nutzen, sofern vorhanden; keine neuen Lehrerantworten erzeugen. Lizenz- und Herkunftsdetails aus den gespeicherten Cards übernehmen. Nichtkommerzielle bzw. unklare Bedingungen bleiben sichtbar.
- Exakte und ungefähre Dublettenprüfung, Abgleich gegen bestehende Entwicklungsgruppen sowie Ermittlung vollständiger Beispiele innerhalb der gewählten Kontextlänge. Erst danach ist die tatsächlich nutzbare Trainingsmenge bekannt.

LiveCodeBench, IFBench, BBEH sowie die ausgeschlossenen verwandten Familien IFEval, IF-RLVR, BIG-Bench und BBH sind nicht Teil dieser Sammlung. Es wurden keine Test- oder Validierungsdateien heruntergeladen. Interne Unit-Test-Felder innerhalb von CodeContests-Trainingsaufgaben sind etwas anderes als der Benchmark-Testsplit; auch diese Felder werden nicht als Trainingsantworten verwendet. Ein umfassender semantischer Kontaminationsnachweis liegt weiterhin nicht vor.

**Reproduzieren**

```sh
.venv/bin/python -m slm.collect
```

Manifest: `data/candidates-2026-09-07/manifest.json`. Je Quelle unter `raw/<name>/`: `metadata.json`, `manifest.json`, `README.md` und die festgelegten Original-Trainingsdateien.
