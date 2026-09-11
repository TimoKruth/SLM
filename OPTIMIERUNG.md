# Hardware-Optimierung: erster Screen freigegeben und eingereiht

Das separate Unterprojekt liegt im Worktree `/Users/timokruth/Projekte/SLM-optimization`,
Branch `codex/hardware-optimization`. Implementierung `ed78584`, Verifikation `1a44aab`.

- [Einstieg und Bedienung](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/README.md)
- [Messprotokoll](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/MEASUREMENT.md)
- [45 Untersuchungsrichtungen](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/catalog.json)
- [Autoresearch-MLX-Referenz](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/AUTORESEARCH.md)
- [CPU-Verifikation](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/VALIDATION.md)

Sechs implementierte Screening-Kandidaten plus Baseline, jeweils fünf gepaarte
Wiederholungen: insgesamt 60 kurze Worker vorbereitet. Echte Replay-Batches und der
ursprüngliche kleine Sechs-Stunden-Checkpoint sind gehasht. 61 CPU-Tests bestanden.
GPU-Validierung und Performance-/Qualitätsbestätigung stehen aus.

Nutzerauftrag „go for the first screen“: erste Messreihe mit maximal einer Stunde
Gesamtbudget freigegeben. Die aktive einmalige CPU-Queue startet sie nach erfolgreichem
Abschluss und Prozessende der laufenden Langzeitkampagne, sobald die GPU exklusiv frei
ist. Beide Optimierungs-STOPs sind entfernt. Kein weiterer manueller Start erforderlich.

Details: [Startprotokoll](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/START.md).
Wartestatus: `runs/optimization-screen-2026-09-11/queue-status.json` im Optimierungs-Worktree;
nach Start gilt dort `status.json`. Wartezeit verbraucht kein Screen-Budget. Queue-Verfall:
12. September 2026, 19:31:18 Europe/Berlin. Keine automatische Wiederholung, Verlängerung
oder Modellübernahme. Bei pausierter/fehlgeschlagener Vorgängerkampagne kein Start.

Die laufende Langzeitkampagne, ihre v4-Daten und das separat vorbereitete v5-Benchmark-
Paket bleiben unverändert. Rohdaten und lokale Messprotokolle werden nicht eingecheckt.
