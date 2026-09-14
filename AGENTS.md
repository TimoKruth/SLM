# Aktueller Projektstand – 14. September 2026

- Neuer ausdrücklicher Auftrag: konservativen FP32-Vergleich **für 15.09.2026, 00:00 Europe/Berlin starten lassen**. Einmaliger lokaler Starter `local.slm.conservative-midnight-20260915` installiert und mit frischem `waiting_for_midnight`-Status verifiziert. Vergleichscode `e43367d` und eingefrorene Eingaben unverändert; separater CPU-Starter `experiments/conservative_midnight.py`, Commit `e04c080`. Plan/Details `CONSERVATIVE_MIDNIGHT_START.md`. Laufender Langzeitblock wird nicht unterbrochen: Falls um Mitternacht noch aktiv, wartet der Starter auf seinen erfolgreichen Abschluss sowie Netzstrom und freie GPU-Lease; spätester Start 15.09. um 06:00, danach verfällt dieser Versuch. Ab tatsächlichem Start höchstens 21.600s, keine Wiederholung oder Modellübernahme. Status `schedule-status.json`, Auftrag `SCHEDULE.json`/`AUTHORIZATION.json` im konservativen Run-Verzeichnis; ursprünglicher STOP wird erst unmittelbar vor autorisiertem Start archiviert. Abbruch über `SCHEDULE_STOP`. Frühere reine Vorbereitungssperre ist durch diesen zeitgebundenen Startauftrag ergänzt.
- Neuer Auftrag „Continue the run“: Langzeitblock 2 am **14.09.2026 um 18:20:56 Europe/Berlin** wiederaufgenommen. Aktive Sitzung `runs/long-horizon-round2-resume-2026-09-14/`, neue harte Frist **15.09.2026 um 05:28:35 Europe/Berlin**. Code unverändert `4c30196` im Worktree `SLM-long-round2`. Fünf Trainings samt Auswertungen übernommen; r1-C setzt `checkpoint-0154741` mit Adam/Sampler fort, noch 4613,515s Prozessbudget, danach zwei Zweistundenläufe samt Auswertung. Restbudget 40058,802s nach 173s Vorbereitung, Pause ausgenommen, kein neues Budget. 430 historische Eingaben und 393 kopierte Dateien geprüft; GPU-Gesundheitsprüfung bestanden, neuer Tokenfortschritt bestätigt. Netzbetrieb, Light-Monitoring und PowerWatch; historische STOP-Sperren erhalten. Konservativer Optimierungsvergleich bleibt ungestartet; keine automatische Modellübernahme oder weitere Rotation.
- Nutzerauftrag „Stop the run please“: Langzeitblock 2 am **12.09.2026 um 13:20:50 Europe/Berlin** sicher gestoppt. Sitzung `runs/long-horizon-round2-resume-2026-09-12/` ist STOP-gesperrt; Training und Supervisor beendet. Fünf Trainings abgeschlossen, r1-C mit Modell/Adam/Sampler auf `checkpoint-0154741` (Schritt 154741, 34.706.025 zusätzliche Tokens) pausiert. Eingefrorene Eingaben unverändert; Restbudget 40231.802s, keine automatische Wiederaufnahme. Belege `USER_STOP_2026-09-12.json` und `STOP_VERIFIED_2026-09-12.json`; künftige Fortsetzung braucht neuen Auftrag und budgetbereinigte Sitzung.
- Neuer Auftrag: **sechsstündigen konservativen FP32-Vergleich nur vorbereiten, ausdrücklich nicht starten**. Worktree `/Users/timokruth/Projekte/SLM-conservative-optimization`, Branch `codex/conservative-optimization`, Code `e43367d`; Plan `CONSERVATIVE_FP32_6H.md`. Einziger Faktor: GPU-Synchronisation nach jedem Update versus nach vier Updates; FP32, gleiche Modell-/Adam-/Daten-/Batch-/LR-Eingaben, kein Preloading. 20 kurze Kontrollen, sechs längere Läufe à 2.750s über drei Datenreihenfolgen, 26 Auswertungen; insgesamt höchstens 21.600s einschließlich Reserven. Neue gruppengetrennte Suiten mit 384/288 Aufgaben aus 24 Quellen; Qualitätskontrolle nach 16.384 gleichen Updates und am Zeitende auf beiden Suiten. 51 CPU-Tests bestanden, Eingaben gehasht. Artefakte `runs/conservative-fp32-6h-2026-09-12/` im neuen Worktree: `READY.json`, `PREPARATION_CHECKS.json`, STOP gesetzt; nur falsches Autorisierungsbeispiel, **keine GPU-Arbeit, kein Starter und keine Warteschlange**. Laufender Langzeitblock unverändert. Separater ausdrücklicher Startauftrag erforderlich; keine automatische Modellübernahme.
- Neuer Auftrag „continue the run please“: Langzeitblock 2 ist am **12.09.2026 um 07:42:05 Europe/Berlin** fortgesetzt. Neue aktive Sitzung `runs/long-horizon-round2-resume-2026-09-12/`, harte Frist **13.09.2026 um 00:31:22 Europe/Berlin**. Code unverändert auf `4c30196` im Worktree `SLM-long-round2`; Details `LANGZEIT_RUNDE_2_FORTSETZUNG.md`. Drei Trainings samt Auswertungen übernommen; r0-D vom vollständigen `checkpoint-0146497` mit Adam/Sampler weitergeführt. Restbudget 60.556,654s nach 199s Vorbereitung, kein Budgetreset. Historische Sitzung bleibt STOP-gesperrt. Light-Monitoring/PowerWatch aktiv, keine Optimierung übernommen und keine automatische weitere Rotation.
- Die separate Optimierungs-/Qualitätsstudie ist am **12.09.2026 um 01:31:50 Europe/Berlin** vollständig abgeschlossen, eingefrorene Eingaben unverändert. Kein Vergleich erfüllt alle vorab gesetzten Qualitäts-/Geschwindigkeitskriterien; keine automatische Modellübernahme. Die folgenden Start-/Pausenhinweise dokumentieren ihren historischen Ablauf.
- Netzstrom bestätigt: Die sechsstündige Optimierungs-/Qualitätsstudie hat am **11.09.2026 um 21:20:00 Europe/Berlin** automatisch begonnen; harte Deadline **12.09.2026 um 03:19:59 Europe/Berlin**. Alle vier realen FP32/BF16-Checkpoint-/Adam-/Sampler-Fortsetzungskontrollen bestanden. Anschließend Elternmodell-Qualitätsauswertung, dann geplanter Screen und längere Vergleiche. Verbindlicher Live-Status im oben genannten neuen Worktree: `runs/quality-optimization-6h-2026-09-11/status.json`. Der historische Hinweis auf Warten am Akku ist erledigt. Langzeitblock bleibt pausiert.
- Neuer ausdrücklicher Auftrag: **sechsstündige Optimierungs- und Qualitätsstudie vorbereiten und starten**. Separater Worktree `/Users/timokruth/Projekte/SLM-quality-optimization`, Branch `codex/quality-optimization`, Code `3244a2a`; Plan `QUALITY_OPTIMIZATION_6H.md`. 120 gepaarte Replay-Prozesse über FP32/BF16, acht längere Trainings, 26 Qualitätsauswertungen auf neuen 300er-/195er-Suiten; 53 CPU-Tests bestanden. Äußerer Starter am 11.09. um 20:59:41 Europe/Berlin gestartet, zunächst höchstens 30 Minuten auf Netzstrom wartend, da der Mac am Akku ist. GPU-Arbeit und 21.600s-Budget beginnen automatisch erst bei Netzstrom; Zustand `runs/quality-optimization-6h-2026-09-11/direct-status.json`, danach `status.json`, jeweils im neuen Worktree. Keine automatische Wiederholung, Verlängerung, Modellübernahme oder Wiederaufnahme des pausierten Langzeitblocks. Details `OPTIMIERUNG.md`.
- Neuer Auftrag „mindestens 45 Benchmarks“: separate Vorbereitung auf **47 Quellen / 13 Fähigkeitsgruppen** erweitert. Code `/Users/timokruth/Projekte/SLM-benchmarks45`, Branch `codex/benchmarks-45`; Einstieg `BENCHMARKS_47.md`. Finale Daten `data/v6-benchmarks47-balanced-2026-09-11/`, Abschlussbeleg `READY.json`: 787.383 zusätzliche, insgesamt 2.344.017 Trainingspaare. Zwölf neue Quellen: MultiNLI, MRPC, QQP, CB, COPA, MultiRC, WiC, WSC, GoEmotions, MedQA, SAMSum, LogiQA 2.0. Ganze CB-Gruppen ergänzen die seltene neutrale Klasse in beiden internen Holdouts; kein neues Modell trainiert. Laufende v4-Kampagne, v5-Daten und Hardware-Optimierung unverändert. Keine Startfreigabe, kein Remote-Push, neue Daten nicht archiviert.
- Neuer Auftrag: laufenden Langzeitblock pausieren und Hardware-Optimierung jetzt für bis zu eine Stunde ausführen. Langzeit r0-D am 11.09. um 19:56:12 Europe/Berlin sicher auf `checkpoint-0146497` pausiert; Modell/Adam/Sampler erhalten, eingefrorene Eingaben unverändert. Erster Optimierungs-Screen vollständig abgeschlossen: alle 60 Worker von 19:57:39 bis 20:15:00; BF16 im Median 1,283× Durchsatz, längere Qualitätsbestätigung noch ausstehend. Worktree `/Users/timokruth/Projekte/SLM-optimization`, Branch `codex/hardware-optimization`; aktueller Zustand `runs/optimization-screen-2026-09-11/status.json`, äußerer Wächter `direct-status.json`. Frühere Warteschlange beendet; `queue-status.json` ist historisch. Keine automatische Verlängerung, Modellübernahme oder Wiederaufnahme des Langzeitblocks. Details `OPTIMIERUNG.md`.
- Zusätzliche Benchmark-Daten vorbereitet, kein neuer Trainingsstart: Branch `codex/benchmark-expansion`, Dokument `BENCHMARK_ERWEITERUNG.md`. Neue separate Datenversion `data/v5-expanded-2026-09-11/`: bestehende 32 Quellen plus TriviaQA, TyDiQA-GoldP (neun Sprachen) und TabMWP; 122.691 zusätzliche Trainingspaare. `READY.json` dokumentiert die Verifikation. TAT-QA bleibt nach Screening wegen fehlender Berichtstrennung unaufgenommen. Laufende Kampagne weiter auf eingefrorener v4-Mischung; Vorbereitung ist keine Startfreigabe. Neue Daten noch nicht archiviert.
- Neuer ausdrücklicher Auftrag: nach technisch erfolgreichem ersten Block die nächsten Parameter laufen lassen. Erster Block vollständig abgeschlossen, kein bestätigter Qualitätsgewinner.
- Zweiter Langzeitblock unter `runs/long-horizon-round2-2026-09-11/` ist auf Nutzerwunsch pausiert (STOP gesetzt); `status.json` ist verbindlich. Drei Trainings vollständig, r0-D teilweise mit finalem Checkpoint `checkpoint-0146497`. Historischer Start 2026-09-11T13:08:47+02:00 und historische Frist 2026-09-12T12:48:47+02:00; Wiederaufnahme braucht neue budgetbereinigte Sitzung. Code-Commit `4c30196` unverändert im Worktree `/Users/timokruth/Projekte/SLM-long-round2`, Branch `codex/long-horizon-round2`. Plan und Grenzen: `LANGZEIT_RUNDE_2.md`. Pause und Restbudget in `USER_PAUSE_2026-09-11.json` / `PAUSE_VERIFIED_2026-09-11.json`.
- Kontrolle LR 3e-5, LR 3e-6, LR 1e-4, Kosinus 3e-5 bis 3e-6 über 100M zusätzliche Tokens; zwei Datenreihenfolgen, je zwei Stunden. Ein Folgeblock mit derselben maximalen 24h-Größe einschließlich Vorbereitung/Auswertung, keine automatische weitere Rotation. Alte Restreserve bleibt ungenutzt.
- Eingefrorene Kampagneneingaben unverändert lassen. Light-Monitoring und PowerWatch aktiv; keine automatische Modellübernahme. Historische Daten und Worktrees erhalten.
- Zentrale bisherige Einordnung: ERKENNTNISSE.md; aggregierte historische Belege: results/2026-09-11/INDEX.md. Lokale ZIP64-Archive: SICHERUNG.md; keine externe Sicherung beauftragt. Neue Kampagnendaten sind noch nicht Bestandteil dieser Archive.
- Änderungen zeitnah committen; Remote-Sicherung nur bei entsprechendem Auftrag. Rohdaten und systemweite Prozessprotokolle nicht ins öffentliche Repository aufnehmen.
- read-training-status bleibt ausschließlich Projekt-Skill unter .agents/skills/. Der allgemeine read-system-resources-Skill ist global.

