# Vergleich auf 886 Entwicklungsaufgaben

Originale Benchmark-Aufgaben aus 31 Quellen; intern zurückgehalten, keine selbst erzeugten Aufgaben. Prompts wurden vereinheitlicht. 843 Aufgaben sind gegenüber der bisherigen kleinen Auswahl neu, 43 überlappen. Die Entwicklungsdaten dienten bereits zur Checkpoint-Auswahl; kein unabhängiger Abschlusstest.

| Messung | Fähigkeitsbereiche gleich | Quellen gleich |
| --- | ---: | ---: |
| correct | 133 | 133 |
| scored | 702 | 702 |
| generated | 886 | 886 |
| token_limit | 92 | 136 |

| Fähigkeitsbereich | Bereiche gleich | Quellen gleich |
| --- | ---: | ---: |
| entailment | 65.6% | 57.3% |
| mathematics | 1.0% | 1.0% |
| science_and_causality | 17.1% | 20.4% |
| reading_and_extraction | 12.7% | 13.7% |
| commonsense_and_social | 15.6% | 17.2% |
| dialogue | 6.2% | 12.5% |

Gepaarter Vergleich: 47 nur vom Quellenmodell richtig, 47 nur vom Bereichsmodell richtig. Exploratives McNemar-p=1.0000; keine Aussage über unabhängigen Transfer oder mehrere Seeds.

Mehrheitsbaselines aus Trainingsdaten und sämtliche Quellenwerte stehen in `comparison.json`. Offene Antworten und SQL-Funktionalität sind nicht Teil der Gesamtquote.

Bestätigter SciTail-Konvertierungsfehler: 8.472 entails-Beispiele wurden verworfen. Die verbleibenden Aufgaben enthalten nur neutral; 32/32 sind kein Fähigkeitsnachweis. Ohne SciTail erreichen beide Modelle 101/670 = 15,1 %. Korrektur für die nächste Datenversion vorbereitet; historische Daten unverändert.

Die jeweils einzige richtige mathematische Endantwort enthält einen falschen Rechenweg: 90/2=30 beim Bereichsmodell und 12+12=36 beim Quellenmodell. Belege und Herkunft des Datenfehlers: data_quality.json.
