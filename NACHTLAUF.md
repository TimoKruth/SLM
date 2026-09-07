**Erster Nachtlauf: 6.–7. September 2026**

Der Lauf wurde als einmaliger lokaler macOS-LaunchAgent ausgeführt. Er benötigt keine Cloud, keine Zugangsdaten und keine laufende Chatverbindung. Der Mac muss eingeschaltet und am Strom bleiben; den Deckel offen lassen. `caffeinate` verhindert während des Jobs normalen Leerlauf-Ruhezustand. Der Bildschirm darf sich abschalten. Nach einem Neustart wird der Job nicht automatisch erneut gestartet.

**Zeit und Umfang**

- Start: 6. September 2026 nach dem Probelauf und einer zusätzlichen Prüfung auf identische Code-Lösungen; exakter Zeitpunkt in `metrics.jsonl`.
- Trainingsende: spätestens 7. September 2026, 05:50 Uhr Europe/Berlin.
- Bericht und qualitative Antworten: anschließend, bis spätestens 06:00 Uhr.
- Obergrenze: 100 Millionen tatsächlich verarbeitete, nicht aufgefüllte Trainingstokens.
- Modell: 97.536.768 Parameter, 12 Decoder-Blöcke, 768 Dimensionen, 12 Attention-Heads, SwiGLU, RoPE und geteilte Ein-/Ausgabe-Embeddings.
- Initialisierung: zufällig. Keine heruntergeladenen Modellgewichte.
- Tokenizer: eigener Byte-Level-BPE mit 16.384 Tokens, nur auf der Trainingspartition gelernt.
- Kontext: 1.024 Tokens; vollständige Aufgaben werden zusammengepackt, längere Datensätzeinträge explizit ausgeschlossen.
- MLX FP32, AdamW, Gradient-Clipping; Batchgröße 2, Lernrate bis 0,0003 mit Warmup und zeit-/tokenabhängiger Absenkung.
- Checkpoints alle fünf Minuten, Entwicklungsmessung etwa alle 30 Minuten.

**Daten**

| Quelle | Trainingspaare | Gespeicherte Trainingstokens | Entwicklungspaare |
| --- | ---: | ---: | ---: |
| APPS | 30.920 | 14.154.259 | 1.523 |
| MBPP | 359 | 36.739 | 15 |
| GSM8K | 7.092 | 1.237.220 | 381 |
| MATH | 6.994 | 1.986.770 | 358 |
| SQuAD | 82.630 | 17.603.966 | 4.776 |
| BoolQ | 8.969 | 1.525.604 | 457 |
| HellaSwag | 37.777 | 3.852.259 | 2.022 |
| PIQA | 14.069 | 758.422 | 753 |
| WinoGrande | 38.471 | 1.906.638 | 1.923 |
| AI2 ARC | 3.193 | 254.233 | 176 |
| **Gesamt** | **230.474** | **43.316.110** | **12.384** |

Die Anzahl bezeichnet Aufgaben-Lösungs-Paare. Bei APPS werden bis zu acht unterschiedliche, als Python 3 parsebare Original-Referenzlösungen je Aufgabe verwendet. Parsebarkeit ist kein Beweis funktionaler Korrektheit; die Programme werden bei der Aufbereitung nicht ausgeführt. Alle Paare einer Aufgabe bleiben in derselben Partition. SQuAD wird nach Artikeln und HellaSwag nach Quellen gruppiert. Die Entwicklungsdaten werden ausschließlich aus den Original-Trainingsanteilen abgetrennt.

HellaSwag wird als Fortsetzungsaufgabe mit der positiven Originalantwort verwendet; seine generierten falschen Antwortmöglichkeiten werden nicht trainiert. Bei PIQA wird nur die richtige Originallösung verwendet. Die ursprünglichen Testanteile werden nicht eingelesen. Das originale PIQA-Archiv enthält auch Entwicklungsdateien; ausschließlich die beiden Trainingsdateien werden daraus gelesen.

Die Datenaufbereitung entfernt identische normalisierte Prompts zwischen verschiedenen Aufgaben-IDs. Der ergänzende Audit fand keine vollständig identischen Paare im aufbereiteten Korpus, aber eine identische Python-AST-Referenzlösung zwischen Training und Entwicklung. Die gesamte betroffene Entwicklungsgruppe mit acht Varianten wurde daraufhin ausgeschlossen. Eine automatisierte Prüfung bestätigt nun, dass normalisierte Prompts, definierte Herkunftsgruppen und identische Code-ASTs nicht zwischen unseren Partitionen überlappen. Es gibt weiterhin keinen umfassenden semantischen Dubletten- oder Kontaminationsnachweis. PIQAs Datenlizenz ist in den verwendeten HF-Metadaten unspezifiziert; Daten und Gewichte werden nicht veröffentlicht.

Die Mischung wird nach Sequenzen gewichtet: APPS 30 %, MBPP 2 %, GSM8K 12 %, MATH 12 %, SQuAD 16 %, BoolQ 4 %, HellaSwag 7 %, PIQA 7 %, WinoGrande 6 %, AI2 ARC 4 %. Wegen unterschiedlicher Packungsdichte sind das nicht exakt die Anteile verarbeiteter Tokens. Kleine Quellen werden mehrfach gesehen.

