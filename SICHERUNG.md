# Sicherung und Wiederherstellung

Stand: 11. September 2026. Auf Nutzerwunsch zunächst **lokale ZIP-Archive**, kein externer Upload. Ablage auf dem ursprünglichen Mac: `/Users/timokruth/SLM-Sicherungen/2026-09-11/`. Eine lokale Sicherung auf derselben SSD schützt nicht vor Verlust dieser SSD. Der öffentliche GitHub-Stand enthält Code, Dokumentation und aggregierte Ergebnisse; keine Rohdaten, Modellgewichte oder systemweiten Prozessprotokolle.

## Geprüfter Bestand

54 ZIP-Archive mit insgesamt 139,81 GiB (150,12 GB) und 15.439 Einträgen. Sämtliche Archive wurden vollständig gelesen und mit ihren SHA-256-/CRC-Prüfsummen geprüft. Eine tatsächliche Teilwiederherstellung von Code, PowerWatch und einem Laufbericht bestand: 304 wiederhergestellte Dateien erneut gehasht, Git-Bundle erfolgreich geklont und SQLite-Integritätsprüfung mit 57.026 Messpunkten erfolgreich. Prüfzeit und Einzelbestand: [backup-index.json](results/2026-09-11/backup-index.json).

Der Code-Snapshot im ZIP ist Commit `bca55d7`; der anschließende Git-Commit ergänzt nur Sicherungsnachweise und Dokumentation. `SHA256SUMS` liegt neben den Archiven.

## Inhalt

- `data--<Version>.zip`: jede Datenversion separat, zusätzlich lose Dateien in `data--root.zip`.
- `runs--<Laufgruppe>.zip`: sämtliche Dateien je Laufgruppe, einschließlich Modell-/Adam-/Sampler-Checkpoints, Antworten, Status, Pläne, Fehlversuche und Performance-Protokolle. Auch historische Versionen bleiben erhalten.
- `powerwatch-support.zip`: konsistenter SQLite-Snapshot über die SQLite-Backup-API, Sammler- und Adaptercode, LaunchAgent-Konfigurationen und der lokale globale Ressourcen-Skill. Die laufende Datenbank wurde nicht einfach mit offenen WAL-Dateien kopiert.
- `code.zip`: versionierter Quellstand und Git-Bundle aller lokalen Branches/Tags. Git-Bundle bewahrt auch die historischen Branch-Commits und ermöglicht deren Wiederherstellung ohne GitHub. Private temporäre T3-Checkpoint-Refs sind nicht Teil des Branch-Bundles.
- Je ZIP eine `.manifest.json` mit Pfad, Dateityp, Größe und SHA-256 jeder enthaltenen Datei sowie SHA-256 des ZIPs. `BACKUP.json` beschreibt den Bestand; `VERIFIED.json` hält eine vollständige Leseprüfung der Archive fest. `RESTORE_TEST.json` dokumentiert die tatsächliche Wiederherstellungsprobe.
- Das versionierte `results/2026-09-11/backup-index.json` enthält nur Archivnamen, Größen und Prüfsummen sowie Prüfstatus. Die vollständigen privaten Manifeste befinden sich neben den ZIPs.

ZIP64 ist für Dateien/Archive über 4 GB aktiviert. Große Binärdateien werden ohne zusätzliche Kompression gespeichert; Textdateien leicht komprimiert. So bleiben die Archive mit Standardwerkzeugen lesbar, ohne lange Kompressionslast. Die Sicherung folgt Symlinks nicht; interne Verweise werden als Unix-ZIP-Symlinks gespeichert. Alle bei der Vorbereitung gefundenen 3183 Daten-/Laufsymlinks zeigen innerhalb des ursprünglichen Projektbaums.

## Archive prüfen

Mit Python 3, ohne MLX, GPU oder zusätzliche Pakete:

```sh
python3 tools/archive_project.py verify --backup /pfad/zur/2026-09-11
```

Die Prüfung liest jedes ZIP vollständig, prüft Archiv-SHA-256, Eintragsliste, entpackte Dateigröße und SHA-256 sowie ZIP-CRC. Eine Teilprüfung ist beispielsweise mit `--part runs--broad-campaign-2026-09-07` möglich. Nur der dokumentierte Prüfstatus zählt; eine angefangene `.partial`-Datei ist keine fertige Sicherung. Prüfsummen erkennen Beschädigung; sie ersetzen keine unabhängige zweite Kopie und keine kryptographische Signatur.

