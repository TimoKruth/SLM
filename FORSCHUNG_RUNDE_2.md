# Zweite begrenzte Forschungsrunde – 9. September 2026

Expliziter Nutzerauftrag: weitere Läufe starten, um mehr Daten zu erhalten.
Kampagne: `runs/research-round2-2026-09-09/`.
Code: `/Users/timokruth/Projekte/SLM-research-round2`, Branch
`codex/bounded-research-round2`. Aktuelle Phase und Frist: `status.json` im
Kampagnenverzeichnis; automatische abschließende Auswertung: `REPORT.md`.

## Motivation und Versuch

Die erste Runde endete nach 35 Minuten ohne bestätigten Kandidaten. Auf ihrer
248er-Auswahlstichprobe lag auch das unverändert weitertrainierte Modell hinter dem
unangetasteten Sechs-Stunden-Modell. Höhere Lernrate und vierfaches Antwortgewicht
halfen nicht. Die zweite Runde prüft deshalb kleinere Änderungen und verwendet eine
größere Auswahlstichprobe. Sie ersetzt keine historischen Ergebnisse.

| Variante | Feste Lernrate | Antwortgewicht |
| --- | ---: | ---: |
| baseline | 0,00003 | 1 |
| lower-lr | 0,00001 | 1 |
| mild-answer-weight | 0,00003 | 2 |

Je Variante zwei neue Datenreihenfolgen, Sampler-Seeds 202609092 und 202609093;
jeweils 3M zusätzliche echte Tokens. Alle sechs Versuche starten unabhängig vom selben
27,3M-Elterncheckpoint `size-27m-2026-09-09-plus3h/checkpoint-0135594`, einschließlich
AdamW. Es sind keine Fortsetzungen der sechs Pilotvarianten und keine unabhängigen
Modellinitialisierungen. Die neue Kontrollvariante ergänzt die bisherigen Messungen
um zwei weitere Datenreihenfolgen.

FP32, Kontext 1024, Batchgröße 2, 32 unveränderte korrigierte Original-Trainingsquellen,
gleiche Familienmischung. Der bereits geprüfte gewichtete Next-Token-Loss bleibt
unverändert implementiert. Zwischen Varianten sind nur die gemeinsame freie
Antwortauswertung und der Referenz-Antwortloss vergleichbar, nicht der unterschiedlich
gewichtete Trainingsloss. Baseline/Interventionen erhalten innerhalb einer Wiederholung
identische Trainingsbatches; Hash, Tokenzahl, Quellenzählungen und Samplerzustände
müssen übereinstimmen.

## Größere Auswertung und zusätzliche Kontrolle

Bis zu 16 statt acht deterministisch gezogene Entwicklungsgruppen je Quelle aus der
historischen 886er-Suite. Bekannte fragliche Referenzen bleiben vorab ausgeschlossen.
Die Auswahlstichprobe enthält somit historische und teilweise bereits im Pilot
bewertete Aufgaben. Sie ist keine neue unabhängige Testmenge. Die tatsächliche
Anzahl und Quellenabdeckung stehen in `suite-audit.json`.

Die Gegenprüfung zieht bis zu acht andere Gruppen je Quelle, außerhalb aller
historischen 886er-Gruppen sowie außerhalb der Gegenprüfung des ersten Piloten.
Beide Suiten sind von Trainingsgruppen getrennt. Frühere Inline-Dev-Loss-Messungen
können diese internen Entwicklungsaufgaben dennoch enthalten haben. Externe
Endbenchmarks bleiben geschlossen. Keine funktionale Code-/SQL-Auswertung und keine
behauptete umfassende Bewertung offener Texte in dieser kurzen Runde.

Auswahl und Gegenprüfung folgen weiterhin der im Pilot vorab festgelegten Regel:
mindestens zwei Prozentpunkte Gewinn bei der Familien-Makrogenauigkeit in beiden
Datenreihenfolgen, höchstens fünf Prozentpunkte mittlerer Rückgang in jeder bewertbaren
Familie. Genauigkeit ist das Mittel der Quellengenauigkeiten je Familie, anschließend
das gleich gewichtete Mittel der bewertbaren Familien; Antwortloss ist sekundär.

