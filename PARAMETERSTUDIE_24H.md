# Systematische Parameterstudie: 24 Stunden Zusatzbudget

Der Nutzer hat am 9. September 2026 ausdrücklich beauftragt, Parameter breit zu
variieren, und anschließend **24 zusätzliche Stunden einschließlich Kontrollen und
Auswertungen** freigegeben. Die bereits gestartete zweite Forschungsrunde zählt
nicht dazu. Die neue Kampagne wartet seriell auf deren Ende.

Code: `/Users/timokruth/Projekte/SLM-parameter-study`, Branch `codex/parameter-study`.
Kampagne: `runs/parameter-study-2026-09-09/`. Warteschlange: `queue.json`;
aktive Phase/Frist: `status.json`; fortlaufender Bericht: `REPORT.md`.

## Erkenntnisziel und Grenzen

Gemessen werden Richtung und Größe der Effekte für ausdrücklich festgelegte
Parameterstufen, Modelle, Daten und Laufzeiten. Endlich viele Versuche können weder
alle Einstellungen noch alle Wechselwirkungen erschöpfend erklären. Ergebnisse
heißen daher etwa „verbessert in beiden Wiederholungen“, „uneinheitlich“ oder
„noch ununtersucht“, niemals pauschal „dieser Parameter ist verstanden“.

