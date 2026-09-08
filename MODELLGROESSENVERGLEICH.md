# Größenvergleich vom 8. September 2026

Der Nutzer hat die Datenkorrektur und den Vergleich von 27,3M gegen 97,5M Parametern mit **je drei Stunden Training** freigegeben. Die Ausführungsreihenfolge ist klein, Auswertungen, groß, Auswertungen. Beide beginnen mit Zufallsgewichten, identischem Tokenizer, denselben korrigierten Trainingsdaten und demselben Sampling-Seed. Keine Zufallssuche oder automatische Verlängerung.

## Datenprüfung

Neue, separate Version: `data/v4-broad-corrected-2026-09-08/`. Historische Daten bleiben unverändert. Der Konverter korrigiert SciTail `entails` → `entailment` sowie WIQA `no_effect` → `no effect`. Der zweite Fehler wurde bei dieser Prüfung entdeckt: Historisch wurden 9.936 WIQA-Beispiele dieser Klasse abgewiesen. Alte WIQA-Auswertungen decken damit nicht die vollständige Aufgabe ab.

Die neue Version enthält **1.433.943 Trainingspaare aus 32 Quellen**. Für alle Quellen wurden Original-Trainingsherkunft, gespeicherte Rohdatei-Hashes, Zeilenzahlen, nichtleere Antworten, Sequenzindizes, Kontextlängen und exakte Gruppen-/Prompt-Trennung geprüft. Bei 19 Quellen mit diskreten Antwortklassen wurde zusätzlich jede erhaltene Antwort gegen den ursprünglichen Prompt und die richtige Klasse geprüft; keine ursprüngliche gültige Trainingsklasse fehlt. Ungültige Original-SNLI-Labels werden separat ausgewiesen. Kontextfilter, Häufigkeiten kurzer Antworten und Klassenverteilungen stehen in `audit.json`. Die v2-Daten bleiben als identisches Präfix erhalten.

SciTail enthält im Training nun 7.989 entailment und 13.886 neutral; WIQA 9.566 no effect, 9.387 more und 9.434 less. Bei exakten Gruppen und Prompts gibt es keine Überschneidung zwischen Training und Entwicklung. Eine zusätzliche begrenzte Suche nach nahen Dubletten fand keine Treffer; das ist keine vollständige semantische Kontaminationsprüfung.

## Fester Vergleich

- Architektur: 27.294.208 Parameter (512 Dimensionen, 6 Schichten, 8 Köpfe, Hidden 1.368) gegen 97.536.768 Parameter (768, 12, 12, 2.048). Beide Float32, Kontext 1.024, Batchgröße 2, kompilierter Trainingsschritt.
- Sampling: gleiche Wahrscheinlichkeit je Fähigkeitsgruppe, darin gleiche Wahrscheinlichkeit je Quelle. Die vorangegangene um SciTail bereinigte 670-Aufgaben-Auswertung ergab Gleichstand; Gruppenbalance bleibt wegen des breiten Lernziels bestehen. Gleiche Auswahlwahrscheinlichkeiten bedeuten nicht gleiche Tokenanteile; tatsächliche Quellen-Tokenzahlen werden mitgeführt.
- AdamW mit Spitzen-Lernrate 3e-4 und 100 Aufwärmschritten. Für diesen Größenvergleich gilt neu eine gemeinsame **tokenbasierte** Kosinuskurve bis 100 Millionen Tokens, danach Untergrenze 3e-5. Dadurch hängt die Lernrate bei gleicher Datenmenge nicht von der Geschwindigkeit der Architektur ab. Das Drei-Stunden-Limit beendet jeden Lauf unabhängig davon. Ohne `--schedule-tokens` bleibt das bisherige Trainerverhalten bestehen.
- Primärer Vergleich: jeweils der **letzte** vollständige Modellstand nach dem Zeitbudget. Beste Entwicklungs-Checkpoints bleiben zusätzlich gespeichert, werden aber nicht nachträglich als primärer Endpunkt gewählt.
- Zusätzliche feste Zwischenstände: jeweils der erste abgeschlossene Trainingsschritt über 10, 20 und 30 Millionen Tokens. Diese kleinen Auswertungs-Snapshots enthalten Gewichte und tatsächliche Token-/Quellen-/Schrittzahlen, keinen Optimizer. Nicht erreichte Zwischenstände werden ausdrücklich übersprungen. Nur beidseitig vorhandene Zwischenstände werden miteinander verglichen.
- Ein Seed und feste Reihenfolge: explorativer Größenvergleich, keine endgültige allgemeine Rangfolge.

