# Referenzbereinigung und neue Gegenprüfungsdaten

15. September 2026, Nutzerauftrag „go for it“. Vorbereitung mit CPU, ohne Modelltraining oder Modell-Auswertung. Historische Daten, Scores und aktive Kampagnen bleiben unverändert.

## Separate Datenversion

`data/v4-reference-audited-2026-09-15/` ist eine Ableitung der bisherigen 32-Quellen-Version v4. Sechs bereits geprüfte Referenzgruppen werden vollständig quarantänisiert: APPS 4184, BoolQ 7445, AQuA 62285/32965/79813 und die prüfbedürftige ANLI-Gruppe um 4356d65b-47d2-44f4-baf3-dfed217d688d. Die ANLI-Referenz ist als mehrdeutig markiert, nicht als sicher falsch. Ganze Gruppen auszuschließen verhindert, dass andere Aufgaben oder Lösungsvarianten derselben Gruppe weiterhin in der neuen Entwicklungsauswertung auftauchen.

Das entfernt 23 **Entwicklungsdatensätze**: 8 APPS-, 1 BoolQ-, 3 AQuA- und 11 ANLI-Einträge. Alle 1.433.943 Trainingspaare bleiben bytegleich und in derselben Reihenfolge. Es gibt keine erfundenen Ersatzantworten. Auch die Trainingsgewichtung und der Tokenizer bleiben gleich. Die neue Version behebt bekannte Probleme in der künftigen Entwicklungsauswertung; sie belegt keinen Trainingsdatenfehler als Ursache der bisherigen Qualitätsrückgänge.

Unveränderte Token-/Masken-/Indexdateien sind eigenständige Kopien. Betroffene Entwicklungsdateien enthalten exakt die alten Token- und Maskensegmente der beibehaltenen Aufgaben mit neuen zusammenhängenden Indizes. Die neue Version wurde nicht in eine Kampagne übernommen; die 47-Quellen-Vorbereitung ist eine getrennte Datenlinie.

## Neue Gegenprüfung

