# Erkenntnisse und Grenzen – Stand 11. September 2026

Alle geplanten Trainings des letzten Vergleichs sind abgeschlossen. Es läuft keine neue Trainingskampagne. Es wurde kein Kandidat automatisch übernommen. Ziel bleibt ein vielseitiges, von Grund auf nur mit Benchmark-Trainingsmaterial gelerntes Sprachmodell; Coding ist eine mögliche Fähigkeit.

Diese Übersicht verbindet die bisherigen Schlussfolgerungen mit dem [versionierten Ergebnisarchiv](results/2026-09-11/INDEX.md). Dessen Quellen und Prüfsummen stehen in `sources.json`. Vollständige Rohantworten, Pläne, Daten, fehlgeschlagene Versuche, Checkpoints und Leistungsprotokolle liegen zusätzlich in getrennten lokalen ZIP64-Archiven; Umfang und Wiederherstellung beschreibt [SICHERUNG.md](SICHERUNG.md). „Versioniert“ und „extern gesichert“ sind unterschiedliche Aussagen.

## Daten und wissenschaftliche Aussage

- Erster Pilot: zehn Datensätze, 230.474 Trainingspaare und 43.316.110 gespeicherte Tokens; Modell mit 97.536.768 Parametern. Die spätere breite Mischung umfasst 32 Quellen und sieben Fähigkeitsgruppen.
- `data/v3-broad` hatte Konverterfehler: 8.472 SciTail-Beispiele mit `entails` und 9.936 WIQA-Beispiele mit `no_effect` wurden verworfen. Historische Scores dieser Daten dürfen nicht als korrekte Klassenabdeckung gelten. Die alte Version bleibt erhalten.
- Korrigierte auditierte Version: `data/v4-broad-corrected-2026-09-08`, 1.433.943 Trainingspaare aus 32 Quellen. Klassenabbildungen, Rohdatenabgleich und Gruppentrennung geprüft. Details: [MODELLGROESSENVERGLEICH.md](MODELLGROESSENVERGLEICH.md), Audit in den Datenarchiven.
- Eigene Aufgabenadapter und Metriken verwenden Original-Trainingsmaterial bzw. intern abgetrennte Entwicklungsgruppen. Die bisherigen Vergleichsscores sind keine offiziellen Benchmark-Gesamtscores. Gruppengetrennte Gegenprüfungen aus bekannten Quellen sind noch kein Transfer auf neue Benchmark-Familien.
- Die drei vorgesehenen externen Abschlusstests LiveCodeBench, IFBench und BBEH bleiben reserviert. Kein externer Transfernachweis und kein Nachweis eines mittelmäßig funktionierenden Coding-Modells liegen vor.
- TAT-QA und MultiNLI wurden separat als Kandidaten geladen und vorgeprüft, nicht in die 32 aktiven Quellen aufgenommen. Englischer Text, 1024er Kontext und begrenzte Bewertbarkeit schränken das breite Lernziel ein. Details: [BREITES_LERNEN.md](BREITES_LERNEN.md), [NAECHSTER_LAUF.md](NAECHSTER_LAUF.md).

## Frühe Läufe und Kontrollmessungen

Der erste Nachtlauf verarbeitete 94.774.946 Tokens in 6h34m; der beste Entwicklungsloss trat bereits bei 75.096.066 Tokens auf. Syntaktisch plausibler Code bedeutete keine funktionale Lösung: die ausführbare Diagnose des besten Checkpoints ergab 0/81 gelöste Aufgaben, obwohl 65 Ausgaben parsebar waren. Referenzlösungen und stärkere Tests wurden getrennt kontrolliert. Historische Details: [README.md](README.md), [NACHTLAUF.md](NACHTLAUF.md), [LAUF_2.md](LAUF_2.md), [Codebericht](results/2026-09-11/code-eval-2026-09-07/REPORT.md).

Die frühen Familien-/Quellenvergleiche und kleinen Lernkontrollen lieferten kein stabiles breites Qualitätsurteil. Insbesondere die falsche SciTail-Klassenabdeckung, kleine Suiten und leistungsabhängige Tokenmengen begrenzen diese Ergebnisse. Sie bleiben als historische Daten erhalten, werden nicht nachträglich umetikettiert.

## Modellgröße: 27,3M gegen 97,5M Parameter

Nach jeweils drei Stunden sah das kleine Modell 119,0M Tokens, das große 38,5M. Das kleine erreichte 194/702 richtige bewertbare Antworten, das große 142/702. Bei gleichen 10M/20M/30M Tokenständen ergab sich keine konsistente Überlegenheit des kleinen Modells über alle Fähigkeiten. Aussage: Unter diesem Zeitbudget und diesen Betriebsbedingungen liefert das kleine mehr Fortschritt pro Stunde; daraus folgt keine grundsätzliche Überlegenheit geringerer Kapazität.

Die Fortsetzung um jeweils drei weitere Stunden bewirkte:

