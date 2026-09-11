# Zweiter Langzeitblock: Lernrate und Verlauf

Nutzerauftrag vom 11. September 2026: „Wir hatten eine Evaluation aller Parameter gestartet. Bitte lass die nächsten Parameter laufen nachdem der erste run erfolgreich war“.

Der erste Langzeitblock ist technisch vollständig abgeschlossen: acht Trainings, alle 44 Stufen erfolgreich, Eingaben unverändert. Kein Kandidat erfüllte sämtliche Qualitätskriterien. Die Fortsetzung untersucht daher die nächste vorgesehene Achse aus der Rotation und übernimmt keinen vermeintlichen Gewinner.

Code: `/Users/timokruth/Projekte/SLM-long-round2`, Branch `codex/long-horizon-round2`.
Kampagne: `runs/long-horizon-round2-2026-09-11/`. Der aktuelle Status und die harte Frist stehen nach Start in `status.json`. Strukturierter Plan: `plans/long-horizon-round2-2026-09-11/plan.json`.

## Vorab festgelegter Vergleich

| Bedingung | Lernrate | Verlauf |
| --- | ---: | --- |
| A, gemeinsame Kontrolle | 3e-5 | konstant |
| B | 3e-6 | konstant |
| C | 1e-4 | konstant |
| D | 3e-5 → 3e-6 | Kosinus über 100M zusätzliche Tokens; danach konstant 3e-6 |

A–B–C–D / D–C–B–A mit Daten-Seeds 2026091101 und 2026091102. Acht Trainings mit je 7200 Sekunden Prozessbudget einschließlich Laden, Checkpoints und 60 Sekunden Abschlussreserve. Alle starten unabhängig vom ursprünglichen kleinen Sechs-Stunden-Modell einschließlich Adam-Zustand. 27,3M Parameter, FP32, gleiche Familiengewichtung, unveränderte korrigierte 32 Quellen. Zwei Datenreihenfolgen sind keine unabhängigen Initialisierungsseeds.

Der Kosinusverlauf verwendet zusätzliche Tokens seit dem ursprünglichen Start dieser Adaptation. Wiederaufnahme setzt ihn anhand des gespeicherten Tokenzählers fort. 100M ist eine vorab gesetzte Verlaufslänge, kein zusätzliches Trainingsziel: Zeitende bleibt maßgeblich. Die alten Kurzläufe hatten andere Verlaufslängen; ihre Effekte sind nicht unmittelbar dieselbe Behandlung.

Direkte Vergleiche B−A, C−A und D−A jeweils pro Wiederholung und Fähigkeitsgruppe. Dies ist kein 2×2-Faktorielles Design; keine Mischungswechselwirkung berechnen. Gleiche Tokenstände bei 15M und 50M sowie finaler Zeitendpunkt auf unveränderter 473er-Auswahlsuite. Neue interne 200er-Gegenprüfung mit Ausschluss aller bisherigen Gegenprüfungen, Suchsuite und Trainingsgruppen. Das Audit hält Herkunft und Gruppenabdeckung fest. Alle acht Endpunkte sowie das unveränderte Elternmodell werden auf dieser neuen Suite bewertet. Keine direkte Gleichsetzung mit den aggregierten Scores anderer Gegenprüfungen.

Bisherige Kriterien bleiben: mindestens +2 Prozentpunkte in beiden Wiederholungen gegen A, kein mittlerer Familienrückgang über 5 Punkte und bestandene Elternmodellkontrolle. Kein automatischer Modellwechsel. Die 57 historischen Varianten bleiben vollständig im Katalog; weitere Achsen sind noch offen.

## Begrenzung und Betrieb

Die bisherige Blockgröße wird für diesen Folgeauftrag übernommen: maximal 24 Stunden einschließlich Vorbereitung und Auswertung. Es wurde eine optionale Budgetfrage gestellt; ohne abweichende Antwort gilt die kommunizierte gleiche Blockgröße. 1200 Sekunden Vorbereitung werden konservativ vorab belastet, der Supervisor erhält höchstens 85.200 Sekunden. Maximal geplante Stufen einschließlich Bericht: 79.110 Sekunden. Acht Trainings benötigen 16 Stunden; 33 Auswertungen erhalten je 600 Sekunden plus 30 Sekunden Prozessreserve. Kein automatischer weiterer Block, keine Verwendung der alten Restreserve und keine Verlängerung einzelner Trainings.

Light-Monitoring, zehn Aufwärmschritte, 60s-Zwischenstände und PowerWatch bleiben aktiv. Checkpoints mit Adam/Sampler alle 300 Sekunden; zusätzliche Tokenstände bei 15/30/50/75/100/150M, sofern erreicht. STOP und Budgetkontrollen sowie höchstens zwei begrenzte GPU-Recovery-Versuche bleiben erhalten. Andere Fehler pausieren sofort. Historische Worktrees und Versuchsdaten bleiben unverändert.

Bei Vorbereitung Netzbetrieb, AC powermode 0, normale Thermik, ungefähr 31 GiB verfügbarer RAM und 1 TiB freier Datenträgerplatz. Parallel sind EvoNN-Tests sichtbar; die alte abgeschlossene EvoNN-Kampagne ist kein vollständiger Beleg für aktuelle Leerlaufbedingungen. Einstellungen und fremde Prozesse werden nicht verändert. Aktuelle Prozessaufnahme in `preflight-observation.json`, Leistungs-/Strombedingungen zusätzlich je Training; systemweite Änderungen sind über PowerWatch nachvollziehbar. Gleiche Zeit garantiert keine gleiche Tokenzahl.

## Kontrollen

75 Tests für Studienlogik, Lernrate, Wiederaufnahme, Zeitbudget, Vergleichsberichte, Monitoring und GPU-Zulassung bestanden. Echte kurze Prüfung des Kosinuslaufs mit Unterbrechung, vollständigem Checkpoint, Wiederaufnahme und regulärem Zeitende: `runs/long-round2-validation-2026-09-11/RESULT.json`. Vor langen Trainings folgen volle Eingabehashprüfung, GPU-Gesundheitsprüfung und numerische Kontrolle am Elternmodell im Supervisor.

Stoppen: `touch /Users/timokruth/Projekte/SLM/runs/long-horizon-round2-2026-09-11/STOP`.
Start erfolgt einmalig über `run_slm.py --module long_study.campaign` im neuen Worktree; `status.json` verhindert einen zweiten Start mit zurückgesetztem Budget.
