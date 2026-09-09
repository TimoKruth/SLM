# Aktueller Stand: Fortsetzung gestartet

Der Nutzer hat die Wiederaufnahme ausdrücklich beauftragt. Start: **9. September 2026, 22:05:42 Uhr**; harte Budgetgrenze: **10. September 2026, 20:12:35 Uhr**, jeweils Europe/Berlin. Das verbleibende Budget beträgt beim Start 22h 06m 53s; bei Abschluss aller geplanten Versuche endet die Studie früher.

Aktueller Zustand: `runs/parameter-study-recovery-2026-09-09/status.json`. Auftrag und aktuelle Betriebsbedingungen: `START_AUTHORIZATION.json` im selben Verzeichnis. Die historische STOP-Sperre bleibt erhalten; der eingefrorene Recovery-Code ist unverändert. Die folgende Reparaturdokumentation beschreibt den Stand **vor** dieser Startfreigabe.

---

# Metal-Fehler: Reparatur und vorbereitete Fortsetzung

Der Nutzer beauftragte am 9. September 2026 die Fehlerbehebung, damit später wieder
ein Lauf gestartet werden kann. **Keine Freigabe zur Wiederaufnahme des Trainings.**
Die alte und die neu vorbereitete Kampagne bleiben durch STOP gesperrt.

Code: `/Users/timokruth/Projekte/SLM-study-recovery`, Branch `codex/study-recovery`.
Diagnose/Prüfungen: `runs/study-repair-2026-09-09/`.
Vorbereitete Fortsetzung: `runs/parameter-study-recovery-2026-09-09/`.

## Befund

Die ursprüngliche Studie lief ab 09:45 Uhr und traf um 11:34 Uhr erstmals auf
`Unable to reach MTLCompilerService`, zunächst mit Broken pipe, danach mit
Reentrancy avoided. Alle 84 fehlgeschlagenen Stufen zeigen diese Infrastrukturklasse.
Der bisherige Supervisor probierte danach weitere Varianten durch und endete um
11:36 Uhr ohne vollständiges Paar für die Auswahl. 31 vollständige Trainingsstände
und 30 vollständige Trial-Auswertungen waren gespeichert.

Beim Reparaturauftrag war Metal wieder erreichbar. Deshalb wurden weder geteilte
macOS-Dienste beendet noch der Mac neu gestartet. Die genaue Ursache des zeitweiligen
Dienst-/Verbindungsausfalls ist nicht nachgewiesen. Eine dauerhafte Fehlerfreiheit
des Betriebssystemdienstes lässt sich durch kurze Kontrolltests nicht garantieren.

## Änderungen

- Ein kurzer GPU-Vorabtest prüft FP32, BF16, Zufallsoperationen, kompilierte Updates
  und wechselnde Inferenzlängen, bevor reguläre Arbeit beginnt.
- GPU-Dienst-/Verbindungsfehler und Speichermangel werden von Fehlern einer einzelnen
  Modellvariante unterschieden. Sie sind keine schlechten Benchmark-Ergebnisse.
- Nach einem GPU-Verbindungsfehler wird der Kindprozess vollständig beendet. Ein
  neuer, kurzer Health-Prozess öffnet nach zwei Sekunden eine frische Metal-Verbindung.
  Nur bei Erfolg wird dieselbe Stufe einmal erneut versucht; die fehlgeschlagene
  Ausgabe bleibt unter `attempts/` erhalten. Historische Elternmodelle werden dabei
  niemals verschoben oder verändert.
- Wiederherstellung und Wiederholung zählen vollständig gegen die ursprüngliche
  Stufenfrist und das restliche Gesamtbudget. Die Wiederholung bekommt nur Restzeit;
  ihre wissenschaftlichen Jobparameter bleiben identisch.
- Maximal zwei automatische GPU-Wiederherstellungsversuche pro Kampagne. Bleibt der
  Dienst gestört, entsteht eine `paused_infrastructure`-Pause mit STOP. Weitere
  Parameter werden nicht mehr gestartet. Kein automatischer Mac-Neustart.
