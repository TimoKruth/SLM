Aktualisierung 15.09.2026: [Analyse des konservativen FP32-Vergleichs](CONSERVATIVE_RESULT_ANALYSIS.md). Gleiche 8.192 Updates: keine beobachteten Korrektheitsregressionen, etwa 2,2% schneller; Zeitendpunkte bleiben wegen unterschiedlicher Updatezahlen und nicht bestandener Qualitäts-/Betriebskriterien unbestätigt. Keine Optimierung übernommen.

# Erkenntnisse und Grenzen – Stand 15. September 2026

Beide Langzeitblöcke zur Parametervariation sind vollständig abgeschlossen; kein Kandidat wurde automatisch übernommen. Der separate konservative FP32-Vergleich hat einen eigenen Status und ist nicht Teil dieser Parameterergebnisse. Ziel bleibt ein vielseitiges, von Grund auf nur mit Benchmark-Trainingsmaterial gelerntes Sprachmodell; Coding ist eine mögliche Fähigkeit.

Diese Übersicht verbindet die bisherigen Schlussfolgerungen mit dem [historischen Ergebnisarchiv](results/2026-09-11/INDEX.md) und dem [Ergebnisarchiv des zweiten Langzeitblocks](results/2026-09-15/INDEX.md). Herkunft und Prüfsummen stehen beim älteren Export in `sources.json`, beim neuen in `verification.json`. Historische Rohantworten, Pläne, Daten, fehlgeschlagene Versuche, Checkpoints und Leistungsprotokolle liegen zusätzlich in getrennten lokalen ZIP64-Archiven; Umfang und Wiederherstellung beschreibt [SICHERUNG.md](SICHERUNG.md). Die neuen Laufartefakte sind noch nicht Bestandteil dieser ZIPs. „Versioniert“ und „extern gesichert“ sind unterschiedliche Aussagen.

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

## Zweiter Langzeitblock: Lernrate und Verlauf

Acht unabhängige Anpassungen desselben ursprünglichen 27,3M-Sechs-Stunden-Checkpoints mit FP32 und unveränderter Familienmischung aus 32 korrigierten Quellen. Vier Bedingungen mit jeweils zwei Datenreihenfolgen und 7200s Prozessbudget einschließlich Abschlussreserve. Alle acht Trainings und 33 Auswertungen abgeschlossen am 14. September um 23:55:05 Europe/Berlin. Gesamtverbrauch einschließlich voriger Sitzungen und Vorbereitung 66.390,316s aus 86.400s; 20.009,684s Reserve bleiben ungenutzt. Der Supervisor bestätigt unveränderte eingefrorene Eingaben.

| Variante | Lernrate / Verlauf | Gegenprüfung Folge 0 | Folge 1 | Mittel |
|---|---|---:|---:|---:|
| Ausgangsmodell | gleicher ursprünglicher Checkpoint | 24,13% | gleicher Checkpoint | 24,13% |
| A | konstant 3e-5 | 25,17% | 27,60% | 26,39% |
| B | konstant 3e-6 | 21,88% | 24,90% | 23,39% |
| C | konstant 1e-4 | 24,86% | 20,90% | 22,88% |
| D | Kosinus 3e-5 → 3e-6 über 100M zusätzliche Tokens | 28,89% | 24,38% | 26,63% |

Die Genauigkeit ist ein Mittel über sechs bewertbare Fähigkeitsgruppen, kein Anteil korrekter Antworten an allen 200 Aufgaben. Die Gegenprüfung umfasst 25 Quellen, 200 generierte und 160 auf Korrektheit bewertete Aufgaben. Der Loss bewertet die Originalreferenzen aller 200 Aufgaben bei vorgegebenen korrekten vorherigen Tokens. Die neue Gegenprüfung hat andere Gruppen als Block 1: 24,13% statt damals 27,74% beim identischen Elternmodell bedeutet deshalb keinen Qualitätsverlust.

- Kein Kandidat erfüllt alle Kriterien: mindestens +2 Prozentpunkte gegenüber A in beiden Wiederholungen, kein mittlerer Familienrückgang über 5 Punkte und bestandene Elternmodellkontrolle. Keine automatische Übernahme.
- B verliert auf der Gegenprüfung gegenüber A 3,30 / 2,71 Punkte, obwohl der Referenzloss sinkt und die Auswahlsuite besser ausfällt. Bessere Referenzvorhersage bestätigt hier keine bessere freie Antwortqualität.
- C verliert 0,31 / 6,70 Punkte gegenüber A und erhöht den Referenzloss in beiden Wiederholungen. Das liefert unter diesen Bedingungen keinen Grund, die hohe LR weiter zu priorisieren.
- D gewinnt im Mittel nur 0,24 Punkte gegenüber A: +3,72 in Folge 0, −3,23 in Folge 1. D besteht die Elternmodellkontrolle, aber nicht den geforderten konsistenten Vorteil gegenüber A. Auch bei gleichen 50M Tokens auf der Auswahlsuite wechselt das Vorzeichen (+1,27 / −1,15 Punkte). D bleibt eine Hypothese, kein bestätigter Gewinner.
- Bei gleichen 50M Tokens liegt B auf der Auswahlsuite nur +0,06 / +0,45 Punkte vor A, C −5,30 / −1,34 Punkte dahinter. Diese Suche-Endpunkte ersetzen keine Gegenprüfung bei gleichen Tokens.
- Die zusätzlichen Tokenmengen reichen bei knapp gleicher aktiver Trainingszeit von 82,9M bis 126,0M. D erreicht in Folge 0 das Ende seiner 100M-Kosinuskurve nicht, in Folge 1 schon. Pausen und Betriebsbedingungen begrenzen die Interpretation bei festem Zeitbudget. Zwei Datenreihenfolgen sind keine unabhängigen Modellinitialisierungen; keine Signifikanz- oder externe Transferbehauptung.

