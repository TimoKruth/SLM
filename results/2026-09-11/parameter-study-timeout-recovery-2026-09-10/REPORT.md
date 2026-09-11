# Systematische Parameterstudie (24h-Budget)

Status: completed; Phase: finished

Gültig ausgewertete Läufe: 118. Alle fehlenden oder fehlgeschlagenen Läufe bleiben unbewertet.
Vergleiche gelten nur für die gemessenen Stufen, Trainingsdauer und Ausgangsmodelle. Zwei Datenreihenfolgen sind keine unabhängigen Initialisierungen. Der Architekturblock hat zwei neue Initialisierungen je Konfiguration. Keine Signifikanz- oder externe Transferbehauptung.
Referenz-Antwortloss wird über alle Quellen gemittelt. Generative Genauigkeit ist das Familien-Makro der bewertbaren Quellen; funktionale Code-/SQL- und offene Textqualität sind hier nicht umfassend bewertet.

| Phase / Variante | Wiederholung | Parameter | Tokens | Sekunden | Tokens/s | GPU-Spitze (GB) | Genauigkeit | Antwortloss |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Unverändertes Elternmodell | — | 27294208 | 0 | — | — | — | 28.78% | 1.4515 |
| adaptation / answer-only | 0 | 27294208 | 1500699 | 149.3 | 10051 | 2.47 | 22.59% | 1.4865 |
| adaptation / answer_weight-0.5 | 0 | 27294208 | 1500699 | 144.6 | 10378 | 2.47 | 28.89% | 1.4516 |
| adaptation / answer_weight-2.0 | 0 | 27294208 | 1500699 | 141.4 | 10611 | 2.47 | 27.46% | 1.4531 |
| adaptation / answer_weight-4.0 | 0 | 27294208 | 1500699 | 140.8 | 10661 | 2.47 | 26.11% | 1.4547 |
| adaptation / baseline | 0 | 27294208 | 1500699 | 148.2 | 10128 | 2.47 | 28.54% | 1.4512 |
| adaptation / beta1-0.8 | 0 | 27294208 | 1500699 | 141.1 | 10634 | 2.47 | 28.59% | 1.4557 |
| adaptation / beta1-0.95 | 0 | 27294208 | 1500699 | 138.3 | 10854 | 2.47 | 28.56% | 1.4437 |
| adaptation / beta2-0.9 | 0 | 27294208 | 1500699 | 139.8 | 10737 | 2.47 | 27.70% | 1.4814 |
| adaptation / beta2-0.99 | 0 | 27294208 | 1500699 | 137.6 | 10905 | 2.47 | 28.45% | 1.4234 |
| adaptation / boost-commonsense_and_social | 0 | 27294208 | 1500348 | 138.5 | 10834 | 2.47 | 27.80% | 1.4573 |
| adaptation / boost-dialogue | 0 | 27294208 | 1500699 | 150.1 | 9997 | 2.47 | 25.12% | 1.4577 |
| adaptation / boost-entailment | 0 | 27294208 | 1501485 | 139.5 | 10760 | 2.47 | 28.48% | 1.4558 |
| adaptation / boost-mathematics | 0 | 27294208 | 1500044 | 152.3 | 9848 | 2.47 | 28.52% | 1.4590 |
| adaptation / boost-programming_and_queries | 0 | 27294208 | 1501388 | 151.6 | 9903 | 2.47 | 27.25% | 1.4483 |
| adaptation / boost-reading_and_extraction | 0 | 27294208 | 1500353 | 138.6 | 10821 | 2.47 | 24.71% | 1.4596 |
| adaptation / boost-science_and_causality | 0 | 27294208 | 1501328 | 151.6 | 9902 | 2.47 | 24.31% | 1.4582 |
| adaptation / clip-0.0 | 0 | 27294208 | 1500699 | 139.3 | 10772 | 2.48 | 28.11% | 1.4532 |
| adaptation / clip-0.5 | 0 | 27294208 | 1500699 | 140.8 | 10658 | 2.47 | 28.54% | 1.4501 |
| adaptation / clip-2.0 | 0 | 27294208 | 1500699 | 140.5 | 10681 | 2.47 | 28.36% | 1.4520 |
| adaptation / context-1024-eligible-512 | 0 | 27294208 | 1500285 | 137.8 | 10888 | 2.47 | 26.68% | 1.4543 |
| adaptation / context-2048-eligible-512 | 0 | 27294208 | 1500241 | 168.3 | 8916 | 4.90 | 26.55% | 1.4755 |
| adaptation / context-512-eligible-512 | 0 | 27294208 | 1500826 | 157.4 | 9535 | 1.91 | 24.79% | 1.5349 |
| adaptation / effective-batch-4 | 0 | 27294208 | 1500699 | 138.8 | 10808 | 3.93 | 29.35% | 1.4226 |
| adaptation / effective-batch-8 | 0 | 27294208 | 1504153 | 134.2 | 11208 | 6.54 | 28.76% | 1.4182 |
| adaptation / eps-1e-06 | 0 | 27294208 | 1500699 | 140.7 | 10669 | 2.47 | 27.87% | 1.4443 |
| adaptation / execution-eager | 0 | 27294208 | 1500699 | 166.5 | 9015 | 2.61 | 28.54% | 1.4512 |
| adaptation / lr-0.0001 | 0 | 27294208 | 1500699 | 138.1 | 10869 | 2.47 | 22.59% | 1.5534 |
| adaptation / lr-1e-05 | 0 | 27294208 | 1500699 | 138.2 | 10862 | 2.47 | 26.16% | 1.4305 |
| adaptation / lr-3e-06 | 0 | 27294208 | 1500699 | 138.4 | 10841 | 2.47 | 26.80% | 1.4343 |
| adaptation / microbatch-1-effective-2 | 0 | 27294208 | 1500699 | 153.5 | 9780 | 2.57 | 28.54% | 1.4512 |
| adaptation / microbatch-4-effective-4 | 0 | 27294208 | 1500699 | 134.8 | 11130 | 4.03 | 29.35% | 1.4226 |
| adaptation / mixture-sources | 0 | 27294208 | 1501139 | 137.1 | 10947 | 2.47 | 29.06% | 1.4420 |
| adaptation / precision-bf16 | 0 | 27294208 | 1500699 | 108.5 | 13831 | 1.82 | 28.54% | 1.4510 |
| adaptation / reset_optimizer-True | 0 | 27294208 | 1500699 | 137.5 | 10914 | 2.47 | 28.02% | 1.4573 |
| adaptation / schedule-cosine | 0 | 27294208 | 1500699 | 151.5 | 9905 | 2.47 | 28.48% | 1.4343 |
| adaptation / weight_decay-0.0 | 0 | 27294208 | 1500699 | 145.7 | 10297 | 2.47 | 28.54% | 1.4502 |
| adaptation / weight_decay-0.3 | 0 | 27294208 | 1500699 | 148.2 | 10127 | 2.47 | 28.22% | 1.4535 |
| adaptation / answer-only | 1 | 27294208 | 1500108 | 149.7 | 10022 | 2.47 | 26.43% | 1.5091 |
| adaptation / answer_weight-0.5 | 1 | 27294208 | 1500108 | 144.3 | 10394 | 2.47 | 22.42% | 1.4556 |
| adaptation / answer_weight-2.0 | 1 | 27294208 | 1500108 | 161.4 | 9293 | 2.47 | 26.76% | 1.4609 |
| adaptation / answer_weight-4.0 | 1 | 27294208 | 1500108 | 142.4 | 10534 | 2.47 | 29.03% | 1.4695 |
| adaptation / baseline | 1 | 27294208 | 1500108 | 153.0 | 9803 | 2.47 | 24.35% | 1.4559 |
| adaptation / beta1-0.8 | 1 | 27294208 | 1500108 | 140.2 | 10696 | 2.47 | 23.92% | 1.4589 |
| adaptation / beta1-0.95 | 1 | 27294208 | 1500108 | 136.5 | 10988 | 2.47 | 24.33% | 1.4490 |
| adaptation / beta2-0.9 | 1 | 27294208 | 1500108 | 140.8 | 10653 | 2.47 | 23.57% | 1.4860 |
| adaptation / beta2-0.99 | 1 | 27294208 | 1500108 | 147.0 | 10204 | 2.47 | 25.61% | 1.4306 |
| adaptation / boost-commonsense_and_social | 1 | 27294208 | 1501665 | 139.9 | 10737 | 2.47 | 28.26% | 1.4535 |
| adaptation / boost-dialogue | 1 | 27294208 | 1500168 | 139.1 | 10784 | 2.47 | 29.64% | 1.4553 |
| adaptation / boost-entailment | 1 | 27294208 | 1500214 | 139.6 | 10747 | 2.47 | 25.52% | 1.4613 |
| adaptation / boost-mathematics | 1 | 27294208 | 1501112 | 146.4 | 10256 | 2.47 | 25.24% | 1.4542 |
| adaptation / boost-programming_and_queries | 1 | 27294208 | 1500844 | 138.1 | 10869 | 2.47 | 27.40% | 1.4502 |
| adaptation / boost-reading_and_extraction | 1 | 27294208 | 1500472 | 142.3 | 10543 | 2.47 | 26.50% | 1.4523 |
| adaptation / boost-science_and_causality | 1 | 27294208 | 1501385 | 144.8 | 10370 | 2.47 | 26.88% | 1.4582 |
| adaptation / clip-0.0 | 1 | 27294208 | 1500108 | 137.7 | 10893 | 2.48 | 23.89% | 1.4584 |
| adaptation / clip-0.5 | 1 | 27294208 | 1500108 | 137.3 | 10926 | 2.47 | 24.35% | 1.4555 |
| adaptation / clip-2.0 | 1 | 27294208 | 1500108 | 143.5 | 10457 | 2.47 | 24.00% | 1.4568 |
| adaptation / context-1024-eligible-512 | 1 | 27294208 | 1501503 | 138.2 | 10861 | 2.47 | 27.92% | 1.4566 |
| adaptation / context-2048-eligible-512 | 1 | 27294208 | 1501709 | 159.5 | 9417 | 4.90 | 26.65% | 1.4869 |
| adaptation / context-512-eligible-512 | 1 | 27294208 | 1500734 | 159.1 | 9430 | 1.91 | 26.26% | 1.5539 |
| adaptation / effective-batch-4 | 1 | 27294208 | 1500108 | 142.0 | 10567 | 3.93 | 24.86% | 1.4282 |
| adaptation / effective-batch-8 | 1 | 27294208 | 1500108 | 134.2 | 11180 | 6.54 | 27.35% | 1.4220 |
| adaptation / eps-1e-06 | 1 | 27294208 | 1500108 | 140.1 | 10710 | 2.47 | 24.35% | 1.4517 |
| adaptation / execution-eager | 1 | 27294208 | 1500108 | 177.5 | 8449 | 2.61 | 24.35% | 1.4559 |
| adaptation / lr-0.0001 | 1 | 27294208 | 1500108 | 144.7 | 10369 | 2.47 | 27.92% | 1.5623 |
| adaptation / lr-1e-05 | 1 | 27294208 | 1500108 | 138.5 | 10833 | 2.56 | 25.81% | 1.4363 |
| adaptation / lr-3e-06 | 1 | 27294208 | 1500108 | 160.6 | 9343 | 2.47 | 26.87% | 1.4368 |
| adaptation / microbatch-1-effective-2 | 1 | 27294208 | 1500108 | 179.2 | 8369 | 2.57 | 24.35% | 1.4559 |
| adaptation / microbatch-4-effective-4 | 1 | 27294208 | 1500108 | 136.1 | 11025 | 4.03 | 24.86% | 1.4282 |
| adaptation / mixture-sources | 1 | 27294208 | 1501480 | 140.7 | 10673 | 2.47 | 29.51% | 1.4577 |
| adaptation / precision-bf16 | 1 | 27294208 | 1500108 | 110.0 | 13633 | 1.82 | 24.00% | 1.4568 |
| adaptation / reset_optimizer-True | 1 | 27294208 | 1500108 | 137.4 | 10918 | 2.47 | 24.41% | 1.4632 |
| adaptation / schedule-cosine | 1 | 27294208 | 1500108 | 137.8 | 10887 | 2.47 | 26.29% | 1.4392 |
| adaptation / weight_decay-0.0 | 1 | 27294208 | 1500108 | 138.6 | 10826 | 2.47 | 24.35% | 1.4543 |
| adaptation / weight_decay-0.3 | 1 | 27294208 | 1500108 | 137.6 | 10903 | 2.47 | 23.31% | 1.4592 |
| cold / cold-97m | 0 | 97536768 | 3001771 | 857.8 | 3499 | 5.47 | 13.23% | 3.0859 |
| cold / cold-baseline | 0 | 27294208 | 3001771 | 273.9 | 10958 | 2.47 | 13.76% | 3.0974 |
| cold / cold-bias-correction-off | 0 | 27294208 | 3001771 | 286.8 | 10466 | 2.47 | 14.65% | 3.0956 |
| cold / cold-dim-384 | 0 | 19291008 | 3001771 | 224.9 | 13345 | 2.51 | 13.46% | 3.1425 |
| cold / cold-dim-640 | 0 | 36083840 | 3001771 | 359.3 | 8354 | 2.69 | 12.14% | 3.1142 |
| cold / cold-heads-4 | 0 | 27294208 | 3001771 | 261.1 | 11496 | 2.51 | 13.16% | 3.1013 |
| cold / cold-hidden-1024 | 0 | 24123904 | 3001771 | 280.1 | 10716 | 2.49 | 11.97% | 3.1140 |
| cold / cold-hidden-2048 | 0 | 33561088 | 3001771 | 315.2 | 9524 | 2.76 | 15.10% | 3.1135 |
| cold / cold-init-std-001 | 0 | 27294208 | 3001771 | 298.2 | 10065 | 2.47 | 13.42% | 3.2241 |
| cold / cold-layers-4 | 0 | 20992512 | 3001771 | 215.3 | 13941 | 2.06 | 13.43% | 3.1139 |
| cold / cold-layers-8 | 0 | 33595904 | 3001771 | 358.7 | 8369 | 2.88 | 13.01% | 3.1012 |
| cold / cold-no-warmup | 0 | 27294208 | 3001771 | 275.0 | 10915 | 2.47 | 13.23% | 3.1120 |
| cold / cold-97m | 1 | 97536768 | 3000589 | 856.7 | 3503 | 5.47 | 10.23% | 3.1285 |
| cold / cold-baseline | 1 | 27294208 | 3000589 | 296.3 | 10127 | 2.47 | 10.48% | 3.1387 |
| cold / cold-bias-correction-off | 1 | 27294208 | 3000589 | 290.8 | 10318 | 2.47 | 9.14% | 3.1606 |
| cold / cold-dim-384 | 1 | 19291008 | 3000589 | 245.8 | 12209 | 2.51 | 10.57% | 3.1819 |
| cold / cold-dim-640 | 1 | 36083840 | 3000589 | 378.1 | 7937 | 2.70 | 8.46% | 3.1287 |
| cold / cold-heads-4 | 1 | 27294208 | 3000589 | 255.4 | 11749 | 2.51 | 9.49% | 3.1545 |
| cold / cold-hidden-1024 | 1 | 24123904 | 3000589 | 254.7 | 11781 | 2.49 | 10.98% | 3.1347 |
| cold / cold-hidden-2048 | 1 | 33561088 | 3000589 | 339.9 | 8828 | 2.76 | 8.69% | 3.1406 |
| cold / cold-init-std-001 | 1 | 27294208 | 3000589 | 274.5 | 10930 | 2.47 | 8.54% | 3.2422 |
| cold / cold-layers-4 | 1 | 20992512 | 3000589 | 204.9 | 14645 | 2.06 | 9.14% | 3.1209 |
| cold / cold-layers-8 | 1 | 33595904 | 3000589 | 365.4 | 8211 | 2.88 | 9.11% | 3.1750 |
| cold / cold-no-warmup | 1 | 27294208 | 3000589 | 290.7 | 10321 | 2.47 | 8.05% | 3.1362 |
| interaction / factorial-00 | 0 | 27294208 | 1501720 | 151.6 | 9903 | 2.47 | 28.49% | 1.4379 |
| interaction / factorial-01 | 0 | 27294208 | 1501720 | 139.5 | 10765 | 2.47 | 28.49% | 1.4384 |
| interaction / factorial-02 | 0 | 27294208 | 1501720 | 139.0 | 10806 | 2.47 | 28.00% | 1.4368 |
| interaction / factorial-03 | 0 | 27294208 | 1501720 | 140.2 | 10711 | 2.47 | 28.00% | 1.4372 |
| interaction / factorial-04 | 0 | 27294208 | 1501720 | 150.7 | 9966 | 2.47 | 27.48% | 1.4650 |
| interaction / factorial-05 | 0 | 27294208 | 1501720 | 138.8 | 10819 | 2.47 | 27.13% | 1.4663 |
| interaction / factorial-06 | 0 | 27294208 | 1501720 | 139.4 | 10774 | 2.47 | 25.57% | 1.4695 |
| interaction / factorial-07 | 0 | 27294208 | 1501720 | 139.4 | 10776 | 2.47 | 25.57% | 1.4707 |
| interaction / factorial-00 | 1 | 27294208 | 1501402 | 139.3 | 10781 | 2.47 | 27.70% | 1.4406 |
| interaction / factorial-01 | 1 | 27294208 | 1501402 | 142.1 | 10565 | 2.47 | 27.70% | 1.4411 |
| interaction / factorial-02 | 1 | 27294208 | 1501402 | 146.7 | 10236 | 2.47 | 25.77% | 1.4419 |
| interaction / factorial-03 | 1 | 27294208 | 1501402 | 137.9 | 10891 | 2.47 | 26.12% | 1.4424 |
| interaction / factorial-04 | 1 | 27294208 | 1501402 | 139.3 | 10781 | 2.47 | 26.90% | 1.4664 |
| interaction / factorial-05 | 1 | 27294208 | 1501402 | 139.9 | 10733 | 2.47 | 26.90% | 1.4676 |
| interaction / factorial-06 | 1 | 27294208 | 1501402 | 138.3 | 10858 | 2.47 | 25.37% | 1.4699 |
| interaction / factorial-07 | 1 | 27294208 | 1501402 | 138.3 | 10853 | 2.47 | 25.17% | 1.4708 |
| long / baseline | 0 | 27294208 | 15000390 | 1441.9 | 10403 | 2.47 | 26.93% | 1.4594 |
| long / mixture-sources | 0 | 27294208 | 15001498 | 1479.4 | 10141 | 2.47 | 29.57% | 1.4097 |
| long / baseline | 1 | 27294208 | 15000555 | 1442.7 | 10398 | 2.47 | 24.12% | 1.4565 |
| long / mixture-sources | 1 | 27294208 | 15000273 | 1416.7 | 10589 | 2.47 | 28.03% | 1.4106 |

