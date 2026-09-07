# Zweiter Trainingslauf: sechs Stunden

Stand: 7. September 2026, nach geprüftem Start. Aktueller Maschinenstatus steht in `runs/expanded-2026-09-07-6h/status.json`.

**Zeitplan**

- Start: 2026-09-07T09:19:13.127259+02:00
- Trainingsende: 2026-09-07T15:19:13.127259+02:00
- Anschließend Bericht und Code-Diagnose; Auswertungsfenster bis 2026-09-07T15:34:13.127259+02:00.
- Die sechs Stunden sind ein festes Zeitfenster einschließlich periodischer Entwicklungsmessung und Checkpoints. Aufbereitung und Probelauf zählen nicht mit. Wiederanläufe verlängern die Deadline nicht.

**Modell und Daten**

97.536.768 Parameter, zufällige Neuinitialisierung, gleiche Architektur wie Lauf 1: 12 Decoder-Blöcke, 768 Dimensionen, 12 Heads, SwiGLU, RoPE, FP32. Der auf den ursprünglichen Trainingsdaten gelernte Tokenizer mit 16.384 Einträgen bleibt eingefroren. Keine vortrainierten Gewichte oder neuen Lehrerantworten.

24 Quellen, 1.095.239 Trainingspaare, 190.909.332 gespeicherte Trainingstokens und 58.627 Entwicklungspaare. Vollständige Beispiele bis 1.024 Tokens; längere Beispiele werden ausgeschlossen. Die alten Daten und Checkpoints bleiben unter ihren bisherigen Pfaden erhalten.

AdamW, volle Next-Token-Loss über Aufgabe und Antwort, Batchgröße 2, Lernrate bis 0,0003 mit Warmup und zeitabhängiger Absenkung. Für diesen Lauf greift die Zeitgrenze; das frühere Limit von 100 Millionen verarbeiteten Tokens wurde aufgehoben. Python und SQL erhalten zusammen rund 47,3 % des Samplings nach Sequenzen. Die tatsächlichen Tokenanteile hängen von der Packungsdichte ab.

| Quelle | Trainingspaare | Trainingstokens | Entwicklungspaare | Samplinggewicht |
| --- | ---: | ---: | ---: | ---: |
| apps | 30.879 | 14.361.579 | 1.523 | 22.66 % |
| mbpp | 359 | 41.190 | 15 | 2.96 % |
| code_contests | 39.651 | 22.599.604 | 2.134 | 17.73 % |
| spider | 6.400 | 2.553.105 | 374 | 3.94 % |
| gsm8k | 7.092 | 1.237.220 | 381 | 7.88 % |
| math | 6.994 | 1.986.770 | 358 | 6.90 % |
| aqua_rat | 92.558 | 15.696.728 | 4.798 | 5.91 % |
| squad | 82.630 | 17.603.966 | 4.776 | 3.94 % |
| boolq | 8.969 | 1.525.604 | 457 | 1.48 % |
| hellaswag | 37.777 | 3.852.259 | 2.022 | 2.46 % |
| piqa | 14.069 | 758.422 | 753 | 2.46 % |
| winogrande | 38.471 | 1.906.638 | 1.923 | 1.97 % |
| arc | 3.193 | 254.233 | 176 | 1.48 % |
| sciq | 11.088 | 1.554.619 | 585 | 1.48 % |
| openbookqa | 4.675 | 269.863 | 273 | 0.99 % |
| commonsenseqa | 9.274 | 539.712 | 467 | 1.48 % |
| qasc | 7.718 | 769.867 | 414 | 1.48 % |
| quartz | 2.610 | 201.884 | 74 | 0.99 % |
| quarel | 1.854 | 130.292 | 87 | 0.99 % |
| ropes | 10.549 | 2.825.736 | 299 | 1.48 % |
| drop | 68.750 | 23.856.728 | 4.292 | 2.46 % |
| hotpotqa | 6.020 | 5.113.146 | 0 | 2.46 % |
| race | 82.886 | 37.402.637 | 4.505 | 1.97 % |
| snli | 520.773 | 33.867.530 | 27.941 | 2.46 % |

**Trennung und Änderungen**