- Drei aufeinanderfolgende andere Fehler insgesamt oder innerhalb derselben
  Stufenart führen ebenfalls zur Diagnosepause. So werden systematische
  Auswertungsfehler nicht durch zwischendurch erfolgreiche Trainings überdeckt.
- Ein STOP wird bereits vor Prozessstart/Budgetbeginn respektiert.

Eine Stufenwiederholung startet ein unvollständiges Training gegebenenfalls erneut
ab seinem definierten Elternmodell innerhalb der Restfrist. Es gibt weiterhin keine
Garantie, beliebige mitten im GPU-Schritt verlorene Arbeit wiederherzustellen.
Vollständig gespeicherte Trainings und gültige Auswertungen werden gezielt übernommen.

## Kontrollierte Fortsetzung

`study.recovery` prüft die alten Eingabehashes und die unveränderten numerischen
Kernfunktionen. Vollständige Trainings werden auf Job, Signatur, Tokenziel,
Sampler-Endzustand, Modellkonfiguration und vorhandene Checkpointdateien geprüft.
Auswertungen müssen vollständig sein und exakt zu Modell-, Tokenizer- und Suitehash
passen. Nur validierte Ergebnisse werden übernommen; Teilresultate bleiben im
historischen Lauf erhalten und werden nicht als gültige Auswertung verwendet.

Die neue Kampagne erhält unabhängige APFS-Kopien der gültigen Modelle/Optimierer und
Ergebnisse, keine beschreibbaren Hardlinks. Fehlgeschlagene Verzeichnisse werden nicht
als Trainingszustände übernommen. Die Suiten bleiben bytegleich: keine neue Auswahl
von Aufgaben aufgrund der bisherigen Ergebnisse. Rechenschritte und Modellmathematik
bleiben unverändert; nur Überwachung, Wiederverwendung und Prozessfristen ändern sich.

Das bereits verbrauchte Budget von 6666,1948 Sekunden wird auf 6667 Sekunden
aufgerundet. Zusätzlich werden konservativ 120 Sekunden für Reparaturprüfungen und
Vorbereitung abgezogen. **Restbudget: 79.613 Sekunden = 22h 06m 53s**, keine neuen
24 Stunden. Spätere Fortsetzungen berücksichtigen die kumulierte Nutzung erneut.
Die Pause selbst ist keine Trainingszeit.

Die einmalige Startfreigabe bleibt ausstehend. READY.json und recovery-audit.json
zeigen die validierten übernommenen und noch offenen Versuche. Nach ausdrücklichem
Startauftrag kann ausschließlich der STOP der neuen Kampagne entfernt und diese
über `run_slm.py --module study.campaign` gestartet werden. Der historische STOP bleibt.

## Verifikation

- CPU-Tests prüfen Fehlerklassifikation, Restbudget, Schutz historischer Pfade,
  Modell-/Suitezuordnung und die echte Supervisor-Steuerung mit simulierten
  Metal-Ausfällen. Bei dauerhaftem Fehler startet kein zweiter Parameter.
- Zwei neue GPU-Prozesse prüfen jeweils fünf Sekunden lang FP32/BF16, kompilierte
  Updates und unterschiedliche Eingabelängen. Ergebnisse: `health-before/health.json`
  und `health-second/health.json` im Diagnoseverzeichnis.
- Ein Kontrolllauf am wirklichen 27,3M-Elterncheckpoint vergleicht akkumulierte
  Updates mit dem Produktionsschritt einschließlich Optimiererarrays:
  `real-control/control.json`.
- Die ursprünglich gescheiterte Auswertung wird auf einer unabhängigen Kopie des
  gespeicherten Modells mit derselben 473er-Suite nachgeprüft. Nur eine vollständig
  bestandene, hashvalidierte Auswertung wird zusätzlich übernommen.

Alle GPU-Kontrollen laufen mit Monitoring light durch run_slm.py. Es wird kein
reguläres Training, kein Supervisor und keine Warteschlange für die Fortsetzung gestartet.
