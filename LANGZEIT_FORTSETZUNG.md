# Fortsetzung nach Nutzerpause am 10. September 2026

Der Nutzer hat um Wiederaufnahme gebeten. Historische Kampagne `runs/long-horizon-2026-09-10` bleibt STOP-gesperrt und unverändert. Neue Sitzung: `runs/long-horizon-resume-2026-09-10`, Code im Worktree `SLM-long-resume`, Branch `codex/long-horizon-resume`.

Drei vollständige Trainings und ihre Auswertungen werden unabhängig per APFS-Kopie übernommen. Lauf r0-D setzt den vollständigen Checkpoint `checkpoint-0137865` mit Adam- und Samplerzustand fort. Die alte Stufe verbrauchte 231,6749368 Sekunden ihres 7200-Sekunden-Prozessbudgets; verbleiben 6968,3250632 Sekunden einschließlich Lade-/Checkpointzeit und 60 Sekunden Abschlussreserve. Anschließend vier unveränderte Zweistundenläufe samt Auswertung. Modell, Daten, Suiten, Jobparameter und numerischer Kern bleiben unverändert.

Die vorige Sitzung verbuchte kumuliert 23263,7037239 Sekunden des 86400-Sekunden-Budgets. Vorbereitung wird zusätzlich konservativ belastet; exakte Reserve und Restbudget stehen in `resume.json` und `plan.json`. Die Pause selbst zählt nicht. Die neue verbindliche Deadline entsteht beim Start in `status.json`. Kein neues Budget, keine automatische Verlängerung oder Modellübernahme.

Beim Wiederaufnahmeauftrag ist Netzbetrieb mit `powermode 1` statt zuvor `2` gemessen. Einstellung bleibt unverändert, Zeitpunkt des Wechsels unbekannt. Aktuelle Werte in RUN_CONDITIONS und START_AUTHORIZATION; Tokenzahlen und geänderte Bedingungen bei Zeitvergleichen berücksichtigen. EvoNN war bereits abgeschlossen.

Neuer Supervisor `long_study.resume` überspringt nur validierte fertige Läufe, prüft kopierte Artefakte und Fortsetzungssignatur und nutzt den vorhandenen seriellen Runner mit begrenzter GPU-Recovery. Vorab eine kurze GPU-Gesundheitsprüfung im Restbudget. Light-Monitoring und PowerWatch bleiben aktiv. 50 CPU-Tests bestanden; numerischer Kern unverändert. Die erste echte Fortsetzung dient zusätzlich als Überprüfung der Checkpoint-Wiederaufnahme.