Die Studie trennt kurze Adaptation eines bestehenden Modells, neue Initialisierungen,
ausgewählte Wechselwirkungen und längere Wiederholungen. Screening und anschließende
Interaktionsprüfung folgen dem Grundgedanken sequenzieller Versuchsplanung:
[NIST: iterative Versuchsplanung](https://www.itl.nist.gov/div898/handbook/pri/section2/pri223.htm).
Einzelfaktorvergleiche allein können Wechselwirkungen übersehen:
[NIST: One variable at a time](https://www.itl.nist.gov/div898/handbook/pri/section2/pri212.htm).

## Festgelegte Versuche

| Block | Konfigurationen × Wiederholungen | Arbeit je Lauf | Prozessobergrenze je Training |
| --- | ---: | ---: | ---: |
| Adaptation, Mischung, Kontext, Ausführung | 37 × 2 = 74 | 1,5M zusätzliche Tokens | 360s |
| Neue Architektur-/Initialisierungsvarianten | 12 × 2 = 24 | 3M Tokens ab Zufallsinitialisierung | 1200s |
| Lernrate × Antwortgewicht × Gewichtszerfall | 8 × 2 = 16 | 1,5M zusätzliche Tokens | 360s |
| Kontrolle und ausgewählter Kandidat, länger | 2 × 2 = 4 | 15M zusätzliche Tokens | 2100s |

Das sind 114 kurze Vergleiche und vier längere Läufe. Zwei Datenreihenfolgen bei
Adaptation sind keine unabhängigen Modellinitialisierungen. Im Architekturblock
werden tatsächlich zwei unabhängige Initialisierungsseeds verwendet. Laufreihenfolge
innerhalb der Blöcke wird vorab deterministisch gemischt; Kontrollläufe kommen zuerst.
Tatsächliche Tokenzahlen und kleiner Überschuss des letzten vollständigen Updates
werden gespeichert. Langsame Varianten mit unvollständigem Tokenziel sind kein
gültiger Qualitätsvergleich.

## Parameterstufen

Gemeinsamer Adaptations-Ausgangspunkt ist das unveränderte kleine Sechs-Stunden-Modell
`size-27m-2026-09-09-plus3h/checkpoint-0135594` mit AdamW-Zustand.
Die folgenden Abweichungen werden zunächst einzeln gegen die jeweilige Kontrolle geprüft:

| Parameter | Kontrolle | Untersuchte Abweichungen |
| --- | --- | --- |
| Lernrate | 3e-5 konstant | 3e-6, 1e-5, 1e-4 |
| Lernratenverlauf | konstant | Kosinus bis 10 % über das Tokenbudget |
| Gewichtszerfall | 0,1 | 0; 0,3 |
| Adam β1 | 0,9 | 0,8; 0,95 |
| Adam β2 | 0,95 | 0,9; 0,99 |
| Adam ε | 1e-8 | 1e-6 |
| Gradientennormbegrenzung | 1 | 0,5; 2; ausgeschaltet |
| Antworttokengewicht | 1 | 0,5; 2; 4 |
| Prompttokengewicht | 1 | 0, also nur Antwortziele |
| Optimiererzustand | übernehmen | AdamW bei denselben Elterngewichten zurücksetzen |
| Mikro-/effektive Batchgröße | 2 / 2 | 1 / 2; 4 / 4; 2 / 4; 2 / 8 |
| Vorwärts-Rechengenauigkeit | FP32 | BF16 mit FP32-Mastergewichten |
| Ausführung | kompiliert | eager |
| Quellenmischung | gleiche Masse je Familie | gleiche Masse je Quelle |
| Fähigkeitsgewichtung | sieben Familien gleich | jede Familie einzeln doppelt gewichtet, dann normalisiert |
| Trainingskontext | 1024 | 512; 2048, jeweils auf gemeinsamem ≤512-Token-Datensatz |

Die sieben Fähigkeitsgruppen bleiben in allen Mischungen vertreten. Coding erhält
keine Sonderpriorität. Alle Daten stammen aus derselben korrigierten, auditierten
Version mit 32 Quellen. Kein externes Testmaterial und keine synthetischen Antworten.

Gradientenakkumulation summiert nach tatsächlichem gewichteten Tokenanteil und führt
Clipping/AdamW genau einmal pro effektivem Batch aus. Eine bloße Mittelung verschieden
langer Mikro-Batch-Losses wäre hier falsch. Gleiches effektives Batchformat und gleiche
Datenkonfiguration müssen identische Batch-Hashes, Token-/Quellenzählungen und
Samplerzustände liefern. Bei anderen effektiven Batches bleibt die Reihenfolge
vergleichbar, aber die Updatezahl und der kleine Endpunktüberschuss verändern sich.

Kontextlänge würde im bisherigen Sampler zugleich lange Originalaufgaben ausfiltern.
Daher haben die drei Kontextvarianten eine eigene gemeinsame ≤512-Token-Zulassung und
eine 1024-Kontrolle auf genau diesem Teilbestand. Sie bleiben als Effekt von Kontext
**und Packung** gekennzeichnet. Die gemeinsame Evaluation verwendet weiterhin Kontext
1024. Diese drei Varianten konkurrieren nicht um den allgemeinen längeren Lauf.

Im Kaltstartblock gelten Lernrate 3e-4, 100 Warmup-Updates und die 27,3M-Architektur
(Dimension 512, sechs Schichten, acht Köpfe, FFN 1368) als Kontrolle. Abweichungen:

- Schichten 4 / 8; Dimension 384 / 640; Köpfe 4; FFN-Breite 1024 / 2048.
- Ganze 97,5M-Architektur: Dimension 768, zwölf Schichten/Köpfe, FFN 2048.
- Initialisierungs-Standardabweichung 0,01 statt 0,02 bei unveränderter Residualskalierung.
- Adam-Bias-Korrektur aus statt an; Warmup aus statt 100 Updates.

Architekturänderungen verändern teilweise auch Parameterzahl und Rechenkosten. Beides
wird ausgewiesen. Gleiche Tokenmenge ist kein gleiches Rechenbudget. Drei Millionen
Tokens zeigen frühes Lernen, nicht die erreichbare Endqualität. Optimiererfamilie
bleibt AdamW; geänderte β-Werte mit geerbten Momenten messen ausdrücklich den Übergang
ab einem bestehenden Modell und nicht die gesamte Trainingsgeschichte mit diesem β.

Der vollständige 2×2×2-Interaktionsblock kreuzt LR {1e-5, 3e-5}, Antwortgewicht {1, 2}
und Gewichtszerfall {0, 0,1}. Je zwei neue Datenreihenfolgen. Haupteffekte und
Differenzen-von-Differenzen werden auf vollständigen Blöcken berechnet; unvollständige
Blöcke bleiben unbewertet. Keine Signifikanzbehauptung aus zwei Wiederholungen.

## Auswertung und längere Gegenprüfung

Die 473er-Auswahlsuite der zweiten Runde bleibt identisch, damit die neuen Resultate
auf denselben Aufgaben vergleichbar sind. Eine weitere Gegenprüfung zieht bis acht
neue Entwicklungsgruppen je Quelle außerhalb der historischen 886er-Gruppen und
beider bisherigen Gegenprüfungen. Sie wird erst nach Ende der laufenden Runde
CPU-seitig erstellt und vor neuen Ergebnissen eingefroren. Gruppentrennung zum
Training wird geprüft. Frühere Inline-Dev-Loss-Nutzung bleibt möglich; es handelt
sich weiterhin um interne Entwicklung, nicht um unberührte externe Benchmarks.

Gemeinsame Maße: freie Antwortgenauigkeit je Quelle/Familie, Referenz-Antwortloss,
gepaarte Unterschiede je Datenreihenfolge, Tokens/s, Gesamtzeit, GPU-Speicherspitze
und Systemressourcen. Verschieden gewichtete Trainingslosses sind nicht direkt
vergleichbar. Die generative Genauigkeit deckt funktionalen Code, SQL und offene
Textqualität nicht vollständig ab; für diese Quellen liegt hier vor allem der
Referenz-Antwortloss vor. „Alle Fähigkeiten verstanden“ wäre daraus nicht ableitbar.

Ein Screening-Kandidat benötigt gegenüber seiner Kontrolle mindestens zwei
Prozentpunkte Gewinn in beiden Wiederholungen, höchstens fünf Punkte mittleren
Rückgang je bewertbarer Familie sowie keine Verschlechterung gegenüber dem
unveränderten Elternmodell bei Genauigkeit und Antwortloss. Auswahl zuerst nach
Erfüllung dieser Kriterien, dann mittlerer Genauigkeitsänderung und zuletzt Loss.
Auch ohne bestandene Schwelle wird der beste Kandidat ausdrücklich explorativ für
die längere Gegenprüfung gewählt; dies begründet keine Übernahme.

Vier längere Läufe: Kontrolle und Kandidat, jeweils mit zwei neuen Datenreihenfolgen,
ab denselben ursprünglichen Elterngewichten. Zusätzlich werden Modellstände bei
1,5M Zusatz-Tokens gespeichert und später auf derselben Suite bewertet. Der Vergleich
1,5M gegen 15M verfolgt dadurch dieselbe Trajektorie. Die endgültige Gegenprüfung nutzt
die neue Suite und erneut das unangetastete Elternmodell. Kein automatischer Modellwechsel.

## Nicht variierte Größen

Tokenizer/Vokabular erfordern eine separate Train-only-Neutokenisierung, Datenprüfung
und einen Vergleich gleicher Originalbeispiele beziehungsweise Bytes. Neue
Optimiererfamilien, Aktivierungen, Norm-/RoPE-Varianten, Dropout und Embedding-Bindung
sind zusätzliche Architekturfragen und werden in diesen 24 Stunden nicht variiert.
Dekodierung und Bewertungsregeln bleiben als Messinstrument fest. Die vom Nutzer
gewünschte geräuscharme Leistungseinstellung wird nicht verändert. Monitoring- und
I/O-Takte bleiben fest. Diese Grenzen stehen auch maschinenlesbar im Plan und Bericht.

## Betrieb und Budget

Die Summe aller Stufenobergrenzen beträgt **85.530 Sekunden (23h 45m 30s)**,
einschließlich Vorbereitung, GPU-Kontrolle, Auswahl-/Gegenprüfungen und vier frühen
Langlauf-Snapshots. Die harte globale Grenze liegt bei **86.400 Sekunden** ab Start
des neuen Supervisors. Warten auf die bereits freigegebene laufende Runde zählt nicht.
Das Budget wird nie zurückgesetzt oder verlängert; es ist eine Obergrenze, keine
Pflicht, ungenutzte Zeit mit weiteren Versuchen zu füllen.

GPU-Arbeit läuft seriell über `run_slm.py`, unter der bestehenden GPU-Sperre.
Monitoring `light`, zehn Aufwärmschritte, 60s-Zwischenstände und PowerWatch bleiben
aktiv. `RUN_CONDITIONS.json` zeichnet Leistungsmodus und Stromversorgung auf.
Unter 6 GiB verfügbarem System-RAM beendet sich ein Trainingsversuch; einzelne Fehler
werden protokolliert, nicht automatisch wiederholt. Fehler der Kontrollprüfung,
veränderte Eingaben, globale Frist oder STOP beenden die Kampagne.

Quellcode und vorab erzeugte Jobdateien werden bereits vor dem Einreihen gehasht.
Suiten, Daten und Elterncheckpoint werden vor GPU-Start zusätzlich eingefroren und
danach geprüft. Die vier aus der Auswahl abgeleiteten Langlauf-Jobdateien sind neue,
dokumentierte Ausgaben der vorab festgelegten Auswahlregel. Historische Worktrees,
Gewichte und Ergebnisse bleiben erhalten. Rund 1,2 TiB freier Plattenplatz wurden
vor Vorbereitung festgestellt; es werden keine alten Checkpoints gelöscht.

Stoppen: `touch runs/parameter-study-2026-09-09/STOP`.
Die Warteschlange startet bei STOP nicht; der Supervisor beendet einen aktiven
Kindprozess. Kein automatischer Neustart einer begonnenen Kampagne.

Start der einmaligen Warteschlange:
`.venv/bin/python run_slm.py --module study.queue --run runs/parameter-study-2026-09-09`
