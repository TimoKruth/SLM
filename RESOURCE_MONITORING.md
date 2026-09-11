# Permanentes Ressourcenmonitoring

Seit 8. September 2026 ist die Systemübersicht in dieses Projekt eingebunden. Verwendet wird der bereits laufende **PowerWatch**-Sammler. Es wurde kein zweiter Sammler und kein Prometheus installiert.

**Übersicht:** [runs/system-resources/latest.html](runs/system-resources/latest.html). Die Datei wird automatisch jede Minute neu erstellt; eine geöffnete Ansicht lädt sich ebenfalls jede Minute neu. Standardansicht: letzte sechs Stunden. Aktuelle CPU-/GPU-Werte und das Alter der letzten Messung stehen oben.

## Messung und Aufwand

- Sammlung alle **15 Sekunden**, Aufbewahrung **30 Tage** in einer lokalen SQLite-Datenbank. Historische Daten waren bereits vorhanden und werden weiterverwendet.
- CPU/Systemlast, GPU-Treiberwerte, belegter/freier/komprimierter RAM, Swap-Zähler, Datenträger- und Netzwerkzähler, Prozesse und weitere vorhandene PowerWatch-Diagnosen.
- GPU-, CPU-, Last- und RAM-Kurven mit Uhrzeiten. Lücken über 45 Sekunden werden unterbrochen; eine Ansicht mit mehr als 90 Sekunden alten Messwerten wird sichtbar als veraltet markiert. Fehlende Werte werden nicht als Null dargestellt.
- Die zusätzliche Berichtserstellung liest SQLite im Read-only-Modus und veröffentlicht HTML atomar. Bei einem Fehler bleibt die letzte vollständige Ansicht erhalten; `status.json` beschreibt den Fehler. Die Erzeugung benötigt in den Stichproben etwa 0,1–0,5 Sekunden Wandzeit und 0,14–0,60 CPU-Sekunden pro Minute, kurzzeitig rund 30 MiB RAM. Der vorhandene Sammler belegte etwa 19 MiB RAM. Das ist keine vollständige Messung seines Aufwands einschließlich aller Hilfsprozesse.
- Bericht mit niedriger CPU-/I/O-Priorität, ohne Modellzugriff oder zusätzliche GPU-Rechenarbeit. Keine Änderungen an der laufenden Trainingskampagne, ihrer Instrumentierung, Datenbasis oder Leistungseinstellung.
- Kein Netzwerkserver, kein offener Port, kein Cloud-Dienst. In der Übersicht werden Prozess-/Programmnamen angezeigt, keine Kommandozeilenargumente. Die vorhandene PowerWatch-Datenbank wird durch den Bericht nicht verändert.

## Aussagegrenzen

Die Werte beziehen sich auf das **gesamte System** und können auch andere Anwendungen enthalten. CPU-Werte stammen aus dem jeweiligen `top`-Messfenster des bestehenden Sammlers und sind nicht automatisch ein Mittel über das gesamte 15-Sekunden-Intervall. GPU-Prozente sind Treiberanzeigen unter der jeweils aktuellen Leistungseinstellung, keine Messung der maximalen Rechenleistung oder Speicherbandbreite.

„RAM frei“ aus PowerWatch bedeutet physisch unbenutzten Speicher. Das ist weniger als der noch verfügbare Speicher einschließlich freigebbarer Caches. Der Belegt-Verlauf ist ausdrücklich inklusive Caches beschriftet. Swap-Werte werden als Zähler angezeigt und nicht fälschlich als Bytes interpretiert. Die Berichte enthalten keine Messung des gesamten Stromverbrauchs.

Sammlung und automatische Berichte laufen in der angemeldeten Benutzersitzung. Beim nächsten Anmelden starten sie automatisch. Der Monitor verhindert keinen Ruhezustand; Schlaf-/Abmeldezeiten erzeugen entsprechende Lücken.

## Dateien und Dienste

- Sammler: `~/Library/Application Support/PowerWatch/powerwatch`
- Rohdaten: `~/Library/Application Support/PowerWatch/data/powerwatch.sqlite3`
- Sammlerdienst: `~/Library/LaunchAgents/com.local.powerwatch.plist`
- Separater Berichtsadapter: `~/Library/Application Support/PowerWatch/slm_resource_report.py`
- Berichtsdienst: `~/Library/LaunchAgents/com.local.powerwatch.slm-report.plist`
- Projektquelle: `resource_monitor/report.py`, Installation: `resource_monitor/install.py`
- Status, Versionshashes und Installation: `runs/system-resources/status.json` und `installation.json`

Die installierte Kopie des Berichtsadapters bleibt bei einem Git-Branchwechsel bestehen. HTML und Status werden überschrieben; es entstehen keine fortlaufend wachsenden Berichtslogs. Für lange Verläufe ist die SQLite-Datenbank maßgeblich, nicht die jeweils aktuelle HTML-Datei. Die SQLite-Datei kann nach Ablauf der Aufbewahrungsfrist freien Platz intern wiederverwenden, ohne sofort kleiner zu werden.

## Bedienung

Übersicht öffnen:

```sh
open /Users/timokruth/Projekte/SLM/runs/system-resources/latest.html
```

Separaten Bericht der letzten 24 Stunden erzeugen (ändert die automatische Sechs-Stunden-Ansicht nicht):

```sh
/usr/bin/python3 resource_monitor/report.py --output runs/system-resources-24h --hours 24
```

Dienststatus:

```sh
launchctl print gui/$(id -u)/com.local.powerwatch
launchctl print gui/$(id -u)/com.local.powerwatch.slm-report
```

Der Berichtsdienst steht zwischen seinen kurzen Ausführungen normalerweise auf `not running`; `last exit code = 0` und ein frisches `status.json` bestätigen erfolgreiche Updates.

Beide Dienste vorübergehend stoppen (Rohdaten bleiben erhalten):

```sh
launchctl bootout gui/$(id -u)/com.local.powerwatch.slm-report
launchctl bootout gui/$(id -u)/com.local.powerwatch
```

Wieder aktivieren:

```sh
launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/com.local.powerwatch.plist"
launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/com.local.powerwatch.slm-report.plist"
```

Für dauerhaftes Abschalten auch `launchctl disable gui/$(id -u)/<Dienstname>` verwenden; vor dem späteren Aktivieren entsprechend `launchctl enable`. Dies sind Benutzer-Dienste und benötigen kein `sudo`.

Adapter nach einer Änderung installieren/aktualisieren:

```sh
/usr/bin/python3 resource_monitor/install.py
```

Voraussetzung ist die vorhandene lokale PowerWatch-Installation. Der Installer ergänzt nur den Berichtsdienst und startet den vorhandenen Sammler, falls dieser nicht geladen ist.
