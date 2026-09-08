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

# Systemressourcen

- Permanenter lokaler Sammler: PowerWatch, alle 15 Sekunden, 30 Tage Verlauf. Automatisch aktualisierte Übersicht: `runs/system-resources/latest.html`; Status und Details: `RESOURCE_MONITORING.md`.
- Das Systemmonitoring ist vom Trainings-Monitoring unabhängig. Es bleibt bei Branchwechseln als Benutzer-Dienst installiert und verändert keine eingefrorenen Versuchseingaben.
- Bei Auslastungsangaben aktuelle Messzeit prüfen. GPU-Werte gelten systemweit; freier RAM ist nicht gleich verfügbarer RAM inklusive freigebbarer Caches. Schlaf-/Messlücken und geänderte Leistungseinstellungen berücksichtigen.

# Vorbereitung nach dem Größenvergleich

- Der Größenvergleich ist abgeschlossen. Nächste Vorbereitung: `NAECHSTER_LAUF.md`, Code im Worktree `/Users/timokruth/Projekte/SLM-next-run-prep`, Branch `codex/next-run-preparation`. Artefakte: `runs/next-preparation-2026-09-08/`.
- Der Nutzer beauftragte ausschließlich die Vorbereitung bis vor dem längeren Lauf. Der dortige `next_run/long_plan.json` ist ein ungestarteter Vorschlag, keine Startfreigabe.
- Im Vorbereitungsbranch ist `--forward-precision bf16` eine getestete Option mit FP32-Mastergewichten; Standard bleibt FP32. Standalone-Evaluation bleibt FP32, Inline-Dev folgt dem Trainer. Rechengenauigkeit gehört zur Wiederaufnahmesignatur.
- Auffällige Originalreferenzen werden separat in Sensitivitätsanalysen ausgewiesen; historische Scores bleiben erhalten. TAT-QA-/MultiNLI-Trainingsdateien sind vorgemerkt, nicht in die bestehende Mischung integriert.

# Aktive Fortsetzung am 9. September 2026

- Neuer Nutzerauftrag: beide Drei-Stunden-Modelle vom letzten Checkpoint jeweils drei Stunden weitertrainieren. Diese Freigabe gilt für die Fortsetzung; der vorherige BF16-Neustartvorschlag bleibt ungestartet.
- Kampagne: `runs/size-continuation-2026-09-09/`. Code: `/Users/timokruth/Projekte/SLM-continuation`, Branch `codex/size-continuation`. Details: `FORTSETZUNG_MODELLGROESSEN.md`.
- Eigene Runs `size-27m-2026-09-09-plus3h` und `size-97m-2026-09-09-plus3h`; unabhängig kopierte letzte Modellstände inklusive AdamW und Sampler. Original-FP32-Konfiguration und 100M-Token-Kurve beibehalten.
- Klein ist am 9. September um 00:38:53 gestartet, Trainingsende 03:38:53 Europe/Berlin. Danach Auswertung, groß für weitere 10.800 Sekunden und gemeinsame Auswertung. Aktueller Status und Fristen sind im Kampagnenverzeichnis verbindlich.
- Keine aktiven Kampagneneingaben ändern. Alte und kumulierte Tokenzahlen unterscheiden; die Pause zwischen Sitzungen ist keine Trainingszeit. Keine automatische weitere Verlängerung.