## Gepaarte Effekte

| Vergleich | Genauigkeitsänderung je Wiederholung (pp) | Mittlere Antwortloss-Änderung |
| --- | --- | ---: |
| adaptation:answer-only gegen baseline | -5.95, +2.08 | +0.0442 |
| adaptation:answer_weight-0.5 gegen baseline | +0.35, -1.93 | +0.0000 |
| adaptation:answer_weight-2.0 gegen baseline | -1.08, +2.41 | +0.0034 |
| adaptation:answer_weight-4.0 gegen baseline | -2.43, +4.68 | +0.0086 |
| adaptation:beta1-0.8 gegen baseline | +0.05, -0.43 | +0.0037 |
| adaptation:beta1-0.95 gegen baseline | +0.02, -0.02 | -0.0072 |
| adaptation:beta2-0.9 gegen baseline | -0.84, -0.78 | +0.0302 |
| adaptation:beta2-0.99 gegen baseline | -0.09, +1.26 | -0.0266 |
| adaptation:boost-commonsense_and_social gegen baseline | -0.74, +3.91 | +0.0019 |
| adaptation:boost-dialogue gegen baseline | -3.41, +5.29 | +0.0030 |
| adaptation:boost-entailment gegen baseline | -0.06, +1.17 | +0.0050 |
| adaptation:boost-mathematics gegen baseline | -0.02, +0.89 | +0.0030 |
| adaptation:boost-programming_and_queries gegen baseline | -1.29, +3.05 | -0.0043 |
| adaptation:boost-reading_and_extraction gegen baseline | -3.83, +2.15 | +0.0024 |
| adaptation:boost-science_and_causality gegen baseline | -4.23, +2.53 | +0.0047 |
| adaptation:clip-0.0 gegen baseline | -0.43, -0.46 | +0.0023 |
| adaptation:clip-0.5 gegen baseline | +0.00, +0.00 | -0.0008 |
| adaptation:clip-2.0 gegen baseline | -0.17, -0.35 | +0.0009 |
| adaptation:context-2048-eligible-512 gegen context-1024-eligible-512 | -0.14, -1.27 | +0.0257 |
| adaptation:context-512-eligible-512 gegen context-1024-eligible-512 | -1.90, -1.67 | +0.0890 |
| adaptation:effective-batch-4 gegen baseline | +0.81, +0.50 | -0.0281 |
| adaptation:effective-batch-8 gegen baseline | +0.22, +3.00 | -0.0334 |
| adaptation:eps-1e-06 gegen baseline | -0.67, +0.00 | -0.0055 |
| adaptation:execution-eager gegen baseline | +0.00, +0.00 | -0.0000 |
| adaptation:lr-0.0001 gegen baseline | -5.94, +3.57 | +0.1043 |
| adaptation:lr-1e-05 gegen baseline | -2.38, +1.46 | -0.0201 |
| adaptation:lr-3e-06 gegen baseline | -1.74, +2.52 | -0.0180 |
| adaptation:microbatch-1-effective-2 gegen baseline | +0.00, +0.00 | -0.0000 |
| adaptation:microbatch-4-effective-4 gegen baseline | +0.81, +0.50 | -0.0281 |
| adaptation:mixture-sources gegen baseline | +0.52, +5.16 | -0.0037 |
| adaptation:precision-bf16 gegen baseline | +0.00, -0.35 | +0.0004 |
| adaptation:reset_optimizer-True gegen baseline | -0.52, +0.06 | +0.0067 |
| adaptation:schedule-cosine gegen baseline | -0.05, +1.94 | -0.0168 |
| adaptation:weight_decay-0.0 gegen baseline | +0.00, +0.00 | -0.0013 |
| adaptation:weight_decay-0.3 gegen baseline | -0.32, -1.04 | +0.0028 |
| cold:cold-97m gegen cold-baseline | -0.53, -0.25 | -0.0109 |
| cold:cold-bias-correction-off gegen cold-baseline | +0.89, -1.34 | +0.0100 |
| cold:cold-dim-384 gegen cold-baseline | -0.30, +0.09 | +0.0441 |
| cold:cold-dim-640 gegen cold-baseline | -1.61, -2.02 | +0.0034 |
| cold:cold-heads-4 gegen cold-baseline | -0.60, -0.99 | +0.0099 |
| cold:cold-hidden-1024 gegen cold-baseline | -1.79, +0.50 | +0.0063 |
| cold:cold-hidden-2048 gegen cold-baseline | +1.34, -1.79 | +0.0090 |
| cold:cold-init-std-001 gegen cold-baseline | -0.33, -1.93 | +0.1151 |
| cold:cold-layers-4 gegen cold-baseline | -0.32, -1.34 | -0.0006 |
| cold:cold-layers-8 gegen cold-baseline | -0.74, -1.36 | +0.0201 |
| cold:cold-no-warmup gegen cold-baseline | -0.53, -2.43 | +0.0060 |
| long:mixture-sources gegen baseline | +2.64, +3.91 | -0.0478 |

