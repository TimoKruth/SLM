# Modellgröße und längeres Training: 3 → 6 Stunden

Internal development; six hours cumulative active budgets in two sessions, not six uninterrupted wall-clock hours. One seed, fixed order and changed operating time limit causal conclusions.

Je Modell drei zusätzliche Stunden vom letzten vollständigen Endcheckpoint; Modellgewichte, AdamW und Sampler fortgesetzt. Unveränderte FP32-Architektur, Daten und 100M-Token-Lernratenkurve. Keine neuen Daten oder BF16-Optimierung.

| Modell | Tokens vorher | Tokens zusätzlich | Tokens gesamt | Korrekt 3h → 6h | Antwort-Loss 3h → 6h |
|---|---:|---:|---:|---:|---:|
| 27m | 119,011,223 | 126,852,146 | 245,863,369 | 194/702 → 193/702 | 1.472 → 1.445 |
| 97m | 38,476,763 | 38,546,750 | 77,023,513 | 142/702 → 181/702 | 1.679 → 1.441 |

| Fähigkeit | Klein 3h | Klein 6h | Groß 3h | Groß 6h |
|---|---:|---:|---:|---:|
| programming_and_queries | unbewertet | unbewertet | unbewertet | unbewertet |
| mathematics | 2.1% | 2.1% | 2.1% | 2.1% |
| reading_and_extraction | 28.1% | 26.5% | 17.3% | 26.2% |
| commonsense_and_social | 28.9% | 27.3% | 18.0% | 26.6% |
| science_and_causality | 31.2% | 30.3% | 21.7% | 24.4% |
| entailment | 57.3% | 57.3% | 50.0% | 54.2% |
| dialogue | 31.2% | 28.1% | 25.0% | 34.4% |

## 27m

Zusätzliche korrekte Antworten: -1. Tokens/s inklusive Start, Prüfungen und Checkpoints im Zusatzbudget: 11746.
Code bestanden: 0 → 0.
WikiSQL-Ausführungsproxy: {'mismatch': 18, 'match': 14} → {'mismatch': 19, 'match': 13}.
Tokenlimits: 112 → 118.

## 97m

Zusätzliche korrekte Antworten: 39. Tokens/s inklusive Start, Prüfungen und Checkpoints im Zusatzbudget: 3569.
Code bestanden: 0 → 0.
WikiSQL-Ausführungsproxy: {'mismatch': 20, 'match': 11, 'candidate_failed': 1} → {'mismatch': 20, 'match': 12}.
Tokenlimits: 136 → 102.

## Interpretation

Der Zugewinn von Stunde 3 bis 6 wird je Größe separat ausgewiesen. Bei gleichem Zeitbudget bleibt die tatsächlich gesehene Tokenmenge verschieden. Das kleine Modell startet bereits auf der Lernratenuntergrenze 3e-5; das große folgt seiner unveränderten Kurve ab etwa 38,5M Tokens. Der Versuch misst diese konkrete Fortsetzung, nicht eine größenunabhängig optimale Lernrate.
Betriebsbedingungen und PowerWatch-Verlauf ergänzen die Messungen. Die Pause zwischen den Sitzungen ist keine Trainingszeit. Mehrheitsregeln, ausführbare Tests und Quellenergebnisse stehen im JSON. Historische Referenzmängel bleiben dieselben; die interne Suite ist kein externer Transferbeleg.
Keine automatische weitere Verlängerung.
