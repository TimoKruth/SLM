# Zufallsnetze: begrenzte Durchsatz-Stichprobe

Die Frage ist, wie viele vollständig neu initialisierte Sprachmodelle sich unter den aktuellen Gerätebedingungen prüfen lassen. Eine günstige Einzelprüfung ist noch kein effizienter Weg zu einem kompetenten Modell: Gewichtslernen nutzt die Richtung der Fehler, unabhängiges Neuwürfeln verwirft diese Information.

## Genehmigter Versuch vom 8. September 2026

Maximal **20 Minuten einschließlich Aufwärmen und Kontrollen**; kein anschließender Drei-Stunden-Lauf ohne neue Entscheidung. Ein äußerer Supervisor beendet den Prozess spätestens nach 1.200 Sekunden und räumt anschließend auf. Ausführung seriell mit gemeinsamem GPU-Lock, Monitoring `light`, unveränderten Systemeinstellungen. Der Nutzer meldete reduzierte Leistung wegen der Lautstärke; der genaue aktuelle Modus ist nicht vollständig bekannt.

```sh
.venv/bin/python run_slm.py --module random_search.pilot \
  --run runs/random-search-pilot-2026-09-08 \
  --budget-seconds 1200 --search-seconds 300 --max-candidates 256
```

Die interne Frist wird zwischen synchronisierten Vorwärtsläufen und vor jedem generierten Token geprüft. Für eine harte Laufzeitgrenze zusätzlich einen äußeren Prozess-Watchdog verwenden; ein einzelner Geräteaufruf kann nicht durch diese Python-Prüfung unterbrochen werden. Ein `STOP` im Laufverzeichnis beendet die Suche an der nächsten Kandidaten-/Modellgrenze; der äußere Supervisor kann zusätzlich jede Sekunde darauf prüfen.

- Dieselbe Architektur und Initialisierung wie die vorhandenen Trainingsläufe: rund 97,54 Millionen Parameter, Float32, Kontext 1.024, Wortschatz 16.384. Der vorhandene, nur auf Trainingsdaten erlernte Tokenizer bleibt konstant. Keine heruntergeladenen Modellgewichte, Gradienten oder Optimizer-Schritte bei den Zufallskandidaten.
- Eingabe: eingefrorene interne Entwicklungssuite mit 886 Original-Benchmark-Aufgaben. SciTail wird wegen des dokumentierten Labelkonvertierungsfehlers ausgeschlossen; verbleiben 854 Aufgaben aus 30 Quellen. Vollständige Referenzen oberhalb der Kontextgrenze werden für die Loss-Messung ausdrücklich protokolliert und ausgeschlossen.
- Vor den Modellprüfungen deterministisch eine Auswahlaufgabe und eine gruppengetrennte Kontrollaufgabe je Quelle festlegen. Alle Quellen sind gleich gewichtet. Das ist eine kleine Durchsatzprobe, kein umfassender Fähigkeitstest.
- Nach einem separaten Aufwärmkandidaten bis zu fünf Minuten bzw. 256 frische Kandidaten erzeugen. Auswahl ausschließlich nach mittlerem Antwort-Loss auf den 30 Auswahlaufgaben. Seed, synchronisierte Initialisierungs- und Vorwärtszeit sowie Loss jedes Kandidaten speichern. Die Gesamtdauer der Suche umfasst außerdem Bereinigung und Protokollierung.
- Erst nach Festschreiben des besten Seeds die 30 Kontrollaufgaben auswerten. Vergleiche: erster Zufallskandidat, ausgewählter Zufallskandidat, beste Checkpoints der beiden bisherigen Drei-Stunden-Trainings.
- Für diese vier Modelle zusätzlich freie Antworten auf bis zu zwei Kontrollaufgaben je Fähigkeitsgruppe erzeugen. Maximal 256 Tokens; Ergebnisse samt Abbruchgründen speichern. Auswertbare und nicht automatisch bewertete Aufgaben getrennt zählen.
- Ausgewählten Zufallskandidaten und trainiertes Quellen-Modell zusätzlich auf allen passenden Referenzen mit Teacher Forcing messen. Diese größere Auswertung enthält auch Auswahlaufgaben und ist deshalb **kein unabhängiger Transfer-Nachweis**.

`protocol.json` friert Aufgaben, Quellen, Hashes und Grenzen ein; `winner.json` entsteht vor den Kontrollen. `trials.jsonl`, `controls.json`, `results.json`, `supervisor.json`, `RUN_CONDITIONS.json` und `performance/` erlauben die Nachprüfung. Zufallsnetze werden über Seed, Modellcode und Bibliotheksversionen reproduziert; ein Seed allein ist keine plattformübergreifende Garantie.

## Interpretation und Entscheidung über ein größeres Budget

Drei Kosten getrennt berichten: Initialisieren, schnelle Auswahl über Referenz-Loss und freie Antwortgenerierung. Teacher Forcing gibt dem Modell die vorherigen richtigen Antworttokens; ein geringerer Loss bedeutet nicht, dass es die Antwort selbst erzeugen kann. Die Hochrechnung einer kompletten freien Auswertung aus wenigen Aufgaben ist entsprechend unsicher.

Ein Drei-Stunden-Budget wird in Kandidatenzahl hochgerechnet, **nicht** in Erfolgswahrscheinlichkeit. Wiederholtes Auswählen nach denselben Aufgaben passt die Auswahl an diese Aufgaben an, auch ohne Gradienten. Ein Vorteil nur auf Auswahlaufgaben rechtfertigt keinen längeren Lauf. Interessant wäre ein klarer, auf getrennten Kontrollen bestätigter Fortschritt, idealerweise wiederholt über unabhängige Suchen und mit größeren Kontrollen. Die bisherigen trainierten Checkpoints nutzten Entwicklungs-Loss zur Checkpointwahl und enthalten den SciTail-Datenfehler; sie liefern einen beschreibenden Bezug, keinen sauberen neuen Budgetvergleich.

Ohne entsprechende Qualitätssignale hat korrigiertes, breit angelegtes Training Vorrang vor drei Stunden unabhängigem Neuwürfeln. Eine spätere Suche nach wenigen Hyperparametern, kleinen Gewichtsanpassungen oder Subnetzmasken wäre eine **andere Methode** und müsste gesondert geplant werden.

Keine automatische parallele GPU-Ausführung: Inferenz benötigt typischerweise weniger Speicher und keinen Rückwärtslauf, kann aber Recheneinheiten und Speicherbandbreite stark auslasten. Laufzeit und MLX-Spitzenspeicher messen weder Stromverbrauch noch freie GPU-Kapazität. Ob parallele Arbeit sinnvoll ist, erfordert einen separaten, kontrollierten Durchsatzvergleich und ein eigenes Budget.

## Vergleichbare Forschung

[Ramanujan et al., „What's Hidden in a Randomly Weighted Neural Network?“ (CVPR 2020)](https://arxiv.org/abs/1911.13299) finden leistungsfähige **Subnetze** in größeren zufällig gewichteten Netzen. Dabei wird die Subnetzauswahl optimiert; das ist kein Nachweis, dass blind neu erzeugte vollständige Sprachmodelle häufig kompetent sind.

[Bergstra und Bengio, „Random Search for Hyper-Parameter Optimization“ (JMLR 2012)](https://www.jmlr.org/beta/papers/v13/bergstra12a.html) untersuchen zufällige Hyperparameterwahl. Die dabei ausgewählten Modelle werden weiterhin trainiert; das Verfahren entspricht nicht zufällig gezogenen Endgewichten.
