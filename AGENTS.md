# Künftige Trainingsläufe

Der Nutzer hat am 7. September 2026 leichtgewichtiges Performance-Monitoring für die nächsten Läufe aktiviert.

- Neue Trainings- und zugehörige Auswertungsläufe über `.venv/bin/python run_slm.py --run <Laufverzeichnis> ...` starten. Der Standard ist `slm.sixhour`; für andere Einstiegspunkte `--module` verwenden.
- `run_defaults.json` ist die verbindliche Projektvorgabe: Monitoring `light`, zehn Aufwärmschritte, Zwischenstände alle 60 Sekunden. Der überwachte Supervisor reicht den Modus an Training, Bericht und Code-Auswertung weiter.
- Monitoring nur bei ausdrücklicher Anweisung ausschalten (`--monitoring off`); `detail` bleibt für gesonderte Diagnoseversuche vorgesehen.
- Direkte technische Einstiegspunkte wie `python -m slm.train` umgehen die Projektvorgabe. Sie nicht versehentlich für neue reguläre Läufe verwenden.
- Laufende oder eingefrorene Versuche nicht nachträglich instrumentieren. Der Versuch `expanded-2026-09-07-6h` samt anschließender Auswertung bleibt unverändert.
- Details und Grenzen stehen in `PERFORMANCE.md`. Die bereits eingeplanten A/B-Diagnosen behalten ihre ausdrücklich gewählten Messmodi.

# Breites Lernziel

- Ziel ist ein vielseitiges Benchmark-only-Sprachmodell. Coding ist ein Beispiel, keine bevorzugte Zielkompetenz.
- Neue Mischungen über die Fähigkeiten in `slm/breadth.py` planen; Lernfortschritt je Bereich ausweisen. Neue Quellen zuerst auf Original-Trainingssplit, Gruppentrennung, Kontextlänge und Herkunft prüfen.
- Der aktuelle Vergleich nutzt dieselben 32 Quellen mit gleicher Gewichtung je Fähigkeitsgruppe beziehungsweise je Quelle. Details und Grenzen: `BREITES_LERNEN.md`.
- Der Lernkontrollversuch misst Wiedererkennen eigener Trainingsaufgaben separat von Entwicklung. Nie als Transfer-Erfolg berichten.

# Betriebsbedingungen bei Vergleichen

- Vor Performance- und Qualitätsvergleichen `RUN_CONDITIONS.json`/`RUN_CONDITIONS.md` im Lauf- und Kampagnenverzeichnis lesen. Diese ergänzen die automatisch erfassten Monitoring-Metadaten.
- Für die breite Versuchsreihe vom 7. September 2026 meldet der Nutzer reduzierte Leistung zur Geräuschbegrenzung; genauer Modus und Beginn sind unbekannt. Keine rückwirkende Annahme über frühere Läufe oder Kalibrierungen. Vergleiche bei festem Zeitbudget müssen zusätzlich tatsächliche Tokens und mögliche Änderungen der Leistungseinstellung berücksichtigen.

# Bekannter Datenfehler: SciTail

- Am 8. September 2026 bestätigt: `data/v3-broad` verwarf alle 8.472 SciTail-Beispiele mit Original-Label `entails`; nur `neutral` blieb übrig. SciTail-Scores dieser Datenversion sind kein Fähigkeitsnachweis und müssen bei Vergleichen separat ausgeschlossen werden.
- Vor neuen regulären Trainings eine neue Datenversion mit korrigierter Labelabbildung und erneuter Prüfung erstellen. Der Fix mit Regressionstest liegt im Branch `codex/evaluation-preparation`, Commit `66623cf`. Historische Daten nicht überschreiben. Belege: `runs/broad-886-2026-09-08/data_quality.json`.

# Korrigierte Daten und Größenvergleich (8. September 2026)

- Zusätzlich bestätigt: WIQA `no_effect` wurde wegen der Antwortoption `no effect` abgewiesen (9.936 Originalbeispiele). Beide Klassenkonverter sind korrigiert; historische Daten und Resultate bleiben unverändert.
- Neue auditierte Daten: `data/v4-broad-corrected-2026-09-08`, 1.433.943 Trainingspaare aus 32 Quellen. `audit.json` dokumentiert Rohdatenabgleich, Klassenabdeckung und exakte Trennung.
- Der Nutzer hat den Größenvergleich 27,3M gegen 97,5M mit je drei Stunden Training freigegeben. Plan und Status: `runs/size-campaign-2026-09-08/`. Dokumentation: `MODELLGROESSENVERGLEICH.md` im Worktree `/Users/timokruth/Projekte/SLM-evaluation-prep`, Branch `codex/model-size-comparison`.
- Dieser Vergleich verwendet eine gemeinsame tokenbasierte Lernratenkurve, dieselbe Familienmischung und feste 10M/20M/30M-Token-Snapshots. Primärer Endpunkt ist der letzte Modellstand nach drei Stunden. Nachgelagerte Auswertungen laufen automatisch, keine Verlängerung.
- Während der Kampagne keine eingefrorenen Code-/Dateneingaben verändern. Daten und Runs liegen physisch im Hauptworkspace; der Kampagnencode läuft im genannten Worktree.

