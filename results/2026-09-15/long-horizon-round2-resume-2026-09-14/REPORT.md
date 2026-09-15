# Langzeitblock 2: Lernrate und Verlauf

Status: completed; Phase: finished

Interne Aufgaben, zwei Datenreihenfolgen desselben Elternmodells. Keine externe Transfer- oder Signifikanzbehauptung.
CPU-EvoNN-Überlappung und Leistungsmodus gehören zu den Betriebsbedingungen; gleiche Zeit bedeutet nicht gleiche Tokens.

| Lauf | Status | Zusätzliche Tokens | Gemessene aktive Sekunden |
| --- | --- | ---: | ---: |
| long-round2-r0-A | completed | 126001643 | 7140.2 |
| long-round2-r0-B | completed | 119759878 | 7140.2 |
| long-round2-r0-C | completed | 111730243 | 7140.1 |
| long-round2-r0-D | completed | 82908374 | 7139.3 |
| long-round2-r1-D | completed | 115507385 | 7140.1 |
| long-round2-r1-C | completed | 97810411 | 7139.3 |
| long-round2-r1-B | completed | 100724130 | 7140.3 |
| long-round2-r1-A | completed | 88126776 | 7140.2 |

## Qualität

| Seedfolge | Bedingung | Endpunkt | Genauigkeit | Antwortloss |
| --- | --- | --- | ---: | ---: |
| 0 | A | 15M | 26.42% | 1.4546 |
| 0 | A | 50M | 27.78% | 1.4466 |
| 0 | A | final_search | 26.49% | 1.4444 |
| 0 | A | final_confirmation | 25.17% | 1.4785 |
| 0 | B | 15M | 28.29% | 1.4279 |
| 0 | B | 50M | 27.84% | 1.4194 |
| 0 | B | final_search | 30.65% | 1.4143 |
| 0 | B | final_confirmation | 21.88% | 1.4586 |
| 0 | C | 15M | 24.09% | 1.5194 |
| 0 | C | 50M | 22.48% | 1.5082 |
| 0 | C | final_search | 23.93% | 1.4631 |
| 0 | C | final_confirmation | 24.86% | 1.5098 |
| 0 | D | 15M | 26.57% | 1.4524 |
| 0 | D | 50M | 29.05% | 1.4361 |
| 0 | D | final_search | 27.62% | 1.4251 |
| 0 | D | final_confirmation | 28.89% | 1.4545 |
| 1 | D | 15M | 28.10% | 1.4485 |
| 1 | D | 50M | 26.25% | 1.4398 |
| 1 | D | final_search | 25.83% | 1.4253 |
| 1 | D | final_confirmation | 24.38% | 1.4562 |
| 1 | C | 15M | 22.95% | 1.5164 |
| 1 | C | 50M | 26.06% | 1.5199 |
| 1 | C | final_search | 23.91% | 1.5136 |
| 1 | C | final_confirmation | 20.90% | 1.5538 |
| 1 | B | 15M | 28.29% | 1.4248 |
| 1 | B | 50M | 27.85% | 1.4230 |
| 1 | B | final_search | 28.73% | 1.4237 |
| 1 | B | final_confirmation | 24.90% | 1.4601 |
| 1 | A | 15M | 28.10% | 1.4503 |
| 1 | A | 50M | 27.40% | 1.4575 |
| 1 | A | final_search | 27.22% | 1.4702 |
| 1 | A | final_confirmation | 27.60% | 1.4853 |

Bedingungen: A = Kontrolle: LR 3e-5 konstant; B = LR 3e-6 konstant; C = LR 1e-4 konstant; D = LR 3e-5, Kosinus bis 3e-6 über 100M zusätzliche Tokens

Vorab festgelegte Kontraste: contrasts.json. Fehlende Zeit-/Tokenstände werden nicht imputiert. Keine automatische Modellübernahme.
