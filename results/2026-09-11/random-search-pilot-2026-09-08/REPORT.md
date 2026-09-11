# Zufallsnetz-Stichprobe vom 8. September 2026

Abgeschlossen in **3.54 Minuten**, einschließlich Aufwärmen, Suche, Kontrollen und Monitoring-Abschluss; Budgetobergrenze 20 Minuten. **256 vollständig neu initialisierte Modelle** mit jeweils 97,536,768 Parametern geprüft. Kein Gewichtstraining innerhalb dieser Stichprobe.

## Gemessener Durchsatz

| Prüfung | Sekunden pro Netz | Netze in drei Stunden |
|---|---:|---:|
| Nur Initialisierung (Median) | 0.0210 | — |
| Initialisierung + 30 Auswahlaufgaben, einschließlich Such-Verwaltung | 0.550 | 19,624 |
| Initialisierung + 854 Referenzaufgaben | 16.85 | 640 |
| 854 freie Antworten, aus 13 Aufgaben hochgerechnet | 931.9 | 11 |

Suchphase: 140.88 Sekunden; 109.0 Kandidaten/Minute. Median der synchronisierten Referenzprüfung allein: 0.510 Sekunden.
Die Drei-Stunden-Zahlen sind serielle Durchsatzprojektionen vor zusätzlichen Abschlusskontrollen, keine Erfolgswahrscheinlichkeiten. Die freie Generierung ist nur eine grobe Hochrechnung aus einer kleinen, nach Fähigkeitsgruppen begrenzten Probe.

## Qualität auf denselben Kontrollen

| Modell | Antwort-Loss auf 30 Kontrollen ↓ | Freie Antworten: korrekt / bewertbar | Tokenlimit / 13 |
|---|---:|---:|---:|
| Erstes Zufallsnetz | 9.7172 | 0 / 11 | 13 / 13 |
| Ausgewähltes Zufallsnetz | 9.5183 | 0 / 11 | 13 / 13 |
| Training: Fähigkeitsgruppen | 1.8953 | 4 / 11 | 2 / 13 |
| Training: Quellen | 1.8058 | 2 / 11 | 3 / 13 |

Auswahl-Loss aller Zufallsnetze: 9.4800 bis 10.2453; Mittelwert 9.8554. Gewinner-Seed: 2026090883. Gleichverteilung über 16.384 Tokens hätte einen Loss von ln(16.384) = 9.7041.

Auf allen 854 passenden Referenzaufgaben: Zufallsgewinner 9.5313, trainiertes Quellenmodell 1.7078. Diese größere Auswertung enthält die Auswahlaufgaben und ist nicht unabhängig.

Die 30 Auswahl- und 30 Kontrollaufgaben wurden vorab gruppengetrennt festgelegt; alle stammen aus Original-Trainingssplits von 30 Benchmark-Quellen. SciTail ist ausgeschlossen. Die freie Antwortprobe umfasst 13 Aufgaben; nicht automatisch bewertbare Aufgaben zählen nicht als falsch. Eine kleine Kontrollprobe kann keine umfassende Fähigkeitseinschätzung liefern.

Teacher Forcing gibt die richtigen vorherigen Antworttokens vor. Ein kleinerer Loss allein belegt keine selbstständige Problemlösung. Die trainierten Checkpoints wurden früher anhand von Entwicklungs-Loss ausgewählt und stammen aus der fehlerhaften SciTail-Datenversion. Der Vergleich ist beschreibend; die externen Abschlusstests werden nicht angefasst.

## Betriebsbedingungen und nächster Versuch

MLX-Spitzenspeicher: 1.035 GB. Kein paralleler SLM-GPU-Lauf; keine Änderung der Leistungseinstellung. Der Nutzer meldete reduzierte Leistung zur Geräuschbegrenzung. Betriebssystemeinstellungen sind als Momentaufnahme in `power-settings.txt` abgelegt. Zeit und Speicher sind keine Messung von Energiebedarf oder GPU-Auslastung.

Der ausgewählte Zufallskandidat erzeugte auf 12 von 13 Aufgaben ausschließlich Leerraum. Seine Loss-Verbesserung liefert damit keinen Nachweis nutzbarer Fähigkeiten. Für diese unabhängige Vollgewichts-Zufallssuche empfehle ich derzeit keinen Drei-Stunden-Lauf; korrigiertes Training hat Vorrang.

Ein größerer Zufallssuchlauf wird nicht automatisch gestartet. Ein Qualitätsvorteil auf den getrennten Kontrollen müsste belastbar bestätigt werden, bevor längeres Neuwürfeln als Lernstrategie begründet wäre. Für einen sauberen neuen Trainingsvergleich müssen zunächst die SciTail-Daten korrigiert und erneut geprüft werden.

Protokoll: `protocol.json`; Einzelkandidaten: `trials.jsonl`; vollständige Kontrollantworten und Referenz-Loss: `controls.json`; Zahlen und Projektionen: `results.json`; Zeitbegrenzung: `supervisor.json`; Monitoring: `performance/`. Methodik und Forschung: `random_search/README.md` im Branch `codex/evaluation-preparation`.
