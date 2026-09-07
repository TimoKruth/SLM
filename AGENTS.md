# Künftige Trainingsläufe

Der Nutzer hat am 7. September 2026 leichtgewichtiges Performance-Monitoring für die nächsten Läufe aktiviert.

- Neue Trainings- und zugehörige Auswertungsläufe über `.venv/bin/python run_slm.py --run <Laufverzeichnis> ...` starten. Der Standard ist `slm.sixhour`; für andere Einstiegspunkte `--module` verwenden.
- `run_defaults.json` ist die verbindliche Projektvorgabe: Monitoring `light`, zehn Aufwärmschritte, Zwischenstände alle 60 Sekunden. Der überwachte Supervisor reicht den Modus an Training, Bericht und Code-Auswertung weiter.
- Monitoring nur bei ausdrücklicher Anweisung ausschalten (`--monitoring off`); `detail` bleibt für gesonderte Diagnoseversuche vorgesehen.
- Direkte technische Einstiegspunkte wie `python -m slm.train` umgehen die Projektvorgabe. Sie nicht versehentlich für neue reguläre Läufe verwenden.
- Laufende oder eingefrorene Versuche nicht nachträglich instrumentieren. Der Versuch `expanded-2026-09-07-6h` samt anschließender Auswertung bleibt unverändert.
- Details und Grenzen stehen in `PERFORMANCE.md`. Die bereits eingeplanten A/B-Diagnosen behalten ihre ausdrücklich gewählten Messmodi.