| Modell | Korrekte Antworten 3h → 6h | Antwortloss 3h → 6h | Tokens gesamt |
|---|---:|---:|---:|
| 27,3M | 194/702 → 193/702 | 1,472 → 1,445 | 245,9M |
| 97,5M | 142/702 → 181/702 | 1,679 → 1,441 | 77,0M |

Längeres Training half dem großen Modell in dieser Fortsetzung; das kleine verbesserte vor allem seinen Loss. Die Modelle durchliefen unterschiedliche Abschnitte derselben tokenbasierten LR-Kurve, bei nur einer Initialisierung je Größe. Keine allgemeine Sättigungs- oder Größenregel. Quellen: [3h-Bericht](results/2026-09-11/size-campaign-2026-09-08/REPORT.md), [Fortsetzung](results/2026-09-11/size-continuation-2026-09-09/REPORT.md).

## Zufallsnetze statt Training

Die Stichprobe prüfte 256 frisch initialisierte 97,5M-Netze in insgesamt 3,54 Minuten innerhalb der freigegebenen 20 Minuten. Initialisierung plus kleine Auswahlprüfung benötigte etwa 0,55s pro Netz. Die größere Referenzprüfung wäre deutlich teurer; die Prüfung frei generierter Antworten nochmals wesentlich teurer.

Das ausgewählte Zufallsnetz hatte einen Antwortloss von 9,5313 auf 854 Referenzaufgaben; das trainierte Quellenmodell 1,7078. In der kleinen freien Kontrollprobe löste das Zufallsnetz 0/11 bewertbare Aufgaben. Das ist kein mathematischer Unmöglichkeitsbeweis für Zufallssuche, liefert aber keinen praktischen Grund, drei Stunden dafür einzusetzen. Hochgerechnete Netze pro Zeit sind keine Erfolgswahrscheinlichkeiten. [Stichprobenbericht](results/2026-09-11/random-search-pilot-2026-09-08/REPORT.md).

## Lernkontrolle, Referenzen und Performance

Eine gezielte Diagnose auf nachweislich gesehenen Trainingsaufgaben ergab 58/192 korrekte Antworten gegenüber 55/192 auf etwa längengleichen Entwicklungsaufgaben; Antwortloss 1,299 gegenüber 1,459. Kleine diagnostische Auswahl, kein repräsentativer Memorierungsnachweis. Mathematik blieb auch bei gesehenen Aufgaben schwach. Ausgabelimits von 512 statt 256 Tokens halfen in 16 gezielt ausgewählten Problemfällen nicht; keine allgemeine Aussage zu allen Aufgaben.

Die manuelle Prüfung fand Inhaltsfehler und Wiederholungen sowie fragwürdige Originalreferenzen in APPS, AQuA, BoolQ und einen prüfbedürftigen ANLI-Fall. Originalscores und separate Sensitivitätsanalysen bleiben getrennt. Quellennachweise und fixe Fallliste: [NAECHSTER_LAUF.md](NAECHSTER_LAUF.md), `next_run/manual_findings.json`.

BF16-Vorwärtsrechnung mit FP32-Mastergewichten erreichte im isolierten Kurzvergleich etwa 20,3% mehr Durchsatz als FP32/Batch 2. Gewichts-/Loss-Toleranzen und Speicherung/Wiederaufnahme wurden geprüft. Das garantiert keine gleiche Qualität nach Stunden; regulärer Standard bleibt FP32. Monitoring ist standardmäßig light, PowerWatch separat. Hardware- und Betriebsbedingungen gehören zu jedem Durchsatzvergleich.

## Begrenzte Forschungsrunden und Parameterstudie

Die beiden einstündig begrenzten Forschungsrunden prüften jeweils sechs kurze Anpassungen des kleinen Sechs-Stunden-Modells mit unterschiedlichen Lernraten bzw. Antwortgewichten. Kein bestätigt überlegener Kandidat. Unterschiedlich große Auswahlsuiten dürfen nicht direkt als zeitlicher Lernfortschritt verglichen werden.

Die anschließende systematische Studie schloss 114 kurze und vier längere Trainings samt Auswertungen ab. Der explorative Kandidat Quellenmischung gewann in der längeren Gegenprüfung etwa 1,35 Prozentpunkte im Mittel, erfüllte aber nicht alle festgelegten Kriterien. Ein besserer Einzelwert rechtfertigt keine Modellübernahme. [Vollständige Variantentabelle](results/2026-09-11/parameter-study-timeout-recovery-2026-09-10/REPORT.md).

Untersucht wurden endliche Stufen von LR, Gewichtung, AdamW-Parametern, Batch, Kontext, Rechengenauigkeit, Mischung und einigen Größenvarianten. Nicht umfassend untersucht: Tokenizer, Optimiererfamilien, grundlegende Architekturbausteine oder Decode-Strategien. Alle 57 Varianten bleiben im Katalog; kein vollständiges Parameterwissen.

