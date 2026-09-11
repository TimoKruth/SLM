# Weitere Benchmark-Trainingsdaten vorbereitet

Stand: 11. September 2026. Nutzerauftrag: zusätzliche Benchmarks vorbereiten, um die mögliche Wissens- und Fähigkeitsbreite zu vergrößern. **Kein Training gestartet, keine Warteschlange angelegt.** Branch `codex/benchmark-expansion`. Die aktive zweite Langzeitkampagne und ihre eingefrorenen Eingaben bleiben unverändert.

## Ergebnis

Neue lokale Datenversion: `data/v5-expanded-2026-09-11/`, aufbauend auf dem korrigierten `data/v4-broad-corrected-2026-09-08/`. Sie erhält die bestehenden 32 Quellen und ergänzt drei Quellen mit **122.691 neuen Trainingspaaren**. Insgesamt **1.556.634 Trainingspaare aus 35 Quellen**. Der Tokenizer bleibt bitgleich; alle aufgenommenen Aufgaben einschließlich Antworten passen vollständig in 1.024 Tokens.

| Ergänzung | Zusätzliche Abdeckung | Training | Interne Entwicklung | Interne Gegenprüfung |
| --- | --- | ---: | ---: | ---: |
| TriviaQA, `rc.nocontext` | Kurze Faktenantworten ohne vorgegebenen Kontext | 68.888 | 3.786 | 3.820 |
| TyDiQA-GoldP, `secondary_task` | Lesen und Extraktion in neun Sprachen | 33.148 | 1.882 | 1.807 |
| TabMWP | Mathematik mit Texttabellen und Einheiten | 20.655 | 1.172 | 1.232 |

Die neue Gegenprüfung stammt ebenfalls ausschließlich aus Original-Trainingsdaten. Sie ist von Training und Entwicklung gruppengetrennt und wird separat gespeichert. Keine offiziellen Validierungs-/Testsplits wurden heruntergeladen; die ausgeschlossenen externen Testfamilien bleiben geschlossen. Interne Ergebnisse wären kein externer Transfernachweis.

Die Vorbereitung zeigt ein größeres **Lernangebot**, noch keinen Wissenszuwachs eines Modells. TriviaQA ist hier eine dokumentierte Closed-Book-Adaption, keine Ausführung des offiziellen Reading-Comprehension-Benchmarks.

## Herkunft und Auswahl

