# Langer 24h-Vergleich: autorisierte parallele Ausführung

Der Nutzer hat nach dem Auftrag zum aktiven Paralleltest ausdrücklich freigegeben: „Bei erfolgreichem Paralleltest auch den 24-Stunden-Vergleich starten“.

Der 505,6s-Test unter Hochleistungsmodus führte zwei identische 3M-Token-Trainings aus, abwechselnd mit drei 60s-Abschnitten ohne SLM. Beide bestanden; Durchsatz 19.371/19.206 Tokens/s, gleiche Batches. GPU im Parallelbetrieb etwa 97%, CPU 38–39%, mindestens 35 GiB RAM verfügbar, thermischer Zustand normal und keine neuen Swap-outs. Evonn führte zwei weitere Kampagnenstufen aus. 20 vergleichbare CPU-Fit-Gruppen zeigen deskriptiv im Median etwa 9,4% längere Fit-Zeiten. Es gibt keine identische SLM-Alleinkontrolle; ein genauer gegenseitiger Durchsatzverlust ist damit nicht bestimmt. Technische Machbarkeit ist bestanden, kostenlose Parallelität nicht bewiesen. Artefakte: `runs/parallel-probe-2026-09-10/RESULT.json` und `REPORT.md`. Evonn-Prozesse wurden nicht verändert oder signalisiert.

## Umsetzung

Neuer Code in `long_study`: acht Läufe (Familien-/Quellenmischung × LR 3e-5/1e-5, zwei Datenreihenfolgen). Je 7200s Prozessbudget, einschließlich Laden, Checkpoints und 60s Abschlussreserve; ein reguläres Zeitende ist ein gültiger Modellstand, auch ohne festes Tokenziel. Die mathematischen Trainingsfunktionen werden unverändert aus `study.trial` verwendet. FP32, 27,3M-Parameter-Elternmodell, AdamW und korrigierte 32-Quellen-Daten konstant. Alle 57 bisherigen Varianten bleiben im Planungskatalog.

Vollständige Adam-/Sampler-Checkpoints alle 300s, höchstens die letzten zwei behalten. Tokenstände bei 15/30/50/75/100/150M zusätzlichen Tokens, soweit erreicht. Nicht im letzten Optimierercheckpoint enthaltene Snapshots werden bei Wiederaufnahme archiviert, damit keine künftigen oder unbestätigten Stände als Teil des wiederhergestellten Verlaufs gelten. Wiederaufnahmesignatur bindet Job, Daten und Elterngewichte. Abgeschlossene Läufe können nicht versehentlich erneut fortgesetzt werden.

Die GPU-Stufen bleiben seriell, jeweils durch `run_slm.py` und Monitoring light. Automatische GPU-Wiederherstellung maximal zweimal pro Kampagne, je Stufe höchstens ein Versuch im verbleibenden ursprünglichen Stufenbudget. Gespeicherter Optimiererstand wird dabei übernommen, sofern vorhanden. Andere Fehler inklusive Auswertungstimeout pausieren sofort. STOP, Mindest-RAM, Fristen und Eingabeintegrität werden kontrolliert. Niemand verändert Evonn; dessen Fortschritt wird pro Stufe und alle 60s aufgezeichnet. Unterschiedliche Überlappung mit Evonn ist ein möglicher Störfaktor insbesondere für Vergleiche bei gleicher Zeit; Tokenvergleiche getrennt berichten.

33 Auswertungen mit jeweils 600s+30s: 15M/50M, Zeitendpunkt auf Entwicklung und frischer Gegenprüfung für acht Modelle plus Elternmodell auf neuer Gegenprüfung. Fehlende Tokenstände bleiben fehlend. Frische 200er-Gegenprüfung schließt Trainingsgruppen, bisherige Bestätigungssuiten und die bekannte Entwicklungssuite aus; Herkunft und Referenzen werden auditiert. Keine externe Transferbehauptung und keine automatische Modellübernahme. Bericht enthält die vier direkten Kontraste und die Mischungs-/Lernraten-Wechselwirkung sowie die vorher festgelegten Entscheidungsschwellen.

## Kontrollen und Budget

89 CPU-Tests bestanden. Zusätzlicher echter GPU-Test am 27M-Modell prüfte frühe Unterbrechung, Checkpoint, Wiederaufnahme mit identischer Signatur/Anfangssampler sowie regulären Abschluss am Zeitbudget: 27,4s insgesamt, Tokens 135.570 vor Wiederaufnahme und 468.571 am Ende, Exit nach Wiederaufnahme 0. Artefakte `runs/long-horizon-validation-2026-09-10/RESULT.json`.

Konservativ werden volle 1200s Vorabudget für Paralleltest, technische GPU-Prüfung, CPU-Tests, Suitenaufbereitung und Eingabeprüfung berechnet. Der nachfolgende Supervisor erhält 85.200s (23h40m) aus demselben neuen 24h-Budget. Das ist keine Verlängerung oder Wiederaufnahme der früheren abgeschlossenen Studie. Vorabkontrollen im Supervisor sind zusätzlich innerhalb dieser Restfrist berücksichtigt. Maximal geplante Stufen inkl. Bericht 79.110s. Unverbrauchte Reserve führt nicht zu längeren Trainings oder weiteren Varianten.

Die tatsächliche Startzeit und harte Deadline stehen nach Start ausschließlich in `runs/long-horizon-2026-09-10/status.json`. Die Kampagne darf nicht bei laufendem Evonn automatisch dessen Einstellungen ändern oder dessen Prozesse beenden. Code und Dateneingaben werden vor Start eingefroren.

Tatsächlicher Start: 2026-09-10T12:08:12.475366+02:00. Harte Deadline: 2026-09-11T11:48:12.475361+02:00. Neue Gegenprüfung: 200 Aufgaben aus 25 Quellen, keine Überschneidung der geprüften Gruppen.
