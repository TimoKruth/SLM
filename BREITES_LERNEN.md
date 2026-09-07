# Breite Lernentwicklung – nächste Versuchsreihe

Stand: 7. September 2026. Ziel ist ein vielseitiges, zufällig initialisiertes Sprachmodell aus Benchmark-Trainingsdaten. Coding ist eine Fähigkeit unter mehreren.

## Daten und Fähigkeitsprofil

Die neue, getrennte Datenversion `data/v3-broad/` umfasst **32 Quellen und 1.416.390 Trainingspaare**. Die 24 bisherigen Quellen bleiben erhalten. Neu aufgenommen: Social IQa, Quoref, WIQA, Cosmos QA, WikiSQL, DREAM, ANLI und SciTail. Original-Trainingsdaten und originale Lösungen werden verwendet; die drei externen Abschlusstests bleiben geschlossen. Dokument-, Dialog-, Tabellen- und Prämissengruppen werden vor dem Split getrennt. Neue Gruppen mit exakten Überschneidungen zu bisherigen Prompts oder extrahierten Kontexten werden ausgeschlossen. Eine vollständige semantische Dublettenprüfung liegt weiterhin nicht vor. Unklare Lizenzmetadaten bleiben im Manifest dokumentiert; Daten/Gewichte werden nicht veröffentlicht.

Die sieben Fähigkeitsgruppen stehen in `slm/breadth.py`: Programmierung/Abfragen, Mathematik, Lesen/Extraktion, Alltags-/Sozialverständnis, Naturwissenschaft/Kausalität, Schlussfolgerungen sowie Dialogverständnis. Die aktuelle Auswahl ist weitgehend englisch, textbasiert und auf 1.024 Tokens begrenzt. Mehrsprachigkeit, multimodale Fähigkeiten, längere Kontexte und freies Instruction-Following sind damit noch nicht breit abgedeckt.

## Reihenfolge und Aussagekraft

1. **Belastbarere Entwicklung:** 186 fest ausgewählte generative Aufgaben aus 31 Quellen, zusätzlich die bisherige Code-Aufgabenauswahl mit aktualisierten Funktionsnamen und zusätzlichen Grenzfällen für zwei schwach geprüfte Aufgaben. HotpotQA erhält wegen überlappender Dokumente weiterhin keinen eigenen Entwicklungssplit. QA-Exact-Match/F1, Antworten/Labels, finale Rechenergebnisse und Code-Ausführung werden getrennt berichtet. Offene Texte und SQL-Textübereinstimmung werden nicht als funktionale Erfolgsquote ausgegeben. Ganze Zahlen werden im Code-Checker exakt verglichen. Eine einzelne Originalprobe genügt nicht für einen robusten Code-Treffer.
2. **Lernkontrolle:** 128 kurze Original-Trainingsaufgaben, vier je Quelle; separat dieselben reservierten Entwicklungsgruppen. Ein zufälliges Modell mit 27.294.208 Parametern wird bis zu 4.000 Schritte trainiert. Train-Antworten werden vor und nach Training exakt geprüft, nachher am letzten Checkpoint. Diese Wiedererkennung ist kein Generalisierungsnachweis. Die Vergleichsläufe werden nur freigegeben, wenn die Trainings-Loss um mehr als die Hälfte sinkt und mindestens zehn zusätzliche Trainingsantworten korrekt wiedergegeben werden.
3. **Ausführung absichern:** Der kompilierte Trainingsschritt und KV-Cache sind integriert. Ein GPU-Test mit dem bisherigen 97,5M-Modell prüft alle Gewichte/Adam-Zustände, Wiederaufnahme und echte Prompts aus 23 Quellen. CPU-Regressionsprüfungen ergänzen ihn. Die frühere Monitoring-Kalibrierung scheiterte an Bitgleichheit trotz kleiner Unterschiede bereits zwischen Off-Wiederholungen; neue Kalibrierung weist Bitgleichheit und numerische Toleranzen separat aus. Der fehlende AdamW-Lernratenparameter im separaten Metal-Trace ist korrigiert.
4. **Breiter A/B-Vergleich:** Gleiche 32 Quellen, Beispiele, Architektur (97,5M), Tokenizer, Seed, Optimierer, Ausführung und Trainingszeit. A gewichtet jede Fähigkeitsgruppe gleich (je 1/7, darin Quellen gleich); B jede Quelle gleich (je 1/32). Das sind Samplinganteile nach Sequenzen, keine garantierten Tokenanteile. Tatsächlich verarbeitete Tokens je Quelle werden im Checkpoint protokolliert. Unterschiede in Datenkontakt und Ein-Seed-Varianz begrenzen kausale Aussagen. Vorläufiges Budget: je drei Stunden Training, insgesamt sechs Stunden, zuzüglich Kontrollversuch und Auswertung. Ein ausdrücklich gewähltes anderes Budget hat Vorrang vor diesem Text.
5. **Größen- und Dauervergleich vorbereiten:** Ein Kandidat mit 27,3M Parametern auf der vollständigen breiten Mischung wird separat konfiguriert. Seine Aktivierung und eine längere Trainingsstufe folgen anhand der A/B-Lernkurven und des verfügbaren weiteren Budgets. Der kleine Memorierungsversuch ersetzt diesen Größenvergleich nicht. Kein automatischer Wechsel zu einem Coding-Spezialisten.