# Historische Betriebs- und Versuchsprotokolle

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


# Reparatur der Studie, weiterhin pausiert (9. September 2026)

- Nutzer beauftragte Fehlerbehebung und Startbereitschaft, keine Wiederaufnahme. Die alte Studie bleibt durch STOP gesperrt; keine GPU-Trainings oder Warteschlangen starten ohne ausdrücklichen Folgeauftrag.
- Reparierter Code `/Users/timokruth/Projekte/SLM-study-recovery`, Branch `codex/study-recovery`, Commit `483d292`. Dokumentation `STUDIE_WIEDERHERSTELLUNG.md`; Kontrollen unter `runs/study-repair-2026-09-09/`.
- Metal war beim Reparaturtest wieder erreichbar; keine Systemdienste oder der Mac wurden neu gestartet. Zwei kurze GPU-Prüfungen, Kontrolle am echten Elternmodell und Nachholung der gescheiterten 473er-Auswertung bestanden. Die genaue Ursache des vorübergehenden Dienstfehlers bleibt offen.
- Neuer Vorabtest und Fehlerklassifikation. Bei GPU-Dienstfehler frische Gesundheitsprüfung, höchstens eine Stufenwiederholung im Restbudget; maximal zwei automatische GPU-Recovery-Versuche pro Kampagne. Danach Infrastrukturpause statt weiterer Fehlerkaskade. STOP wird vor Kampagnenstart geprüft.
- Vorbereitete, ebenfalls STOP-gesperrte Fortsetzung: `runs/parameter-study-recovery-2026-09-09/`. 31 vollständige Trainings und 31 validierte Auswertungen unabhängig kopiert; numerischer Kern unverändert. 83 kurze Trainings sowie vier geplante lange Läufe offen.
- Verbindliches Restbudget: 79.613s (22h 06m 53s), nach Abzug bisheriger 6667s plus konservativer 120s Prüfreserve. Kein neues 24h-Budget. READY.json/recovery-audit.json dokumentieren Vorbereitung; noch kein status.json, kein gestarteter Supervisor.
- Zum ausdrücklich beauftragten späteren Start nur den STOP der neuen Fortsetzung entfernen und dort `run_slm.py --module study.campaign` im Recovery-Worktree verwenden. Historische STOP-Sperre, Eingaben und Ergebnisse erhalten. Monitoring light und PowerWatch bleiben aktiv.


