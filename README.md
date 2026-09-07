**SLM aus Benchmarks — Projektskizze**

Stand: 7. September 2026. Status: Erster Trainingslauf und Code-Diagnose abgeschlossen. Der [zweite Lauf](LAUF_2.md) wurde am 7. September um 09:19 Uhr für sechs Stunden gestartet. Betriebsdetails stehen in [NACHTLAUF.md](NACHTLAUF.md).

Wir untersuchen, ob die Aufgabenvielfalt bestehender Sprachmodell-Benchmarks ausreicht, um ein kleines Sprachmodell von Grund auf zu trainieren, das auf unbekannte Aufgaben transferiert. Die Hypothese: Aufgabenstellungen, Kontext, Referenzantworten und vorhandene Lösungswege enthalten verdichtete Lernsignale für Sprache, Schlussfolgern und Programmieren. Ein Netz könnte daraus wiederverwendbare Fähigkeiten entwickeln.

Das Hauptmodell startet mit zufälligen Gewichten. Es erhält ausschließlich nachvollziehbare Trainingsanteile öffentlicher Aufgabendatensätze, keine externen Text- oder Codekorpora, keine vortrainierten Gewichte und keine zusätzlich von großen Modellen erzeugten Lösungen. Auch der Tokenizer wird nur auf dem Trainingsmaterial gelernt. „Alle Benchmarks“ bezeichnet die langfristige Suchrichtung; begonnen wird mit einer kuratierten, deduplizierten Auswahl. Reine Sprachkorpora werden nicht dadurch zulässig, dass sie auch als Perplexitätsbenchmark verwendet werden.

Auf dem vorhandenen M1 Max mit 64 GB Unified Memory beginnen wir mit ungefähr 100–150 Millionen Parametern. Erst nach Messung von Trainingsgeschwindigkeit, Datenumfang und Lernkurven folgt gegebenenfalls ein Modell mit 300–350 Millionen Parametern. Diese Größen sind Planungsvorschläge, keine bereits vermessenen Konfigurationen.

Als drei voneinander deutlich verschiedene Abschlusstests sind vorgesehen:

- **LiveCodeBench:** ausführbaren Python-Code für unbekannte Programmieraufgaben erzeugen.
- **IFBench:** neue, automatisch überprüfbare Ausgabevorgaben befolgen.
- **BIG-Bench Extra Hard:** vielfältige sprachlich formulierte Denkaufgaben lösen.

Diese Tests samt abgeleiteten Daten bleiben vom Training und von der Modellauswahl ausgeschlossen. Verglichen werden eine breite Benchmark-Mischung, ausschließlich Codeaufgaben und eine Mischung ohne Code. Dadurch lässt sich prüfen, ob Aufgabenvielfalt beim Coden hilft und wie weit Transfer zwischen Bereichen reicht.

Ein interessantes erstes Ergebnis wäre reproduzierbarer Transfer auf unbekannte Aufgaben. Ein weitergehendes Ziel wären brauchbare Lösungen einfacher Python-Aufgaben. Ob daraus „mittelmäßiges Coden“ im Alltag entsteht, bleibt eine offene Forschungsfrage.

Die Einordnung verwandter Arbeiten mit Primärquellen steht in [RECHERCHE.md](RECHERCHE.md). Hardwareabschätzung, Datentrennung und Auswertung sind in [EXPERIMENT.md](EXPERIMENT.md) konkretisiert.

Der erste Pilot nutzt 10 Datensätze, 230.474 Trainingspaare und 43.316.110 gespeicherte Trainingstokens. Das zufällig initialisierte Modell hat 97.536.768 Parameter. Der Nachtlauf endete am 7. September um 05:50 Uhr nach 94.774.946 verarbeiteten Trainingstokens (6 Stunden 34 Minuten). Die beste Entwicklungsmessung stammt aus Schritt 42.899 bei 75.096.066 Tokens.

Die ausführbare [Code-Diagnose](runs/code-eval-2026-09-07/REPORT.md) dieses besten Checkpoints ergab **0 von 81 gelösten Aufgaben** (66 APPS, 15 MBPP). 65 Ausgaben sind syntaktisch parsebar, davon enthalten 60 mindestens eine Python-Anweisung. Die Original-Referenzlösungen bestehen alle 189 Testfälle dieser 81 Aufgaben; vier Aufgaben mit fehlgeschlagener Referenzprüfung werden separat ausgeschlossen. Ein zusätzlicher MBPP-Versuch mit je einem sichtbaren Beispiel löst ebenfalls 0 von 15 Aufgaben auf den verbleibenden Assertions. Die drei externen Transfer-Benchmarks bleiben geschlossen.

Der aufbereitete Pool unter `data/v2/` umfasst 1.095.239 Trainingspaare und 190.909.332 Tokens aus **24 Quellen** und wird im [zweiten Lauf](LAUF_2.md) verwendet. Die dafür zusätzlich gesammelten 14 Quellen stehen im [Benchmark-Katalog](BENCHMARKS.md).

Während Lauf 2 wurden **acht weitere Quellen mit 356.312 Original-Trainingszeilen** separat geladen. Damit sind **32 Benchmark-Datensätze gesammelt**, weiterhin 24 im laufenden Training. Zwei Performance-Kandidaten haben CPU-Prüfungen bestanden; ein GPU-Vergleich wartet auf das Ende von Training und Auswertung. Details und Statuspfade: [Vorbereitung für spätere Versuche](VORBEREITUNG_3.md).

## Lizenz

Das Repository enthält Quellcode und Projektdokumentation. Datensätze (`data/`), lokale Trainingsläufe und Modellgewichte (`runs/`) sowie Laufprotokolle werden nicht mitveröffentlicht. Verweise auf `runs/` beziehen sich auf lokale Ergebnisse und sind im GitHub-Repository nicht verfügbar.

Der projektspezifische Quellcode steht unter der **GNU General Public License v3.0** (`GPL-3.0-only`). Der vollständige Lizenztext steht in [LICENSE](LICENSE).

Verwendete Datensätze und Abhängigkeiten unterliegen ihren jeweiligen eigenen Lizenzen.
