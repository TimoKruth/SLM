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


# Begrenzte Forschungsrunde am 9. September 2026

- Der Nutzer hat den Start ausdrücklich beauftragt. Fragen allein sind keine Startfreigabe; der Nutzer fordert Starts ausdrücklich an.
- Kampagne `runs/research-pilot-2026-09-09/`, Code `/Users/timokruth/Projekte/SLM-research`, Branch `codex/bounded-research`, Commit `4dfbadc`. Plan und Grenzen: `BEGRENZTE_FORSCHUNG.md`.
- Start 07:41:07, harte Budgetgrenze 08:41:07 Europe/Berlin. Maximal 60 Minuten einschließlich Kontrollen und GPU-Auswertung, ohne Verlängerung. Verbindlicher Zustand: `status.json` im Kampagnenverzeichnis.
- Sechs Adaptationen des letzten kleinen Sechs-Stunden-Modells: Baseline LR 3e-5, höhere LR 1e-4, Antwortgewicht 4 bei LR 3e-5; jeweils zwei Datenreihenfolgen, 3M zusätzliche Tokens. FP32, identische 32 Quellen. Datenreihenfolgen sind keine unabhängigen Initialisierungsseeds.
- Auswahl auf 248 internen Aufgaben aus 31 Quellen, Gegenprüfung auf 200 anderen Aufgaben aus 25 Quellen. Kein externer Transfernachweis. Automatische Auswertung und Abschlussbericht, keine automatische Übernahme des Kandidaten.
- Eingefrorene Forschungs-Eingaben unverändert lassen. `STOP` im Kampagnenverzeichnis beendet die Runde. Light-Monitoring und PowerWatch bleiben aktiv.


# Zweite Forschungsrunde am 9. September 2026

- Erste Forschungsrunde abgeschlossen um 08:16 Uhr: sechs vollständige Versuche, kein bestätigter Kandidat. Historische Eingaben bleiben unverändert.
- Neuer expliziter Nutzerauftrag für weitere Läufe. Kampagne `runs/research-round2-2026-09-09/`; Code `/Users/timokruth/Projekte/SLM-research-round2`, Branch `codex/bounded-research-round2`, Commit `f0ea5ca`. Details: `FORSCHUNG_RUNDE_2.md`.
- Start 09:05:12, Budgetgrenze 10:05:12 Europe/Berlin; maximal 60 Minuten einschließlich Kontrollen und GPU-Auswertung. Aktueller Status und verbindliche Frist im Kampagnenverzeichnis.
- Sechs neue 3M-Token-Adaptationen vom ursprünglichen kleinen Sechs-Stunden-Checkpoint: Baseline LR 3e-5, niedrigere LR 1e-5, Antwortgewicht 2 bei LR 3e-5. Jeweils Daten-Seeds 202609092 und 202609093; FP32 und unveränderte 32 Quellen.
- Auswahl auf 473 Aufgaben aus 31 Quellen, Gegenprüfung auf 200 anderen Aufgaben aus 25 Quellen. Neue Gegenprüfungsgruppen schließen die des ersten Piloten aus. Kandidaten müssen zusätzlich gegenüber dem unveränderten Elternmodell auf beiden Suiten bestehen. Keine direkte Gegenüberstellung aggregierter Scores aus unterschiedlich großen Auswahlsuiten.
- Light-Monitoring und PowerWatch bleiben aktiv; Eingaben nicht ändern. `STOP` im neuen Kampagnenverzeichnis beendet die Runde. Keine automatische Verlängerung oder Modellübernahme.


# Systematische Parameterstudie: 24 Stunden Zusatzbudget

- Nutzer hat am 9. September ausdrücklich weitere systematische Parametervariation und 24 zusätzliche Stunden einschließlich Kontrollen/Auswertungen freigegeben. Die laufende zweite Runde zählt nicht dazu.
- Warteschlange `runs/parameter-study-2026-09-09/queue.json`, anschließend verbindlicher Status/Frist `status.json`. Code `/Users/timokruth/Projekte/SLM-parameter-study`, Branch `codex/parameter-study`, Commit `d4fc227`. Plan: `PARAMETERSTUDIE_24H.md`.
- 114 vorab festgelegte kurze Läufe plus vier längere: 37 Adaptations-/Mischungs-/Ausführungsvarianten, zwölf Kaltstartvarianten, acht LR×Antwortgewicht×Gewichtszerfall-Kombinationen, jeweils zwei Wiederholungen. Lange Kontrolle/Kandidat mit zwei neuen Datenreihenfolgen und 1,5M-/15M-Token-Ständen.
- Budget beginnt erst nach Ende der zweiten Runde und ohne konkurrierenden GPU-Job, dann harte Grenze 86.400s. Kein Neustart, keine Verlängerung. GPU-Arbeit seriell, Monitoring light und PowerWatch aktiv.
- Endliche Stufen statt Behauptung vollständigen Parameterwissens. Tokenizer/neue Optimiererfamilien/grundlegende Architekturbausteine bleiben ausdrücklich ununtersucht. Signifikanz oder externe Übertragung werden nicht aus zwei Wiederholungen behauptet.
- Die eingefrorenen Code-/Planeingaben der Warteschlange unverändert lassen. Suiten/Daten/Elterncheckpoint werden vor neuer GPU-Arbeit zusätzlich eingefroren. STOP im Studienverzeichnis beendet Warteschlange/Kampagne. Keine automatische Modellübernahme.
