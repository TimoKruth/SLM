# Vorbereitetes Unterprojekt zur Hardware-Optimierung

Das separate Unterprojekt liegt im Worktree `/Users/timokruth/Projekte/SLM-optimization`,
Branch `codex/hardware-optimization`. Implementierung `ed78584`, Verifikation `dokumentiert im Unterprojekt`.

- [Einstieg und Bedienung](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/README.md)
- [Messprotokoll](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/MEASUREMENT.md)
- [45 Untersuchungsrichtungen](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/catalog.json)
- [Autoresearch-MLX-Referenz](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/AUTORESEARCH.md)
- [CPU-Verifikation](/Users/timokruth/Projekte/SLM-optimization/optimization_lab/VALIDATION.md)

Sechs implementierte Screening-Kandidaten plus Baseline, jeweils fünf gepaarte
Wiederholungen: insgesamt 60 kurze Worker vorbereitet. Echte Replay-Batches und der
ursprüngliche kleine Sechs-Stunden-Checkpoint sind gehasht. 61 CPU-Tests bestanden.
GPU-Validierung und Performance-/Qualitätsbestätigung stehen aus.

Nur vorbereitet: STOP im Unterprojekt und im Lauf bleibt gesetzt; keine GPU-Messung,
kein Trainingsstart und keine Queue. Eine Stunde Gesamtobergrenze ist lediglich ein
Vorschlag, keine Freigabe. Ein späterer Start benötigt einen ausdrücklichen Auftrag
mit endlichem Budget. Keine automatische Modellübernahme.

Die laufende Langzeitkampagne, ihre v4-Daten und das separat vorbereitete v5-Benchmark-
Paket bleiben unverändert. Rohdaten und lokale Messprotokolle werden nicht eingecheckt.
