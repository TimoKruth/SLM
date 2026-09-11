# Langer 2×2-Vergleich

Status: completed; Phase: finished

Interne Aufgaben, zwei Datenreihenfolgen desselben Elternmodells. Keine externe Transfer- oder Signifikanzbehauptung.
CPU-EvoNN-Überlappung und Leistungsmodus gehören zu den Betriebsbedingungen; gleiche Zeit bedeutet nicht gleiche Tokens.

| Lauf | Status | Zusätzliche Tokens | Gemessene aktive Sekunden |
| --- | --- | ---: | ---: |
| long-horizon-r0-A | completed | 140636884 | 7140.2 |
| long-horizon-r0-B | completed | 138292364 | 7140.1 |
| long-horizon-r0-C | completed | 139545075 | 7140.1 |
| long-horizon-r0-D | completed | 106375001 | 7139.0 |
| long-horizon-r1-D | completed | 82866896 | 7140.2 |
| long-horizon-r1-C | completed | 76081800 | 7140.2 |
| long-horizon-r1-B | completed | 76540399 | 7140.2 |
| long-horizon-r1-A | completed | 76165841 | 7140.2 |

## Qualität

| Seedfolge | Bedingung | Endpunkt | Genauigkeit | Antwortloss |
| --- | --- | --- | ---: | ---: |
| 0 | A | 15M | 29.33% | 1.4495 |
| 0 | A | 50M | 25.35% | 1.4418 |
| 0 | A | final_search | 26.00% | 1.4675 |
| 0 | A | final_confirmation | 26.94% | 1.4248 |
| 0 | B | 15M | 26.94% | 1.4276 |
| 0 | B | 50M | 25.06% | 1.4092 |
| 0 | B | final_search | 23.31% | 1.3951 |
| 0 | B | final_confirmation | 24.97% | 1.3871 |
| 0 | C | 15M | 29.73% | 1.4317 |
| 0 | C | 50M | 27.54% | 1.4210 |
| 0 | C | final_search | 27.86% | 1.4470 |
| 0 | C | final_confirmation | 28.89% | 1.4181 |
| 0 | D | 15M | 28.17% | 1.4092 |
| 0 | D | 50M | 28.10% | 1.3976 |
| 0 | D | final_search | 25.86% | 1.3954 |
| 0 | D | final_confirmation | 29.44% | 1.3968 |
| 1 | D | 15M | 27.74% | 1.4098 |
| 1 | D | 50M | 29.87% | 1.3903 |
| 1 | D | final_search | 26.98% | 1.3989 |
| 1 | D | final_confirmation | 22.99% | 1.4104 |
| 1 | C | 15M | 28.25% | 1.4356 |
| 1 | C | 50M | 28.95% | 1.4285 |
| 1 | C | final_search | 23.85% | 1.4429 |
| 1 | C | final_confirmation | 26.49% | 1.4219 |
| 1 | B | 15M | 27.47% | 1.4235 |
| 1 | B | 50M | 28.43% | 1.4048 |
| 1 | B | final_search | 26.32% | 1.4186 |
| 1 | B | final_confirmation | 18.54% | 1.4163 |
| 1 | A | 15M | 27.07% | 1.4594 |
| 1 | A | 50M | 31.57% | 1.4513 |
| 1 | A | final_search | 25.41% | 1.4691 |
| 1 | A | final_confirmation | 30.83% | 1.4375 |

Alle direkten Kontraste und Wechselwirkungen: contrasts.json. Fehlende Zeit-/Tokenstände werden nicht imputiert. Keine automatische Modellübernahme.
