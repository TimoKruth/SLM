# Zweiten Langzeitblock fortgesetzt – 12. September 2026

Nutzerauftrag: „continue the run please“. Die zwischenzeitliche sechsstündige Optimierungs-/Qualitätsstudie war bereits am 12. September um 01:31:50 Europe/Berlin vollständig abgeschlossen, Eingaben unverändert. Ihr Bericht bestätigt keine Konfiguration anhand sämtlicher Qualitäts-/Geschwindigkeitskriterien. Der offene Langzeitvergleich wird mit seinen ursprünglichen FP32-Parametern fortgesetzt.

Neue Sitzung: `runs/long-horizon-round2-resume-2026-09-12/`. Code unverändert im Worktree `/Users/timokruth/Projekte/SLM-long-round2`, Branch `codex/long-horizon-round2`, Commit `4c30196`. Der geprüfte Einstieg `run_slm.py --module long_study.resume` verwendet weiterhin Light-Monitoring und den seriellen GPU-Zugang.

Drei vollständige Trainings und sämtliche zugehörigen Auswertungen sind unabhängig per APFS-Kopie übernommen und gehasht. Der unterbrochene Kosinuslauf r0-D setzt den letzten vollständigen Stand `checkpoint-0146497` bei Schritt 146497 und 265.596.762 kumulierten Tokens fort, einschließlich Adam und Sampler. Davon stammen 19.733.393 Tokens aus dieser Adaptation. Modell-, Daten-, Job- und Wiederaufnahmesignaturen passen. 249 kopierte Dateien geprüft; keine gemeinsam beschreibbaren Hardlinks. Historische STOP-Sperren und Originalergebnisse bleiben erhalten; die kopierte lokale STOP-Datei liegt als `STOP.source-history` vor.

## Restbudget

Historisch verbraucht: 25644.346s. Vorbereitung einschließlich konservativer 90s-Abschlussreserve: 199s. Verbleibendes globales Budget: 60556.654s (16h 49m 16,654s). Die nächtliche Nutzerpause ist ausgenommen; bereits historisch verbuchte Schlafzeit wird konservativ nicht zurückerstattet. Kein neues 24h-Budget.

Der Teil-Lauf erhält noch 5779.532s Prozessbudget einschließlich Laden und Abschlusscheckpoint. Danach vier unveränderte 7200s-Trainings. Alle ausstehenden Auswertungen laufen automatisch; geplante maximale Stufenzeit einschließlich Bericht 47799.532s. Keine automatische Modellübernahme, weitere Rotation oder Verlängerung.

Start: **2026-09-12T07:42:05.721733+02:00**. Neue harte Budgetfrist: **2026-09-13T00:31:22.376022+02:00**, Europe/Berlin. Live-Status und verbindliche Frist stehen in `status.json` der neuen Sitzung; alte Start-/Fristangaben bleiben historisch.

## Prüfung und Betrieb

Alle 413 historischen eingefrorenen Eingaben erneut gehasht und unverändert. Checkpoint-Hashes stimmen mit dem Pausenbeleg überein; Adam-Datei auf ZIP-Integrität geprüft. 45 Tests für Zeitbudget, Wiederaufnahme, Lernratenverlauf, Berichte, Monitoring und GPU-Sperre bestanden. Die GPU-Gesundheitsprüfung in der neuen Sitzung bestand. Der echte fortgesetzte Lauf meldet bereits höhere Schritt-/Tokenzahlen und führt die Kosinus-Lernrate fort.

Beim Start am Netz, Akku 100%, ungefähr 42 GiB verfügbarer RAM; keine konkurrierenden SLM-GPU-Prozesse. Leistungseinstellungen unverändert, genau erfasst in `RUN_CONDITIONS.json` / `START_AUTHORIZATION.json`, zusätzlich je Lauf. Light-Monitoring und PowerWatch bleiben aktiv. Historische Betriebsunterschiede bei Zeit-/Tokenvergleichen beachten.

Stoppen: `touch runs/long-horizon-round2-resume-2026-09-12/STOP`. Neue Ergebnisse noch nicht in den früheren ZIP-Archiven. Kein Remote-Push beauftragt.

## Auf Nutzerwunsch gestoppt

Am 12.09.2026 um 13:20:50 Europe/Berlin nach „Stop the run please“ sicher pausiert. Fünf Trainings abgeschlossen; r1-C speicherte `checkpoint-0154741` mit Modell, Adam und Sampler. 34.706.025 zusätzliche, 280.569.394 kumulierte Tokens. Beide Prozesse beendet, STOP gesetzt, eingefrorene Eingaben unverändert. Verbleibendes ursprüngliches Budget 40231.802s; keine automatische Wiederaufnahme. Details und Dateihashes in `STOP_VERIFIED_2026-09-12.json`.

## Erneute Fortsetzung am 14. September 2026

Auftrag „Continue the run“. Neue Sitzung `runs/long-horizon-round2-resume-2026-09-14/`, unveränderter Code auf `4c30196` im Worktree `SLM-long-round2`. Start 2026-09-14T18:20:56.745881+02:00, neue harte Frist 2026-09-15T05:28:35.547763+02:00 (Europe/Berlin).

Fünf abgeschlossene Trainings samt sämtlichen Auswertungen unabhängig per APFS-Kopie übernommen und gehasht. r1-C setzt den letzten vollständigen `checkpoint-0154741` bei Schritt 154741, 34.706.025 zusätzlichen und 280.569.394 kumulierten Tokens fort. Adam-Datei auf Integrität geprüft; Modell-/Job-/Sampler-Signaturen unverändert. 430 historische eingefrorene Eingaben und 393 kopierte Dateien geprüft, keine Hardlinks. Historische STOP-Dateien bleiben erhalten; die lokale kopierte Sperre liegt als `STOP.before-resume-20260914` vor.

Bisheriger Gesamtverbrauch 46168,198s plus 173s Vorbereitung (gemessene Arbeit plus 90s Abschlussreserve); verbleiben 40058.802s. Die Nutzerpause seit 12. September zählt nicht. r1-C erhält noch 4613.515s einschließlich Lade-/Checkpointzeit, danach r1-B und r1-A mit jeweils 7200s. Maximale verbleibende Stufenzeit samt Auswertung/Bericht 27193.515s. Kein neues Budget, keine automatische Verlängerung oder zusätzliche Kampagne.

Keine Code- oder Konfigurationsänderung. Vorhandene Resume-Tests bleiben maßgeblich; Budget-/Signatur-/Auswertungsprüfungen erneut am tatsächlichen Fortsetzungsplan ausgeführt. GPU-Gesundheitsprüfung bestanden; Training meldet bereits höhere Schritt-/Tokenzahlen. Beim Start Netzbetrieb, AC powermode 0, rund 47 GiB RAM verfügbar; Einstellungen unverändert. Aktuelle Bedingungen und Autorisierung in `RUN_CONDITIONS.json` / `START_AUTHORIZATION.json`. Light-Monitoring und PowerWatch aktiv.

Stoppen: `touch runs/long-horizon-round2-resume-2026-09-14/STOP`. Neue Ergebnisse noch nicht archiviert; kein Remote-Push.
