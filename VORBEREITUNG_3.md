# Vorbereitung während Lauf 2

Stand: 7. September 2026, 10:41 Uhr (Europe/Berlin).

Der laufende Sechs-Stunden-Versuch verwendet weiterhin seine eingefrorenen **24 Quellen**. Zusätzlich sind acht Quellen für spätere Versuche gespeichert; damit sind **32 Benchmark-Datensätze gesammelt**. Die neuen Daten wurden dem laufenden Training nicht hinzugefügt. Alle 14 Python-Dateien stimmen mit dessen Quellcode-Snapshot überein; auch die Prüfsumme seines Datenmanifests ist unverändert.

## Acht neue Quellen

| Quelle | Ergänzender Schwerpunkt | Original-Trainingszeilen | Lizenzmetadaten |
| --- | --- | ---: | --- |
| [Social IQa](https://huggingface.co/datasets/allenai/social_i_qa) | Soziale Situationen und Absichten | 33.410 | nicht angegeben; Card gesondert prüfen |
| [Quoref](https://huggingface.co/datasets/allenai/quoref) | Bezüge zwischen Personen und Aussagen im Text | 19.399 | CC BY 4.0 |
| [WIQA](https://huggingface.co/datasets/allenai/wiqa) | Folgen veränderter Bedingungen in Abläufen | 29.808 | nicht angegeben |
| [Cosmos QA](https://huggingface.co/datasets/allenai/cosmos_qa) | Schlussfolgerungen aus Alltagstexten | 25.262 | CC BY 4.0 |
| [WikiSQL](https://huggingface.co/datasets/Salesforce/wikisql) | SQL aus Frage und Tabelle | 56.355 | unknown |
| [DREAM](https://huggingface.co/datasets/dataset-org/dream) | Dialogverständnis | 6.116 | unknown |
| [ANLI](https://huggingface.co/datasets/facebook/anli) | Anspruchsvolle Folgerungs- und Widerspruchsaufgaben | 162.865 | CC BY-NC 4.0 |
| [SciTail](https://huggingface.co/datasets/allenai/scitail) | Naturwissenschaftliche Folgerungen | 23.097 | nicht angegeben |
| **Summe** | **8 Quellen; ANLI-Runden gemeinsam gezählt** | **356.312** | |

Die zehn Parquet-Dateien belegen insgesamt 74.303.219 Bytes, etwa 74,3 MB. Sämtliche Dateiprüfsummen, Zeilenzahlen und Card-Prüfsummen wurden nach dem Download erneut geprüft. Es sind Rohdatenzeilen, noch keine deduplizierten Trainingspaare.

Speicherort: `data/candidates-wave3-2026-09-07/`. `manifest.json` enthält URLs, Revisionen, Splitnamen, Spalten, Größen und SHA-256-Prüfsummen; `verification.json` dokumentiert die erneute Prüfung. Der Downloader ist `experiments/collect_wave3.py`.

Nur ursprüngliche Trainingssplits wurden geladen. Bei sechs Quellen stammen die Parquet-Dateien aus Hugging Faces Konvertierungsrevision. Diese und die Revision der ursprünglichen Dataset Card sind getrennt festgehalten; damit ist keine Identität der Ausgangsrevisionen bewiesen. Dataset-Ladeskripte wurden nicht ausgeführt. LiveCodeBench, IFBench, BBEH und die ausgeschlossenen verwandten Familien bleiben geschlossen.

Vor der Verwendung sind Herkunft, Antwortlabels, vollständige Beispiele innerhalb des Kontextfensters und Überschneidungen zu bisherigen Entwicklungsgruppen zu prüfen. Insbesondere brauchen Quoref dokumentweise und DREAM dialogweise Gruppen; WikiSQL braucht tabellenweise Gruppen sowie eine geprüfte SQL-Serialisierung. SciTail muss auch gegen bestehende naturwissenschaftliche Quellen geprüft werden. ANLI darf durch seine Größe die Mischung nicht dominieren.

Social IQa beschreibt in seiner Card auch maschinell erzeugte falsche Antwortkandidaten. Diese sollten für das Experiment ausgeschlossen werden; die Herkunft der positiven Antworten ist vor einer Aufnahme zu bestätigen. MathQA wurde wegen seiner Ableitung aus AQuA-RAT zurückgestellt. Eine zusammengeführte SQL-Sammlung aus Spider und WikiSQL wurde ebenfalls zurückgestellt; stattdessen liegt jetzt WikiSQL separat vor.

## Performance vorbereitet und geprüft

Zwei isolierte Kandidaten liegen unter `experiments/performance/`:

1. **KV-Cache für Generierung:** Bereits berechnete Attention-Schlüssel und -Werte bleiben erhalten. Die RoPE-Positionen werden beim Anhängen weiterer Tokens korrekt versetzt. Grundlage ist die [MLX-RoPE-API](https://ml-explore.github.io/mlx/build/html/python/nn/_autosummary/mlx.nn.RoPE.html).
2. **Kompilierter Trainingsschritt:** Forward-Pass, Gradienten, Clipping und AdamW-Update werden gemeinsam mit explizitem Modell- und Optimiererzustand kompiliert. Die Lernrate bleibt dynamisch. Grundlage ist die [MLX-Dokumentation zur Kompilierung](https://ml-explore.github.io/mlx/build/html/usage/compile.html); lokal wurde die API von MLX 0.31.2 geprüft.

**Sieben Tests bestanden**, ausschließlich auf der CPU beziehungsweise ohne Modellrechnung: Logits bei stückweisem Cache-Aufbau, identische greedy Tokenfolgen, frischer Cache pro Anfrage, Kontextgrenze, fünf äquivalente Optimiererschritte mit wechselnder Lernrate sowie die Startschutzprüfungen für laufendes Training, veränderten Quellcode und abgelaufene Warteschlange. Die kleinen CPU-Modelle prüfen Funktion und numerische Übereinstimmung; ein GPU-Geschwindigkeitsgewinn ist damit noch nicht belegt.

Der CPU-Sampler wurde zusätzlich mit 500 echten Batches nach 25 Aufwärm-Batches vermessen: im Mittel **0,093 ms pro Batch**. Bei der gleichzeitig beobachteten Trainingsrate ergibt das grob **0,028 %** einer Trainingsschrittzeit. Das schließt Modellrechnung, MLX-Konvertierung und initiales Laden aus. Der Python-Sampler ist damit voraussichtlich kein relevanter Engpass. Durchschnittlich sind **82,1 %** der 2 × 1.024 Tokenplätze belegt; besseres Packing ist ein späterer Kandidat, muss aber die gewünschte Aufgabenmischung erhalten. Rohmessung: `runs/performance-2026-09-07/sampler.json`.

## Automatischer GPU-Vergleich nach dem laufenden Versuch

Der einmalige LaunchAgent `local.slm.performance-20260907` wartet, bis der Supervisor des aktuellen Laufs fertig ist und kein SLM-Trainings- oder Evaluationsprozess mehr läuft. Das Training hat sein Zeitfenster bis **15:19 Uhr**, die anschließende Auswertung bis ungefähr **15:34 Uhr**. Die Warteschlange verfällt um **17:34 Uhr**; der GPU-Vergleich selbst ist auf **zehn Minuten** begrenzt.

Gemessen werden drei Wiederholungen mit wechselnder Reihenfolge: bisheriger gegenüber kompiliertem Trainingsschritt bei gleichen Gewichten und echten, vorgeladenen Batches; anschließend Generierung mit und ohne KV-Cache bei gleicher Prompt- und Ausgabelänge. Aufwärmen einschließlich Kompilierung wird separat erfasst. Loss-Verläufe und generierte Tokenfolgen werden verglichen. Dies ist eine Geschwindigkeitsmessung, keine zusätzliche Qualitätsbewertung.

Plan und Status: `runs/performance-2026-09-07/plan.json` und `status.json`. Nach erfolgreichem Abschluss entstehen dort `results.json` und `REPORT.md`; bei Fehler oder Zeitablauf bleiben Status und Log erhalten. Ein `STOP` in diesem Verzeichnis verhindert den Start, solange der Job noch wartet. Auch ein Abbruch des Hauptlaufs verhindert den nachgelagerten Versuch. Geänderte geplante Quelldateien führen zum Überspringen des Vergleichs.

Die Kandidaten werden nicht automatisch in die Trainingspipeline übernommen. Eine Übernahme folgt erst auf die GPU-Messung und eine Prüfung von Checkpoint-Wiederaufnahme und realen Aufgaben.
