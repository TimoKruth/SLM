# Größenvergleich: jeweils drei Stunden Fortsetzung

Am 9. September 2026 hat der Nutzer die Fortsetzung **beider letzten Drei-Stunden-Modelle vom letzten Modellstand für jeweils weitere drei Stunden** beauftragt. Dies ersetzt für diesen Versuch den vorherigen Vorschlag eines neuen, optimierten Sechs-Stunden-Laufs.

- Ausgangspunkte: 27,3M bei Schritt 65.659 / 119.011.223 Tokens sowie 97,5M bei Schritt 21.214 / 38.476.763 Tokens, jeweils `latest`, nicht `best`.
- Eigene Verzeichnisse: `runs/size-27m-2026-09-09-plus3h/` und `runs/size-97m-2026-09-09-plus3h/`. Gewichte, vollständiger AdamW-Zustand, Sampler-RNG und Zähler werden unverändert aus unabhängig kopierten Endcheckpoints übernommen. `parent.json` enthält Herkunft und Prüfsummen. Historische Daten/Resultate bleiben erhalten.
- Identischer numerischer Trainingscode wie im ursprünglichen Vergleich: FP32, kompilierter Schritt, Kontext 1.024, Batch 2, gleiche breite korrigierte Mischung aus 32 Quellen. BF16 und neue Kandidatendaten bleiben außerhalb dieses Versuchs.
- Die ursprüngliche Kosinus-Lernratenkurve bis 100M Tokens bleibt erhalten; keine neue Aufwärmphase des Optimierers. Klein beginnt bereits bei 3e-5; groß folgt ab 38,5M seiner bisherigen Kurve. Dies ist eine Fortsetzung des ursprünglichen Versuchs, keine Optimierung der Lernrate je Größe.
- Reihenfolge: klein trainieren → auswerten → groß trainieren → auswerten. Jede Trainingsstufe erhält genau einmal 10.800 zusätzliche Sekunden bei Startfreigabe, inklusive Laden/Datenprüfung, Entwicklung und Checkpoints; maximal 120 Sekunden anschließende Checkpoint-Aufräumfrist. Bei Wiederaufnahme keine neue Frist. Kein zusätzlicher Durchlauf nach Abschluss.
- Nach jeder Stufe dieselben 886 internen Entwicklungsaufgaben, 256 Tokens Antwortbudget, Referenz-Loss und ausführbare Code-Aufgaben. WikiSQL-Ausführungsproxy und Trainings-Mehrheitsregeln stehen im Abschlussbericht. Je Auswertung maximal 900 Sekunden Nutzbudget. Die externen Tests bleiben geschlossen.
- Primärer Vergleich: letzte Modellstände nach kumuliert 3 und 6 Stunden aktiven Trainingsbudgets; Zugewinn je Größe und Unterschiede zwischen Größen. Der Bericht zieht die alten Tokenzähler ab, statt vorangegangene Tokens als neue Arbeit zu zählen. Pausen zwischen Sitzungen sind keine Trainingszeit.
- Alte 10M/20M/30M-Snapshots verbleiben in den Elternläufen. Ihre Grenzwerte bleiben wegen der Wiederaufnahmesignatur unverändert; es werden keine neuen gleich großen Token-Endpunkte behauptet. Zwischenzeitliche Entwicklung und Checkpoints bleiben aktiv.

Kampagne: `runs/size-continuation-2026-09-09/`, mit `plan.json`, `progress.json`, `status.json`, Stage-Logs, Performance-Berichten und automatischem `REPORT.md`/`comparison.json` am Ende. Code: `/Users/timokruth/Projekte/SLM-continuation`, Branch `codex/size-continuation`.

Alle Starts laufen durch `run_slm.py` mit Monitoring `light`, zehn Aufwärmschritten des Messsystems und 60-Sekunden-Zwischenständen. `caffeinate` verhindert Ruhezustand während der Kampagne; GPU-Arbeit läuft seriell unter der gemeinsamen Sperre. PowerWatch misst zusätzlich systemweit alle 15 Sekunden. `pmset` wird vor jeder Trainingsstufe protokolliert, Leistungseinstellungen werden nicht verändert. Reduzierte Leistung, Temperatur, Systemkonkurrenz, ein Seed und feste Reihenfolge begrenzen den Vergleich.

Geordnet stoppen: `touch runs/size-continuation-2026-09-09/STOP`. Die Kampagne beendet den aktuellen Kindprozess und startet keine weitere Stufe. Laufende oder eingefrorene Eingaben im Kampagnen-Worktree nicht verändern.

Verifikation vor Start: identische Prüfsummen der ursprünglichen numerischen Trainings-/Generierungsmodule, Prüfung der alten Kampagneneingaben, unabhängige Checkpointkopien mit Datei-Hashes und passender Wiederaufnahmesignatur. Zwölf gezielte Tests für Token-Deltas, Bericht, Token-Snapshots und Projektstarter bestanden.
