# Hardware-Optimierung: erster Screen läuft

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

Neuer Nutzerauftrag: laufenden Langzeitblock pausieren und Optimierung jetzt für die
nächste Stunde ausführen. Langzeit r0-D wurde um 19:56:12 Europe/Berlin sicher auf
`checkpoint-0146497` pausiert; Modell, Adam und Sampler sind erhalten. Die alte
Warteschlange ist beendet.

Der ursprüngliche 60-Worker-Screen läuft seit **19:57:39**, spätestens bis **20:57:39**
am 11. September 2026 (Europe/Berlin). Er darf früher fertig werden. Der erste Baseline-
Worker ist erfolgreich abgeschlossen. Status: `runs/optimization-screen-2026-09-11/status.json`
im Optimierungs-Worktree; äußerer Wächter `direct-status.json`. Keine automatische
Verlängerung oder weitere Rotation; keine automatische Wiederaufnahme des Langzeitblocks.

Details: [aktuelles Startprotokoll](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/START.md).

Die eingefrorenen Eingaben der pausierten Langzeitkampagne sowie die vorbereiteten
v5/v6-Daten bleiben unverändert. Rohdaten und lokale Messprotokolle werden nicht eingecheckt.