GPU-Dienstfehler, Metal-Hangs und zu kurze Auswertungsfristen unterbrachen frühere Sitzungen. Die Fehlerklassifikation und begrenzte Wiederherstellung wurden verbessert, Auswertungen auf 600s plus Prozessreserve angehoben. Der GPU-Hang wird korrekt erkannt; seine eigentliche Ursache ist nicht als behoben nachgewiesen. Historische Fehlversuche und Budgetabzüge bleiben erhalten. Details: `GPU_HANG_FIX.md`, `STUDIE_WIEDERHERSTELLUNG.md`, `AUSWERTUNGSFRIST_FIX.md`.

## Langer 2×2-Vergleich: finale Einordnung

Acht Anpassungen des ursprünglichen kleinen Sechs-Stunden-Modells: Familien-/Quellengewichtung × LR 3e-5/1e-5, jeweils zwei Datenreihenfolgen und knapp zwei Stunden pro Training. Abschluss am 11. September um 05:53 Uhr; 60170,916s Gesamtverbrauch einschließlich konservativer Vorbereitung, rund 7h17m ungenutzte Reserve. Keine weitere automatische Nutzung.

| Variante | Mischung | LR | Gegenprüfung Folge 0 | Folge 1 | Mittel |
|---|---|---:|---:|---:|---:|
| Ausgangsmodell | — | — | 27,74% | gleicher Checkpoint | 27,74% |
| A | Familien | 3e-5 | 26,94% | 30,83% | 28,89% |
| B | Quellen | 3e-5 | 24,97% | 18,54% | 21,75% |
| C | Familien | 1e-5 | 28,89% | 26,49% | 27,69% |
| D | Quellen | 1e-5 | 29,44% | 22,99% | 26,22% |

- Kein Vergleich erfüllt sämtliche vorab festgelegten Kriterien einschließlich Elternmodell-Kontrolle. Kein bestätigter Gewinner.
- D gegenüber B: etwa +4,5 Prozentpunkte in beiden Gegenprüfungen. Auch auf der Auswahlsuite bei gleichen 50M Tokens liegt D vorn: +3,04 bzw. +1,43 Punkte. Das ist das klarste wiederholte Signal für eine LR×Mischungs-Abhängigkeit; kein Beweis eines Vorteils gegenüber dem Elternmodell.
- C gegenüber A ist uneinheitlich. Die niedrigere LR ist damit keine allgemeine Empfehlung für jede Mischung.
- In sieben von acht Trajektorien liegt der finale Auswahlsuiten-Score unter dem bei 50M Tokens. Spätere Checkpoints sind nicht automatisch besser. Das beweist allein kein Overfitting und betrifft Anpassungen eines bereits trainierten Modells, nicht jeden denkbaren Kaltstart.
- Quellengewichtung verringert häufig den Referenzloss, ohne die freie Antwortqualität durchgängig zu verbessern. Loss ist ein Quellenmittel mit richtigen vorherigen Tokens; Genauigkeit ein Familienmittel über bewertbare Ausgaben. Abdeckung und Gewichtung unterscheiden sich.
- Gegenprüfung: 200 generierte Aufgaben, davon 160 tatsächlich auf Antwortkorrektheit bewertet, sechs bewertbare Familien. Beispielsweise nur acht DREAM-Aufgaben: eine zusätzliche richtige Antwort verschiebt das Familien-Makro bereits um etwa 2,08 Prozentpunkte. Zwei Datenreihenfolgen sind keine unabhängigen Initialisierungsseeds. Keine Signifikanzbehauptung.
- Folge 0 verarbeitete 106–141M Tokens, Folge 1 76–83M. Leistungsmodus und Stromquelle wechselten; EvoNN überlappte nur zu Beginn. Gleiche Zeit ist deshalb nicht gleiches Trainingsvolumen. Der Paralleltest hatte keine vollständige SLM-Alleinkontrolle; deskriptiv ungefähr 9,4% längere EvoNN-CPU-Fits sind keine präzise kausale Verlangsamung.

Quellen: [Langzeitbericht](results/2026-09-11/long-horizon-resume-2026-09-10/REPORT.md), zugehörige `quality.json`, `contrasts.json`, `assessment.json`; [Paralleltest](results/2026-09-11/parallel-probe-2026-09-10/REPORT.md). Vollständige Betriebsbedingungen und Antworten in den ZIPs.

## Nächste offene Fragen – keine Startfreigabe

Vor weiteren langen Trainings vorhandene Antworten je Fähigkeit bei gleichen Tokenständen prüfen: Inhalt, Format, Wiederholungen und Trunkierung trennen. Danach größere gruppengetrennte Gegenprüfung und gleiche Tokenbudgets vorab festlegen. Kein Ausschluss einer Variante allein wegen dieser kleinen Studie. Keine Änderung historischer Scores oder eingefrorener Eingaben. Externe Tests erst nach fixierter Auswahl öffnen.