Details je Fähigkeitsgruppe und Durchsatz: effects.json; vollständige 2×2×2-Wechselwirkungen: interactions.json.
Gepaarte Lernkurve derselben langen Trajektorien bei 1,5M/15M Zusatz-Tokens: duration-effects.json.
Kontextvergleiche verwenden dieselben auf 512 Tokens begrenzten Originalbeispiele, ändern aber deren Packung. Größere globale Batches ändern Zahl der Updates und Token-Überschuss am Endpunkt. Architekturvergleiche ändern teilweise zugleich die Parameterzahl; keine isolierte Kapazitätsaussage.

Auswahl für längere Prüfung: {'contender': 'mixture-sources', 'search_passed': False, 'contrast': {'accuracy_deltas': [0.005249669312169358, 0.0515873015873016], 'mean_accuracy_delta': 0.02841848544973548, 'family_deltas': {'entailment': 0.07291666666666669, 'mathematics': 0.0, 'science_and_causality': -0.01438492063492064, 'reading_and_extraction': -0.02083333333333333, 'commonsense_and_social': 0.0390625, 'dialogue': 0.09375}, 'mean_answer_loss_delta': -0.0036818523221570088, 'passes_screen': False, 'reference': 'baseline', 'phase': 'adaptation', 'block': 'adaptation', 'speed_ratios': [1.0808625588784846, 1.0887992505564434], 'parent_guard': {'accuracy_deltas': [0.0028521825396825573, 0.007316468253968256], 'answer_loss_deltas': [-0.009447205246373436, 0.0062579754577059], 'passed': False}}, 'criterion': 'Among completed adaptation (not context/cold) variants, require both paired accuracy gains >=2pp, no average family decline >5pp, and no loss/accuracy decline against unchanged parent in either repetition. Rank passing status then mean accuracy gain then reference answer loss. Even if none passes, take best exploratory contender into paired 15M-token replication. Long confirmation uses fresh groups, two new data seeds and unchanged-parent control; never auto-adopt.', 'selected_before_confirmation': True}

