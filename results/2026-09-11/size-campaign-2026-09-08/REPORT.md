# Größenvergleich: korrigiertes breites Benchmark-Training

Je drei Stunden ab Startfreigabe; Initialisierung, Datenprüfung im Trainer, Validierung und Checkpoints zählen zum Zeitbudget. Auswertungen folgen separat. Gleiche Daten, Sampling, Seed, Kontext, Batchgröße und tokenbasierte Lernratenkurve; Modellgröße und dadurch erreichter Durchsatz unterscheiden sich.

| Modell | Parameter | Trainings-Tokens | Schritte |
|---|---:|---:|
| 27m | 27,294,208 | 119,011,223 | 65,659 |
| 97m | 97,536,768 | 38,476,763 | 21,214 |

## Nach drei Stunden: letzte Modellstände

| Fähigkeit | 27m Genauigkeit / Loss | 97m Genauigkeit / Loss |
|---|---:|---:|
| programming_and_queries | unbewertet / 1.927 | unbewertet / 2.104 |
| mathematics | 2.1% / 2.204 | 2.1% / 2.439 |
| reading_and_extraction | 28.1% / 1.486 | 17.3% / 1.773 |
| commonsense_and_social | 28.9% / 1.919 | 18.0% / 2.188 |
| science_and_causality | 31.2% / 1.113 | 21.7% / 1.301 |
| entailment | 57.3% / 0.140 | 50.0% / 0.149 |
| dialogue | 31.2% / 0.733 | 25.0% / 0.904 |

Genauigkeit ist das Mittel der automatisch bewertbaren Quellen im Bereich; unterschiedliche Metriken bleiben getrennt. Loss nutzt richtige vorherige Antworttokens. Narrative Antworten, SQL und Programmcode werden nicht als normale Antwortgenauigkeit ausgegeben. HotpotQA hat keinen eigenen Entwicklungssplit.

## Vergleich bei ähnlicher Tokenzahl

### Ziel 10,000,000 Tokens

Tatsächlich: [10000674, 10000674]; identische Schritte und Quellen-Tokenzahlen: True.

| Fähigkeit | 27m Genauigkeit / Loss | 97m Genauigkeit / Loss |
|---|---:|---:|
| programming_and_queries | unbewertet / 2.815 | unbewertet / 2.810 |
| mathematics | 0.0% / 3.474 | 0.0% / 3.415 |
| reading_and_extraction | 11.5% / 2.740 | 13.7% / 2.682 |
| commonsense_and_social | 1.6% / 3.281 | 3.1% / 3.271 |
| science_and_causality | 17.5% / 2.160 | 18.4% / 2.140 |
| entailment | 46.9% / 0.171 | 45.8% / 0.164 |
| dialogue | 0.0% / 2.291 | 0.0% / 2.262 |
### Ziel 20,000,000 Tokens

Tatsächlich: [20000377, 20000377]; identische Schritte und Quellen-Tokenzahlen: True.

| Fähigkeit | 27m Genauigkeit / Loss | 97m Genauigkeit / Loss |
|---|---:|---:|
| programming_and_queries | unbewertet / 2.322 | unbewertet / 2.291 |
| mathematics | 1.0% / 2.935 | 0.0% / 2.859 |
| reading_and_extraction | 15.9% / 2.257 | 15.2% / 2.275 |
| commonsense_and_social | 7.8% / 2.639 | 5.5% / 2.693 |
| science_and_causality | 19.7% / 1.727 | 18.8% / 1.720 |
| entailment | 46.9% / 0.164 | 43.8% / 0.169 |
| dialogue | 6.2% / 1.394 | 9.4% / 1.428 |
### Ziel 30,000,000 Tokens

Tatsächlich: [30001624, 30001624]; identische Schritte und Quellen-Tokenzahlen: True.

| Fähigkeit | 27m Genauigkeit / Loss | 97m Genauigkeit / Loss |
|---|---:|---:|
| programming_and_queries | unbewertet / 2.201 | unbewertet / 2.149 |
| mathematics | 0.0% / 2.658 | 1.0% / 2.577 |
| reading_and_extraction | 16.9% / 1.887 | 12.2% / 1.849 |
| commonsense_and_social | 11.7% / 2.381 | 12.5% / 2.290 |
| science_and_causality | 20.4% / 1.510 | 17.7% / 1.456 |
| entailment | 46.9% / 0.154 | 55.2% / 0.152 |
| dialogue | 3.1% / 1.114 | 12.5% / 1.125 |

## Einfache Vergleichswerte und ausführbare Aufgaben

### 27m

| Quelle | Modell korrekt | Trainings-Mehrheitsregel korrekt | Aufgaben |
|---|---:|---:|---:|
| boolq | 23 | 24 | 32 |
| snli | 20 | 12 | 32 |
| wiqa | 5 | 4 | 9 |
| anli | 13 | 12 | 32 |
| scitail | 22 | 20 | 32 |

Code: {'syntax_error': 29, 'runtime_error': 45, 'wrong_answer': 7}; bestanden mit stärkerer Testabdeckung: 0. WikiSQL-Ausführungsdiagnosen: {'mismatch': 18, 'match': 14}.
Leere Antworten: 0; Tokenlimits: 112.

### 97m

| Quelle | Modell korrekt | Trainings-Mehrheitsregel korrekt | Aufgaben |
|---|---:|---:|---:|
| boolq | 24 | 24 | 32 |
| snli | 17 | 12 | 32 |
| wiqa | 3 | 4 | 9 |
| anli | 11 | 12 | 32 |
| scitail | 20 | 20 | 32 |

Code: {'syntax_error': 64, 'runtime_error': 16, 'wrong_answer': 1}; bestanden mit stärkerer Testabdeckung: 0. WikiSQL-Ausführungsdiagnosen: {'mismatch': 20, 'match': 11, 'candidate_failed': 1}.
Leere Antworten: 0; Tokenlimits: 136.

## Grenzen

Ein Seed je Größe und feste Reihenfolge erlauben keine belastbare allgemeine Rangfolge. Die gemeldete reduzierte Leistung bleibt bestehen; tatsächliche Betriebssystemeinstellungen wurden vor jedem Training protokolliert. Stromverbrauch und freie GPU-Kapazität wurden nicht gemessen. Quellenverteilungen, Entwicklungs-Lernkurven und Einzelmetriken stehen in `comparison.json`. SciTail und WIQA stammen hier aus der korrigierten Version; historische Ergebnisse wurden nicht überschrieben.

Keine automatische Verlängerung. Einen längeren Lauf erst anhand von Lernkurven, freier Antwortqualität, Mehrheitsregeln und Ressourcenaufwand auswählen. Externe Abschlusstests bleiben geschlossen.
