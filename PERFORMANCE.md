# Optionales Performance-Monitoring

Stand: 7. September 2026. Implementiert unter `slm_perf/`. Auf Nutzerwunsch ist **`light` für künftige Läufe über den Projektstarter aktiviert**. Die Vorgabe steht in `run_defaults.json`. Der laufende Sechs-Stunden-Versuch und sein bereits geplanter Performance-Vergleich verwenden unveränderten Quellcode und unveränderte Daten.

## Was gemessen wird

| Bereich | Leichtgewichtige Messung | Zusätzliche Detailansicht |
| --- | --- | --- |
| Start und Datenladen | Prozessstart, Prüfsummen, Sampler-Initialisierung, Datei- und Parquet-Lesen | Python-Aufrufprofil einschließlich nativer Aufrufe |
| Datenaufbereitung | Konvertierung, Code-Überlappungsprüfung, Tokenizer, Arrow-Konvertierung, Dateiausgabe | Aufgerufene Python-Funktionen mit Eigen- und Gesamtzeit |
| Training | Batch-Packing, Array-Erstellung, vollständiger Schritt, Graph-Aufbau für Forward/Backward, Gradienten-Clipping, Optimierer-Update, bestehendes `mx.eval`, Skalarauslesen | Aufrufprofil; GPU-Kernels separat im Metal-Trace |
| Entwicklungsmessung | Gesamte Evaluation, Sampler, Forward-Graph und bestehende Auswertung der Summen | Aufrufprofil und Host-Timeline |
| Checkpoints | Gesamtdauer, Gewichte, Optimiererzustand, JSON, Kopieren, Aufräumen und Wiederaufnahme | Details der tatsächlich aufgerufenen I/O-Funktionen |
| Generierung und Code-Test | Tokenizer, Modell-Graph, bestehendes synchronisierendes Token-Auslesen, Generierung, Scoring, Sandbox-Prozess und Wartezeit | Aufrufprofil; GPU-Kernels im separaten Diagnoseversuch |
| Supervisor und Bericht | Teilprozesse, Wartezeiten, Berichtserstellung und Dateiausgabe | Eigene Berichte je Kindprozess |

Die Phasen bilden einen Baum. **Inklusive Zeit** enthält Kindphasen; **Eigenzeit** zieht deren Zeit ab. Der Bericht zeigt auch Eigenzeitanteile, Aufrufzahlen, Mittelwerte und ungefähre p50/p95-Werte. Inklusive Zeiten dürfen nicht addiert werden. Eigenzeit kann auch Wartezeit enthalten und ist keine reine CPU-Rechenzeit.

