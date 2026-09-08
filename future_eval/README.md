# Vorbereitung während der breiten Trainingsläufe

Stand: 7. September 2026. Isolierter Arbeitsbaum: `/Users/timokruth/Projekte/SLM-evaluation-prep`, Branch `codex/evaluation-preparation`. Änderungen an Starter und Monitoring gelten hier ausschließlich für neue Offline-Module. Der ursprüngliche Trainingsarbeitsbaum und seine eingefrorenen Quellen bleiben unverändert.

## Bereits erledigt

- 372 vorhandene Antworten des bisherigen 97,5M-Modells und des kleinen Lernkontrollmodells offline analysiert. Symptome, feste Label-Strategien und grobe Wilson-Intervalle werden je Quelle ausgewiesen. Ein aus Entwicklungsantworten berechnetes Mehrheitslabel wird nicht als trainierte Baseline ausgegeben.
- Acht gezielt ausgewählte Befunde anhand der Aufgaben geprüft. Die automatische Kategorie „Antwort falsch“ allein unterscheidet weder Verständnis- noch Schlussfolgerungsfehler.
- 24 Formulare für offene Antworten erzeugt, mit getrennten Kriterien, gemischter Reihenfolge und separatem Modellschlüssel. Noch keine unabhängigen menschlichen Bewertungen; kein automatischer Qualitätsnachweis.
- SQL-Ausführungsproxy entwickelt: eine Originaltabelle in SQLite, schreibgeschützt, mit VM-, Zeit- und Ausgabelimits. Ergebnismengen bewahren Duplikate; ORDER-BY-Referenzen verlangen die Reihenfolge. Leere Referenzergebnisse und der begrenzte Nachweis durch eine einzelne Tabelle bleiben sichtbar. Spider benötigt weiterhin passende Originaldatenbanken; der WikiSQL-Proxy löst diese Lücke nicht.
- Kandidaten und Herkunftsfragen in [CANDIDATES.md](CANDIDATES.md), nächste Performance-Versuchsanordnung in [performance_plan.json](performance_plan.json).

Artefakte: `runs/eval-preparation-2026-09-07/offline-analysis/REPORT.md`, `MANUAL_REVIEW.md`, `analysis.json`; offene Prüfung unter `open-review/`. Die Offline-Analyse lief mit dem Projektstarter und `light`-Monitoring, ohne Modellrechnung.

## Automatisch nach erfolgreichem Abschluss der Kampagne

Die separate Warteschlange wartet auf `runs/broad-campaign-2026-09-07/status.json: completed` und freie GPU-Zulassung. Bei Fehlschlag oder STOP der Kampagne startet sie nicht. Vor dem Start prüft sie ihre eigenen Quellen und Eingabemanifeste. Eine gemeinsame Lease verhindert parallel startende reguläre GPU-Jobs während der maximal 20 Minuten langen Datenprüfung. Keine GPU-Modellrechnung wird ausgeführt.

1. Original-Trainingsdaten einmal lesen; SHA-256 gegen Manifest prüfen. Mehrheit aus eindeutigen ursprünglichen Trainingsaufgaben je Klassifikationsquelle bestimmen, anschließend auf bestehenden Entwicklungsantworten vergleichen.
2. Bis zu 32 Entwicklungsgruppen je Quelle auswählen, verteilt über drei Promptlängenbereiche. Pro Prompt bleiben mindestens 256 Tokens verfügbar; längere Referenzen werden in der Statistik sichtbar. Die neue Auswahl ist interne Entwicklung, kein frischer externer Transfer-Test. Sie ersetzt keinen laufenden A/B-Test.
3. Höchstens 512 Trainingsgruppen je Quelle gegen die neue Entwicklungsstichprobe auf nahe Textdubletten untersuchen. Vier Shingle-Schlüssel holen Kandidaten, Jaccard ≥ 0,85 bestätigt Treffer. Das kann Überschneidungen finden, aber keine vollständige oder semantische Dublettenfreiheit beweisen.
4. Originaltabellen zu WikiSQL-Aufgaben aus dem bereits gespeicherten, geprüften Trainings-Parquet zuordnen. Vorhandene Antworten aus Ausgangsmodell und beiden A/B-Läufen mit dem SQL-Proxy prüfen. Fehlende Tabellen/Referenzfehler getrennt ausweisen.
5. Fehlerstatistiken der abgeschlossenen A/B-Läufe ergänzen.

Ausgabe: `runs/eval-preparation-2026-09-07/after-campaign/`. Queue-Status und Plan: `runs/eval-preparation-2026-09-07/queue/`. Geordnet stoppen: `touch runs/eval-preparation-2026-09-07/queue/STOP`. Kein automatischer Wiederholungsstart nach Fehlern und keine Veränderung der sechs Stunden Trainingsbudget.

## Grenzen und nächste Entscheidungen

Die reduzierte Rechnerleistung bleibt eine dokumentierte Betriebsbedingung. Neue Performance-Messungen werden erst mit einem konkreten, aus den Profilen begründeten Kandidaten gestartet. Testzahl, Seed, feste Arbeitsmenge und Leistungseinstellung stehen bereits im Plan. Ein Vergleich unterschiedlicher Datenmischungen ersetzt keinen kontrollierten Code-Performance-Vergleich.

Für zusätzliche Daten sind train-only Herkunft, Gruppen, Lizenzangaben, Ausschlussfamilien und Tokenizer-Eignung noch zu prüfen. Es wurden jetzt keine neuen Benchmark-Instanzen heruntergeladen. Für Social IQa widersprechen sich Card-Beschreibung und Autorendarstellung zur Herkunft der Antwortoptionen; der Abgleich mit der tatsächlich verwendeten Originalversion bleibt offen.

## Bestätigter Fehler vom 8. September 2026

Die 886er-Auswertung deckte einen SciTail-Konvertierungsfehler auf: Original-Label `entails` wurde nicht auf `entailment` abgebildet. 8.472 positive Beispiele wurden verworfen; `data/v3-broad` enthält für diese Quelle nur `neutral`. Perfekte SciTail-Treffer sind damit ungültig als Fähigkeitsnachweis. Der Konverter und ein Regressionstest für beide Originalklassen sind korrigiert (18 relevante Tests bestanden, Aufruf über den kanonischen Python-Pfad). Historische Daten bleiben erhalten; vor neuen Trainings eine neue Datenversion mit beiden Klassen und erneuter Gruppen-/Dublettenprüfung erstellen. Der korrigierte Vergleich ohne SciTail steht in `runs/broad-886-2026-09-08/REPORT.md`.
