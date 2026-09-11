# Hardware-Optimierung und Ausgabequalität

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
