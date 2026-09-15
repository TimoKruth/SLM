# Ergebnisarchiv vom 15. September 2026

Abgeschlossener zweiter Langzeitblock: Lernrate und Verlauf, acht Trainings mit zwei Datenreihenfolgen und 33 vollständige Auswertungen. Abschluss am 14. September 2026 um 23:55:05 Europe/Berlin. Kein Vergleich erfüllt sämtliche vorab festgelegten Kriterien; keine Modellübernahme.

- [Unveränderter Kampagnenbericht](long-horizon-round2-resume-2026-09-14/REPORT.md), dazu `quality.json`, `contrasts.json` und `assessment.json` als unveränderte Kopien.
- [Aggregierte Auswertungen](long-horizon-round2-resume-2026-09-14/evaluation-summaries.json): ausgewählte Metrikfelder aus allen 33 Zusammenfassungen einschließlich Elternmodell, ohne Rohantworten.
- [Abschluss und Budget](long-horizon-round2-resume-2026-09-14/completion.json): ausgewählte Status- und Trainingsfelder; keine systemweiten Prozessprotokolle.
- [Verifikation und Herkunft](long-horizon-round2-resume-2026-09-14/verification.json): SHA-256 aller gelesenen Quellen und Umfang der Prüfungen. Alle 32 Qualitätseinträge aus den Zusammenfassungen nachgerechnet, vollständige Auswertung kontrolliert und alle drei Annahmeentscheidungen nachgerechnet. Die Eingabeintegrität ist die Abschlussbestätigung des Supervisors; beim Export wurden keine Modelle geladen oder Eingaben erneut vollständig gehasht.

Einordnung und nächste Schritte: [ERKENNTNISSE.md](../../ERKENNTNISSE.md). Vorabplan: [LANGZEIT_RUNDE_2.md](../../LANGZEIT_RUNDE_2.md). Die Gegenprüfung unterscheidet sich vom ersten Langzeitblock; ihre absoluten Scores sind nicht direkt vergleichbar. Historische Betriebsbedingungen bleiben in den lokalen Laufverzeichnissen; wechselndes Trainingsvolumen begrenzt den Vergleich bei gleicher Zeit.

Dieser Export umfasst aggregierte Ergebnisse des Parametervergleichs. Er ist keine vollständige Checkpoint-/Datensicherung; die neuen Artefakte sind nicht durch die älteren ZIP-Archive abgedeckt. Der separate konservative FP32-Vergleich gehört nicht zu diesem Export. Keine neue Trainingsfreigabe und kein Remote-Push.