# Wiederaufnahme der Parameterstudie (9. September 2026)

- Neuer ausdrücklicher Nutzerauftrag: „Bitte lasse den 24 h Lauf dann weiter laufen“. Die zuvor pausierte Fortsetzung ist gestartet; nur ihr STOP wurde entfernt. Die historische Studie bleibt gesperrt.
- Aktive Kampagne: `runs/parameter-study-recovery-2026-09-09/`, Code unverändert im Recovery-Worktree auf Commit `483d292`. Verbindlicher Zustand und Frist: `status.json`.
- Start: 2026-09-09T22:05:42.638012+02:00; harte Budgetgrenze: 2026-09-10T20:12:35.638007+02:00 (Europe/Berlin). Restbudget beim Start 79.613s, kein neues 24h-Budget und keine automatische Verlängerung. Ein früherer Abschluss aller geplanten Versuche ist möglich.
- Vor Start wurden sämtliche eingefrorenen Eingabehashes geprüft; keine konkurrierenden GPU-Jobs. Stromversorgung beim Start am Netz, bestehende Leistungseinstellung unverändert. Aktuelle Startbedingungen und Auftrag: `START_AUTHORIZATION.json`; die vorbereitenden RUN_CONDITIONS bleiben historisch erhalten.
- Monitoring light, PowerWatch und die begrenzte Metal-Fehlerbehandlung sind aktiv. Eingefrorene Code-/Daten-/Planeingaben unverändert lassen; keine automatische Modellübernahme.