## Auswertung und Betrieb

Gemeinsame, vorher eingefrorene Suite: **886 Aufgaben aus 31 Quellen mit eigenen Entwicklungsgruppen**; HotpotQA bleibt wegen geteilter Dokumente ohne eigenen Dev-Split. SciTail-Auswahl: 20 neutral / 12 entailment; WIQA: 4 no effect / 3 less / 2 more. Dazu 85 separate Code-Aufgaben mit Referenzprüfung; nicht bestandene Referenzen werden ausgewiesen und ausgeschlossen. Die externen Abschlusstests bleiben geschlossen.

Alle Endstände und erreichten Token-Zwischenstände werden auf denselben 886 Aufgaben mit freien Antworten und Teacher-Forcing-Loss gemessen. Fähigkeiten werden getrennt ausgewiesen. Die Endstände erhalten zusätzlich ausführbare Code-Tests; WikiSQL wird auf Originaltabellen mit einem separaten SQLite-Ausführungsproxy nachbewertet. Erzählerische Texte und Spider haben keinen vollständigen funktionalen Qualitätsscore. Mehrheitsregeln werden ausschließlich aus Trainingsantworten gelernt.

Leichtgewichtiges Monitoring ist überall aktiv. Der Nutzer meldete reduzierte Leistung zur Geräuschbegrenzung; Systemeinstellungen werden nicht geändert. `pmset`-Momentaufnahmen werden vor jedem Training gespeichert. Gemessen werden Zeit, Tokens und Speicher; weder Energieverbrauch noch freie GPU-Kapazität werden daraus abgeleitet.

Die drei Stunden beginnen bei Startfreigabe jeder Trainingsstufe; Initialisierung, Trainer-Datenprüfung, Validierung und Zwischenstände zählen dazu. Abschließendes Checkpoint-Schreiben hat eine kurze separate Aufräumfrist. Nachgelagerte Auswertungen sind auf jeweils 900 Sekunden begrenzt und kommen zum Trainingsbudget hinzu. GPU-Arbeit läuft seriell unter der gemeinsamen Prozesssperre. Schlafen des Rechners wird während der Kampagne durch `caffeinate` verhindert.

## Artefakte und Steuerung

- Kampagne: `runs/size-campaign-2026-09-08/`; eingefrorener Plan, Datei-Hashes, Zeitfristen und Fortschritt.
- Trainingsläufe: `runs/size-27m-2026-09-08-3h/` und `runs/size-97m-2026-09-08-3h/`.
- Daten-Audit: `data/v4-broad-corrected-2026-09-08/audit.json`.
- Auswertungsvorbereitung: `runs/size-eval-preparation-2026-09-08/`.
- Funktionsprüfung: `runs/size-preflight-2026-09-08/` (12 Schritte; kein Ergebnis des Größenvergleichs).
- Automatischer Abschluss: `runs/size-campaign-2026-09-08/REPORT.md` und `comparison.json`.

Geordnet stoppen: `touch runs/size-campaign-2026-09-08/STOP`. Der Supervisor beendet den aktuellen Kindprozess und beginnt keine weitere Trainingsstufe. Fehler oder veränderte eingefrorene Eingaben stoppen die Kampagne; ein Wiederaufnehmen vergibt bestehenden Stufen keine neue Drei-Stunden-Frist. Nicht während dieser Kampagne Trainings-, Auswertungs- oder Monitoring-Code ändern.

Code und Startverzeichnis: `/Users/timokruth/Projekte/SLM-evaluation-prep`, Branch `codex/model-size-comparison`. Die ignorierten `data/`- und `runs/`-Verknüpfungen zeigen auf `/Users/timokruth/Projekte/SLM/`; dort liegen die tatsächlichen großen Artefakte. Der kanonische Interpreter ist `/Users/timokruth/Projekte/SLM/.venv/bin/python` (auch für die Sandbox-Code-Auswertung).
