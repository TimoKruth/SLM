# Erste begrenzte Forschungsrunde (9. September 2026)

Der Nutzer hat den Start ausdrücklich beauftragt. Dies ist die erste kontrollierte
Ursachenprüfung nach dem Plateau des kleinen Modells, als Baustein einer späteren
autoresearch-artigen Forschungsschleife. Keine offene Suche und keine automatische
Budgetverlängerung. Fragen des Nutzers allein sind keine Startfreigabe.

Code: Worktree `/Users/timokruth/Projekte/SLM-research`, Branch
`codex/bounded-research`. Kampagne: `runs/research-pilot-2026-09-09`.
Status: dort `status.json`; abschließende Auswertung: `REPORT.md`.

## Hypothesen und festgelegter Ablauf

Alle Versuche verwenden das 27,3M-Modell aus
`size-27m-2026-09-09-plus3h/checkpoint-0135594`, einschließlich AdamW.
Ausgangspunkt: 245.863.369 Tokens, 135.594 Schritte, sechs Stunden bisherige
Trainingszeit. FP32, Batchgröße 2, Kontext 1024, dieselbe familiengewichtete Mischung
aus 32 korrigierten Original-Trainingsquellen.

| Variante | Feste Lernrate | Gewicht Antworttokens | Zweck |
| --- | ---: | ---: | --- |
| baseline | 0,00003 | 1 | Kontrolle der bisherigen LR-Untergrenze |
| higher-lr | 0,0001 | 1 | Prüfen, ob die niedrige LR weitere Anpassung begrenzt |
| answer-weight | 0,00003 | 4 | Prüfen, ob mehr Gewicht auf Antworten hilft |

Jede Variante trainiert zweimal ab denselben Elterngewichten und Optimiererzuständen
auf jeweils 3M zusätzlichen echten Tokens. Wiederholung 0 übernimmt den gespeicherten
Samplerzustand; Wiederholung 1 setzt ausschließlich dessen Zufallsfolge auf 202609091.
Innerhalb jeder Wiederholung müssen Tokenzahl, Schrittzahl, Quellenzählungen,
Batch-Hash sowie anfänglicher und abschließender Samplerzustand übereinstimmen.
Dies sind zwei Datenreihenfolgen, keine zwei unabhängigen Initialisierungen.

Die neue Gewichtung verwendet
`sum(CE * real * (1 + (answer_weight-1)*answer)) / sum(real * (1 + (answer_weight-1)*answer))`.
Prompttokens bleiben enthalten, Padding ausgeschlossen. Gewichteter Trainingsloss
ist zwischen Varianten nicht vergleichbar; die Auswertung bleibt für alle identisch.
Die Wiederaufnahmesignatur wird geändert, damit der reguläre Trainer diese veränderte
Zielfunktion nicht unbemerkt als unveränderten historischen Lauf fortsetzt.

Vorab prüft ein GPU-Kontrolllauf mit dem echten Elterncheckpoint zwei Updates gegen
den bisherigen Produktionsschritt, einschließlich Modell und aller Optimiererarrays.
Für die Kontrolle gelten die vorhandenen Toleranzen rtol=5e-4 und atol=3e-6.
CPU-Tests prüfen Padding/Gewichtung, Gruppentrennung, Vergleichs- und Auswahlregeln.

## Auswertung und Grenzen

Die Auswahlstichprobe enthält bis zu acht deterministisch per Hash gezogene
Entwicklungsaufgaben je Quelle aus der historischen 886er-Suite. Bekannte auffällige
Originalreferenzen werden vor Ergebniszugriff ausgeschlossen. Die zweite Stichprobe
zieht bis zu acht andere Entwicklungsgruppen je Quelle, außerhalb aller historischen
886er-Gruppen und außerhalb der Auswahlstichprobe. Beide bleiben von Trainingsgruppen
getrennt. Tatsächliche Abdeckung und Ausschlüsse stehen in `suite-audit.json`.