# GPU-Hang-Fix vorbereitet (10. September 2026)

- Nutzer beauftragte Erkennung und Vorbereitung eines Fixes für einen möglichen GPU-Hang-Abbruch. Kein Hot-Patch, keine Wiederaufnahme und keine zusätzlichen GPU-Tests beauftragt.
- Separater Worktree `/Users/timokruth/Projekte/SLM-gpu-hang-fix`, Branch `codex/gpu-hang-recovery`, Commit `b58809f`. Details: `GPU_HANG_FIX.md`.
- Die native MLX-Meldung `Caused GPU Hang Error` / `kIOGPUCommandBufferCallbackErrorHang` (Exit -6) wird dort als GPU-Infrastrukturfehler erkannt und durch die vorhandene begrenzte Wiederherstellung behandelt. Ursache des Hängers nicht nachgewiesen behoben. 75 CPU-Tests bestanden, numerischer Kern unverändert.
- Aktive Kampagne und eingefrorener Recovery-Code bleiben unverändert. Nach eventuellem Ende/Abbruch erst Status und Integrität prüfen; neue vorbereitete Fortsetzung muss kumulierten Budgetverbrauch abziehen und STOP-gesperrt bleiben, bis ein ausdrücklicher Startauftrag vorliegt.


# Auswertungsfristen korrigiert und erneut fortgesetzt (10. September 2026)