## Betrieb

- Projektstarter: `.venv/bin/python run_slm.py`; Modus `light` bleibt Vorgabe. `--execution eager` ist eine Vergleichsoption des Trainers, kompiliert ist der neue Standard. Cache- und Trainingsausführung verändern keine Modellarchitektur oder Checkpointdarstellung.
- `slm.broad_eval` ist über den Projektstarter erreichbar; benötigt `--suite` und einen neuen `--output`-Ordner. Trainingskontrolle nutzt `--partition memorization --checkpoint latest`.
- Kampagne: `runs/broad-campaign-2026-09-07/plan.json`. Stufen laufen nacheinander mit `caffeinate`, GPU-Zulassung, festen gespeicherten Deadlines, begrenztem Aufräumen und Prüfsummen für Quellen und Manifeste. Wiederaufnahme verlängert eine gespeicherte Deadline nicht. Unvollständige Auswertung oder fehlgeschlagene Lernkontrolle stoppen die Folgearbeiten.
- Geordnet stoppen: `touch runs/broad-campaign-2026-09-07/STOP`. Einzelne Trainingsläufe beachten zusätzlich ihr eigenes `STOP`.
- Ergebnisse liegen unter dem jeweiligen Lauf: `broad-eval/summary.json`, `broad-eval/REPORT.md` und `performance/`. Die Kampagne erstellt `comparison.json` und `REPORT.md` mit getrennten Fähigkeitswerten. Historische Läufe und ihre gespeicherten Resultate werden nicht umgeschrieben.

## Verifikation und Grenzen

Tests: `.venv/bin/python -m pytest tests experiments/performance/test_variants.py experiments/performance/test_queue.py` (während GPU-Arbeit ausschließlich CPU-Testgerät verwenden).

Die breite Entwicklung nutzt kleine feste Stichproben und teilweise strenge Text-Proxys, keine vollständigen offiziellen Benchmark-Messungen. Referenz- oder Kontextprobleme werden ausgewiesen. Neue externe Benchmark-Familien bleiben bis zum eingefrorenen Abschlussprotokoll unbenutzt. Ein Ergebnis aus einem einzelnen Seed ist explorativ; größere Schlussfolgerungen benötigen Wiederholungen und unabhängige Bestätigung.

## Abgeschlossene Vorbereitung

84 Tests bestanden, zusätzlich GPU-Gleichwertigkeit und Datenprüfung. Die Lernkontrolle endete nach 4.000 Schritten: 0/128 → 127/128 exakte Trainingsantworten; erste protokollierte Trainings-Loss 9,03497, letzte 0,029684. Auf der separaten Entwicklung: 14/144 bewertete Antworten korrekt, 186 insgesamt generiert. Das zeigt Lernfähigkeit, noch keine breite Generalisierung. Details: `runs/broad-control-2026-09-07/CONTROL_REPORT.md`. Der Größenvergleich ist in `experiments/next_stage.json` vorbereitet und nicht zusätzlich eingeplant.

Die unabhängige Monitoring-Bestätigung bestand mit dokumentierter numerischer Toleranz; beobachteter Light-Overhead im kurzen Eager-Vergleich +0,78 %, erfolgreiche Metal-Aufzeichnung. Die breiten Hauptläufe bleiben auf `light`.

## Leistungseinstellung dieser Versuchsreihe

Der Nutzer meldet während des ersten Hauptlaufs reduzierte Rechnerleistung zur Geräuschbegrenzung. Genaue Einstellung und Beginn sind unbekannt. Durchsatzwerte sind daher keine Messung der maximalen Hardwareleistung und nicht ohne Weiteres mit früheren Läufen vergleichbar. Der Vergleich der Datengewichtungen setzt dieselbe Leistungseinstellung in beiden Läufen voraus; tatsächliche Tokens und Durchsatz müssen zusätzlich zum Zeitbudget berücksichtigt werden. Die vorherige Monitoring-Kalibrierung ist hinsichtlich dieser Einstellung nicht nachträglich bestätigt. Ergänzende Metadaten stehen in `RUN_CONDITIONS.json` und `RUN_CONDITIONS.md` bei der Kampagne und beiden Hauptläufen. Training, Fristen und Instrumentierung bleiben unverändert.
