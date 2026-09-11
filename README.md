**SLM aus Benchmarks — Projektskizze**

Stand: **11. September 2026**. Größenvergleich, Fortsetzungen und Parameterstudien einschließlich des letzten 2×2-Langzeitvergleichs sind abgeschlossen. Es gibt noch keinen bestätigten allgemeinen Transfergewinn. Aktuelle [Erkenntnisse](ERKENNTNISSE.md), [versionierte Ergebnisberichte](results/2026-09-11/INDEX.md) und [Sicherung/Wiederherstellung](SICHERUNG.md) sind die zentralen Einstiegspunkte. Die folgenden Absätze enthalten auch die ursprüngliche Projektskizze und historische Pilotstände.

Wir untersuchen, ob die Aufgabenvielfalt bestehender Sprachmodell-Benchmarks ausreicht, um ein kleines Sprachmodell von Grund auf zu trainieren, das auf unbekannte Aufgaben transferiert. Die Hypothese: Aufgabenstellungen, Kontext, Referenzantworten und vorhandene Lösungswege enthalten verdichtete Lernsignale für Sprache, Schlussfolgern und Programmieren. Ein Netz könnte daraus wiederverwendbare Fähigkeiten entwickeln.

Das Hauptmodell startet mit zufälligen Gewichten. Es erhält ausschließlich nachvollziehbare Trainingsanteile öffentlicher Aufgabendatensätze, keine externen Text- oder Codekorpora, keine vortrainierten Gewichte und keine zusätzlich von großen Modellen erzeugten Lösungen. Auch der Tokenizer wird nur auf dem Trainingsmaterial gelernt. „Alle Benchmarks“ bezeichnet die langfristige Suchrichtung; begonnen wird mit einer kuratierten, deduplizierten Auswahl. Reine Sprachkorpora werden nicht dadurch zulässig, dass sie auch als Perplexitätsbenchmark verwendet werden.

Auf dem vorhandenen M1 Max mit 64 GB Unified Memory beginnen wir mit ungefähr 100–150 Millionen Parametern. Erst nach Messung von Trainingsgeschwindigkeit, Datenumfang und Lernkurven folgt gegebenenfalls ein Modell mit 300–350 Millionen Parametern. Diese Größen sind Planungsvorschläge, keine bereits vermessenen Konfigurationen.

Als drei voneinander deutlich verschiedene Abschlusstests sind vorgesehen:

- **LiveCodeBench:** ausführbaren Python-Code für unbekannte Programmieraufgaben erzeugen.
- **IFBench:** neue, automatisch überprüfbare Ausgabevorgaben befolgen.
- **BIG-Bench Extra Hard:** vielfältige sprachlich formulierte Denkaufgaben lösen.

Diese Tests samt abgeleiteten Daten bleiben vom Training und von der Modellauswahl ausgeschlossen. Der nächste Vergleich verwendet dieselbe breite Mischung mit zwei Gewichtungen: gleiche Anteile je Fähigkeitsgruppe beziehungsweise je Quelle. Die Entwicklung wird nach Fähigkeiten getrennt gemessen.

Ein interessantes Ergebnis wäre reproduzierbarer Transfer auf unbekannte Aufgaben in unterschiedlichen Bereichen, etwa Lesen, Schlussfolgern, Mathematik oder Programmierung. Welche Fähigkeiten sich tatsächlich entwickeln, bleibt offen.

Die Einordnung verwandter Arbeiten mit Primärquellen steht in [RECHERCHE.md](RECHERCHE.md). Hardwareabschätzung, Datentrennung und Auswertung sind in [EXPERIMENT.md](EXPERIMENT.md) konkretisiert.

Der erste Pilot nutzt 10 Datensätze, 230.474 Trainingspaare und 43.316.110 gespeicherte Trainingstokens. Das zufällig initialisierte Modell hat 97.536.768 Parameter. Der Nachtlauf endete am 7. September um 05:50 Uhr nach 94.774.946 verarbeiteten Trainingstokens (6 Stunden 34 Minuten). Die beste Entwicklungsmessung stammt aus Schritt 42.899 bei 75.096.066 Tokens.

Die ausführbare [Code-Diagnose](runs/code-eval-2026-09-07/REPORT.md) dieses besten Checkpoints ergab **0 von 81 gelösten Aufgaben** (66 APPS, 15 MBPP). 65 Ausgaben sind syntaktisch parsebar, davon enthalten 60 mindestens eine Python-Anweisung. Die Original-Referenzlösungen bestehen alle 189 Testfälle dieser 81 Aufgaben; vier Aufgaben mit fehlgeschlagener Referenzprüfung werden separat ausgeschlossen. Ein zusätzlicher MBPP-Versuch mit je einem sichtbaren Beispiel löst ebenfalls 0 von 15 Aufgaben auf den verbleibenden Assertions. Die drei externen Transfer-Benchmarks bleiben geschlossen.

Der aufbereitete Pool unter `data/v2/` umfasst 1.095.239 Trainingspaare und 190.909.332 Tokens aus **24 Quellen** und wird im [zweiten Lauf](LAUF_2.md) verwendet. Die dafür zusätzlich gesammelten 14 Quellen stehen im [Benchmark-Katalog](BENCHMARKS.md).

Während Lauf 2 wurden acht weitere Quellen separat geladen. Die geprüfte neue Datenversion enthält **32 Quellen und 1.416.390 Trainingspaare**. Kompilierter Trainingsschritt und KV-Cache haben CPU-Prüfungen und eine GPU-Prüfung mit Wiederaufnahme und echten Prompts bestanden. Aktuelles Protokoll: [Breites Lernen](BREITES_LERNEN.md); historische Vorbereitung: [Vorbereitung 3](VORBEREITUNG_3.md).

Das [Performance-Monitoring](PERFORMANCE.md) ist für **künftige Läufe im Modus `light` aktiviert**. Neue Läufe über `.venv/bin/python run_slm.py --run runs/<neuer-lauf> --data data/v2` starten. Die Projektvorgaben stehen in `run_defaults.json`; mit `--monitoring off` lässt sich die Messung ausdrücklich ausschalten. Training und zugehörige Auswertung erhalten eigene Performance-Berichte. Der laufende Versuch bleibt unverändert; ein separater GPU-Test des Messaufwands ist nach den laufenden Aufgaben eingeplant.

## Lizenz

Das Repository enthält Quellcode und Projektdokumentation. Datensätze (`data/`), lokale Trainingsläufe und Modellgewichte (`runs/`) sowie Laufprotokolle werden nicht mitveröffentlicht. Verweise auf `runs/` beziehen sich auf lokale Ergebnisse und sind im GitHub-Repository nicht verfügbar.

Der projektspezifische Quellcode steht unter der **GNU General Public License v3.0** (`GPL-3.0-only`). Der vollständige Lizenztext steht in [LICENSE](LICENSE).

Verwendete Datensätze und Abhängigkeiten unterliegen ihren jeweiligen eigenen Lizenzen.