## Daten wiederherstellen

Genug freien Platz bereitstellen. Das Ziel darf noch nicht existieren:

```sh
python3 tools/archive_project.py restore \
  --backup /pfad/zur/2026-09-11 \
  --destination /pfad/zum/neuen-wiederherstellungsordner
```

Dateien erscheinen unter `project/data`, `project/runs` und `support` beziehungsweise `code`. Absolute Symlinks auf das ursprüngliche SLM-Projekt werden auf den wiederhergestellten Projektbaum relativ umgebogen. Links werden erst nach den regulären Dateien angelegt. Dateiinhalte bleiben unverändert. Eine Teilwiederherstellung mit `--part` kann Verweise auf nicht mit ausgewählte Archive enthalten; für einen vollständigen Datenstand alle Teile wiederherstellen.

Historische JSON-Dateien und eingefrorene Hashlisten enthalten absolute Quellpfade. Sie sind Belege und werden nicht automatisch umgeschrieben. Für eine exakt gleiche Betriebsumgebung den ursprünglichen Pfadbaum einschließlich benötigter Worktrees wiederherstellen. Bei anderer Verzeichnisstruktur einen neuen Laufplan mit überprüfter Pfadzuordnung erzeugen; alte Signaturen nicht als weiter gültig ausgeben. Kein historischer Supervisor darf durch bloßes Entfernen von STOP oder Löschen von status.json neu gestartet werden.

## Code und Abhängigkeiten

```sh
git bundle verify /wiederhergestellt/code/repository.bundle
git clone --branch main /wiederhergestellt/code/repository.bundle SLM-restored
cd SLM-restored
uv sync --locked
```

Das Bundle enthält die benannten Branches; der Archiv-Quellstand steht außerdem unter `code/source`. Die SHA des enthaltenen Code-Snapshots steht in `code/CODE_SNAPSHOT.json`. Historische Worktrees lassen sich mit `git worktree add --detach <pfad> <commit>` rekonstruieren; die Zuordnung steht in `code/WORKTREES.json`. Die virtuelle Python-Umgebung selbst ist nicht gesichert, sondern über `pyproject.toml`/`uv.lock` reproduzierbar. Dafür werden passende Plattform/Python sowie Zugang zu den Paketen benötigt.

## PowerWatch wiederherstellen

Erst im separaten Wiederherstellungsordner die SQLite-Datei öffnen und `PRAGMA integrity_check` prüfen. Bei Wiederherstellung in eine bestehende Installation den PowerWatch-Sammler kontrolliert stoppen, die bisherige Installation separat bewahren und dann den Snapshot einsetzen. Keine laufende WAL-Datenbank überschreiben. Die gesicherten Skripte gehören nach `~/Library/Application Support/PowerWatch/`, die Datenbank nach `data/powerwatch.sqlite3`; LaunchAgent-Dateien enthalten maschinenspezifische Pfade und müssen vor dem Laden geprüft werden. Das Skript startet keine Dienste automatisch.

PowerWatch speichert systemweite Prozessinformationen. Die ZIPs sind deshalb privat lokal abgelegt und sollen nicht als öffentliche GitHub-Release-Assets hochgeladen werden. Der Snapshot erhält den Verlauf zum Sicherungszeitpunkt; der aktive Sammler behält weiterhin seine rollierende 30-Tage-Aufbewahrung.

## Für folgende Forschungsrunden

1. Code, Protokoll und Startbedingungen vor Einfrieren versionieren und remote sichern.
2. Nach Abschluss aggregierte Erkenntnisse und Quellen-Hashes mit `tools/export_results.py` in ein neues Ergebnisverzeichnis exportieren; keine historischen Berichte überschreiben.
3. Nach ausdrücklichem Sicherungsauftrag neue ZIPs mit `tools/archive_project.py create --project <projekt> --backup <neuer-ordner>` erzeugen und vollständig prüfen. Dieses Kommando archiviert Daten/Runs; Code-Bundle und konsistenter PowerWatch-Snapshot werden danach mit `python3 tools/archive_support.py --backup <ordner> --code <repo>` ergänzt (Python 3.12 oder neuer).
4. Keine automatische Nutzung ungebrauchter Trainingsbudgets. Ein neuer Forschungsauftrag braucht eine explizite Startfreigabe.
