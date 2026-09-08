# Vorbereitung des nächsten längeren Laufs

Stand: 8. September 2026. **Vorbereitung abgeschlossen; kein längerer Lauf gestartet oder eingeplant.** Code: Worktree `/Users/timokruth/Projekte/SLM-next-run-prep`, Branch `codex/next-run-preparation`. Ergebnisse: `runs/next-preparation-2026-09-08/`. Historische Versuche und deren Auswertungen bleiben erhalten.

## Was die Diagnose zeigt

Auf der vollständigen eingefrorenen 886-Aufgaben-Suite erreicht das kleine Modell 112-mal das Ausgabelimit; 109 Antworten zeigen nach einer ausdrücklich heuristischen Regel starke Wiederholung. Diese Merkmale überlappen. Mathematik ist besonders betroffen: 59/96 Antworten am Limit, 65/96 mit Wiederholung. Daten-Packing ist kein relevanter Zeitengpass: 0,21 % Eigenzeit gegenüber 98,78 % an der GPU-Ausführungs-/Wartegrenze. Das ist Host-Wall-Zeit, keine isolierte GPU-Kernelzeit.

256 Original-Trainingsaufgaben aus 32 Quellen wurden nachweislich in den ersten 10 Millionen Tokens gesehen. Dafür wurde der originale Sampler 5.520 Schritte rekonstruiert; 10.000.674 Tokens und sämtliche Quellen-Tokenzahlen stimmen exakt mit dem damaligen Snapshot überein. Jeder ausgewählte Datensatz wurde zusätzlich gegen die gespeicherte Tokensequenz geprüft. 248 Entwicklungsaufgaben wurden quellenweise nach ähnlicher Prompt-/Antwortlänge zugeordnet; ihre Gruppen sind disjunkt. HotpotQA hat keine eigene Entwicklung und bleibt aus dem gepaarten Vergleich ausgeschlossen.

| Kleine Diagnose, 31 gemeinsame Quellen | Gesehene Trainingsaufgaben | Entwicklung |
|---|---:|---:|
| Generierte Antworten | 248 | 248 |
| Korrekt / automatisch bewertbar | 58/192 (30,2 %) | 55/192 (28,6 %) |
| Antwort-Loss, Mittel je Quelle | 1,299 | 1,459 |
| Exakte Wiederholung der Referenz | 59/248 | 50/248 |

Die Stichprobe belegt keinen großen allgemeinen Memorierungsvorsprung. Sie ist klein und diagnostisch: je Quelle die ersten acht Datensätze in Datei-Reihenfolge aus einem per Hash ausgewählten Pool von 64 nachweislich gesehenen Aufgaben, keine repräsentative Zufallsstichprobe. Entwicklungsaufgaben sind nur näherungsweise längengleich. DREAM zeigt einen größeren Unterschied (7/8 gegen 2/8); Mathematik bleibt sogar auf den gesehenen Aufgaben bei 0/24. Wiedererkennen und Transfer bleiben getrennte Aussagen. Mehrheitsantworten aus Original-Trainingsdaten stehen separat im JSON-Bericht.

Ein gesonderter Versuch verdoppelte das Ausgabelimit bei 16 ausgewählten Problemfällen von 256 auf 512 Tokens. Alle 16 erreichten erneut ihr Limit; nur drei waren automatisch auf Korrektheit bewertbar, keiner davon wurde richtig. Diese gezielte Stichprobe ersetzt keine Gesamtauswertung und rechtfertigt keine globale Aussage, dass längere Ausgaben nie helfen.

In den ersten 10 Millionen Trainingstokens entfielen nur 19,1 % der nicht gepaddeten Zielpositionen auf Antworten. Der aktuelle vollständige Next-Token-Loss lernt absichtlich auch Aufgaben-/Kontextsprache. Das ist kein Konverterfehler. Antwortgewichtung wäre eine begründete spätere A/B-Frage, wird aber hier nicht zusätzlich geändert.

## Referenzqualität

19 gezielte Fälle aus allen sieben Fähigkeitsbereichen wurden manuell geprüft. Häufige Probleme waren falsche Inhalte und Wiederholung, nicht nur harmlose Formatabweichungen. Drei besonders auffällige Originalreferenzen wurden in den Rohdaten bestätigt:

- APPS 4184 enthält unter acht Original-Lösungen eine hardcodierte, nicht allgemein gültige Primzahlprüfung. Diese steht als Referenz einer internen Generierungsaufgabe; daraus wurde kein funktionaler Code-Erfolg abgeleitet.
- AQuA 62285 spricht von identischen Mangos, die Referenz verwendet aber `3^30` und widersprüchlich drei/vier Empfänger. Das Modell trifft diese Endantwort mit falschem Rechenweg: kein belastbarer Mathematiknachweis.
- BoolQ 7445 fragt „where …“, hat aber das Original-Label `True` und wird deshalb als Ja/Nein-Aufgabe dargestellt. Ein Treffer ist hier kein Nachweis einer passenden Sachantwort.

