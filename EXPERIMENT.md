**Versuchsplan für den M1 Max mit 64 GB**

Entwurf vom 6. September 2026. Konfigurationen und Erfolgskriterien sind Vorschläge für die erste Umsetzung, keine bereits erzielten Ergebnisse.

**1. Was genau gelernt werden soll**

Hauptfrage: Lernt ein zufällig initialisiertes generatives Sprachmodell aus originalen Benchmark-Trainingsdaten Fähigkeiten, die auf vollständig ausgeschlossene Benchmarks übertragen werden?

Zwei Teilfragen müssen getrennt bleiben: Hilft eine breite Mischung von Sprache, Mathematik und Logik beim Lernen aus Codebeispielen? Und entsteht Coding auch dann, wenn der Trainingspool keinerlei Code enthält? Die zweite Frage ist wesentlich strenger. Ohne beobachtete Programmiersyntax wäre brauchbares freies Python aus zufälligen Gewichten eine sehr starke Erwartung.

Zulässig sind Aufgabenstellungen, zugehöriger Kontext, Originalantworten, Referenzprogramme und bereits mitgelieferte Erklärungen aus überprüften Trainingsanteilen. Mehrere Lösungen derselben Aufgabe dürfen genutzt werden, werden aber als Varianten einer Aufgabe gezählt. Falsche Kandidaten werden nicht als richtige Lösung trainiert. Reine Testdatensätze, zusätzliche Webkorpora und nachträglich generierte Lehrerantworten sind ausgeschlossen. Bekannte synthetische Originalquellen werden markiert und für den strengsten Hauptlauf ausgeschlossen.

**2. Daten in überschaubaren Stufen aufbauen**