Die Gegenprüfung ist kein unangetasteter externer Test: Einzelne Entwicklungsaufgaben
können früher in Inline-Dev-Loss eingegangen sein. LiveCodeBench, IFBench und BBEH
werden nicht geladen. Code-/SQL-Ausführung und offene Textqualität werden in dieser
kurzen Runde nicht bewertet; ihre Referenz-Antwortverluste werden separat ausgewiesen.

Primär: mittlere Quellengenauigkeit innerhalb jeder bewertbaren Fähigkeitsgruppe,
dann gleich gewichtetes Mittel über diese Gruppen. Sekundär: Referenz-Antwortloss.
Erfolg im Screening verlangt mindestens zwei Prozentpunkte Verbesserung gegen die
passende Baseline in **beiden** Datenreihenfolgen und höchstens fünf Prozentpunkte
mittleren Rückgang in jeder Gruppe. Unter den Kandidaten wird zuerst Erfüllung des
Kriteriums, dann mittlere Genauigkeitsverbesserung, dann niedrigere Lossänderung
verwendet. Auch ohne bestandene Schwelle wird der beste Kandidat zur Gegenprüfung
ausgewählt; das begründet keine Empfehlung. Die Gegenprüfung verwendet dieselbe
Erfolgsschwelle und beide passenden Baselines. Alle Resultate bleiben sichtbar.

Kleine Stichprobe, kurze Anpassung und gemeinsame Elterngewichte erlauben nur
explorative Hinweise. Es wird keine statistische Signifikanz behauptet. Eine
Bestätigung über längere Laufzeit, andere Modellgrößen und unabhängige Trainingsseeds
wäre ein eigener späterer Versuch.

## Betrieb

- Maximal 60 Minuten gesamte aktive Kampagnen-Wandzeit einschließlich Kontrollen,
  Kompilierung, Checkpoints und GPU-Auswertungen. Dies begrenzt die GPU-Zeit konservativ.
- Kontrolle höchstens 40 Sekunden; jeder Trainingsprozess höchstens 360 Sekunden,
  mit zwölf Sekunden Reserve zum Speichern; Auswertungsprozess höchstens 130 Sekunden
  (davon 120 für Generierung und Antwortloss). Die globale Frist hat Vorrang.
- GPU-Jobs laufen seriell mit bestehender GPU-Sperre. Keine Fristerneuerung,
  automatischen Wiederholungen oder Fortsetzungen bei Fehlern. Unvollständige
  Arbeit/Auswertung darf keinen Kandidaten bestätigen.
- Ein `STOP` im Kampagnenverzeichnis stoppt den aktiven Kindprozess und weitere Arbeit.
  Der Supervisor verhindert Schlafen über `caffeinate`; Leistungseinstellungen bleiben
  unverändert. PowerWatch läuft unabhängig weiter.
- Start über `run_slm.py`, Monitoring `light`, zehn Aufwärmschritte, 60s-Zwischenstände.
  `RUN_CONDITIONS.json` erfasst die aktuellen Einstellungen; tatsächliche Tokens und
  gemessene Laufzeiten sind für Vergleiche maßgeblich.
- Plan, Quellcode, Suiten, Elterncheckpoint und Datendateien werden vor Start gehasht;
  Dateistände werden zwischen Stufen geprüft und nach GPU-Ende erneut gehasht.
  Während des Laufes bleiben diese Eingaben unverändert.
- Historische Modelle werden nur gelesen; neue Modelle stehen unter `trials/`.
  Der Elternvergleich ergänzt ausschließlich ein neues Performance-Protokoll im
  bisherigen Laufverzeichnis. Keine alten Ergebnisse oder Gewichte werden ersetzt.

Vorbereitung: `.venv/bin/python -m research.prepare --run runs/research-pilot-2026-09-09`
(CPU-only). Start: `.venv/bin/python run_slm.py --module research.campaign --run
runs/research-pilot-2026-09-09`. Der Supervisor ist absichtlich einmalig ausführbar.