Zusätzlich ist ein ANLI-Label in der Stichprobe semantisch prüfbedürftig. Die Originalscores bleiben unverändert. Eine separat gekennzeichnete, nachträgliche Sensitivitätsrechnung ohne diese vier Aufgaben ergibt 191/699 gegen 141/699 für klein/groß; die Rangfolge ändert sich nicht. Die feste Ausschlussliste kann für den kommenden Lauf als Zusatzdiagnose verwendet werden. Kein automatisches Umetikettieren und keine stillschweigende Datenänderung.

Artefakte: `manual-review.json`, `MANUAL_REVIEW.md`, `raw-reference-verification.json`, `error-flags.json`, `diagnostic-summary.json`. Die referenzierten IDs und Befunde sind zusätzlich in `next_run/manual_findings.json` versioniert.

## Performance und technische Freigabe

Drei Wiederholungen mit alternierender Reihenfolge, gleichem Checkpoint und identischen vorab gespeicherten Sequenzen. Je Variante 40 Aufwärm- und 80 Messsequenzen. Die GPU-Arbeit lief seriell über Projektstarter, GPU-Sperre und Light-Monitoring. Leistungseinstellungen wurden nicht verändert.

| Variante | Median Nicht-Padding-Tokens/s | Bereich | MLX-Spitzenspeicher |
|---|---:|---:|---:|
| FP32, Batch 1 | 16.604 | 15.308–16.705 | 1,99 GiB |
| FP32, Batch 2 | 17.909 | 17.304–18.035 | 2,30 GiB |
| FP32, Batch 4 | 17.257 | 16.463–17.365 | 3,75 GiB |
| BF16-Rechenoperationen, Batch 2 | 21.540 | 21.534–21.546 | 1,70 GiB |

BF16 liefert hier **20,3 % mehr Durchsatz** und etwa 26 % weniger MLX-Spitzenspeicher als FP32/Batch 2. Die Mastergewichte, Optimiererzustände, Normalisierungen und Loss-Reduktion bleiben FP32. Vorab definierte Loss-Toleranzen und relative Gewichtsabweichungen wurden eingehalten; dies beweist keine langfristig identische Qualität. Batchvarianten haben unterschiedliche Updatezahlen bei gleicher Sequenzmenge und sind kein numerischer Gleichwertigkeitsvergleich. Vorladen, kurze Messdauer und zeitliche Laständerungen verbieten, diese Tokens/s direkt als erwarteten Gesamtdurchsatz eines Stundenlaufs auszugeben.

Der Kandidat ist optional über `--forward-precision bf16` verfügbar; Standard bleibt `fp32`. Standalone-Auswertungen verwenden weiterhin FP32 für alle Modelle. Die Entwicklungsmessung innerhalb des Trainers folgt dessen gewählter Rechengenauigkeit; die beiden Loss-Protokolle dürfen nicht gleichgesetzt werden.

Ein GPU-Vergleich über zwölf Updates (Speichern nach sechs, Laden, weitere sechs) prüfte **134 Modell-/Optimiererarrays**, Loss und Samplerzustand. Alle Prüfungen bestanden; größte Array-Abweichung 1,86e-9. Reguläre überwachte FP32-/BF16-Probeläufe prüften Modellstart und Token-Snapshots. Der erste BF16-Wiederaufnahmetest fand einen Fehler beim Speichern der Konfigurationssignatur; der Fehler wurde korrigiert, ein neuer Versuch lief von Schritt 12 auf 16 weiter. Wiederaufnahme mit falscher Rechengenauigkeit wird vor einer Metadatenänderung zurückgewiesen. Alte FP32-Signaturen bleiben kompatibel. Fehlgeschlagene Diagnoseartefakte bleiben zur Nachvollziehbarkeit erhalten.

39 gezielte CPU-Tests bestanden.

Artefakte: `performance-screen/`, `precision-validation/`, `bf16-preflight-v2/`, `bf16-launcher-verification.json`, `tests.log`. Die kurzen Probeläufe sind keine Qualitätsversuche und werden nicht zum späteren Modellstart weiterverwendet.

## Konkreter nächster Lauf – vorbereitet, nicht gestartet

Der in `next_run/long_plan.json` hinterlegte Vorschlag ist ein **sechsstündiger Neustart des 27,3M-Modells**, Batch 2, Kontext 1.024, gleicher Seed, gleicher Tokenizer und dieselbe korrigierte Mischung aus 32 Quellen. BF16 ist die vorbereitete Effizienzoption. Die gemeinsame tokenbasierte Lernratenkurve wird für diesen Vorschlag auf **300 Millionen Tokens** ausgelegt (Spitze 3e-4, Ende 3e-5). Das ist ein Kurvenhorizont, keine zugesicherte Tokenmenge und keine Verlängerungsfreigabe.