# Vorbereitung nach dem Größenvergleich

- Der Größenvergleich ist abgeschlossen. Nächste Vorbereitung: `NAECHSTER_LAUF.md`, Worktree `/Users/timokruth/Projekte/SLM-next-run-prep`, Branch `codex/next-run-preparation`. Artefakte: `runs/next-preparation-2026-09-08/`.
- Der Nutzer hat nur die Vorbereitung bis vor dem längeren Lauf beauftragt. `next_run/long_plan.json` ist ein ungestarteter Vorschlag, keine Startfreigabe.
- `--forward-precision bf16` ist eine getestete optionale Variante mit FP32-Mastergewichten; Standard bleibt FP32. Rechengenauigkeit gehört zur Wiederaufnahmesignatur. Standalone-Evaluation bleibt FP32, Inline-Dev folgt dem Trainer.
- Vier auffällige Entwicklungsreferenzen nur in separater Sensitivitätsanalyse behandeln; Originalscores erhalten. Neue TAT-QA-/MultiNLI-Dateien sind vorgemerkt, nicht in die 32-Quellen-Mischung integriert.

# Begrenzte Forschungsrunde am 9. September 2026

- Expliziter Startauftrag für die erste kontrollierte LR-/Antwortgewichtungsrunde: `BEGRENZTE_FORSCHUNG.md`, Kampagne `runs/research-pilot-2026-09-09/`.
- Maximal 60 Minuten einschließlich GPU-Kontrollen und Auswertung, sechs feste 3M-Token-Adaptationen des letzten kleinen Sechs-Stunden-Modells. Keine automatische Verlängerung oder Modellübernahme.
- Eingefrorene Kampagneneingaben nicht ändern. Status/Frist im Kampagnenverzeichnis; `STOP` beendet die Runde.
- Fragen des Nutzers allein sind keine Freigabe zum Starten; der Nutzer fordert Starts ausdrücklich an.

# Zweite Forschungsrunde am 9. September 2026

- Expliziter Auftrag für weitere Läufe. Neue Kampagne `runs/research-round2-2026-09-09/`, Worktree `/Users/timokruth/Projekte/SLM-research-round2`, Branch `codex/bounded-research-round2`. Details: `FORSCHUNG_RUNDE_2.md`.
- Sechs neue 3M-Token-Adaptationen vom ursprünglichen kleinen Sechs-Stunden-Checkpoint: Baseline, niedrigere LR 1e-5, milderes Antwortgewicht 2; jeweils Daten-Seeds 202609092 und 202609093. FP32, unveränderte 32 Quellen.
- Höchstens 60 Minuten einschließlich Kontrollen und Auswertung. Verbindliche Frist und Status im Kampagnenverzeichnis, keine Verlängerung.
- Größere Auswahlmenge (bis 16 Aufgaben je Quelle); neue Gegenprüfungsgruppen schließen den ersten Piloten aus. Kandidaten müssen zusätzlich gegenüber dem unveränderten Elternmodell bestehen. Aggregierte Werte der unterschiedlichen Auswahlsuiten nicht direkt vergleichen.
- Historischer Pilot und aktive eingefrorene Eingaben bleiben unverändert. Monitoring light und PowerWatch aktiv. Keine automatische Modellübernahme.

# Systematische Parameterstudie mit 24 Stunden Budget

- Nutzer hat am 9. September ausdrücklich 24 zusätzliche Stunden einschließlich Kontrollen/Auswertungen freigegeben, nach Ende der zweiten Runde. Details `PARAMETERSTUDIE_24H.md`.
- Kampagne `runs/parameter-study-2026-09-09/`, Code `/Users/timokruth/Projekte/SLM-parameter-study`, Branch `codex/parameter-study`. `queue.json` zeigt die Warteschlange, `status.json` die aktive Phase und verbindliche Frist.
- 114 kurze Vergleiche und vier längere Läufe; endlicher vorab festgelegter Parameterraum. Nicht untersuchte Faktoren bleiben im Plan/Bericht ausdrücklich offen. Keine Behauptung vollständigen Parameterwissens.
- Bestehende Runde unverändert lassen. Nach Start keine eingefrorenen Studien-Eingaben ändern. Keine Budgeterneuerung, keine automatische Modellübernahme. STOP im Studienverzeichnis beendet Warteschlange/Kampagne. Monitoring light und PowerWatch bleiben aktiv.