- Nutzerauftrag: „Fix it and resume“. Aktive Kampagne `runs/parameter-study-timeout-recovery-2026-09-10/`. Code `/Users/timokruth/Projekte/SLM-timeout-recovery`, Branch `codex/evaluation-timeout-recovery`, Commit `43ac41c`. Details: `AUSWERTUNGSFRIST_FIX.md`.
- Vorige Fortsetzung pausierte um 03:01:59 nach drei aufeinanderfolgenden Auswertungs-Timeouts. 92 vollständige Trainings, 86 Auswertungen; diese historischen Ergebnisse und STOP-Sperren bleiben erhalten.
- Jetzt 92 Trainings und 87 validierte Auswertungen unabhängig übernommen, inklusive nachgeholter 97M-Auswertung (473/473 Aufgaben plus Referenz-Loss in 126,272s). Noch 22 kurze Trainings, fünf reine Auswertungen und vier lange Läufe offen.
- Auswertungen erhalten einheitlich 600s plus 30s Prozessreserve, unveränderte Suiten und Antwortlängen. Timeout pausiert sofort statt weiterer Versuche; GPU-Hang-Fix aktiviert. 81 Tests und alle Prüfungen des unveränderten numerischen Kerns bestanden.
- Start 2026-09-10T07:49:34.908356+02:00; verbindliche Deadline 2026-09-11T00:56:03.908346+02:00 (Europe/Berlin). Startbudget 61.589s (17h 06m 29s), nach kumuliert 24.564s und weiteren 247s Prüfreserve. Kein neues 24h-Budget; kein automatisches Verlängern. Maximal geplante verbleibende Stufen 45.020s.
- Status/Frist in `status.json`, Auftrag/Betriebsbedingungen in `START_AUTHORIZATION.json`. Beim Start am Netz, Leistungseinstellungen unverändert. Monitoring light und PowerWatch aktiv. Eingefrorene Code-/Daten-/Planeingaben nicht ändern, keine automatische Modellübernahme.


# Langer Vergleich geplant, nicht gestartet (10. September 2026)

- Vorige Parameterstudie vollständig abgeschlossen um 11:16 Uhr: 114 kurze plus vier lange Trainings und sämtliche Auswertungen, keine neuen Fehler in der letzten Fortsetzung; kein bestätigter Kandidat.
- Neuer Nutzerauftrag: großen Vergleich mit 24h Gesamtbudget planen, ausdrücklich nicht starten. Nutzer wählte wenige Varianten mit Stunden pro Lauf; alle anderen bleiben für folgende Runden vorgesehen.
- Plan `LANGZEITVERGLEICH_24H.md`, strukturierte Dateien unter `plans/long-horizon-24h-2026-09-10/`. Vier Bedingungen (Familien-/Quellenmischung × LR 3e-5/1e-5), zwei Datenreihenfolgen, je zwei Stunden; 16h Training, Rest Auswertung/Kontrollen/Reserve. Alle 57 bisherigen Varianten im Katalog erhalten.
- Plan ist nicht ausführbar: neuer Zeitendpunkt/Supervisor und frische gruppengetrennte Gegenprüfung noch umzusetzen. STOP gesetzt, keine Warteschlange oder GPU-Kontrolle gestartet. Keine Startfreigabe aus dieser Planung ableiten.
- Nutzer meldet jetzt Hochleistungsmodus; am Netz powermode 2 verifiziert. Nicht mit vorherigem reduziertem Betrieb gleichsetzen. Evonn-Kampagne aktuell CPU-basiert, GPU im Messfenster gering ausgelastet. Parallelbetrieb technisch plausibel, aber ungemessen hinsichtlich gegenseitiger Verlangsamung; für den kontrollierten Vergleich serieller Projektbetrieb geplant. Evonn unverändert lassen.


# Langer Parallelvergleich gestartet (10. September 2026)

