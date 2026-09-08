# Nächster längerer Lauf: Vorbereitung abgeschlossen

Stand: 8. September 2026. **Kein längerer Lauf gestartet oder eingeplant.**

Der vollständige [Vorbereitungsbericht](/Users/timokruth/Projekte/SLM-next-run-prep/NAECHSTER_LAUF.md) und der Code liegen im Worktree `/Users/timokruth/Projekte/SLM-next-run-prep`, Branch `codex/next-run-preparation`. Laufartefakte liegen gemeinsam unter `runs/next-preparation-2026-09-08/`.

- Fehleranalyse aller 886 Antworten je Modell, 19 manuell geprüfte Fälle, separate Referenz-Sensitivitätsrechnung.
- 256 nachweislich gesehene Trainingsaufgaben und 248 nach Länge zugeordnete Entwicklungsaufgaben ausgewertet. Auf 31 gemeinsamen Quellen: 58/192 gegen 55/192 richtige bewertbare Antworten; kleine diagnostische Stichprobe, kein Transferbeleg.
- Batch- und Rechengenauigkeitsvergleich: BF16-Rechenoperationen mit FP32-Mastergewichten etwa 20,3 % schneller als FP32/Batch 2 im isolierten Kurzvergleich. Optionaler Trainer-Schalter; Standard bleibt FP32.
- 39 Tests sowie GPU-Speicher-/Wiederaufnahmeprüfung und reguläre Start-/Resume-Probeläufe bestanden. Früh gefundener Signaturfehler behoben, Fehlversuch dokumentiert.
- TAT-QA und MultiNLI: nur Original-Trainingsdateien separat geladen und vorgeprüft; weiterhin 32 aktive Trainingsquellen.
- Vorgeschlagener Sechs-Stunden-Lauf, Lernratenkurve, Snapshots und Erfolgskriterien stehen im [inaktiven Plan](/Users/timokruth/Projekte/SLM-next-run-prep/next_run/long_plan.json). Das ist keine Startfreigabe. Externes [Transferprotokoll](/Users/timokruth/Projekte/SLM-next-run-prep/next_run/transfer_protocol.json) vorbereitet; Testdateien ungeöffnet.
