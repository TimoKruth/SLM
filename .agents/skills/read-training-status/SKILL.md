---
name: read-training-status
description: Prüfe den aktuellen Stand der Trainingskampagnen in diesem SLM-Projekt mit einer schnellen gebündelten Code-Abfrage. Verwenden bei „Status?“, „Wie ist der Stand?“, „Läuft das Training noch?“ oder Fragen zu Fortschritt und bisherigen Ergebnissen der SLM-Experimente. Nur für dieses Projekt, keine allgemeine PR- oder Deployment-Statusabfrage.
---

# Trainingsstatus lesen

Im Stammverzeichnis dieses SLM-Projekts einmal ausführen, bevorzugt mit einem vorhandenen Python-Interpreter mit `psutil`:

```sh
.venv/bin/python .agents/skills/read-training-status/scripts/status.py --project . --resources
```

Ohne Projektinterpreter funktioniert `/usr/bin/python3`; verfügbarer RAM bleibt ohne `psutil` gegebenenfalls unbekannt. Keine Abhängigkeiten installieren. `--resources` ergänzt eine kurze PowerWatch-Abfrage über den vorhandenen globalen Ressourcen-Skill; weglassen, wenn nur der Laufstatus relevant ist.

- Ist das Kampagnenverzeichnis aus dem Gespräch bekannt, mit `--run /absoluter/pfad/zur/kampagne` direkt wählen. Das spart Suche und vermeidet Verwechslungen. Keinen historischen Pfad dauerhaft als „aktuell“ festlegen.
- Ohne `--run` durchsucht das Skript ausschließlich `runs/*/status.json` im angegebenen Projekt. Bei mehreren plausibel aktiven Kampagnen gibt es Kandidaten zurück. Anhand des Gesprächs auswählen und direkt abfragen; keine zufällige Auswahl oder neue Starts.
- Unterstützt die lokalen SLM-Kampagnen mit `status`, `phase`, `stages`, `plan.json` und optional `trials/*/status.json`, `quality.json`, `assessment.json`. Andere Formate als unbekannt behandeln und gezielt prüfen; keine Vollständigkeit vortäuschen. Keine Modellimporte, Checkpoint-Ladevorgänge oder rekursiven Logscans.

## Ergebnis beurteilen

`status.json` ist maßgeblich, ein älterer REPORT.md kann hinterherhinken. Das Skript prüft Heartbeat, Dateialter und Prozesszustand getrennt; eine vorhandene PID ist wegen möglicher Wiederverwendung allein kein Lebenszeichen. Frisches Trainings-Dateialter stützt den Fortschritt, beweist allein aber keinen Tokenzuwachs. Bei Widersprüchen gezielt die betroffene Statusdatei bzw. einen kleinen Log-Tail lesen. Keine Reparatur aus einer Statusfrage ableiten.

Berichte Uhrzeit, abgeschlossene Trainings/Plananzahl, aktive Phase, zusätzliche Tokens, Zeitfortschritt und wesentliche neue Qualitätsergebnisse. Trainingsabschluss bedeutet nicht Abschluss sämtlicher Auswertungen. Ausgaben `stage_budget_end_estimate` sind Schätzungen anhand des Stufenbudgets; Checkpointreserve oder frühzeitiger Abschluss können das Ende vorziehen. Die Kampagnen-Deadline ist die harte Budgetgrenze, keine Fertigstellungsprognose. Fehlende Plananzahl oder ETA offenlassen.

Für Qualitätsaussagen die vorhandenen Scores unverändert nennen und ihre Aggregation nicht als Anzahl richtig gelöster Aufgaben umdeuten. Interne Auswahlsuite und Gegenprüfung getrennt halten. Derselbe Endpunkt zwischen Varianten und Datenreihenfolgen ist vergleichbar; unterschiedliche Suiten nicht direkt gegeneinander rechnen. Batch-Trainingsloss ist kein evaluierter Antwortloss. Zusätzliche und kumulierte Tokens unterscheiden. Keine Signifikanz, externe Übertragung oder bestätigten Gewinner aus einem Zwischenstand behaupten.

Für Performancevergleiche `RUN_CONDITIONS.json`/`.md` und aktuelle Leistungseinstellung berücksichtigen. Die Ausgabe nennt die Bedingungsdateien und vorhandenen Paralleljobstatus. Veränderte Überlappung, Leistungseinstellungen und Datenmischung können den Durchsatz beeinflussen. System-GPU ist nicht einem einzelnen Job zuordenbar; Ressourcen-Skill enthält die Messgrenzen.

Die Abfrage liest ausschließlich. Keine Statusdateien regenerieren, eingefrorene Eingaben ändern, Jobs starten/pausieren oder Dienste neu starten. Antworte kompakt; bei wiederholten Statusfragen neue Entwicklungen hervorheben.
