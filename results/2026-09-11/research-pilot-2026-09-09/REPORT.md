# Begrenzte Forschungsrunde

Status: completed

27,3M-Modell ab letztem Sechs-Stunden-Checkpoint. FP32, 32 unveränderte Trainingsquellen. Drei Varianten × zwei Datenreihenfolgen; keine unabhängigen Initialisierungs-Seeds. Je Versuch 3M zusätzliche Tokens, keine automatische Übernahme oder Verlängerung.

Gewichteter Trainingsloss ist zwischen Varianten nicht vergleichbar. Alle Modelle erhalten dieselbe freie Antwortauswertung und denselben Referenz-Antwortloss. Entwicklungsproxies; Code-/SQL-Ausführung und offene Textqualität bleiben unbewertet. Keine Aussage über externe Benchmark-Übertragung oder statistische Signifikanz.

| Variante | Datenreihenfolge | Zusatz-Tokens | Sekunden | Auswahl-Genauigkeit (Familien-Makro) | Antwortloss |
| --- | --- | ---: | ---: | ---: | ---: |
| answer-weight | 0 | 3,000,331 | 278.3 | 27.23% | 1.4301 |
| baseline | 0 | 3,000,331 | 278.8 | 28.84% | 1.4248 |
| higher-lr | 0 | 3,000,331 | 279.1 | 26.12% | 1.5264 |
| answer-weight | 1 | 3,000,086 | 297.7 | 26.12% | 1.4250 |
| baseline | 1 | 3,000,086 | 299.7 | 25.87% | 1.4153 |
| higher-lr | 1 | 3,000,086 | 278.9 | 22.50% | 1.4908 |

Für Gegenprüfung ausgewählt: answer-weight.
Auswahlkriterium erfüllt: False.
Gegenprüfung bestanden: False.
Bestätigter Kandidat nach beiden Kriterien: False.
Gepaarte Änderungen der Familien-Makrogenauigkeit: [-0.03541666666666665, -0.04930555555555555].
Mittlere Antwortloss-Änderung: 0.016996744847856515.
Familienänderungen: {'entailment': -0.041666666666666685, 'mathematics': 0.0, 'science_and_causality': -0.02500000000000001, 'reading_and_extraction': -0.03125, 'commonsense_and_social': -0.03125, 'dialogue': -0.125}.

Die Auswahl- und Gegenprüfungsaufgaben sind gruppengetrennt. Die Gegenprüfung schließt historische 886er-Aufgabengruppen aus, kann aber früheren Inline-Dev-Loss beeinflusst haben. Abdeckung: suite-audit.json. Jede Auswertung enthält Resultate je Aufgabe und Fähigkeitsbereich.

Zeitbudget: maximal 60 Minuten ab Kampagnenstart einschließlich Kontrollen, Kompilierung, Speicherung und GPU-Auswertung. Die Frist wird nicht erneuert. Vollständige Prozesshistorie und Fehler: status.json.
