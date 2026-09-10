# Auswertungsfristen und Fortsetzung (10. September 2026)

Nutzerauftrag: „Fix it and resume“. Code im Worktree `/Users/timokruth/Projekte/SLM-timeout-recovery`, Branch `codex/evaluation-timeout-recovery`, auf Basis des GPU-Hang-Fixes `b58809f`.

## Fehler und Korrektur

Die vorige Fortsetzung pausierte um 03:01:59 nach drei aufeinanderfolgenden Auswertungsfehlern. Insgesamt bestanden sechs Referenz-Loss-Timeouts und zwei native GPU-Hänger. Die bisherige Auswertungsfrist von 110 Sekunden wurde bereits durch die Antwortgenerierung verbraucht; beim ersten 97M-Kaltstart wurden nur 222 von 473 Aufgaben begonnen.

Die neue Fortsetzung verwendet für Auswahl- und Gegenprüfung jeweils 600 Sekunden Rechenfrist plus 30 Sekunden Prozessreserve. Suiten, maximale Antwortlänge (256 Tokens), Bewertungsverfahren, numerischer Code, Trainingsparameter und bereits gespeicherte Scores bleiben unverändert. Alle offenen Auswertungen werden vollständig berechnet. Teilresultate werden nicht als vollständige Messung übernommen.

Die neue CLI-Option `study.recovery --evaluation-seconds` dokumentiert alte und neue Fristen im Audit. Die maximale Summe der noch offenen Stufen berücksichtigt diese Fristen einschließlich Gegenprüfungen und Kontrollen. Sie muss mit zusätzlichem Puffer ins ursprüngliche Restbudget passen. Kein neues 24h-Budget. Ein weiterer Referenz-Loss-Timeout löst nun unmittelbar eine Pause aus; der gespeicherte Modellstand bleibt für eine spätere Auswertung erhalten. Der genaue GPU-Hang-Text löst die bereits getestete begrenzte GPU-Wiederherstellung aus.

## Verifikation und Budget

81 Tests bestanden: Fristenberechnung für alle verbleibenden Stufen, Ablehnung ungültiger Fristen, sofortige Timeout-Pause ohne weitere Trainings sowie GPU-Hang-/Dienstfehler mit begrenzter Wiederholung. Alle elf Prüfungen auf unveränderten numerischen Kern bestanden.

Kontrolle am unabhängigen Modellstand von `cold-r0-cold-97m`: vollständige 473er-Suite einschließlich aller Referenz-Loss-Werte, 126,272 Sekunden Prozesslaufzeit, Exit 0, keine erreichte Deadline. Die Auswertung passt anhand Modell-, Tokenizer- und Suitehash zum historischen Modell und wird übernommen. Messung über `run_slm.py` mit Monitoring light, Artefakte unter `runs/timeout-repair-2026-09-10/`. Dies ist eine erfolgreiche Funktionskontrolle; aus geänderten Betriebsbedingungen darf kein Durchsatzgewinn des Modells abgeleitet werden.

Bisher kumuliert 24.563,759 Sekunden; aufgerundet 24.564. Weitere Reserve: 247 Sekunden (aufgerundete GPU-Kontrolle plus 120 Sekunden für Tests/Vorbereitung). Neues Startbudget: 61.589 Sekunden = 17h 06m 29s. Die Pause zählt nicht als Trainingszeit. Auch die neue Fortsetzung darf keine automatische Verlängerung oder Modellübernahme vornehmen.

## Start

Neue Kampagne: `runs/parameter-study-timeout-recovery-2026-09-10/`. Vorbereitung validiert und kopiert vollständige Ergebnisse unabhängig; alte Läufe und STOP-Sperren bleiben erhalten. Start ausschließlich über `run_slm.py --module study.campaign` aus diesem Worktree. Status, tatsächlicher Start und verbindliche Deadline stehen nach Start in `status.json`; der Nutzerauftrag ist in `START_AUTHORIZATION.json` vermerkt. Light-Monitoring und PowerWatch bleiben aktiv.
