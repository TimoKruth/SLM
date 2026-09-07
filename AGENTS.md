# Künftige Trainingsläufe

Der Nutzer hat am 7. September 2026 leichtgewichtiges Performance-Monitoring für die nächsten Läufe aktiviert.

- Neue Trainings- und zugehörige Auswertungsläufe über `.venv/bin/python run_slm.py --run <Laufverzeichnis> ...` starten. Der Standard ist `slm.sixhour`; für andere Einstiegspunkte `--module` verwenden.
- `run_defaults.json` ist die verbindliche Projektvorgabe: Monitoring `light`, zehn Aufwärmschritte, Zwischenstände alle 60 Sekunden. Der überwachte Supervisor reicht den Modus an Training, Bericht und Code-Auswertung weiter.
- Monitoring nur bei ausdrücklicher Anweisung ausschalten (`--monitoring off`); `detail` bleibt für gesonderte Diagnoseversuche vorgesehen.
- Direkte technische Einstiegspunkte wie `python -m slm.train` umgehen die Projektvorgabe. Sie nicht versehentlich für neue reguläre Läufe verwenden.
- Laufende oder eingefrorene Versuche nicht nachträglich instrumentieren. Der Versuch `expanded-2026-09-07-6h` samt anschließender Auswertung bleibt unverändert.
- Details und Grenzen stehen in `PERFORMANCE.md`. Die bereits eingeplanten A/B-Diagnosen behalten ihre ausdrücklich gewählten Messmodi.

# Breites Lernziel

- Ziel ist ein vielseitiges Benchmark-only-Sprachmodell. Coding ist ein Beispiel, keine bevorzugte Zielkompetenz.
- Neue Mischungen über die Fähigkeiten in `slm/breadth.py` planen; Lernfortschritt je Bereich ausweisen. Neue Quellen zuerst auf Original-Trainingssplit, Gruppentrennung, Kontextlänge und Herkunft prüfen.
- Der aktuelle Vergleich nutzt dieselben 32 Quellen mit gleicher Gewichtung je Fähigkeitsgruppe beziehungsweise je Quelle. Details und Grenzen: `BREITES_LERNEN.md`.
- Der Lernkontrollversuch misst Wiedererkennen eigener Trainingsaufgaben separat von Entwicklung. Nie als Transfer-Erfolg berichten.

# Betriebsbedingungen bei Vergleichen

- Vor Performance- und Qualitätsvergleichen `RUN_CONDITIONS.json`/`RUN_CONDITIONS.md` im Lauf- und Kampagnenverzeichnis lesen. Diese ergänzen die automatisch erfassten Monitoring-Metadaten.
- Für die breite Versuchsreihe vom 7. September 2026 meldet der Nutzer reduzierte Leistung zur Geräuschbegrenzung; genauer Modus und Beginn sind unbekannt. Keine rückwirkende Annahme über frühere Läufe oder Kalibrierungen. Vergleiche bei festem Zeitbudget müssen zusätzlich tatsächliche Tokens und mögliche Änderungen der Leistungseinstellung berücksichtigen.
