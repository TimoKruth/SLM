# 47 Benchmark-Quellen für künftiges Training

Stand: 11. September 2026. Auftrag: den vorbereiteten Bestand auf mindestens 45 Benchmarks verbreitern oder vertiefen. Umsetzung im separaten Worktree `/Users/timokruth/Projekte/SLM-benchmarks45`, Branch `codex/benchmarks-45`. **Nur Datenvorbereitung; kein Training, GPU-Test oder automatische Warteschlange.** Die laufende v4-Kampagne, vorbereitete v5-Daten und das Hardware-Optimierungsprojekt bleiben unverändert.

## Umfang und Zählweise

Aus den 35 bereits vorbereiteten Quellen werden durch zwölf weitere **47 verschiedene Benchmark-Quellen**. Jede Quelle wird genau einmal gezählt: keine zusätzliche Zählung für Konfigurationen, Sprachen, Aufgabenformulierungen oder GLUE-/SuperGLUE-Sammelnamen. MultiNLI wird nicht zusätzlich als GLUE-MNLI gezählt; WSC nicht nochmals als WNLI; LogiQA nur als englische MRC-Version 2.0, ohne NLI-Ableitung oder zusätzliche Zählung der chinesischen Version. TAT-QA und DialogSum bleiben außerhalb der 47.

Neue finale Datenversion: `data/v6-benchmarks47-balanced-2026-09-11/`. Ausgangspunkt ist das unveränderte `data/v5-expanded-2026-09-11/`. Tatsächliche Größen und Prüfresultate stehen in den erzeugten Tabellen am Ende dieses Dokuments sowie in `benchmark_expansion/RESULTS47.json`; `READY.json` im neuen Datenordner ist der Abschlussbeleg.

## Was die Ergänzungen beitragen

