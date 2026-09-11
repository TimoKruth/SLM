# Code-Diagnose des besten Checkpoints

Abgeschlossen: 2026-09-07T08:44:04.307942+02:00

0 von 81 Aufgaben vollständig gelöst; 65 syntaktisch gültige Antworten.

| Quelle | Aufgaben | Gelöst | Syntaxfehler | Laufzeitfehler | Falsche Ausgabe | Timeout |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| apps | 66 | 0 | 12 | 29 | 25 | 0 |
| mbpp | 15 | 0 | 4 | 10 | 1 | 0 |

Ausgewählt: 85 Aufgaben. Davon 81 durch mindestens eine auf allen Originalfällen bestandene Referenzlösung bestätigt; 4 wegen fehlgeschlagener Referenzprüfung separat ausgeschlossen. 189 Original-Testfälle in den bestätigten Aufgaben. Beim Modell Abbruch pro Aufgabe nach dem ersten Fehler; keine erfundene Testfall-Erfolgsquote.

Interne Entwicklungsdiagnose: Aufgaben aus den zurückgehaltenen Original-Trainingsanteilen, nicht im Modelltraining. Der Checkpoint wurde bereits anhand von Entwicklungsloss ausgewählt. APPS nur Standard-Ein-/Ausgabe-Aufgaben; 139 APPS-Funktionsaufgaben sind nicht Teil dieses Prüflaufs. MBPP verwendet wie beim Training den Aufgabentext ohne zusätzliche Tests oder Funktionssignatur; dadurch können Schnittstellenfehler auftreten. Dies ist kein offizieller APPS-/MBPP-Score und keine Messung neuer Benchmark-Familien.

Ein greedy Versuch je Aufgabe, maximal 512 neue Tokens bei insgesamt 1.024 Tokens Kontext. 13 Antworten erreichten das Tokenlimit. Keine Reparatur, kein Umbenennen von Funktionen, keine zusätzlichen Imports. Python 3.12 in macOS-Sandbox, ohne Netzwerk, mit Prozess-, Ausgabe- und Zeitgrenzen. APPS-Ausgaben werden nach Whitespace-Tokens mit numerischer Toleranz 1e-6 verglichen; alternative gültige Ausgaben werden nicht durch Spezialchecker geprüft.

LiveCodeBench, IFBench und BBEH bleiben geschlossen. Dateien: `protocol.json`, `reference_checks.jsonl`, `results.jsonl`, `summary.json`.

Alle 81 gespeicherten Antworten wurden nochmals ausgeführt; die Fehlerklassen blieben unverändert. MBPP bestätigt die tatsächlich erreichte Assertion durch eine zufällige Abschlussmarkierung, damit ein vorzeitiges `sys.exit(0)` nicht als Erfolg zählt. 60 der syntaktisch parsebaren Antworten enthalten mindestens eine Python-Anweisung; bloße Kommentare zählen bei Parsebarkeit mit, lösen aber keine Aufgabe. Details in `rescore.json`.

Zusatzdiagnose MBPP mit einem sichtbaren Originalbeispiel pro Aufgabe (einschließlich erwarteten Funktionsnamens): 0/15 Aufgaben bestanden die jeweils zwei übrigen, nicht gezeigten Assertions. Ein eigener greedy Versuch, gleicher Checkpoint und Tokenrahmen, keine Referenzlösung im Prompt. Separat vom Hauptwert ausweisen; die Zusatzdiagnose untersucht die fehlende Schnittstellenangabe. Details in `mbpp_public_example.json`.

**Einordnung:** Der beste Checkpoint löst in dieser internen Diagnose keine vollständige Codeaufgabe. Syntaktische Parsebarkeit reicht dafür nicht aus; fünf parsebare Antworten bestehen ausschließlich aus Kommentaren bzw. enthalten keine Anweisung. Das sichtbare MBPP-Beispiel behebt die Schnittstellenunklarheit teilweise, führt aber ebenfalls zu keinem Erfolg. Für den nächsten Vergleichslauf sind vollständig spezifizierte Code-Prompts, geprüfte Referenzprogramme und der Vergleich einer breiten Mischung mit einer Code-Mischung besonders aufschlussreich. Die langfristige Benchmark-only-Hypothese ist durch diesen einzelnen kleinen Lauf weder bestätigt noch widerlegt.