Bei MLX bedeutet ein Python-Aufruf häufig zunächst nur Graph-Aufbau. GPU-Ausführung ist erst an bestehenden `eval`-, `item`- oder Speichergrenzen enthalten. Das leichte Monitoring fügt **keine zusätzlichen GPU-Synchronisationen** hinzu. Es behauptet daher beispielsweise nicht, die GPU-Zeit des Backward-Passes allein aus der Dauer von `value_and_grad` zu kennen. Siehe [MLX Lazy Evaluation](https://github.com/ml-explore/mlx/blob/main/docs/src/usage/lazy_evaluation.rst).

`detail` ergänzt ein zeitlich begrenztes cProfile-Aufrufprofil aller tatsächlich erreichten Python-Funktionen und nativen Aufrufe. Dazu gehören auch Modellteile und Bibliotheksfunktionen außerhalb der benannten Phasen. Der standardmäßige Zeitraum von 30 Sekunden endet kooperativ an der nächsten instrumentierten Grenze; ein langer blockierender Aufruf kann ihn überschreiten. Nicht erreichte Pfade haben keine Messwerte. Es handelt sich weder um Zeilenprofiling noch um einen GPU-Kernel-Timer.

## Einschalten und ausschalten

Der verbindliche Einstieg für neue reguläre Läufe ist jetzt `run_slm.py`. Er aktiviert `light`, übernimmt zehn Aufwärmschritte und 60 Sekunden zwischen Zwischenständen und legt bei jedem Start einen eigenen Ordner unter `<Lauf>/performance/<Zeitstempel-ID>/` an. Auch bei Wiederaufnahme bleiben bisherige Messungen erhalten. Mit `--monitoring off` wird die Messung ausdrücklich ausgeschaltet.

Direkte technische Befehle wie `python -m slm.train ...` umgehen diese Projektvorgabe und bleiben ohne Monitoring. Auch der technische Launcher `python -m slm_perf run` behält seinen bisherigen Default `off`; der Projektstarter übergibt den gewünschten Modus ausdrücklich. Dadurch bleiben laufende Prozesse und die geplanten A/B-Diagnosen unverändert.

Für einen **zukünftigen** Gesamtlauf mit Training, Bericht und Code-Auswertung:

```sh
.venv/bin/python run_slm.py \
  --run runs/naechster-lauf \
  --data data/v2
```

Dieser Befehl startet tatsächlich einen neuen Sechs-Stunden-Versuch. Er wurde hier nicht ausgeführt. Das Monitoring wird bei diesem Einstieg automatisch an die überwachten Python-Teilprozesse weitergereicht. Sandbox-Codeprogramme bleiben unverändert. Nicht gleichzeitig mit einem anderen SLM-GPU-Job starten; der Launcher prüft dies vor dem Start.

Unterstützte Trainings-/Auswertungsstarts über `slm_perf run`, der Optimierungsvergleich und die Monitoring-Kalibrierung reservieren außerdem dieselbe atomare GPU-Sperre pro Benutzer (`~/.cache/benchmark-slm/gpu-lease.lock`). Sie gilt über verschiedene Checkouts hinweg und bleibt bis zum Ende des jeweiligen GPU-Prozesses bestehen, auch bei `--mode off`. Die Kalibrierungs-Queue reserviert sie vor dem Prozessstart und reicht den offenen Dateideskriptor an ihr Kind weiter. Überwachte Supervisoren lassen ihre GPU-Teilprozesse die Sperre jeweils reservieren. Bei ausgeschaltetem Monitoring hält der Supervisor die Sperre für seinen gesamten Lauf über den unveränderten Programmeinstieg hinweg. Bereits laufende oder direkt mit `python -m slm.train` gestartete Altprozesse sowie fremde Programme nehmen nicht an dieser Sperre teil. Für diese bleiben Prozessabfragen und der Abbruch der Kalibrierung beim Erkennen eines Konkurrenten erforderlich.

Der Projektstarter `run_slm.py` unterstützt über `--module` die Einstiegspunkte `slm.sixhour` (Standard), `slm.overnight`, `slm.train`, `slm.report`, `slm.code_eval` und `slm.interface_eval`. Sein Modusschalter heißt `--monitoring off|light|detail`; weitere Argumente wie `--data` werden direkt weitergereicht.

Der **technische Launcher `.venv/bin/python -m slm_perf run`** unterstützt zusätzlich unter anderem `slm.collect` und `slm.prepare_v2`. Bei diesem Launcher stehen die ursprünglichen Modulargumente hinter `--`. Seine Monitoring-Optionen sind die folgenden; sie sind keine direkten Optionen von `run_slm.py`. Bestehende Schutzregeln, etwa gegen das Überschreiben eingefrorener Daten, gelten weiterhin.

- `--mode off`: ursprünglicher Codepfad, keine Monitoring-Dateien. Zum Ausschalten alternativ den normalen bisherigen Befehl verwenden.
- `--mode light`: benannte Phasen, feste Speicherobergrenzen pro Histogramm und begrenzter Ereignisverlauf; standardmäßig Datei-Snapshot alle 60 Sekunden an einer Phasengrenze und beim Abschluss.
- `--mode detail --detail-seconds 30`: zusätzlich begrenztes Python-Aufrufprofil und maximal 10.000 Host-Trace-Ereignisse. Für Diagnoseversuche vorgesehen; eigener Messmodus beim Vergleich.
- `--warmup-steps 10`: erste zehn Trainingsschritte je Prozess getrennt von den nachfolgenden Schritten.
- `--flush-seconds 60`: Abstand der Zwischenstände. Häufigere Ausgabe erhöht den Messaufwand.

Die Wahl des Modus erfolgt beim Start. Beim technischen Launcher für eine Wiederaufnahme einen **neuen Monitoring-Ausgabeordner** verwenden; der Projektstarter erzeugt ihn automatisch. Vorhandene Messungen werden nicht überschrieben. Ein Schreibfehler beim laufenden Monitoring deaktiviert weitere Mess-Hooks und beendet auch ein aktives Detailprofil. Er wird festgehalten, soweit die Ausgabe noch möglich ist. Das Training bekommt diesen Monitoring-I/O-Fehler nicht als Ausnahme weitergereicht. Eigene Trainings- oder Checkpoint-Fehler bleiben unverändert sichtbar.

## Berichte und Vergleiche

Jeder überwachte Prozess erzeugt:

- `timings.json`: Zeiten, Histogrammwerte, Ereigniszähler, Fehler, Messkonfiguration, Daten-/Modellkonfiguration, Softwareumgebung, Quellcode-Prüfsummen und tatsächlich instrumentierte Stellen.
- `REPORT.md`: Phasentabelle mit Eigenanteilen; bei Supervisoren Links auf die Berichte der Teilprozesse.
- Bei `detail`: `python.prof`, `python-functions.json` und `trace.json`. Der Trace nutzt das Chrome-Trace-Format und enthält Host-Zeiten.

Die bereits vom Training berechneten Token-, Loss-, Lernraten- und Speicherwerte werden übernommen. Das Monitoring liest dafür keine weiteren GPU-Tensoren aus. Der Gesamtdurchsatz berücksichtigt Start, Entwicklungsmessungen und Checkpoints; die Schrittzeiten weisen Aufwärmen separat aus. Beim Supervisor sind Kindprozesszeiten bereits in dessen Wartezeit enthalten. Für den Trainingsvergleich die beiden **Trainings-Teilprozessberichte** auswählen, statt Kind- und Elternzeiten zu addieren.

```sh
.venv/bin/python -m slm_perf compare \
  runs/baseline/performance/BASELINE-SITZUNG/children/000-slm.train/timings.json \
  runs/kandidat/performance/KANDIDAT-SITZUNG/children/000-slm.train/timings.json \
  --output runs/performance-vergleich.json
```

Die tatsächlichen Kindordner stehen im Supervisor-Bericht; bei Wiederholungen können weitere Nummern entstehen. Der Vergleich zeigt Änderungen der Phasenmittelwerte, hinzugekommene/entfallene Phasen und das Verhältnis der mittleren Trainingsschrittzeiten nach dem Aufwärmen. Abweichende Messmodi, Aufwärmgrenzen, Monitoring-Versionen, Daten-/Modellkonfigurationen oder Softwareumgebungen werden als inkompatibel markiert; das Kommando beendet sich dann mit Exitcode 2. Die Differenzen bleiben zur Diagnose gespeichert und sind kein bestätigter Geschwindigkeitsgewinn. Änderungen am eigentlichen Modell- oder Trainingscode werden kenntlich gemacht, sind für einen A/B-Vergleich aber ausdrücklich erlaubt.

Vergleiche brauchen weiterhin ausreichend Schritte, dieselbe Arbeitsmenge sowie ähnliche Energieversorgung, Temperatur und konkurrierende Systemlast. Ein geänderter Modelloutput kann beispielsweise Generierung früher beenden. Ein kürzerer Programmlauf ist deshalb allein noch kein Beleg für schnelleren Code. Einmalige Startkosten und laufende Kosten getrennt beurteilen.

## Eigenen Messaufwand prüfen

Eine kostenlose aktive Messung ist nicht möglich. Geschätzte Hook-Buchhaltung und Monitoring-Dateiausgabe stehen separat im Bericht, werden aber **nicht rechnerisch vom Durchsatz abgezogen**. Sie erfassen nicht sämtliche indirekten Einflüsse wie Cache- oder Profiler-Effekte.

Ein CPU-Mikrotest mit fünf Wiederholungen von jeweils 20.000 leeren, verschachtelten Spans ergab einen Median von **1,66 µs je Span** auf diesem Rechner. Das ist kein Nachweis des Gesamtaufwands beim GPU-Training. Rohwerte: `runs/monitoring-2026-09-07/hook-cost.json`.

Die Queue `local.slm.monitoring-20260907` wartet zuerst auf das Ende des laufenden Trainings samt Auswertung und anschließend auf den bereits geplanten Vergleich unter `runs/performance-2026-09-07/`. Erst danach folgt ein separater A/B-Versuch:

- Gleiches Modell und gleicher gespeicherter Checkpoint, identische Datenbatches und frische identische AdamW-Zustände.
- `off`, `light` und `detail` in rotierender Reihenfolge, jeweils drei Wiederholungen mit 20 Schritten; davon fünf Aufwärmschritte.
- Identische feste Lernratenfolge; Vergleich aller Loss-Werte und Prüfsummen sämtlicher Gewichte und Optimiererzustände.
- Median, Streuung der Wiederholungen und beobachteter Zusatzaufwand. Unter 1 % bei `light` ist ein zunächst angestrebter, zu prüfender Wert, keine zugesicherte Eigenschaft.
- Danach optional zwei gesonderte Schritte für einen Metal-Kernel-Trace. Er fließt nicht in die A/B-Zeitmessungen ein und verändert keine Trainingsgewichte auf der Platte.

GPU-Kernels und ihre Abhängigkeiten lassen sich aus `kernels.gputrace` in Xcode untersuchen. Ein Trace kann scheitern, obwohl die Zeitmessung erfolgreich ist; dies wird separat dokumentiert. Grundlage: [offizielle MLX-Metal-Profiling-Dokumentation](https://ml-explore.github.io/mlx/build/html/dev/metal_debugger.html).

Queue-Plan und Status: `runs/monitoring-2026-09-07/plan.json` und `status.json`. GPU-Ergebnisse entstehen unter `calibration/`; aktuell liegen noch keine GPU-Overhead-Ergebnisse vor. Die Kalibrierung erhält zehn Minuten Laufzeit; nötiges Aufräumen folgt anschließend und wartet pro eigenem Kind höchstens fünf Sekunden auf reguläres Ende, bevor es den Prozess erzwingend beendet und nochmals höchstens fünf Sekunden wartet. Bleibt ein Kind danach aktiv, meldet die Queue `cleanup_failed` und versucht trotzdem, das andere Kind aufzuräumen. Ein noch lebender Kalibrierungsprozess behält seine geerbte GPU-Sperre bis zum tatsächlichen Prozessende. Die Queue verfällt am 7. September um **18:34 Uhr**. Geänderte geplante Quelldateien verhindern den Start. Ein `STOP` im Queue-Verzeichnis bricht den Versuch ab beziehungsweise verhindert seinen Start. Während der Kalibrierung prüft die Queue alle zwei Sekunden auf weitere SLM-GPU-Prozesse und beendet die Kalibrierung, falls einer auftaucht. Für nicht kooperierende Alt-/Fremdprozesse bleibt ein kurzes gleichzeitiges Zeitfenster möglich. Fehler und Unterbrechungen räumen sowohl Kalibrierungsprozess als auch `caffeinate` auf. Während dieses begrenzten Aufräumabschnitts werden SIGTERM und SIGINT blockiert und erst danach zugestellt; die vorherige Signalmaske wird wiederhergestellt. Ungültige JSON-Statusformen gelten als noch nicht bereit.

Der Queue-Einstieg lautet ausschließlich `.venv/bin/python -m slm_perf.after_idle`. Ein Dateiaufruf wie `python slm_perf/after_idle.py` endet vor dem Zugriff auf Queue-Dateien mit einem Hinweis auf den korrekten Paketaufruf.

Die aktuelle Trainings-Lernrate hängt teilweise von der verstrichenen Zeit ab. Jede zusätzliche Messarbeit kann daher in einem zeitgesteuerten echten Lauf Lernraten oder die Zahl erreichter Schritte geringfügig verändern. Der feste Lernratenplan im A/B-Test trennt diesen Effekt von Änderungen der eigentlichen Berechnung. Für künftige reguläre Läufe ist `light` auf Nutzerwunsch aktiviert; Optimierungen werden weiterhin nicht automatisch übernommen.

## Bisherige Verifikation

Aktuell bestehen **46 Performance- und Queue-Tests**: 43 unter `tests/performance/` (16 Runtime-, Vergleichs- und Schutztests, drei Projektstarter-Tests, zwei CPU-Trainingsäquivalenzfälle für `light` und `detail` und 22 zusätzliche Prozesssperren-/Queue-Fehlerfälle) sowie drei zusätzliche Queue-Schutztests unter `experiments/performance/test_queue.py`. Die Sitzungsnamen im Vergleichsbeispiel oben durch die tatsächlich erzeugten Ordnernamen ersetzen.

Geprüft wurden verschachtelte Zeitrechnung, Fehlerweitergabe, Abschalten einschließlich des Detailprofils bei Monitoring-Schreibfehlern, unveränderte Kontrollflüsse, begrenzte Trace-Größe, Aufwärmtrennung, Vergleichsregeln, der unveränderte Off-Einstieg, Prozessschutz und vollständige Weitergabe der Monitoring-Einstellungen an überwachte Kindprozesse. Ein echter kleiner CPU-Trainingslauf liefert sowohl mit `light` als auch mit `detail` exakt dieselben Gewichte, Optimiererzustände und Sampler-Checkpoint-Zustände wie das Original – einschließlich Wiederaufnahme und bei fixiertem zeitabhängigem Lernratenplan.

Ein zusätzlicher CPU-Probelauf über den tatsächlichen Launcher schloss **12 Schritte mit 44 verschachtelten Messpfaden** fehlerfrei ab: [Beispielbericht](runs/monitoring-2026-09-07/cpu-smoke-final/REPORT.md). Das Spielzeugmodell ist keine Geschwindigkeitsreferenz für das eigentliche Modell.

```sh
.venv/bin/python -m pytest -q tests/performance experiments/performance/test_queue.py
.venv/bin/python -m slm_perf inventory --output runs/performance-coverage.json
```

Die Inventur kompiliert die Instrumentierung für 13 unterstützte Module, ohne deren Arbeitslast auszuführen. Bei neuen Pipeline-Funktionen die Phasenabdeckung in `slm_perf/instrument.py` ergänzen und mit diesen Tests prüfen. Die Instrumentierung verändert den Python-Syntaxbaum ausschließlich im ausdrücklich überwachten Prozess im Speicher; die Dateien unter `slm/` bleiben unverändert.