- [TriviaQA, Autorenseite](https://nlp.cs.washington.edu/triviaqa/): menschlich verfasste Trivia-Fragen. Download des Original-Trainingsanteils aus dem [gepinnten Autoren-Mirror](https://huggingface.co/datasets/mandarjoshi/trivia_qa/tree/0f7faf33a3908546c6fd5b73a660e0f8ff173c2f). Web-/Wikipedia-Darstellungen enthalten dieselben Fragen mehrfach; 61.837 doppelte Prompts entfernt. Nur das originale kanonische Antwortfeld dient als Trainingsziel. Original-Aliase bleiben Metadaten, da darunter auch fragwürdige Referenzen vorkommen; die vorbereitete Auswertung wertet sie nicht automatisch als richtige Antworten.
- [TyDiQA, Originalprojekt](https://github.com/google-research-datasets/tydiqa): Fragen wurden direkt in den jeweiligen Sprachen erhoben, nicht übersetzt. GoldP umfasst neun Sprachen; die elfsprachige Hauptaufgabe ist eine andere Variante. Der offizielle GoldP-Train-Download lieferte HTTP 403; genutzt wird der [gepinnten Trainings-Mirror](https://huggingface.co/datasets/google-research-datasets/tydiqa/tree/da78f23f9119363459acbaf46bf89426ff26c259). Jeder originale Antworttext wurde als exakte Teilzeichenfolge im Kontext bestätigt. Bei 13.508 von 49.881 Datensätzen passen die mitgelieferten Zeichenoffsets nicht zum Text. Diese bleiben unverändert und werden markiert; sie werden nicht als Trainingsziel verwendet. Ursache nicht abschließend geklärt.
- [TabMWP, Originalprojekt](https://github.com/lupantech/PromptPG): ausschließlich `data/tabmwp/problems_train.json` am Commit `5a1a52214521590b075f545b76a4f5ce666345e3`. Interne `split`-Felder aller 23.059 Zeilen sind `train`. Originaltabellen werden als Text, finale Antworten mit vorgegebenen Einheiten übernommen. Manche Original-Lösungen verweisen auf visuelle Hervorhebungen; diese Lösungen bleiben Metadaten und werden nicht zum Lernziel.

Alle Downloads einschließlich Herkunftsdokumenten sind mit URL, Revision, Dateigröße und SHA-256 in `benchmark_expansion/sources.lock.json` festgehalten. Rohdaten bleiben unter `data/candidates-expansion-2026-09-11/`, außerhalb von Git.

Lizenzhinweise sind quellenweise dokumentiert: TabMWP-Daten CC BY-NC-SA 4.0, getrennt von MIT für den Code; TyDiQA-Mirror Apache-2.0 mit fortbestehenden Bedingungen für zugrundeliegende Wikipedia-Inhalte; TriviaQA-Metadaten unbekannt und Autorenseite ohne Eigentum am Copyright der zugrundeliegenden Fragen. Die lokale Vorbereitung ist keine Freigabe zur Veröffentlichung von Daten oder Gewichten.

## Gruppen, Referenzen und Längen

Verbunden werden identische IDs/Prompts, TriviaQA-Fragen, TyDiQA-Artikel und -Kontexte sowie identische TabMWP-Tabellen. Transitive Verbindungen werden vor dem deterministischen Split aufgelöst. Rund 90/5/5 Prozent der Gruppen werden Training, Entwicklung und Gegenprüfung zugewiesen; exakte Anzahlen unterscheiden sich aufgrund der Gruppengrößen.

Alle gespeicherten v4-Trainings- und Entwicklungsdatensätze wurden auf exakte normalisierte Prompt-/Frage-/Kontextüberschneidungen sowie verfügbare Artikelgruppen geprüft. Betroffene neue Gruppen werden vollständig ausgeschlossen. Ebenso werden Gruppen mit unterschiedlichen kanonischen Referenzen für denselben normalisierten Prompt ausgeschlossen; das beweist nicht, dass die alternativen Referenzen falsch waren. **Keine vollständige Near-Duplicate-, Übersetzungs- oder semantische Dublettenfreiheit.** Der Abgleich liest die gespeicherten v4-Datensätze, nicht sämtliche damals verworfenen Originaltexte oder alle ursprünglichen WikiSQL-Datenbanken.

Längenprüfung nach Dubletten-/Gruppenfiltern, vor Längenverwerfung:

| TyDiQA-GoldP-Sprache | Vollständige Aufgaben ≤ 1.024 Tokens | Gemessene Aufgaben | Verbleibende Trainingspaare |
| --- | ---: | ---: | ---: |
| Arabisch | 9.984 | 14.774 | 8.923 |
| Bengali | 455 | 2.376 | 404 |
| Englisch | 3.659 | 3.666 | 3.316 |
| Finnisch | 6.765 | 6.798 | 6.106 |
| Indonesisch | 5.560 | 5.585 | 5.049 |
| Koreanisch | 1.339 | 1.625 | 1.212 |
| Russisch | 4.809 | 6.472 | 4.259 |
| Swahili | 2.592 | 2.642 | 2.346 |
| Telugu | 1.674 | 5.550 | 1.533 |

Besonders Bengali (~81 %) und Telugu (~70 %) verlieren viele Aufgaben durch das bestehende Kontextlimit und den bestehenden Tokenizer. Es wird weder abgeschnitten noch ein neuer Tokenizer trainiert. Die erhaltenen Sprachen werden innerhalb der TyDiQA-Quelle nach ihrer Häufigkeit gesampelt, **nicht gleichgewichtet**. Eine spätere mehrsprachige Tokenizer-/Kontextstudie wäre eine eigene Versuchsfrage.

## Weitere Kandidaten

- **TAT-QA vorbereitet und geprüft, nicht aufgenommen:** 13.215 originale Trainingsfragen, 2.201 Tabellen-/Textkontexte, davon 12.192 vollständige Aufgaben innerhalb des Kontextlimits im Screening. Zahlen, Skalen und Antworttypen sind ausgezählt. Die Originaldatei enthält Tabellen-/Absatz-UUIDs, aber keine Finanzbericht-IDs. Berichtstrennung und numerische Referenzprüfung bleiben vor Aufnahme offen. Datenlizenz laut [Autoren](https://github.com/NExTplusplus/TAT-QA): CC BY 4.0.
- **DialogSum zurückgestellt:** fügt Zusammenfassung hinzu, übernimmt laut [Originalprojekt](https://github.com/cylnlp/dialogsum) aber unter anderem DREAM-Dialoge. DREAM ist bereits enthalten. Vor einem Download/Einbau muss der Abgleich dieser gemeinsamen Ursprünge eingeplant werden.
- **MultiNLI bereits historisch vorgemerkt:** erhöht Umfang und Genrevielfalt, fügt aber keine neue Fähigkeitsgruppe hinzu; deshalb in dieser Erweiterung nachrangig.

## Verwendung und Prüfung

Implementierung: `benchmark_expansion/`. Die neue Familienzuordnung steht explizit in `slm/breadth.py:EXPANSION_FAMILIES`; die bisherigen Standardfamilien bleiben unverändert. Das v5-Manifest schlägt gleiche Masse je einer der neun Familien vor, innerhalb jeder Familie gleiche Masse je Quelle. Dies sind Sequenzanteile, keine garantierten Tokenanteile. Eine Trainingsfreigabe oder kontrollierte Vergleichsanordnung folgt daraus nicht.

Die ursprünglichen v4-Binärdateien werden nach Hashprüfung über lokale Symlinks eingebunden. Die neue Version hängt deshalb weiterhin vom erhaltenen v4-Verzeichnis ab. Der `STOP`-Text im Datenordner ist ein Vorbereitungsmarker, keine vom Trainer erzwungene Sperre. Es existiert keine neu gestartete Kampagne oder Queue.

Reproduktion, ausschließlich CPU-Datenvorbereitung (jeweils neues Ausgabeziel verwenden):

```sh
.venv/bin/python -m benchmark_expansion.fetch --lock benchmark_expansion/sources.lock.json --output data/candidates-expansion-copy
TOKENIZERS_PARALLELISM=false .venv/bin/python -m benchmark_expansion.prepare --base data/v4-broad-corrected-2026-09-08 --stage data/candidates-expansion-copy --output data/v5-expanded-copy
TOKENIZERS_PARALLELISM=false .venv/bin/python -m benchmark_expansion.verify --data data/v5-expanded-copy
```

`verify` hat alle neuen Tokenfolgen und Antwortmasken gegen ihre Textdatensätze, Hashes, Gruppentrennung, vollständige Rohzeilenbilanz und CPU-Sampler-Batches aus allen Quellen erfolgreich geprüft. Die fixierten internen `dev-suite.json` und `confirmation-suite.json` enthalten 170 beziehungsweise 176 Aufgaben mit höchstens 16 verschiedenen Gruppen je Quelle/Sprache. `READY.json` dokumentiert den Abschluss; `benchmark_expansion/RESULTS.json` enthält nur aggregierte Belege für Git. 35 relevante CPU-Regressionsprüfungen bestanden (`tests/test_benchmark_expansion.py`, `tests/test_broad.py`, `tests/test_expanded.py`, MLX explizit auf CPU gesetzt).

Für spätere Modellauswertung unterstützt `slm.broad_eval` die neuen Familien, konservative Exact-Answer-Proxys und sprachweise Berichte. Das neue Suite-Protokoll sieht höchstens 128 generierte Tokens vor; kein offizieller Benchmark-Score, keine stillschweigende Alias- oder numerische Äquivalenzwertung.

Modelltraining und Modellauswertung werden erst nach ausdrücklichem Folgeauftrag über `run_slm.py` mit dem geltenden Light-Monitoring gestartet. Die Datenvorbereitung selbst führt keine Modellrechnung aus. Sie lief im Arbeitsfenster etwa 15:49–16:03 Uhr Europe/Berlin mit reduziertem Prozessvorrang und einem Arrow-/Tokenizer-Thread parallel zur laufenden Kampagne; zusätzliche CPU-/Dateisystemlast bleibt bei zeitbasierten Vergleichen als mögliche Störgröße zu berücksichtigen. Aktive Bedingungsdateien wurden nicht nachträglich geändert. Statuskontrolle um 16:03 Uhr: Runde 2 weiterhin `running`, Phase `long-round2-r0-B`, frischer Trainingsfortschritt, keine gemeldeten Fehler.

Die neuen Roh- und abgeleiteten Daten sind nicht Teil der historischen ZIP64-Archive. Keine externe Sicherung oder Veröffentlichung beauftragt.