Die Ergänzung verwendet ausschließlich die ursprünglichen **Validierungssplits** von [ARC](https://huggingface.co/datasets/allenai/ai2_arc), [DREAM](https://huggingface.co/datasets/dataset-org/dream), [QuaRel](https://huggingface.co/datasets/community-datasets/quarel) und [Quoref](https://huggingface.co/datasets/allenai/quoref). Die Dateien sind auf konkrete Repository-/Parquet-Revisionen fixiert. Originalkarten, Metadaten, Dateipfade und SHA-256-Werte liegen unter `data/evaluation-validation-refresh-2026-09-15/`; der aggregierte Quellenbeleg ist versioniert. Insgesamt wurden 5.605 ursprüngliche Validierungszeilen geladen. Der Train-only-Collector wurde nicht verändert, und diese Ergänzungen sind ausschließlich Evaluationsmaterial.

Für diese vier Quellen wird je die gesamte neue 64er-Quote aus dem ursprünglichen Validierungssplit gewählt. Die übrigen 21 Quellen stammen aus bisher ungenutzten internen v4-Entwicklungsgruppen. Dadurch vermischt die neue Suite zwei Herkunftsarten: originalen Validierungssplit und interne Abtrennung aus Original-Trainingsmaterial. Herkunft ist pro Aufgabe markiert. Absolute Scores wären nicht direkt mit den alten Suiten vergleichbar. Interne Entwicklungsaufgaben können bereits über den Dev-Loss sichtbar gewesen sein; „ungenutzt“ bezieht sich hier auf die erfassten Aufgaben-Suiten, nicht auf jede mögliche frühere Modellberührung.

Vor der Auswahl werden alle gefundenen historischen und vorbereiteten Trainingskorpora sowie bestehende/reservierte Suiten in den lokalen SLM-Worktrees einbezogen. Der Filter sperrt ganze Gruppen bei Überschneidung von Gruppenkennung, normalisiertem Prompt, extrahiertem Kontext/Dialog/Fragetext oder Quoref-Artikelalias. Das ist eine konkrete exakte Inhaltsprüfung, keine vollständige semantische oder Near-Duplicate-Garantie. Reservierungen werden vor Abschluss erneut erfasst und müssen vor einer späteren Nutzung nochmals geprüft werden.

Die Auswahl erfolgt deterministisch mit festem Hash-Salt, ohne Modellausgaben oder Scores. Pro Gruppe höchstens eine Aufgabe; vollständige Originalreferenz sowie Prompt plus 256 Ausgabetokens müssen in 1.024 Tokens passen. Antwortoptionen werden gegen Original-Labels geprüft, bei Quoref zusätzlich alle Referenzspannen gegen den Passage-Text. Vorhandene Referenzmängel werden gruppenweise gesperrt. Der strikte historische Scorer bleibt unverändert; eine passende Optionskennung mit falschem Antworttext wird nicht nachträglich als richtig gewertet.

## Abschluss der Abdeckungsprüfung

Alle Quoten sind erfüllt: **1.360 Aufgaben aus 25 Quellen**, davon **1.280 korrektheitsbewertete Aufgaben** aus 20 Quellen. Jede bewertete Quelle hat 64 Gruppen, jede der fünf unbewerteten Quellen 16. Es werden 256 ursprüngliche Validierungsaufgaben und 1.104 interne v4-Entwicklungsaufgaben verwendet; `original_split=train` bei letzteren bezeichnet die Herkunft beim Datenanbieter, nicht ihre Projektpartition.

| Ergänzte Quelle | Geeignete Gruppen nach Filtern | Ausgewählt | Restlücke |
|---|---:|---:|---:|
| ARC | 866 | 64 | 0 |
| DREAM | 1.284 | 64 | 0 |
| QuaRel | 278 | 64 | 0 |
| Quoref | 265 | 64 | 0 |

Neun lokale Korpusdateien und 61 bestehende/reservierte Suiten wurden geprüft. Unter den implementierten Gruppen- und exakten Inhaltsprüfungen hat die ausgewählte Suite null Überschneidungen mit Training und bestehenden/reservierten Suiten. Bei Quoref wurden 57 Originalzeilen wegen ungültiger Labels/Referenzspannen verworfen, zusätzlich greifen die Kontextgrenzen. Das ist keine vollständige fachliche Begutachtung aller neuen Originalreferenzen.

Suite-SHA-256: `1ec15a68f17b49096b3df611841ff842805ed36882ec680744319f17a2c053b4`. Der übernommene Suite-Schlüssel `data_manifest_sha256` bezeichnet die v4-Basis; die vier Ergänzungen haben zusätzliche Datei-/Revisionsnachweise je Aufgabe und im separaten Quellenmanifest. [Aggregierte Abdeckung](results/2026-09-15/parameter-reference-refresh/coverage-audit.json), [Referenzquarantäne](results/2026-09-15/parameter-reference-refresh/reference-quarantine.json), [Originalquellen](results/2026-09-15/parameter-reference-refresh/validation-sources.json).

## Abschlusskontrollen

Alle 1.508.958 beibehaltenen Datensätze sind bytegleich und in Originalreihenfolge; 23 Einträge fehlen genau gemäß Gruppenquarantäne. 192 abgeleitete Dateien geprüft, die 14.039 beibehaltenen Aufgaben der betroffenen Entwicklungssplits unabhängig erneut tokenisiert und einschließlich Antwortmasken abgeglichen. Alle 1.280 bewertbaren Originalreferenzen bestehen ihren eigenen eingefrorenen Scorer. Die 256 neu ausgewählten Validierungsaufgaben überschneiden sich unter den Inhalts-/Gruppenprüfungen auch nicht mit der historischen v4-Entwicklungsmenge. ARC enthält 45 Easy- und 19 Challenge-Aufgaben; das ist eine Hash-Auswahl, keine Gleichgewichtung der beiden Konfigurationen.

Elf CPU-Tests bestanden. [Abschlussprüfung](results/2026-09-15/parameter-reference-refresh/verification.json) und [Exportprüfsummen](results/2026-09-15/parameter-reference-refresh/exports.json) enthalten die Belege. Referenz-Selbstbewertung prüft Konverter-/Scorer-Kompatibilität, nicht die fachliche Wahrheit jeder Originalantwort.

## Nutzung und Reproduktion

Die lokale Suite liegt unter `runs/parameter-confirmation-refresh-2026-09-15/confirmation-suite.json`, mit `STOP`, Abdeckungsprüfung und Eingabehashes. Es gibt keinen Starter und keine Modellausgaben. **Vollständige Datenabdeckung ist keine Freigabe eines neuen Versuchs.** Vor einer Ausführung müssen konkrete Hypothese, Kandidat, Elternkontrolle, gemeinsamer Token-/Update-Endpunkt, Auswahl-/Entscheidungsregel und begrenztes Ressourcenbudget feststehen. Die reservierten externen Abschlusstests und die Original-Testdateien bleiben ungeöffnet.

Reproduktion aus dem Projektcode; Ausgabepfade müssen neu sein:

```sh
python -m experiments.refresh_parameter_data quarantine --project /path/to/SLM --output /new/data-version
python -m experiments.refresh_parameter_data collect --project /path/to/SLM --output /new/validation-stage
python -m experiments.prepare_fresh_parameter_confirmation --project /path/to/SLM --stage /new/validation-stage --output /new/run-directory --scorer /path/to/SLM-long-round2/slm/broad_eval.py
python -m experiments.verify_parameter_refresh --project /path/to/SLM --output /new/verification.json
python -m pytest -q tests/test_parameter_refresh.py tests/test_parameter_analysis.py
```

Der Abschlussprüfer verwendet die hier dokumentierten lokalen Daten-/Suitepfade. Rohaufgaben, Referenzantworten und Token-Dateien bleiben lokal und werden nicht ins öffentliche Repository aufgenommen. Kein Remote-Push und keine Erweiterung der vorhandenen ZIP-Archive.