- Nutzer beauftragte aktiven Paralleltest und anschließend ausdrücklich den gesamten Vergleich bei erfolgreichem Test. Der 505,6s-Test ist bestanden: zwei identische 3M-Token-Läufe mit ~19,3k Tokens/s, normale Thermik und mindestens 35 GiB verfügbar. Evonn weiter aktiv; deskriptiv ~9,4% längere CPU-Fits in 20 vergleichbaren Gruppen. Keine exakte SLM-Alleinkontrolle.
- Neue aktive Kampagne `runs/long-horizon-2026-09-10/`, Code `/Users/timokruth/Projekte/SLM-long-horizon`, Branch `codex/long-horizon`, Commit `a4b1ea1`. Details `LANGZEIT_START.md`; `status.json` ist verbindlich.
- Start 2026-09-10T12:08:12.475366+02:00, harte Deadline 2026-09-11T11:48:12.475361+02:00 (Europe/Berlin). 1200s Vorabudget konservativ verbucht, Restbudget 85.200s aus dem neuen 24h-Block. Keine automatische Verlängerung oder Modellübernahme.
- Acht Läufe: Familien-/Quellenmischung × LR 3e-5/1e-5, zwei Datenreihenfolgen, jeweils 7200s Prozessbudget inkl. Laden/Checkpoints/60s Abschlussreserve. Gemeinsamer ursprünglicher 27,3M-Elterncheckpoint, FP32. Alle 57 alten Varianten bleiben für spätere Blöcke erhalten.
- Vollständige Adam-/Sampler-Checkpoints alle 300s, Tokenstände 15/30/50/75/100/150M. Auswertung bei 15M/50M und Zeitende auf 473er-Suite sowie Zeitende auf neuer 200er-Gegenprüfung aus 25 Quellen. Audit bestätigt keine Trainings-/früheren Gegenprüfungsgruppenüberschneidungen. Keine externe Transferbehauptung.
- 89 CPU-Tests plus echter Test von Unterbrechung/Checkpoint/Wiederaufnahme/Zeitende bestanden. Light-Monitoring, PowerWatch und begrenzte GPU-Recovery aktiv. Weitere Fehler pausieren. Evonn wird weder signalisiert noch verändert; sein Fortschritt wird pro Stufe und alle 60s erfasst. Veränderte Überlappung und Hochleistungsmodus bei Vergleichen beachten.
- Historische Planungsdateien bleiben unverändert eingefroren; ihre frühere Startsperre ist kein aktueller Status der jetzt autorisierten Kampagne. Aktive Code-/Daten-/Planeingaben nicht ändern.


# Langzeitvergleich nach Nutzerpause fortgesetzt (10. September 2026)

- Nutzerauftrag „fortsetzen“. Historische Kampagne `runs/long-horizon-2026-09-10/` bleibt STOP-gesperrt. Neue aktive Sitzung `runs/long-horizon-resume-2026-09-10/`, Code `/Users/timokruth/Projekte/SLM-long-resume`, Branch `codex/long-horizon-resume`, Commit `5312766`. Details `LANGZEIT_FORTSETZUNG.md`.
- Drei vollständige Trainings und sämtliche Auswertungen unabhängig kopiert und gehasht. Lauf r0-D setzt Checkpoint `checkpoint-0137865` inklusive Adam/Sampler fort; 6968,325s Restprozessbudget, danach vier unveränderte Zweistundenläufe. Keine Wiederholung fertiger Trainings, kein Zurücksetzen der Tokenzahlen.
- Startbudget 62723,296s nach 23263,704s bisherigem Verbrauch plus 413s konservativer Vorbereitung. Pausenzeit ausgenommen. Neue Deadline 2026-09-11T13:10:46.176870+02:00; Status/Frist in status.json verbindlich. Kein neues 24h-Budget.
- Netzbetrieb jetzt powermode 1 statt zuvor 2, Änderungszeit unbekannt. Einstellung unverändert gelassen; RUN_CONDITIONS/START_AUTHORIZATION beachten. EvoNN bereits abgeschlossen.
- Neuer Resume-Supervisor, numerischer Kern unverändert. 99 Tests und tatsächlicher Light-Monitoring-Einstieg bis zur STOP-Sperre bestanden; erster Launcher-Registrierungsfehler vor GPU-Arbeit korrigiert. Initiale Eingaben/Kopien vor GPU-Arbeit geprüft, kurze Health-Stufe im Restbudget. Light-Monitoring, PowerWatch und begrenzte Recovery bleiben aktiv. Keine aktiven Eingaben verändern, keine automatische Verlängerung oder Modellübernahme.