**Zusätzlich** muss jede Wiederholung eines Kandidaten auf beiden Suiten mindestens
die Genauigkeit des unveränderten Elternmodells erreichen und darf dessen
Referenz-Antwortloss nicht verschlechtern. Das Elternmodell wird daher diesmal auch
auf der Gegenprüfung ausgewertet. Ein Vorteil nur gegenüber einer verschlechterten
Trainingskontrolle reicht nicht als bestätigter Fortschritt. Auch ohne bestandene
Schwelle wird der beste Kandidat zur Gegenprüfung ausgewählt und als unbestätigt
gekennzeichnet. Keine automatische Übernahme oder Verlängerung.

Kleine Gruppenstichproben, zwei Datenreihenfolgen und gemeinsame Elterngewichte
erlauben weiterhin nur explorative Aussagen. Schwellen sind konservative
Auswahlregeln, keine Signifikanztests. Die größere Auswahlmenge verhindert einen
direkten Vergleich der aggregierten Prozentwerte mit der 248er-Pilotmenge; direkte
Vergleiche benötigen dieselben Aufgaben.

## Budget, Monitoring und Reproduzierbarkeit

Maximal 60 Minuten gesamte aktive Kampagnen-Wandzeit einschließlich GPU-Kontrolle,
Kompilierung, Speicherung und Auswertung. Vorab werden Eingaben CPU-seitig gehasht.
Die Summe aller geplanten Prozessobergrenzen beträgt 3510 Sekunden:

- GPU-Kontrolle am echten Elterncheckpoint: 40s.
- Sechs Trainingsprozesse: je maximal 360s einschließlich Speicherung, 3M-Token-Ziel.
- Sieben Auswahl-Auswertungen einschließlich Elternmodell: je maximal 130s Prozesszeit
  mit 120s Auswertungsbudget.
- Fünf Gegenprüfungen einschließlich Elternmodell: je maximal 80s Prozesszeit
  mit 70s Auswertungsbudget.

Die globale Frist hat Vorrang. Kein automatischer Neustart bei Fehler, keine
Fristerneuerung. Unvollständige Arbeit oder Auswertung ist nicht als Gewinn zulässig.
Der Kontrolllauf vergleicht zwei echte Updates einschließlich aller Modell- und
Optimiererarrays gegen den Produktionsschritt bei Antwortgewicht 1.

Alle GPU-Stufen laufen seriell mit gemeinsamer GPU-Sperre über `run_slm.py`, Monitoring
`light`, zehn Mess-Aufwärmschritte und 60s-Zwischenstände. PowerWatch läuft unabhängig.
`RUN_CONDITIONS.json` zeichnet die aktuellen Leistungs-/Stromversorgungsbedingungen
auf; Leistungseinstellungen werden nicht geändert. `caffeinate` verhindert Ruhezustand.

Quellcode, Plan, Suiten, ursprünglicher Elterncheckpoint und Daten werden eingefroren;
historischer Pilotcode bleibt im eigenen Worktree unverändert. Prüfsummen und
Dateistände werden vor und nach dem Lauf beziehungsweise zwischen Stufen kontrolliert.
Ein `STOP` im neuen Kampagnenverzeichnis beendet den aktuellen Kindprozess und
verhindert weitere Stufen.

Vorbereitung (CPU): `.venv/bin/python -m research.prepare --profile followup --run
runs/research-round2-2026-09-09`

Start: `.venv/bin/python run_slm.py --module research.campaign --run
runs/research-round2-2026-09-09`

Gestartet am 2026-09-09T09:05:11.996530+02:00. Budgetgrenze: 2026-09-09T10:05:11.996510+02:00.
Auswahl: 473 Aufgaben aus 31 Quellen; Gegenprüfung: 200 Aufgaben aus 25 Quellen.