Feste Snapshots: 30M, 100M, 119.011.223, 200M, 240M und 300M Tokens, jeweils nach dem ersten vollständigen Schritt über der Schwelle. Primärer Endpunkt bleibt der letzte Stand am Zeitlimit. Neue Deadline genau einmal bei Startfreigabe setzen; Nachauswertungen seriell mit je maximal 900 Sekunden. Keine automatische Verlängerung. Vor dem tatsächlichen Start Budget und aktuelle Betriebsbedingungen übernehmen und Prüfsummen erneut kontrollieren.

Dieser Vorschlag optimiert den erwarteten Nutzen pro Stunde. Er ändert **Rechengenauigkeit und Lernratenhorizont** gegenüber dem historischen Drei-Stunden-Lauf; er ist deshalb kein reiner kausaler Dauervergleich. Die vorbereitete konservative Alternative verwendet FP32 und einen 240M-Token-Horizont. Auch dabei ändert sich die Lernratenkurve. Ein streng isolierter Dauervergleich müsste hingegen denselben 100M-Horizont einschließlich langer Phase an der Lernratenuntergrenze beibehalten.

Vorab festgelegtes praktisches Erfolgskriterium: mindestens +3 Prozentpunkte im Mittel der sechs automatisch bewertbaren Fähigkeitsgruppen, Verbesserung in mindestens drei Gruppen und kein Gruppenrückgang über fünf Punkte. Das ist eine explorative Nutzenschwelle, kein statistischer Nachweis. Alle sieben Bereiche, Loss, Ausführungstests, Wiederholungen, Limits, Trainingswiedererkennung und Referenz-Sensitivität werden zusätzlich einzeln berichtet. Sinkt nur der Loss ohne mehr richtige freie Antworten, folgt eine Untersuchung des Lernziels statt automatischer weiterer Trainingsstunden.

Das JSON enthält ausschließlich einen Plan. Kein LaunchAgent, keine Queue und kein Trainingsprozess startet den längeren Lauf.

## Externe Tests und weitere Daten

`next_run/transfer_protocol.json` fixiert den Ablauf für die drei bereits vorgesehenen unabhängigen Abschlussbenchmarks und pinnt die offiziellen Evaluator-Repositories: [LiveCodeBench](https://github.com/LiveCodeBench/LiveCodeBench), [IFBench](https://github.com/allenai/IFBench), [BBEH](https://github.com/google-deepmind/bbeh). Deren Testdateien wurden nicht heruntergeladen oder ausgeführt. Modell-/Datensatzrevision, Auswahl und Prompt-Adapter werden vor dem späteren Öffnen endgültig fixiert. Nicht in 1.024 Tokens passende Aufgaben müssen als nicht unterstützte Abdeckung sichtbar bleiben; ein gefilterter Ausschnitt wird nicht als offizieller Gesamtscore ausgegeben. Diese schweren Tests können für ein solches Modell einen Bodeneffekt haben.

Separat vorgemerkt und heruntergeladen wurden nur die Original-Trainingsdateien:

- [TAT-QA](https://github.com/NExTplusplus/TAT-QA): **13.215 Fragen, 2.201 Tabellenkontexte**, Tabellen-/Textverständnis und Rechnen. In einer vorläufigen vollständigen Längenprüfung passen 12.193 Fragen ins Kontextbudget. Originalmaßstäbe (Prozent, Tausend, Millionen …), Bericht-/Tabellengruppen und Überschneidungen müssen vor Integration erhalten bzw. geprüft werden. Datenlizenz laut gepinntem README: CC BY 4.0; Code-Lizenz separat MIT.
- [MultiNLI](https://huggingface.co/datasets/nyu-mll/multi_nli): **392.702 Paare**, drei gleichmäßig vertretene Labels und fünf Genres. Alle 10.070 längengeprüften Stichproben passen; die vollständige Längenprüfung fehlt noch. Nur 384.286 eindeutige `pairID` bei 392.702 Zeilen: IDs allein reichen nicht zur Deduplizierung. Prämissen-/Promptgruppen und Überschneidungen insbesondere mit bisherigen NLI-Quellen müssen vor Aufnahme geprüft werden. Lizenzbedingungen unterscheiden sich teilweise je Ursprungstext; README archiviert.

Ablage: `data/candidates-next-2026-09-08/`, mit Revisions-IDs, Datei-Hashes, Herkunft und `screening.json`. **Noch keine zusätzlichen Trainingsquellen aktiviert.** Diese Ablage ist bewusst eine geprüfte Vorauswahl, kein bereits vollständig auf Überschneidungen geprüfter Trainingsdatensatz.