| Quelle | Zusätzliche Breite oder Vertiefung | Original-/Distributionsquelle |
| --- | --- | --- |
| MultiNLI | Schlussfolgerungen über verschiedene Textgenres | [Autoren](https://cims.nyu.edu/~sbowman/multinli/) |
| MRPC | Bedeutungsgleichheit von Nachrichtensätzen | [GLUE-Paper mit Originalreferenz](https://aclanthology.org/W18-5446/) |
| QQP | Erkennen gleichbedeutender Fragen | [GLUE-Paper](https://aclanthology.org/W18-5446/) |
| CommitmentBank (CB) | Schlussfolgerungen unter Einbettung, Modalität und Unsicherheit | [Originalprojekt](https://github.com/mcdm/CommitmentBank) |
| COPA | Wahl plausibler Ursachen und Wirkungen | [SuperGLUE-Paper mit Originalreferenz](https://arxiv.org/abs/1905.00537) |
| MultiRC | Prüfen mehrerer möglicher Antworten anhand eines Texts | [SuperGLUE-Paper mit Originalreferenz](https://arxiv.org/abs/1905.00537) |
| WiC | Wortbedeutung in unterschiedlichen Kontexten | [Autoren](https://pilehvar.github.io/wic/) |
| WSC | Pronomen- und Referenzauflösung | [SuperGLUE-Paper mit Originalreferenz](https://arxiv.org/abs/1905.00537) |
| GoEmotions | Mehrfachlabels für emotionale Ausdrucksweisen | [Originalprojekt](https://github.com/google-research/google-research/tree/master/goemotions) |
| MedQA | Medizinisches Prüfungswissen mit originalen Antwortschlüsseln | [Originalprojekt](https://github.com/jind11/MedQA) |
| SAMSum | Zusammenfassung menschlich verfasster Dialoge | [Originalarbeit](https://aclanthology.org/D19-5409/) |
| LogiQA 2.0 | Logisches Schlussfolgern in Prüfungsaufgaben | [Originalprojekt](https://github.com/csitfun/LogiQA2.0) |

Das ist ein größeres und vielfältigeres Lernangebot, kein Nachweis erworbenen Wissens. Die neuen Quellen sind Englisch; die neun Sprachen aus TyDiQA-GoldP bleiben erhalten. Die bekannten v5-Grenzen des Tokenizers für Bengali und Telugu bestehen fort.

## Herkunft und Grenzen

Nur explizit bezeichnete Trainingsdateien werden geladen. Für die SuperGLUE-Aufgaben wird deren veröffentlichte kanonische Trainingspartition verwendet; keine eigene Umdeklarierung von Testdaten als Training. Metadaten, URLs, Revisionen und SHA-256 aller tatsächlich geladenen Dateien stehen in `benchmark_expansion/wave6.lock.json`. Die Rohdaten liegen unter `data/candidates-wave6-2026-09-11/`. Externe abgeschlossene Testfamilien und offizielle Validierungs-/Testsplits wurden nicht heruntergeladen oder geöffnet.

MultiNLI verwendet dieselbe Original-Trainingsrevision wie die frühere Vormerkung. MRPC/QQP und CB/COPA/MultiRC/WiC/WSC verwenden gepinnte GLUE-/SuperGLUE-Distributionen, jeweils nur eine Konfiguration. GoEmotions verwendet ausschließlich den ursprünglichen gefilterten Trainingssplit, nicht die als `raw/train` angebotene Sammlung über alle ursprünglichen Partitionen. MedQA verwendet einen gepinnten Mirror der USMLE-4-Options-Trainingsdatei. Textbücher, MetaMap-Phrasen und generierte Erklärungen werden keine Lernziele. SAMSum verwendet den gepinnten Trainings-Mirror mit 14.731 gelieferten CSV-Datensätzen; das ist der tatsächlich geprüfte Bestand, keine Behauptung einer vollständigen bytegleichen Rekonstruktion des ursprünglichen Archivs. LogiQA 2.0 wird direkt aus dem Autorenrepository geladen; die englische Version wurde laut Autoren professionell durch Menschen übersetzt.

Lizenzangaben bleiben quellenweise sichtbar: LogiQA CC BY-NC-SA 4.0, SAMSum CC BY-NC-ND 4.0; MultiNLI besitzt unterschiedliche Ursprungskonditionen. Bei GLUE/SuperGLUE gelten die jeweiligen Originalbedingungen. GoEmotions meldet Apache-2.0 mit fortbestehenden Rechten an zugrundeliegenden Reddit-Inhalten. Der MedQA-Mirror meldet CC BY 4.0, während das Autorenrepository MIT ausweist; dies klärt Rechte an ursprünglichen Prüfungsinhalten nicht abschließend. Diese lokale Vorbereitung ist keine Veröffentlichungs- oder kommerzielle Freigabe. Rohdaten bleiben außerhalb von Git.

## Aufbereitung und Trennung

- Originale Labelnamen werden vor der Konvertierung aus den Parquet-Metadaten gegen den erwarteten Klassenkatalog geprüft. Insbesondere unterscheiden sich die Reihenfolgen von MultiNLI und CommitmentBank. Negative Labels bei MultiRC, COPA und den binären Aufgaben bleiben erhalten. Alle ursprünglichen Klassen müssen nach Filterung weiterhin im Training vertreten sein.
- Zusammenhängende Gruppen werden vor dem internen Split gebildet: MultiNLI nach `promptID` und Prämisse, CB/COPA nach Prämisse, MRPC/QQP/WiC nach verbundenen Sätzen beziehungsweise Fragen, MultiRC nach Absatz-ID und Absatztext, WSC nach Text, GoEmotions nach Kommentar-ID und Text, MedQA nach Frage, LogiQA nach Kontext/ID, SAMSum nach Dialog/ID. Gleiche Inhalte verbinden Gruppen auch transitiv. Bei Dialogvergleichen werden ergänzend Sprechernamen vor Doppelpunkten entfernt.
- Sämtliche gespeicherten v5-Trainings-/Entwicklungsdatensätze **und die komplette reservierte v5-Gegenprüfung** werden auf exakte normalisierte Prompts, passende Fragen/Kontexte und verfügbare Gruppenkennungen geprüft. Betroffene neue Gruppen werden vollständig entfernt. Die bestehenden 35 Quellen samt Dateien, Partitionen und ursprünglichen kleinen Suiten bleiben erhalten.
- Kanonische Zielkonflikte für identische normalisierte Prompts werden konservativ auf Gruppenebene ausgeschlossen. Unterschiedliche gültige Zusammenfassungen oder Emotionseinschätzungen können darunterfallen; diese Ausschlüsse beweisen keine fehlerhaften Originalantworten. Sämtliche Verwerfungen sind gezählt.
- Der bisherige Tokenizer bleibt bitgleich. Aufgaben werden nur vollständig mit Antwort aufgenommen, wenn sie höchstens 1.024 Tokens benötigen; keine Kürzung und keine neu erzeugten Lehrerantworten. Bei WiC werden die mitgelieferten Wortpositionen sichtbar markiert; bei WSC werden die originalen Ausdruckspositionen ausgewiesen. GoEmotions behält sämtliche originalen Klassen eines Kommentars, nicht nur die erste.
- Der deterministische Gruppensplit zielt auf ungefähr 90 % Training sowie je 5 % interne Entwicklung/Gegenprüfung. Für CB/COPA/WSC werden fehlende Klassen in den kleinen Holdouts durch Verschieben ganzer bisheriger Trainingsgruppen ergänzt. Das ist eine dokumentierte Aufbereitung vor dem ersten Modelllauf, kein nachträgliches Anpassen an Modellergebnisse.

**Abgleichgrenzen:** Keine vollständige Near-Duplicate-, Übersetzungs- oder semantische Kontaminationsprüfung. Bei MRPC fehlen Nachrichtenartikel-IDs und beim gefilterten GoEmotions-Split Reddit-Thread-IDs; die Trennung gilt für die verfügbaren Satz-/Kommentargruppen, nicht nachweislich für sämtliche gemeinsamen Artikel oder Threads. Der Abgleich verwendet gespeicherte v5-Beispiele, nicht alle historisch verworfenen Originaltexte. Interne Tests bleiben Aufgaben aus Original-Trainingspartitionen und sind keine externen Transfernachweise.

## Mischung und Auswertung

`slm/breadth.py:BENCHMARK47_FAMILIES` bildet die 47 Quellen auf 13 Fähigkeitsgruppen ab. Die bisherigen 32- und 35-Quellen-Zuordnungen bleiben unverändert. Das neue Manifest enthält als Vorschlag gleiche Samplingmasse je Familie und darin gleiche Masse je Quelle. Das sind Sequenzanteile, keine garantierten Tokenanteile; kleine Quellen würden entsprechend häufig wiederholt. Eine spätere Trainingsfreigabe sollte Datenkontakt und Fähigkeiten getrennt protokollieren, nicht nur eine Gesamtzahl korrekt gelöster Aufgaben.

Die neue Entwicklungs- und Gegenprüfungssuite enthalten höchstens 16 verschiedene Gruppen pro neuer Quelle; längere Prompts werden so gefiltert, dass mindestens 128 Generierungspositionen verfügbar bleiben. Die vollständigen internen Holdout-Datensätze bleiben separat verfügbar. Kleine Suiten dienen der Diagnose; seltene Emotionen sind nicht notwendigerweise in jeder kleinen Auswahl vertreten.

`slm.broad_eval` unterstützt die neuen Quellen. Klassifikation und Multiple Choice werden als interne Antwort-Proxys berichtet; MultiRC pro Antwortkandidat, nicht als offizielles Frage-Exact-Match. GoEmotions verwendet mengenbasierte Labelgenauigkeit und F1. SAMSum erhält nur einen Wortüberlappungsproxy ohne `correct`-Behauptung; Faktentreue, Auslassungen und Sprecherzuordnung benötigen gesonderte Beurteilung. Medizinische Benchmark-Antwortschlüssel werden als historische Referenzen beibehalten, nicht als aktuell klinisch geprüfte Ratschläge. Keine neue Modellauswertung wurde gestartet.

## Reproduktion und Betrieb

Im Vorbereitungsworktree, mit neuen Ausgabezielen:

```sh
.venv/bin/python -m benchmark_expansion.fetch --lock benchmark_expansion/wave6.lock.json --output data/candidates-wave6-copy
TOKENIZERS_PARALLELISM=false .venv/bin/python -m benchmark_expansion.wave6 --base data/v5-expanded-2026-09-11 --stage data/candidates-wave6-copy --output data/v6-benchmarks47-copy
TOKENIZERS_PARALLELISM=false .venv/bin/python -m benchmark_expansion.verify --data data/v6-benchmarks47-copy
```

Datenvorbereitung und vollständige Verifikation laufen ausschließlich auf CPU mit reduziertem Prozessvorrang und begrenztem Arrow-/Tokenizer-Parallelismus. `verify` prüft Prüfsummen, jede neue Tokenfolge und Antwortmaske gegen die Texte, Rohzeilenbilanz, Gruppentrennung und Sampler-Batches aus allen Trainingsquellen. Alte Binärdateien werden nach Hashprüfung per Symlink übernommen; v6 hängt weiterhin von den erhaltenen v5-/v4-Dateien ab.

Der erste vollständig aufgebaute Zwischenstand `data/v6-benchmarks47-2026-09-11/` bleibt als Vorbereitungsbeleg erhalten. Die finale Version mit ergänzter Klassenabdeckung trägt ausdrücklich `balanced` im Verzeichnisnamen. Das bezeichnet die Klassenabdeckung in den kleinen Holdouts, nicht eine global klassenbalancierte Trainingsmischung.

Der `STOP`-Text im Datenverzeichnis ist nur ein Vorbereitungsmarker, keine vom Trainer erzwungene Sperre. Es wurde keine Kampagne angelegt oder zusätzliches Training gestartet. Künftige Trainings-/Modellauswertungsläufe benötigen einen ausdrücklichen Folgeauftrag und verwenden `run_slm.py` mit Light-Monitoring. CPU-/Dateisystemlast während dieser Vorbereitung ist eine mögliche Störgröße für die gleichzeitig laufende zeitbegrenzte Kampagne; deren eingefrorene Bedingungsdateien werden nicht rückwirkend verändert. Neue Daten sind nicht Bestandteil der historischen ZIP64-Archive; kein Remote-Push oder externe Sicherung.

## Tatsächlicher Datenbestand

| Neue Quelle | Original-Trainingszeilen | Aufgenommenes Training | Interne Entwicklung | Interne Gegenprüfung |
| --- | ---: | ---: | ---: | ---: |
| multinli | 392702 | 353453 | 19333 | 19614 |
| mrpc | 3668 | 3316 | 169 | 183 |
| qqp | 363846 | 329554 | 17342 | 16258 |
| cb | 250 | 232 | 10 | 8 |
| copa | 400 | 343 | 32 | 25 |
| multirc | 27243 | 24166 | 1082 | 1278 |
| wic | 5428 | 4921 | 259 | 248 |
| wsc | 554 | 489 | 25 | 38 |
| go_emotions | 43410 | 38839 | 2160 | 2127 |
| medqa | 10178 | 9166 | 529 | 481 |
| samsum | 14731 | 12407 | 662 | 710 |
| logiqa | 12567 | 10497 | 582 | 597 |

Gesamttraining: **2.344.017 Paare**. Zuwachs gegenüber v5: **787.383 Paare**. Alle Originalklassen bleiben im Training erhalten; bei CB/COPA/WSC sind sie außerdem in beiden vollständigen internen Holdouts vertreten.

## Vollständiger Katalog: 47 Quellen

| Fähigkeitsgruppe | Quellen | Anzahl |
| --- | --- | ---: |
| programming_and_queries | apps, mbpp, code_contests, spider, wikisql | 5 |
| mathematics | gsm8k, math, aqua_rat, tabmwp | 4 |
| reading_and_extraction | squad, boolq, ropes, drop, hotpotqa, quoref, race, multirc | 8 |
| commonsense_and_social | hellaswag, winogrande, piqa, commonsenseqa, social_i_qa, cosmos_qa, wsc, go_emotions | 8 |
| science_and_causality | arc, sciq, openbookqa, qasc, quartz, quarel, wiqa, copa | 8 |
| entailment | snli, anli, scitail, multinli, cb | 5 |
| dialogue | dream | 1 |
| factual_knowledge | triviaqa | 1 |
| multilingual_reading | tydiqa | 1 |
| language_meaning | mrpc, qqp, wic | 3 |
| logical_reasoning | logiqa | 1 |
| medical_knowledge | medqa | 1 |
| summarization | samsum | 1 |

## Verifizierter Abschluss

Alle neuen Tokenfolgen und Antwortmasken, Rohzeilenbilanzen, Gruppen, Hashes und Sampler-Batches wurden vollständig auf CPU geprüft. **47 CPU-Regressionsprüfungen bestanden.** Die kleinen neuen Suiten enthalten **183 Entwicklungsaufgaben** und **184 Gegenprüfungsaufgaben**; alle drei CB-Klassen sind in beiden Suiten enthalten. `READY.json` meldet `verified_preparation_only`. Die 276 nicht von der CB-Splitergänzung betroffenen Tokenarrays sind bitgleich zum ersten Vorbereitungsstand.