Belege: [Ergebnisarchiv mit Herkunft und Verifikation](results/2026-09-15/INDEX.md), [unveränderter Bericht](results/2026-09-15/long-horizon-round2-resume-2026-09-14/REPORT.md), [vorab festgelegter Plan](LANGZEIT_RUNDE_2.md).

## Fehleranalyse und Evaluationsvorbereitung vom 15. September

Die ersten beiden empfohlenen Schritte wurden bearbeitet: [Fehleranalyse](PARAMETER_ERROR_ANALYSIS.md) und [Evaluationsprotokoll](PARAMETER_EVALUATION_PROTOCOL.md). Alle 13.152 gespeicherten Antworten aus 33 Auswertungen stimmen mit dem eingefrorenen Scorer überein. Beim Kontrollmodell sind 190 von 232 falschen Gegenprüfungsantworten ohne die untersuchten Oberflächenwarnungen; Mathematik zeigt zugleich viele Wiederholungen, Format- und Inhaltsfehler. Die gezielte manuelle Prüfung dokumentiert zwei neue Referenzprobleme; ihr Ausschluss ändert die finalen Makroscores nicht. Eine reine Optionsbuchstaben-Normalisierung würde neben einem plausiblen Formatfall drei numerisch widersprüchliche Antworten akzeptieren.

Gepaarte Gruppen-Bootstraps mit 5.000 Ziehungen ergeben für den mittleren Kosinusvorteil von +0,24pp ein exploratives 95%-Intervall von −4,03 bis +4,44pp. Datenreihenfolgen wurden gemeinsam gepaart; keine unabhängigen Modellseeds, keine neue Signifikanz- oder Annahmeentscheidung. Die alte Gegenprüfung ist für weitere Auswahl jetzt explorativ.

Eine größere Diagnose mit denselben 25 Quellen liegt STOP-gesperrt vor: 64 Gruppen je bewertbarer Quelle, 16 je unbewertbarer Quelle, insgesamt 1.360 Aufgaben und 1.280 bewertbare Gruppen. Ausschließlich bereits konsumierte Suiten abgeschlossener Kampagnen, kein Trainingsgruppenüberlapp; noch keine Modell-Auswertung. Eine passende frische Gegenprüfung bleibt wegen fehlender unbenutzter/unreservierter Gruppen bei ARC, DREAM, QuaRel und Quoref unvollständig. Die verbleibende Datenarbeit und Grenzen stehen im Protokoll; keine stillschweigende Wiederverwendung alter Aufgaben als frischer Test.

## Empfohlene nächste Schritte – keine Startfreigabe

1. Bestehende Antworten von A und D sowie die Loss-/Genauigkeitsabweichung bei B auf den bereits geöffneten Suiten untersuchen. Je Fähigkeit Inhaltsfehler, Antwortformat, Wiederholungen, Trunkierung und fragwürdige Referenzen getrennt zählen. Dieselben Aufgaben und vorhandene 15M-/50M-/Endstände verwenden; Originalscores erhalten. Das ist der nächste Untersuchungsschritt vor zusätzlichem Training.
2. Messgrundlage verbessern: stärkere gruppengetrennte Abdeckung je Fähigkeit, insbesondere der kleinen Familien, und auf Aufgaben-/Quellgruppen gepaarte Unsicherheitsanalyse. Eine neue Gegenprüfung erst nach festgelegter Hypothese und Auswahlregel öffnen; bestehende Gegenprüfungen sind nach dieser Analyse explorativ. Reservierte externe Abschlusstests weiter geschlossen halten.
3. Falls die Diagnose einen weiteren LR-Vergleich rechtfertigt, nur A gegen D vom selben Elterncheckpoint mit identischen zusätzlichen Tokenbudgets und mehr gepaarten Datenreihenfolgen prüfen. Vorab Tokenendpunkt, Qualitätskriterien und Abbruchbudget festlegen; benötigte Zeit anhand des langsameren gemessenen Durchsatzes samt Reserven kalkulieren. Für Aussagen über Modellinitialisierungen wären gesonderte unabhängige Trainings erforderlich. Keine weitere breite LR-Rotation allein aus dem kleinen Durchschnittsvorteil ableiten.
4. Breiteres Lernen separat untersuchen: Nach Prüfung der vorbereiteten 47-Quellen-Mischung einen klar abgegrenzten Datenvergleich planen. Quellenanzahl allein ist kein Qualitätsnachweis; LR, Daten und Modellgröße nicht zugleich ändern. Die Entscheidung über GPU-Synchronisation aus dem separaten konservativen FP32-Vergleich anhand seiner eigenen Qualitäts- und Geschwindigkeitskriterien treffen.

Arbeitsreferenz bleibt A mit LR 3e-5; das erklärt sie nicht zur global optimalen Konfiguration und übernimmt keinen neuen Modellcheckpoint. Diese Empfehlungen starten keine zusätzlichen Läufe und verändern keine eingefrorenen Eingaben.
