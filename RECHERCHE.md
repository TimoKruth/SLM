**Literaturrecherche: Kann ein SLM allein aus Benchmarks lernen?**

Recherchestand: 6. September 2026. Die folgenden Befunde beruhen auf Originalarbeiten, Autoren-Repositories und offizieller Dokumentation. Leistungsangaben aus Papers sind Autorenberichte, keine hier reproduzierten Messungen.

Die Idee hat substanzielle Vorläufer. Am nächsten liegen einerseits das Training auf vielen NLP-Aufgaben und andererseits neuere Modelle, die bereits von zufälligen Gewichten aus Aufgaben-Antwort-Paare lernen. Einen belastbaren Nachweis für die exakte Kombination „ausschließlich originale Benchmark-Trainingsdaten, kleines generatives Modell, Training auf einem M1 Max, Transfer auf drei vollständig ausgeschlossene Benchmark-Familien“ habe ich in dieser Recherche nicht gefunden. Das ist keine Behauptung, dass es weltweit keine solche Arbeit gibt.

**Die engsten Vorläufer**

| Arbeit | Was tatsächlich untersucht wird | Bedeutung und Unterschied zum Projekt |
| --- | --- | --- |
| [T0 / Multitask Prompted Training Enables Zero-Shot Task Generalization](https://arxiv.org/abs/2110.08207), 2021/2022 | Viele NLP-Datensätze werden als sprachliche Prompts formuliert; Evaluation auf unbekannten Aufgaben. | Sehr nah an der Transferfrage, aber Fine-Tuning eines bereits vortrainierten Modells. Die Sammlung P3 und das [T0-Repository](https://github.com/bigscience-workshop/t-zero) sind relevante Ausgangspunkte. |
| [FLAN](https://research.google/blog/introducing-flan-more-generalizable-language-models-with-instruction-fine-tuning/), 2021/2022 | Instruction-Tuning mit Ausschluss ganzer Aufgabencluster bei der Evaluation. | Liefert ein methodisches Vorbild für echte Aufgabentrennung; ebenfalls mit Vortraining. |
| [The Flan Collection](https://arxiv.org/abs/2301.13688), 2023 | Vereint unter anderem FLAN, P3 und Natural Instructions; untersucht Mischung, Aufgabenbalance und Promptvarianten. | Gute Grundlage für Datenauswahl. Ein gemeinsamer Download wäre problematisch: Sammlungen überlappen und enthalten mehr als die von uns zugelassenen Originaldaten. [Offizieller Datenbau](https://github.com/google-research/FLAN/blob/main/flan/v2/README.md). |
| [Super-NaturalInstructions / Tk-Instruct](https://arxiv.org/abs/2204.07705), 2022 | 1.616 Aufgaben aus 76 Aufgabentypen; Generalisierung anhand von Instruktionen. | Besonders passend für die Frage, ob mehr Aufgabenvielfalt hilft. Tk-Instruct baut auf T5 auf. Das [Repository](https://github.com/allenai/natural-instructions) enthält Aufgabentrennung und Herkunftsmetadaten. |
| [ExT5](https://arxiv.org/abs/2111.10952), 2021/2022 | Verbindet umfangreiches überwachtes Multitask-Lernen mit selbstüberwachtem Sprachtraining. | Ein Vorläufer für Aufgaben im Pretraining; externe Sprachdaten bleiben ein wesentlicher Unterschied. |
| [tasksource](https://arxiv.org/abs/2301.05948), 2023/2024 | Vereinheitlicht heterogene NLP-Datensätze und untersucht Multitask-Modelle. | Praktisch relevant für die Datenpipeline. Der berichtete Textencoder ist kein von Grund auf gelerntes generatives Coding-SLM. |

**Besonders relevant: neue Arbeiten aus 2026**

[HRM-Text: Efficient Pretraining Beyond Scaling](https://arxiv.org/html/2605.20613v1), Mai 2026, ist der nächste gefundene Vorläufer. Ein Modell mit 1B Parametern wird von Grund auf auf Aufgaben-Antwort-Paaren trainiert. Die Autoren nennen 40 Milliarden einzigartige und 60 Milliarden insgesamt verarbeitete Tokens. Die Mischung enthält FLAN und tasksource, aber auch umformuliertes Wikipedia-Wissen, synthetische Mathematikdaten und weitere Instruktionen. Damit erfüllt sie unsere strenge Datenregel nicht.

Berichtet werden beispielsweise 60,7 % MMLU und 84,5 % GSM8K. Das Training benötigte laut Paper 46 Stunden auf 16 H100-GPUs. Die Kontaminationsanalyse findet bei DROP einen Effekt unter einer der geprüften n-Gramm-Einstellungen; hohe Ergebnisse auf bereinigten Teilmengen ersetzen keine Trennung ganzer Benchmark-Familien. Für uns ist das ein ermutigender, noch nicht selbst reproduzierter Machbarkeitsbefund. Die Ablationen zu Antwort-Loss und PrefixLM sind besonders nützlich. [Originalarbeit](https://arxiv.org/html/2605.20613v1).

[DFM Mimir v1](https://arxiv.org/html/2608.13517v2), August 2026, greift HRM-Text auf: 1B Parameter, zufällige Initialisierung und eine Mischung aus 161 Datensätzen. Der Bericht beziffert den gewichteten Korpus auf etwa 70,5 Milliarden Tokens pro Epoche. Enthalten sind unter anderem synthetische Instruktionen, Mathematik, Übersetzung und Werkzeugnutzung. Die Autoren berichten kompetitive Ergebnisse für Englisch und Dänisch. Diese Arbeit erweitert den Hinweis auf Lernen aus Aufgabenformaten, ist aber ebenfalls kein Experiment ausschließlich mit originalen Benchmark-Daten. Die angehängten Memorierungsprüfungen betreffen insbesondere Extraktion von Trainingsinhalten; sie sind kein Ersatz für unseren Transfer-Test. Technischer Bericht, hier nicht unabhängig reproduziert.

**Kleine Modelle und Coding: benachbarte Evidenz**

| Arbeit | Befund | Was wir daraus ableiten dürfen |
| --- | --- | --- |
| [Textbooks Are All You Need / phi-1](https://arxiv.org/abs/2306.11644), 2023 | 1,3B Parameter; 6B Tokens ausgewählter Webdaten plus 1B Tokens synthetischer Lehrtexte und Übungen. Auch ein 350M-Modell wird untersucht. | Kleine Modelle können bei sorgfältig gewählten Daten Code lernen. Es handelt sich um zusätzliche Code-/Lehrdaten und Lehrerwissen aus GPT-3.5, daher keinen Beleg für Benchmark-only. Historische HumanEval-Ergebnisse sind nicht auf heutige Coding-Tests übertragbar. |
| [TinyStories](https://arxiv.org/abs/2305.07759), 2023 | Modelle unter 10M Parametern erzeugen in einer stark eingeschränkten Geschichtenwelt kohärenten Text. | Begrenzte Fähigkeiten brauchen nicht zwangsläufig Milliarden Parameter. Synthetische Geschichten und eingeschränkte Sprache unterscheiden sich stark von heterogenen Benchmarks und Coding. |
| [Tiny Recursive Models](https://arxiv.org/abs/2510.04871), 2025 | Ein rekursives Netz mit 7M Parametern erzielt Ergebnisse auf strukturierten Rätselaufgaben, darunter ARC-AGI. | Direkte Inspiration für Lernen aus Aufgaben mit kleinen Netzen. Ein rätselspezifisches Netz ist jedoch kein allgemeines Sprach- oder Codemodell; kleine Parameterzahl garantiert auch keine kurze Trainingszeit. |
| [APPS](https://arxiv.org/abs/2105.09938), 2021, und [AlphaCode](https://deepmind.google/blog/competitive-programming-with-alphacode/), 2022 | Programmieraufgaben und Lösungen dienen als Trainingsmaterial; AlphaCode kombiniert GitHub-Vortraining mit CodeContests. | Belegt den Nutzen von Benchmark-Trainingsanteilen für Coding und liefert Datenkandidaten. Das zusätzliche Code-Vortraining unterscheidet diese Ansätze vom Hauptversuch. |

**Warum hohe Benchmark-Werte die Hypothese noch nicht bestätigen**

[Rethinking Benchmark and Contamination for Language Models with Rephrased Samples](https://arxiv.org/abs/2311.04850) zeigt, dass Paraphrasen und Übersetzungen einfache Dublettenfilter umgehen können. Auch synthetische Daten können Testinhalte transportieren. [ConStat](https://arxiv.org/abs/2405.16281) betrachtet deshalb überhöhte Benchmark-Leistung ohne entsprechende Generalisierung als wesentliches Problem. Konsequenz für unser Projekt: Herkunftsprüfung, Aufgabenfamilien-Ausschluss und robuste externe Auswertung sind wichtiger als ein einzelner Hash-Filter.

Der Unterschied zwischen „Benchmark-Daten“ und „Testdaten“ ist eine Rolle im Experiment. Ein offizieller Trainingssplit darf Lernmaterial sein; eine Bewertung auf diesem Material sagt anschließend nichts über Transfer. Einige Benchmarks haben überhaupt keine geeigneten Trainingsanteile. Ein Hugging-Face-Split namens `train` beweist außerdem nicht, dass sein Inhalt tatsächlich für das Training vorgesehen ist: Auch reine Evaluationssammlungen werden so veröffentlicht.

**Auswahl der drei Abschlusstests**

Die Auswahl priorisiert unterschiedliche Fähigkeiten, automatische Bewertung und lokal erzeugbare Antworten. Es sind aktuelle, öffentlich verfügbare Testreihen mit Veröffentlichungen beziehungsweise Versionen aus 2025; sie werden nicht als die drei neuesten Benchmarks überhaupt bezeichnet.

| Test | Gemessene Fähigkeit | Festlegung und Einschränkung |
| --- | --- | --- |
| [LiveCodeBench](https://github.com/LiveCodeBench/LiveCodeBench), `release_v6` | Aus einer Beschreibung ausführbaren Code erzeugen. | Das offizielle Repository dokumentiert v6 mit 1.055 Aufgaben bis April 2025. Vorgeschlagen: Python, Codegeneration, primär das vorab festgelegte Easy-Segment; Gesamtergebnis zusätzlich. `pass@1` anhand ausgeführter Tests. Ein Easy-Teilscore wird nicht als Gesamtscore ausgegeben. |
| [IFBench](https://github.com/allenai/IFBench), 2025 | Präzise Instruktionen und Ausgabevorgaben auf neue Einschränkungen übertragen. | Single-Turn-Version, offizielle Verifier. Primär prompt-level loose accuracy wie im Paper, strict accuracy zusätzlich. 58 neue OOD-Constraints. Inhaltliche Qualität muss ergänzend geprüft werden, denn Regelkonformität allein ist keine gute Antwort. |
| [BIG-Bench Extra Hard](https://github.com/google-deepmind/bbeh), 2025 | Unterschiedliche sprachliche Denkfähigkeiten, etwa symbolisches, zeitliches und räumliches Schlussfolgern. | Offizielle Mini-Version mit 460 Beispielen für den ersten eingefrorenen Abschlusstest. Vollversion mit 4.520 Beispielen für eine spätere, separat geplante Replikation. Offizieller Evaluator und Ergebnisse pro Teilaufgabe. |

Bei LiveCodeBench frieren wir eine dokumentierte Version ein; auf eine vermeintlich stets aktuelle Bedeutung von `release_latest` verlassen wir uns nicht. BBEHs Repository ist seit 10. Juli 2026 archiviert. Die Daten bleiben als statischer Test nutzbar, die Auswertung sollte deshalb mit einer festen Revision dokumentiert werden. [LiveCodeBench-Versionierung](https://github.com/LiveCodeBench/LiveCodeBench), [BBEH-Repository](https://github.com/google-deepmind/bbeh).

IFBench passt auch inhaltlich zur Forschungsfrage: Die Autoren beobachten, dass Training auf bekannten Ausgabevorgaben nicht zuverlässig auf neue Vorgaben überträgt. Das ist genau die Grenze zwischen Lernen einer Fähigkeit und Spezialisierung auf Prüfungsformate, die wir untersuchen wollen. [IFBench-Paper](https://arxiv.org/abs/2507.02833).

BBEH ist für ein von Grund auf trainiertes kleines Modell ausgesprochen schwer. Ergebnisse nahe null sind plausibel und würden allein kein Scheitern jeglicher Generalisierung beweisen. Deshalb gehören leichtere, unabhängig reservierte Entwicklungsaufgaben aus dem Trainingspool zur Lernkurvenanalyse. Die drei Abschlusstests bleiben dabei geschlossen. Eine Auswahl oder Verkürzung nach Sichtung der Modellergebnisse wäre kein unveränderter Benchmark mehr.

**Erwartbares Ergebnis und Forschungsbeitrag**

Meine Einschätzung: Wahrscheinlicher als ein universeller Assistent ist zunächst ein Modell mit ungleichmäßigen Fähigkeiten — brauchbar bei einigen Antwortformaten und einfachen Transformationen, schwach bei freiem Schreiben, Wissen und längeren Programmen. Originale Lösungspaare können Code vermitteln; viele reine Multiple-Choice-Aufgaben enthalten dafür jedoch wenig produktives Lernsignal. Der Umfang nutzbarer, einzigartiger Code-Lösungen dürfte entscheidend sein.

Die interessante lokale Forschungsfrage lautet daher: Wie weit kommt Aufgabenlernen ohne fremde Modellgewichte und ohne zusätzliche Korpora bei einem festen Rechenbudget? Eine positive Antwort wäre messbarer Transfer auf neue Aufgaben; ein belastbar negatives Ergebnis würde die Grenze dieser Datenquelle und dieses Budgets dokumentieren. „Mittelmäßig coden“ bleibt ein anspruchsvolles Ziel, das einfache Wettbewerbsaufgaben allein nicht abschließend messen.

Für die Fortsetzung sind HRM-Text als engster methodischer Vorläufer, FLAN/Natural Instructions als Datenlandkarte und phi-1 als Vergleich für den Wert expliziter Code-Lösungen die wichtigsten Anknüpfungspunkte. Die konkrete Umsetzungsskizze steht in [EXPERIMENT.md](EXPERIMENT.md).

**Suchumfang und offene Punkte**

Gesucht wurde entlang von Multitask-Prompting, Instruction-Tuning, Training from scratch auf Aufgabenpaaren, kleinen Code-/Reasoning-Modellen, Benchmark-Kontamination sowie MLX-Training auf Apple Silicon. Suchtreffer aus Foren und Zusammenfassungsseiten dienten höchstens als Wegweiser; die Einordnung oben verweist auf Primärquellen. Das ist eine gezielte breite Recherche, keine systematische Literaturübersicht mit Vollständigkeitsanspruch.

Noch offen sind der tatsächlich zulässige Datenumfang nach Filterung, die genaue Familien- und Herkunftsliste, festgeschriebene Datenrevisionen, ausführbare Evaluationsadapter und gemessener Trainingsdurchsatz auf dem konkreten Mac. Diese Recherche hat keine Datensätze heruntergeladen, Modelle installiert oder Training gestartet.