LiveCodeBench, IFBench und BBEH bleiben geschlossen. Dieser erste Nachtlauf liefert noch keinen Beleg für Transfer auf diese Tests.

**Status und Ergebnisse**

Alle Laufdateien liegen unter `runs/night-2026-09-06/`:

- `status.json`: letzter Trainingsstatus, Schrittzahl und verarbeitete Tokens.
- `supervisor.json`: Lebenszeichen der Prozessüberwachung.
- `training.log` und `metrics.jsonl`: Trainings- und Entwicklungsverlauf.
- `latest.json`: Verweis auf den letzten vollständigen Checkpoint mit Modell, Optimizer und Zufallszustand des Datensamplers.
- `best.safetensors` / `best.json`: beste bisherige Gewichte nach Entwicklungs-Antwort-Loss.
- `REPORT.md`: lokaler Bericht, nach Abschluss aktualisiert.
- `samples.json`: bis zu 20 qualitative Antworten auf zurückgehaltene Entwicklungsaufgaben; keine ausgeführten Coding-Tests.
- `config.json`, `data_manifest.json`, `source/`, `source_sha256.json`: Konfiguration, Datenrevisionen, Dateiprüfsummen und Quellcodesnapshot.

Status anzeigen:

```sh
cat runs/night-2026-09-06/status.json
tail -n 5 runs/night-2026-09-06/training.log
```

Geordnet stoppen; der Trainingsprozess speichert anschließend einen letzten Checkpoint:

```sh
touch runs/night-2026-09-06/STOP
```

Der Supervisor versucht bei einem Prozessfehler maximal zwei Wiederanläufe aus dem letzten vollständigen Checkpoint. Er überwacht die Zeitgrenze unabhängig vom Trainingsprozess. Nichtendliche Loss/Gradienten und zu wenig verfügbarer Systemspeicher führen zum Abbruch. Wiederanlaufzustände werden gegen Daten- und Konfigurationssignatur geprüft.

Für das Training sind höchstens 32 GiB MLX-Speicher und 4 GiB Cache vorgesehen; die Anfangsmessung lag deutlich darunter. Die separate Beispielgenerierung hat eine Grenze von 8 GiB und 512 MiB Cache, damit wechselnde Eingabelängen den Speicher nicht unnötig belegen.

**Verifikation vor dem Nachtlauf**

Zehn automatisierte Tests prüfen kausale Attention, Padding-Masken, tatsächliches Lernen auf einer kleinen Kontrollaufgabe, Checkpoint-Wiederherstellung einschließlich des nächsten Optimizer-Updates und Datensampler-Zustands, Herkunftsgruppierung und identische Code-Lösungen, Ausschluss synthetischer HellaSwag-Negativantworten und Prozessbeendigung durch Deadline/Stopdatei. Ein echter Vollmodell-Probelauf und dessen Wiederanlauf wurden ausgeführt. Berichterstellung und 20 qualitative Ausgaben wurden ebenfalls geprüft.

Der erste mehrminütige Probelauf wurde über die Stopdatei geordnet beendet und mit vollständigem Checkpoint unter `runs/warmup-2026-09-06/` archiviert. Nach Ausschluss der einen betroffenen Entwicklungsgruppe startet der Hauptlauf erneut von zufälligen Gewichten. SHA-256-Prüfsummen sämtlicher 60 abgeleiteter Daten-/Indexdateien werden beim Trainingsstart überprüft.

Der kurze Vollmodell-Probelauf ergab etwa 4.600–4.800 nicht aufgefüllte Trainingstokens pro Sekunde und 5,34 GB MLX-Spitzenverbrauch. Das ist eine Anfangsmessung; thermische Effekte, Checkpoints und Entwicklungsmessungen können die über Nacht erreichte Datenmenge verändern.

Der erste automatische Checkpoint des endgültigen Laufs wurde um etwa 23:21 Uhr bestätigt: Schritt 667, 1.162.358 verarbeitete Tokens. Die gespeicherten Modellgewichte wurden in einem separaten Prozess geladen, ein Vorwärtslauf lieferte endliche Werte, und der gespeicherte Optimizer-Schritt stimmt mit den Metadaten überein. Das laufende Training wurde dabei nicht unterbrochen.

**Ergebnisstand vom 7. September 2026**

Der Lauf ist erfolgreich abgeschlossen: 54.168 Schritte, 94.774.946 verarbeitete Trainingstokens, Ende 05:50 Uhr. Der beste Checkpoint stammt aus Schritt 42.899; seine anschließend ausgeführte [Code-Diagnose](runs/code-eval-2026-09-07/REPORT.md) löst 0 von 81 referenzgeprüften Entwicklungsaufgaben. Die ursprünglichen 20 Morgenbeispiele bleiben unverändert; die neuen ausführbaren Prüfungen und Zusatzdiagnosen liegen separat unter `runs/code-eval-2026-09-07/`.
