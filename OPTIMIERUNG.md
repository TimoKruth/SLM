Aktiver fokussierter Vergleich (15.09.2026): [12.000 identische Updates, Start und Grenzen](FOCUSED_FP32_START.md). Status im Worktree `SLM-focused-optimization`, Lauf `focused-fp32-12000-2026-09-15`.

Abgeschlossen und analysiert (15.09.2026): [Ergebnisse und nächste gezielte Prüfung](CONSERVATIVE_RESULT_ANALYSIS.md). Kein neuer Lauf gestartet.

Aktuell (15.09.2026): konservativer Vergleich nach Zeitplanungsfehler repariert und mit Restbudget neu gestartet. Siehe [Start und Grenzen](CONSERVATIVE_RECOVERY_START.md). Verbindlicher Status im Worktree `SLM-conservative-recovery`, Run `conservative-fp32-recovery-2026-09-15`.

# Hardware-Optimierung und Ausgabequalität

**Neuer Startauftrag:** Der konservative FP32-Vergleich ist für **15.09.2026 um
00:00 Europe/Berlin** vorgemerkt. Der lokale Starter ist aktiv und wartet auf
Mitternacht. Falls die aktuelle Langzeitkampagne noch läuft, wartet er auf ihren
erfolgreichen Abschluss; keine Unterbrechung oder GPU-Konkurrenz. Spätester Start
06:00, danach verfällt dieser Versuch. Sechs Stunden Budget ab tatsächlichem Start.
[Startprotokoll](/Users/timokruth/Projekte/SLM/CONSERVATIVE_MIDNIGHT_START.md).
Die folgenden Angaben „nicht gestartet/keine Autorisierung“ beschreiben die ursprüngliche Vorbereitung.

## Konservativer Vergleich vorbereitet — nicht gestartet

Neuer ausdrücklicher Auftrag: sechs Stunden Vergleich vorbereiten, **ohne Start**.
Code `e43367d` im separaten Worktree `/Users/timokruth/Projekte/SLM-conservative-optimization`,
Branch `codex/conservative-optimization`.

- [Vollständiger Plan und spätere Bedienung](/Users/timokruth/Projekte/SLM-conservative-optimization/CONSERVATIVE_FP32_6H.md)
- [Vorbereitungsbeleg](/Users/timokruth/Projekte/SLM-conservative-optimization/runs/conservative-fp32-6h-2026-09-12/READY.json)

FP32 bleibt unverändert; einziger Faktor ist Warten auf GPU-Ergebnisse nach jedem
Update oder nach vier Updates. 20 kurze Kontrollen, sechs längere Läufe über drei
Datenreihenfolgen und 26 Qualitätsauswertungen. Budget einschließlich Reserven:
höchstens 21.600 Sekunden; je längerer Lauf 2.750 Sekunden inklusive Checkpoints.
Neue Auswahlsuite 384 und Gegenprüfung 288 Aufgaben aus 24 Quellen. Beide Suiten
prüfen den Stand nach 16.384 identischen Updates sowie den Zeitendpunkt.

51 CPU-Tests bestanden, Daten-/Codeeingaben gehasht, STOP gesetzt. Keine nutzbare
Autorisierung, keine GPU-Prüfung, kein gestarteter Prozess, keine automatische
Warteschlange. Der laufende Langzeitblock wurde nicht verändert. Ein späterer Start
benötigt einen eigenen ausdrücklichen Auftrag und freie Projekt-GPU-Kapazität.

## Historie: erste größere Optimierungsstudie abgeschlossen

**Die Studie vom 11./12.09.2026 endete vollständig um 01:31:50 Europe/Berlin.
Kein Kandidat erfüllte alle vorab gesetzten Kriterien; keine Optimierung übernommen.
Die nachfolgenden Start-/Warte-/Pausenangaben dokumentieren ausschließlich den damaligen Ablauf.**

Der Nutzer hat ausdrücklich eine neue **sechsstündige Studie samt Start** beauftragt.

- [Plan, Messgrößen und Budget](/Users/timokruth/Projekte/SLM-quality-optimization/QUALITY_OPTIMIZATION_6H.md)
- [Aktueller äußerer Start-/Wächterstatus](/Users/timokruth/Projekte/SLM-quality-optimization/runs/quality-optimization-6h-2026-09-11/direct-status.json)
- [CPU-Verifikation](/Users/timokruth/Projekte/SLM-quality-optimization/quality_optimization/VALIDATION.md)

Code im separaten Worktree `/Users/timokruth/Projekte/SLM-quality-optimization`, Branch
`codex/quality-optimization`, Commit `3244a2a`. Der Starter ist seit **20:59:41 am
11. September 2026 (Europe/Berlin)** aktiv. Beim Start war der Mac am Akku: Er wartet
maximal 30 Minuten auf Netzstrom. Sobald dieser vorliegt, beginnt automatisch die
GPU-Studie mit höchstens 21.600 Sekunden inklusive Prüfungen/Auswertung. Danach ist
`runs/quality-optimization-6h-2026-09-11/status.json` im neuen Worktree verbindlich.
Bei fehlendem Netzstrom bis Fristende beendet sich der Starter ohne GPU-Arbeit;
keine automatische erneute Warteschlange. Netztrennung während der Studie stoppt sie.

Vorgesehen sind 120 Replay-Prozesse (FP32/BF16 × sechs Ausführungsprofile × fünf
gepaarte Wiederholungen), acht längere Online-Trainings mit zwei Datenreihenfolgen
und 26 Auswertungen. Neue getrennte Suiten: 300 Auswahl- und 195 Gegenprüfungsaufgaben
aus je 25 Quellen. Vergleich nach identischer Datenexposition und nach gleichem
Zeitbudget, gemeinsame FP32-Inferenz, ursprüngliche v4-Daten und 27,3M-Elternmodell.
53 CPU-Tests bestanden; reale Checkpoint-/GPU-Kontrollen sind die erste Studienphase.
Keine automatische Modellübernahme und keine Behauptung vollständiger Optimierung.

## Erster Screen abgeschlossen

Der ursprüngliche Screen im Worktree `/Users/timokruth/Projekte/SLM-optimization`,
Branch `codex/hardware-optimization`, hat **alle 60 Worker** am 11. September zwischen
19:57:39 und 20:15:00 abgeschlossen. BF16 erreichte einen medianen Durchsatzfaktor
von **1,283×** gegenüber FP32 und bestand die kurzen numerischen Stabilitätschecks.
Das ist noch kein Nachweis gleichwertiger längerfristiger Ausgabequalität.

- [Ergebnisse des ersten Screens](/Users/timokruth/Projekte/SLM-optimization/runs/optimization-screen-2026-09-11/REPORT.md)
- [45 Untersuchungsrichtungen](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/catalog.json)
- [Autoresearch-MLX-Referenz](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/AUTORESEARCH.md)

Der Langzeitblock bleibt seit 19:56:12 sicher auf `checkpoint-0146497` pausiert,
einschließlich Modell, Adam und Sampler. Seine STOP-Sperren und eingefrorenen Eingaben
bleiben unverändert. Ebenso bleiben die vorbereiteten v5-/v6-Daten unverändert.
Keine automatische Wiederaufnahme, Verlängerung oder weitere Studienrotation.
Rohdaten und lokale Messprotokolle werden nicht eingecheckt; kein Remote-Push.