Die ursprünglichen Entwicklungsgruppen bleiben reserviert. Identische neue Prompts und Fragen mit Original-Dubletten werden entfernt; Codeaufgaben werden zusätzlich über Fünfwort-Shingles mit Jaccard-Schwelle 0,8 auf nahe Dubletten geprüft. Referenzen mit identischen Python-ASTs über die Partitionen hinweg führen zum Ausschluss ganzer neuer Aufgaben. Der abschließende Audit bestätigt null Überschneidungen bei Gruppen, exakten Prompts und Code-ASTs sowie null ursprüngliche Entwicklungsgruppen im Training. Eine vollständige semantische Kontaminationsprüfung liegt nicht vor.

CodeContests liefert nur als Python 3 parsebare korrekte Original-Referenzen, höchstens acht unterschiedliche pro Aufgabe. Falsche Lösungen und Unit-Test-Felder werden nicht zu Lernzielen. Parsebarkeit allein belegt keine funktionale Korrektheit aller Trainingsreferenzen. MBPP/APPS-Funktionsaufgaben erhalten zusätzlich den erwarteten Funktionsnamen, ohne Assertions oder Lösungsprogramme in den Prompt zu kopieren. Spider-Prompts enthalten die passenden Tabellen- und Fremdschlüsselschemata.

HotpotQA hat wegen gemeinsam genutzter Dokumente keinen eigenen internen Entwicklungssplit. Aufgaben mit erkannten Überschneidungen zu reservierten SQuAD-Artikeltiteln wurden ausgeschlossen. Die periodische Entwicklungsloss umfasst die übrigen 23 Quellen und ist daher nicht direkt mit dem bisherigen Zehn-Quellen-Mittelwert vergleichbar. Datenmischung und Promptformat ändern sich gemeinsam; Verbesserungen wären nicht isoliert einer einzigen Änderung zuzuordnen.

LiveCodeBench, IFBench und BBEH bleiben geschlossen; auch die zusätzlich ausgeschlossenen verwandten Familien werden nicht verwendet.

**Betrieb und Auswertung**

- Einmaliger lokaler LaunchAgent: `local.slm.expanded-20260907-6h`. Der Prozess läuft unabhängig von der Chatverbindung. `caffeinate` verhindert währenddessen normalen Ruhezustand; der Mac muss eingeschaltet bleiben. Kein automatischer Start nach einem Neustart.
- Vollständige Checkpoints alle fünf Minuten, letzte zwei behalten; beste Gewichte zusätzlich in `best.safetensors`. Entwicklungsmessung etwa alle 30 Minuten. Höchstens zwei Wiederanläufe aus einem vollständigen Checkpoint, innerhalb derselben Deadline.
- Nach dem Training: Bericht und qualitative Beispiele; anschließend Code-Diagnose des besten Checkpoints auf dem gleichen ursprünglichen Entwicklungsbestand wie beim ersten Lauf (81 referenzgeprüfte Aufgaben, wenn die Referenzprüfung unverändert ausfällt). Zusätzlich MBPP mit einem sichtbaren Beispiel und Bewertung der übrigen Assertions, sofern die Auswertungszeit reicht.
- Falls die Zeitgrenze eine Auswertung beendet, bleiben Ergebnisse und Checkpoints erhalten; `code-eval-status.json` kennzeichnet eine unvollständige Code-Diagnose.

**Verifikation**

19 automatisierte Tests bestanden. Der Vollmodell-Probelauf trainierte 30 Schritte, wurde aus dem gespeicherten Modell-/Optimizer-/Sampler-Zustand bis Schritt 35 fortgesetzt und erzeugte erfolgreich einen Bericht mit 20 qualitativen Beispielen. Der neue Lauf wurde als tatsächlich laufender Trainingsprozess bestätigt; erste Messung rund 4.700 Tokens/s und 5,34 GB MLX-Spitzenspeicher.

**Dateien**

- [Datenmanifest](data/v2/manifest.json), [Datenaudit](data/v2/audit.json).
- [Zeitplan](runs/expanded-2026-09-07-6h/schedule.json), [Live-Status](runs/expanded-2026-09-07-6h/status.json), [Prozessüberwachung](runs/expanded-2026-09-07-6h/supervisor.json).
- Nach Abschluss: `runs/expanded-2026-09-07-6h/REPORT.md` und `runs/expanded-2026-09-07-6h/code-eval/REPORT.md`.

Geordnet stoppen:

```sh
touch runs/expanded-2026-09-07-6h/STOP
```
