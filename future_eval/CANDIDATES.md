# Gezielte Erweiterung der Fähigkeiten

Recherche: 7. September 2026. Diese Liste ist eine Vorauswahl anhand von Primärquellen; keine neue Quelle ist damit für Training freigegeben oder heruntergeladen. Nur Original-Trainingsanteile kommen infrage. LiveCodeBench, IFBench, BBEH und die ausgeschlossenen verwandten Familien bleiben geschlossen.

| Kandidat | Neue Abdeckung | Vor einer Aufnahme prüfen |
| --- | --- | --- |
| [TyDi QA](https://github.com/google-research-datasets/tydiqa) | Originale mehrsprachige Informationsfragen; die Hauptaufgabe umfasst elf Sprachen. | Sprachumfang hängt von der Taskvariante ab. Nur Training; dokumentweise Trennung gegen vorhandene Wikipedia-Aufgaben. Zunächst Tokenizer-Abdeckung und Kontextlänge messen; kein neuer Tokenizer in laufenden Versuchen. |
| [XL-Sum](https://github.com/csebuetnlp/xl-sum) | Mehrsprachige Zusammenfassung journalistischer Texte mit zugehörigen Zusammenfassungen. | Nur Aufgabenpaare des Trainingssplits; keine zusätzlichen Nachrichtenkorpora. Doppelte Artikel und Sprachvarianten gemeinsam gruppieren. Lizenz, Herkunft der Zusammenfassungen und Verlust durch 1.024 Tokens prüfen. |
| [TAT-QA](https://github.com/NExTplusplus/TAT-QA) | Kombinierte Tabellen- und Textfragen mit numerischem Schlussfolgern. | Originale `dataset_raw`-Trainingsdatei wählen; abgeleitete heuristische Felder nicht als ursprüngliche Erklärungen ausgeben. Bericht-/Tabellengruppen trennen, Zahlen und Einheiten erhalten. |
| [Natural Instructions](https://github.com/allenai/natural-instructions) als Katalog | Systematische Suche nach noch fehlenden Aufgabentypen und Instruktionsformaten. | Keine Gesamtübernahme. Originalquellen, Instanzlizenzen, Überschneidungen und Ausschlussfamilien einzeln prüfen. Aufgabenbeschreibungen und Antwortinstanzen haben unterschiedliche Herkunft. |

Priorität: zunächst Tabellen/Text und Zusammenfassung, anschließend ausgewählte Sprachen nach Tokenizerprüfung. Für freies Befolgen von Ausgabevorgaben wird vor einer konkreten Quelle geprüft, dass keine IFBench-/IFEval-/IF-RLVR-Ableitung verwendet wird.

## Offener Herkunftsabgleich: Social IQa

Die gespeicherte und [aktuelle Dataset Card](https://huggingface.co/datasets/allenai/social_i_qa/blob/main/README.md) erwähnt maschinell erzeugte Antwortkandidaten. Dagegen beschreiben die [Autorenseite](https://maartensap.com/social-iqa/) und die [veröffentlichte Arbeit](https://aclanthology.org/D19-1454/) menschlich erstellte richtige und falsche Antworten. Deshalb ist die frühere pauschale Aussage in `VORBEREITUNG_3.md` nicht als endgültige Herkunftsklärung zu behandeln.

Die aktuelle Konvertierung enthält die Original-Antwortoptionen. Vor einem als streng synthetikfrei bezeichneten Folgelauf muss die tatsächlich geladene Revision gegen die Original-Trainingsversion mit Antwort-Herkunftsangaben abgeglichen werden. Bis dahin: Herkunft dieser Optionen offen kennzeichnen, keine bewiesene synthetische Kontamination behaupten. Die laufende Mischung wird nicht nachträglich verändert.
