# Ergebnisarchiv vom 15. September 2026

Abgeschlossener zweiter Langzeitblock: Lernrate und Verlauf, acht Trainings mit zwei Datenreihenfolgen und 33 vollständige Auswertungen. Abschluss am 14. September 2026 um 23:55:05 Europe/Berlin. Kein Vergleich erfüllt sämtliche vorab festgelegten Kriterien; keine Modellübernahme.

- [Unveränderter Kampagnenbericht](long-horizon-round2-resume-2026-09-14/REPORT.md), dazu `quality.json`, `contrasts.json` und `assessment.json` als unveränderte Kopien.
- [Aggregierte Auswertungen](long-horizon-round2-resume-2026-09-14/evaluation-summaries.json): ausgewählte Metrikfelder aus allen 33 Zusammenfassungen einschließlich Elternmodell, ohne Rohantworten.
- [Abschluss und Budget](long-horizon-round2-resume-2026-09-14/completion.json): ausgewählte Status- und Trainingsfelder; keine systemweiten Prozessprotokolle.
- [Verifikation und Herkunft](long-horizon-round2-resume-2026-09-14/verification.json): SHA-256 aller gelesenen Quellen und Umfang der Prüfungen. Alle 32 Qualitätseinträge aus den Zusammenfassungen nachgerechnet, vollständige Auswertung kontrolliert und alle drei Annahmeentscheidungen nachgerechnet. Die Eingabeintegrität ist die Abschlussbestätigung des Supervisors; beim Export wurden keine Modelle geladen oder Eingaben erneut vollständig gehasht.

Einordnung und nächste Schritte: [ERKENNTNISSE.md](../../ERKENNTNISSE.md). Vorabplan: [LANGZEIT_RUNDE_2.md](../../LANGZEIT_RUNDE_2.md). Die Gegenprüfung unterscheidet sich vom ersten Langzeitblock; ihre absoluten Scores sind nicht direkt vergleichbar. Historische Betriebsbedingungen bleiben in den lokalen Laufverzeichnissen; wechselndes Trainingsvolumen begrenzt den Vergleich bei gleicher Zeit.

Dieser Export umfasst aggregierte Ergebnisse des Parametervergleichs. Er ist keine vollständige Checkpoint-/Datensicherung; die neuen Artefakte sind nicht durch die älteren ZIP-Archive abgedeckt. Der separate konservative FP32-Vergleich gehört nicht zu diesem Export. Keine neue Trainingsfreigabe und kein Remote-Push.

## Fehleranalyse und Evaluationsvorbereitung

[Auswertung](../../PARAMETER_ERROR_ANALYSIS.md) und [Protokoll](../../PARAMETER_EVALUATION_PROTOCOL.md): 33 Auswertungen / 13.152 gespeicherte Antworten nachgerechnet, gepaarte Gruppenintervalle, manuelle Referenz-/Parserprüfung und größere Diagnose vorbereitet. [Aggregierte Belege](parameter-error-analysis/analysis.json), [Abdeckung](parameter-error-analysis/coverage-audit.json), [gezielte Fallprüfung](parameter-error-analysis/manual-review.json). Herkunft in `analysis-provenance.json`, `preparation-provenance.json` und `exports.json` im selben Unterverzeichnis. Rohantworten und neue Aufgabentexte bleiben lokal. Frische Gegenprüfung wegen Abdeckungslücken nicht bereit; keine neuen Trainings oder Modell-Auswertungen gestartet.

## Größere gespeicherte Checkpoint-Diagnose

[Abgeschlossener Bericht](expanded-checkpoint-diagnostic/REPORT.md): neun vollständige Auswertungen und 12.240 validierte Antworten, keine bestätigte Verbesserung gegenüber dem Elternmodell. [Durchführung und Einordnung](../../EXPANDED_DIAGNOSTIC_RUN.md). Aggregierte Metriken, Unsicherheiten, Herkunft und Budget in `analysis.json`, `provenance.json`, `exports.json` und `completion.json` im selben Unterverzeichnis. Keine Rohantworten, neuen Trainings oder Modellübernahme.

## Referenzbereinigung und vollständige Gegenprüfungsabdeckung

[Bericht](../../PARAMETER_REFERENCE_REFRESH.md): 23 Entwicklungsdatensätze aus sechs Referenzgruppen quarantänisiert, Training bytegleich; neue separate Suite mit 1.360 Aufgaben / 1.280 bewertbaren Aufgaben und geschlossenen ARC-/DREAM-/QuaRel-/Quoref-Lücken. [Abdeckung](parameter-reference-refresh/coverage-audit.json), [Quarantäne](parameter-reference-refresh/reference-quarantine.json), [Quellenrevisionen](parameter-reference-refresh/validation-sources.json). Eingabehashes und CPU-Abschlussprüfung im selben Verzeichnis. Keine Rohaufgaben, Modellausgaben oder Trainingsstarts. Die frühere Aussage fehlender Datenabdeckung ist damit historisch; Versuchsparameter und Ausführungsbudget bleiben vor Nutzung festzulegen.