Als Kataloge dienen FLAN, P3, Natural Instructions und tasksource. Wir importieren geprüfte Originalquellen und rekonstruieren deren Splits, statt diese überlappenden Sammlungen vollständig aneinanderzuhängen. Natural Instructions weist ausdrücklich darauf hin, dass die Lizenz der Aufgabeninstanzen von der Lizenz der Instruktionsmetadaten abweichen kann. [Natural Instructions](https://github.com/allenai/natural-instructions).

Für Code sind zunächst die Trainingsanteile von APPS und CodeContests interessant; APPS hat 5.000 Trainingsaufgaben und 5.000 Testaufgaben. Für Sprache/Logik kommen geprüfte Quellen der genannten Kataloge hinzu, für Mathematik beispielsweise der Trainingsanteil von MATH. Die Aufnahme erfolgt erst nach Prüfung von Ursprung, Split, Lösungsqualität und Testüberschneidungen. [APPS-Auswertung und Splits](https://github.com/bigcode-project/bigcode-evaluation-harness/blob/main/docs/README.md), [CodeContests](https://github.com/google-deepmind/code_contests/blob/main/README.md?plain=1), [MATH](https://arxiv.org/abs/2103.03874).

Das Datenmanifest erfasst je Quelle Revision, Original-Split, Aufgabenfamilie, Herkunft, Nutzungsbedingungen, Aufgaben-IDs, synthetischen Ursprung, Dublettengruppen und Nutzungsrolle. Berichtet werden Originalaufgaben, Lösungsvarianten, einzigartige Tokens und tatsächlich verarbeitete Tokens separat. Hundert Promptvorlagen derselben Frage werden nicht als hundert unabhängige Aufgaben gezählt.

Erst nach diesem Audit lässt sich sagen, wie groß die nutzbare Menge ist. Ein Pilotbudget von 50–100 Millionen verarbeiteten Tokens ist eine Budgetentscheidung, keine Behauptung über bereits vorhandene Daten. Eine spätere Steigerung auf 300 Millionen bis 1 Milliarde verarbeitete Tokens hängt von Durchsatz, neuen Daten und Überanpassung ab.

**3. Train, Entwicklung und Abschlusstest trennen**

- Die gesamten LiveCodeBench-, IFBench- und BBEH-Daten samt Lösungen und Ableitungen bleiben aus Training, Tokenizertraining und Modellauswahl ausgeschlossen.
- Für einen konservativen Familientest bleiben auch BIG-Bench/BBH sowie IFEval und IF-RLVR draußen. Die im BBEH-Repository genannten Ursprungsdatensätze werden zusätzlich geprüft und ausgeschlossen. Andere Codebenchmarks dürfen trainiert werden: Geprüft wird dort Transfer auf neue Codeaufgaben, nicht erstmals auftretende Programmiersyntax.
- Wettbewerb- und Problem-IDs verbinden Codeaufgaben über Spiegelungen hinweg. Textnormalisierung, exakte und ungefähre Dublettenprüfung sowie normalisierte Codevergleiche ergänzen die Herkunftsprüfung.
- Innerhalb zulässiger Original-Trainingsdaten reservieren wir Entwicklungsaufgaben vor dem Training. Aufgaben, Dokumentquellen und Varianten bleiben gruppiert. Zusätzlich werden ganze Entwicklungsfamilien reserviert, um Transfer schon während der Entwicklung zu verfolgen.
- Der Abgleich gegen externe Tests läuft separat und liefert Ausschluss-IDs; Testinhalte oder deren Lösungen gelangen nicht in Trainingsdateien. Ein Filter reduziert das Kontaminationsrisiko, beweist aber keine vollständige Abwesenheit semantischer Überschneidungen.
- Die drei Abschlusstests werden erst nach Festlegung aller Modellvarianten, Checkpoints, Prompts und Budgets ausgewertet. Nachträgliche Anpassungen benötigen einen neuen, unabhängigen Bestätigungstest.

Die Warnung vor Paraphrasen ist empirisch begründet: reine Zeichenkettenfilter können sinngleiche Testinhalte übersehen. [Rethinking Benchmark and Contamination](https://arxiv.org/abs/2311.04850). Ein wiederholt zur Optimierung verwendeter Test ist funktional ein Entwicklungsset.

**4. Modell und lokale Machbarkeit**

Empfohlener Start: ein einfacher Decoder-Transformer mit ungefähr 100–150M Parametern, zufälliger Initialisierung und einem nur auf dem zulässigen Trainingspool gelernten BPE-Tokenizer mit Byte-Fallback. Ein festes Byte-Alphabet ist eine strengere Alternative, benötigt aber längere Sequenzen. Sprachlicher Schwerpunkt: zunächst Englisch und Python, weil ein mehrsprachiger Anspruch das Experiment verbreitern würde.

MLX bietet native Trainingsbausteine für Apple Silicon und ein offizielles Beispiel für Training eines Decoder-Sprachmodells. Das Beispiel ist technische Grundlage; seine mitgelieferten Sprachkorpora gehören nicht automatisch in unseren Versuch. MLX-LM unterstützt Vollmodell- und Adapter-Fine-Tuning und ist für spätere Kontrollmodelle relevant. [MLX-Trainingsbeispiel](https://github.com/ml-explore/mlx-examples/blob/main/transformer_lm/main.py), [MLX-LM](https://github.com/ml-explore/mlx-lm).

Eine einfache Speicherrechnung mit **16 Byte je Parameter** für FP32-Gewichte, Gradienten und zwei Adam-Zustände ergibt:

| Parameter | Speicher nur für diese Modell-/Optimizer-Zustände | Einordnung als Planung |
| --- | --- | --- |
| 100M | 1,6 GB | Guter Start für mehrere kontrollierte Versuche. |
| 350M | 5,6 GB | Sinnvolle spätere Skalierung bei überzeugendem Pilot. |
| 1B | 16 GB | Unter geeigneten Einstellungen speicherseitig plausibel; Rechenzeit wird wesentlich schwieriger. |

Das sind keine Gesamtverbrauchsprognosen: Aktivierungen, Attention, Logits, temporäre Kopien, MLX-Cache und macOS kommen hinzu. Dtype, Optimizer und Implementierung ändern die Rechnung. Kontextlänge und Batchgröße können mehr ausmachen als die reinen Gewichte. 64 GB Unified Memory stehen außerdem nicht vollständig als frei nutzbarer Trainingsspeicher zur Verfügung.

Start mit kurzen Sequenzen von 512–1.024 Tokens, kleinem Microbatch, Gradient Accumulation und bei Bedarf Checkpointing. Lange Codeaufgaben erfordern später längere Kontexte oder eine vorab dokumentierte Auswahl vollständig passender Trainingsbeispiele. Aufgaben und Antworten werden nicht unbemerkt abgeschnitten. Auch beim Test werden zu lange Eingaben als Abdeckungsproblem ausgewiesen; Teilmengenresultate dürfen nicht als vollständige Benchmark-Werte erscheinen.

Zuerst wird ein kurzer Lasttest mit der tatsächlich vorgesehenen Architektur durchgeführt: etwa 10–20 Minuten nach Aufwärmen, Messung von Trainingstokens pro Sekunde, Spitzenverbrauch und Swap. Vorwärts-/Rückwärtslauf und Optimizer müssen enthalten sein. Inferenzgeschwindigkeiten anderer Modelle sind hierfür unbrauchbar.

Zur Orientierung dient folgende **reine Szenariorechnung, keine M1-Max-Messung**:

| Angenommener Trainingsdurchsatz | 100M verarbeitete Tokens | 1B verarbeitete Tokens |
| --- | --- | --- |
| 500 Tokens/s | 55,6 Stunden | 23,1 Tage |
| 2.000 Tokens/s | 13,9 Stunden | 5,8 Tage |
| 5.000 Tokens/s | 5,6 Stunden | 2,3 Tage |

Rechnung: Tokens geteilt durch Tokens/s; Evaluation, Checkpoints und Pausen kommen hinzu. Der Durchsatz hängt vom Modell ab und darf nicht zwischen Zeilen verschiedener Modellgrößen übertragen werden. Eine seriöse Laufzeit nennen wir erst nach dem Lasttest. Training eines 100–350M-Modells ist ein plausibles lokales Forschungsprojekt; eine konkurrenzfähige 7B-Neuentwicklung ist für diese erste Untersuchung kein sinnvoller Umfang.

**5. Vergleichsläufe, die die Hypothese beantworten**

| Lauf | Daten | Aussage |
| --- | --- | --- |
| A: breite Mischung | Code plus Sprache, Logik und Mathematik | Hauptversuch: Transfer aus vielen Benchmark-Aufgaben. |
| B: nur Code | Gleiche zulässige Codequellen | Zeigt, ob ein Code-Spezialist bei gleichem Gesamtbudget besser ist. |
| C: ohne Code | Bereinigte Sprache-, Logik- und Mathematikdaten | Prüft Transfer ohne beobachtete Codebeispiele. Auch Code in Kontexten und Lösungen muss entfernt werden. |
| D: zufälliges Modell | Kein Training | Prüft Ausgangsniveau und Evaluationspipeline. Ergänzend einfache Antwort-/Retrieval-Baselines. |

A, B und C verwenden dieselbe Architektur, denselben auf der zulässigen Gesamt-Trainingsmenge gelernten Tokenizer und ein gleiches Gesamt-Tokenbudget. Beim streng codefreien Lauf C verwenden wir stattdessen einen gemeinsamen festen Byte-Tokenizer für einen gesonderten A/B/C-Vergleich, damit der Tokenizer keine Codeinformation einführt. Diese beiden Vergleichsserien dürfen nicht direkt vermischt werden.

Der Vergleich A gegen B bei gleichem Budget misst den Nutzen der Ressourcenverteilung, nicht isoliert den Effekt zusätzlicher Nicht-Code-Daten: A sieht dann weniger Code. Bei einem positiven Signal folgt deshalb ein Vergleich mit identischer Code-Exposition und explizit ausgewiesenem Zusatzbudget für Nicht-Code-Daten. Sampling wird nach Familien begrenzt, damit eine große Quelle nicht alle anderen verdrängt.

Als Entwicklungsablation vergleichen wir Next-Token-Loss über Aufgabe und Lösung mit Loss nur über die Lösung. Das ist bei zufälliger Initialisierung eine offene Implementierungsfrage. Rekurrente Architekturen und PrefixLM folgen erst bei funktionierender Standardbaseline. Ein späteres vortrainiertes kleines Kontrollmodell kann den Abstand zum praktischen Nutzen zeigen; dessen Leistung belegt nicht die Benchmark-only-Hypothese.

**6. Erfolg vorab definieren und korrekt auswerten**

Die drei Tests und ihre Quellen sind in [RECHERCHE.md](RECHERCHE.md) beschrieben. Für den ersten Abschlusslauf werden Datenrevisionen und IDs vorab eingefroren: LiveCodeBench v6 Easy plus separater Gesamtscore, IFBench Single-Turn und BBEH Mini. Generierung und Bewertung werden getrennt, sodass Antworten lokal mit MLX entstehen können, während offizielle Bewertungslogik genutzt wird. Generierter Code läuft in einer isolierten Umgebung ohne Netzwerk, mit Zeit- und Speicherlimit.

Vorgeschlagenes frühes Coding-Ziel: mindestens 10 % vollständig gelöste Aufgaben auf dem eingefrorenen LiveCodeBench-Easy-Segment bei genau einem deterministischen Versuch je Aufgabe. Das ist ein bewusst gesetzter Projektmeilenstein, keine Prognose und keine Definition durchschnittlicher menschlicher Coding-Kompetenz. Abweichungen vom offiziellen Samplingprotokoll werden klar angegeben; Vergleiche erfolgen nur unter identischen Bedingungen.

Ein Befund zu breiterem Transfer braucht Verbesserungen auf mehreren unabhängigen Aufgabenbereichen und gegenüber passenden Baselines. Für Code sind A gegen B, für die anderen Bereiche ebenfalls die jeweiligen Vergleiche aussagekräftiger als nur ein Sieg über Zufall. Gleiche Prompts, Kontextgrenzen und Ausgabebudgets gelten für alle Modelle. Fehler wegen Syntax, Format, Timeout und falscher Lösung werden getrennt berichtet.

Aufgabenweise Ergebnisse und Unsicherheitsintervalle werden gespeichert; bei Aufgabenfamilien wird die Gruppierung in der Analyse berücksichtigt. Nach einem günstigen Pilot werden die entscheidenden Trainingsvergleiche mit drei Seeds wiederholt. Checkpoints werden ausschließlich über Entwicklung ausgewählt. Erst anschließend werden die festgelegten Modelle auf allen Abschlusstests bewertet.

Für die praktische Aussage „kann mittelmäßig coden“ wären anschließend neue, unabhängig erstellte Alltagsaufgaben nötig, etwa kleine Funktionen, Dateiverarbeitung und Bugfixes mit verdeckten Tests. Wettbewerbsaufgaben decken Repository-Arbeit, Bibliothekskenntnis und Wartbarkeit nur begrenzt ab. Solche Praxistests werden als eigene spätere Untersuchung ausgewiesen.

**Umsetzungsstand vom 7. September 2026:** Der erste Nachtlauf und die ausführbare interne Code-Diagnose sind abgeschlossen; siehe [Code-Bericht](runs/code-eval-2026-09-07/REPORT.md). Neue Original-Trainingsquellen werden getrennt im [Benchmark-Katalog](BENCHMARKS.md) gesammelt. Als Nächstes folgen deren Aufbereitung und gruppierter Überschneidungsabgleich, insbesondere CodeContests gegen APPS. Danach lässt sich ein kontrollierter Vergleich von breiter Mischung und reinem Code-Training festlegen. Die externen Abschlusstests bleiben bis zur Festlegung dieser Vergleichsläufe geschlossen.
