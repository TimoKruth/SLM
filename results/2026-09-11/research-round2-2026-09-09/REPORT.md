# Begrenzte Forschungsrunde

Status: completed

27,3M-Modell ab letztem Sechs-Stunden-Checkpoint. FP32, 32 unveränderte Trainingsquellen. Drei Varianten × zwei Datenreihenfolgen; keine unabhängigen Initialisierungs-Seeds. Je Versuch 3M zusätzliche Tokens, keine automatische Übernahme oder Verlängerung.

Gewichteter Trainingsloss ist zwischen Varianten nicht vergleichbar. Alle Modelle erhalten dieselbe freie Antwortauswertung und denselben Referenz-Antwortloss. Entwicklungsproxies; Code-/SQL-Ausführung und offene Textqualität bleiben unbewertet. Keine Aussage über externe Benchmark-Übertragung oder statistische Signifikanz.

| Variante | Datenreihenfolge | Zusatz-Tokens | Sekunden | Auswahl-Genauigkeit (Familien-Makro) | Antwortloss |
| --- | --- | ---: | ---: | ---: | ---: |
| Ausgangsmodell ohne Zusatztraining | — | 0 | — | 28.78% | 1.4515 |
| baseline | 0 | 3,000,119 | 341.2 | 27.23% | 1.4529 |
| lower-lr | 0 | 3,000,119 | 333.2 | 25.79% | 1.4342 |
| mild-answer-weight | 0 | 3,000,119 | 304.7 | 25.49% | 1.4567 |
| baseline | 1 | 3,000,360 | 323.5 | 29.11% | 1.4509 |
| lower-lr | 1 | 3,000,360 | 317.4 | 28.93% | 1.4311 |
| mild-answer-weight | 1 | 3,000,360 | 313.0 | 27.82% | 1.4525 |

Für Gegenprüfung ausgewählt: lower-lr.
Auswahlkriterium erfüllt: False.
Gegenprüfung bestanden: False.
Bestätigter Kandidat nach beiden Kriterien: False.
Gepaarte Änderungen der Familien-Makrogenauigkeit: [0.016319444444444442, 0.02604166666666663].
Mittlere Antwortloss-Änderung: -0.01757291740854272.
Familienänderungen: {'entailment': 0.0625, 'mathematics': 0.020833333333333332, 'science_and_causality': 0.012500000000000011, 'reading_and_extraction': -0.046875, 'commonsense_and_social': 0.015625, 'dialogue': 0.0625}.
Zusätzliche Gegenprüfung gegen unverändertes Ausgangsmodell: {'accuracy_deltas': [-0.009027777777777746, -0.014236111111111116], 'answer_loss_deltas': [-0.030811951921787095, -0.02529648056486633], 'passed': False}.

Die Auswahl- und Gegenprüfungsaufgaben sind gruppengetrennt. Die Gegenprüfung schließt historische 886er-Aufgabengruppen aus, kann aber früheren Inline-Dev-Loss beeinflusst haben. Abdeckung: suite-audit.json. Jede Auswertung enthält Resultate je Aufgabe und Fähigkeitsbereich.

Zeitbudget: maximal 60 Minuten ab Kampagnenstart einschließlich Kontrollen, Kompilierung, Speicherung und GPU-Auswertung. Die Frist wird nicht erneuert. Vollständige Prozesshistorie und Fehler: status.json.