Längere Gegenprüfung: {'accuracy_deltas': [0.01736111111111116, 0.009722222222222243], 'mean_accuracy_delta': 0.013541666666666702, 'family_deltas': {'entailment': 0.020833333333333315, 'mathematics': -0.020833333333333332, 'science_and_causality': 0.11250000000000002, 'reading_and_extraction': 0.0, 'commonsense_and_social': 0.03125, 'dialogue': -0.0625}, 'mean_answer_loss_delta': -0.020562104837445028, 'passes_screen': False, 'parent_guard': {'accuracy_deltas': [0.014236111111111116, 0.044791666666666674], 'answer_loss_deltas': [-0.01678177650435808, -0.03008763788617208], 'passed': True}, 'confirmed_candidate': False, 'contender': 'mixture-sources'}

## Noch nicht untersucht

- tokenizer_vocab: Needs separate train-only tokenizer/data-version audit and common-example/byte comparison; not varied in this campaign.
- optimizer_family: AdamW only; WD=0 tests Adam-like decay removal, not a tuned comparison to SGD/Muon.
- architecture_components: Activation/norm/RoPE/dropout/tied embeddings remain fixed; not inferred from size variations.
- decode_settings: Evaluation protocol held fixed; no tuning on reference answers.
- system_power: User noise-limited power setting preserved, not a tuning factor.
- io_cadence: Existing light monitoring/checkpoint policy held fixed for comparisons.

Kein automatischer Modellwechsel oder weiterer Lauf nach Budgetende. Ein STOP im Kampagnenverzeichnis beendet die Arbeit.
