# Langer Parametervergleich: 24-Stunden-Plan

**Nur geplant, nicht gestartet.** Keine Warteschlange, kein Trainingsprozess und kein zusätzlicher GPU-Test eingerichtet. `STOP` bleibt gesetzt; `plan.json` ist ausdrücklich keine ausführbare Kampagne. Der Nutzer wählte wenige Varianten mit Stunden pro Lauf; alle übrigen bleiben für folgende Runden vorgesehen.

## Fragestellung

Zeigen Datenmischung und Lernrate erst nach längerem Training klare und wiederholbare Wirkungen? Der erste Block untersucht vier Konfigurationen in einem vollständigen 2×2-Vergleich. Er ist der erste Teil einer Rotation und keine Auswahl endgültiger Gewinner aus den kurzen Tests.

Die bisherigen 57 Varianten bleiben mit ihren vollständigen Parametern in `plans/long-horizon-24h-2026-09-10/variant-catalog.json` erhalten. Keine Variante wird aufgrund ihrer bisherigen Qualität ausgeschlossen. Alle 57 zweimal in 24 Stunden zu trainieren ergäbe selbst ohne Auswertung nur 12 Minuten 38 Sekunden pro Training und würde die neue Fragestellung kaum erfüllen.

## Erster Block

| Kennung | Gewichtung der Trainingsdaten | Lernrate | Wiederholungen | Prozessbudget je Training |
| --- | --- | --- | --- | --- |
| A | Gleiche Gewichtung je Fähigkeitsgruppe | 3e-5 | 2 | 2 Stunden |
| B | Gleiche Gewichtung je Quelle | 3e-5 | 2 | 2 Stunden |
| C | Gleiche Gewichtung je Fähigkeitsgruppe | 1e-5 | 2 | 2 Stunden |
| D | Gleiche Gewichtung je Quelle | 1e-5 | 2 | 2 Stunden |

Das sind acht Trainings und 16 Stunden Trainingsbudget. Ein Training läuft rund fünfmal so lange wie die zuletzt als lang bezeichneten 24-Minuten-Läufe. D ergänzt die schon einzeln untersuchten Einstellungen um ihre Kombination. Die niedrigere Lernrate prüft, ob langsamere Anpassung erst später aufholt; die alternative Mischung prüft, ob sich der zeitliche Verlauf je Fähigkeit ändert. Höhere Lernraten bleiben ausdrücklich für Folgeblöcke vorgesehen.

Alle starten unabhängig vom selben ursprünglichen kleinen Sechs-Stunden-Modell: `size-27m-2026-09-09-plus3h/checkpoint-0135594`, einschließlich desselben Optimiererzustands. Kein Start vom bisherigen Kandidaten und keine Aneinanderreihung der acht Trainings. 27,3M Parameter, FP32, ursprüngliche Batch-/Kontext-/Optimiererparameter und korrigierte Daten aus 32 Quellen bleiben konstant. Damit betrifft dieser Block die weitere Anpassung eines bereits trainierten Modells; Aussagen über Training von null oder 97M-Modelle folgen daraus nicht.

Je Wiederholung wird dieselbe neue Datenreihenfolge über alle vier Konfigurationen verwendet, Seeds 2026091001 und 2026091002. Unterschiedliche Mischungen verändern bewusst die ausgewählten Quellen; identische Seeds garantieren dort keine identischen Beispiele. Es sind zwei Datenreihenfolgen desselben Elternmodells, keine unabhängigen Modellinitialisierungen. Reihenfolge A–B–C–D / D–C–B–A gleicht frühe und späte Positionen teilweise aus. Keine Änderung der Reihenfolge nach Zwischenergebnissen.

## Lernen bei gleicher Zeit und gleicher Tokenzahl

- **Primärer Endpunkt:** gültiger letzter Modellstand nach zwei Stunden Prozesszeit einschließlich Laden und Checkpoints, Auswertung auf einer vor Start eingefrorenen frischen Gegenprüfung.
- **Verlauf bei gleicher Datenmenge:** Auswertung bei rund 15M und 50M zusätzlichen echten Tokens sowie am Endpunkt auf derselben 473er-Entwicklungssuite. Batch-Überlauf und tatsächliche Tokenzahl mitberichten. 15M knüpft an die vorherigen langen Versuche an.
- Zusätzlich Modellstände bei 30M, 75M, 100M und 150M Tokens speichern, sofern erreicht; zunächst keine zusätzlichen GPU-Auswertungen dieser Stände. Sie erlauben später feinere Analysen mit eigenem Budget.
- Zeit, Tokens, Schritte, Optimiererupdates, Trainingsverlust, Referenz-Antwortloss und Aufgabenleistung pro Quelle/Fähigkeit gemeinsam ausweisen. Gleiche Laufzeit kann je Mischung und Betriebsbedingungen unterschiedliche Tokenmengen bedeuten.
- Wenn ein Tokenstand innerhalb der zwei Stunden nicht erreicht wird, gilt er als nicht verfügbar. Keine automatische Verlängerung oder Hochrechnung. Der feste Zeitendpunkt bleibt auswertbar; unvollständige Tokenvergleiche ausdrücklich kennzeichnen.

Die 473er-Suite dient dem Verlauf und ist bereits bekannt. Die frische Gegenprüfung soll etwa 200 geeignete Aufgaben mit breiter Quellenabdeckung enthalten, getrennt auf Originalgruppenebene von Training und sämtlichen früheren Gegenprüfungen. Vor Start Datenherkunft, Gruppenüberschneidungen, Klassenabdeckung, Kontextgrenzen und Referenzen auditieren und Suiten einfrieren. Bei zu wenig geeigneten neuen Gruppen vor Trainingsbeginn Plan korrigieren, keine alten Gegenprüfungen stillschweigend wiederverwenden. Auch die frische interne Suite ist kein externer Benchmark-Transfernachweis. Funktionales Coding/SQL sowie offene Textqualität bleiben außerhalb des aggregierten Genauigkeitsscores und dürfen nicht als mitbewiesen gelten.

32 Auswertungen für acht Trainings (zwei Tokenstände, Zeitendpunkt auf Entwicklung und frischer Gegenprüfung) plus eine Gegenprüfung des unveränderten Elternmodells. Dessen historische Entwicklungsauswertung kann nur bei passenden Modell-/Suitehashes übernommen werden. Jede GPU-Auswertung erhält 600 Sekunden plus 30 Sekunden Prozessreserve; Antwortlimit weiterhin 256 Tokens.

## Auswertung und Entscheidungen

Vorab vier direkte Kontraste: B−A und D−C für die Mischung; C−A und D−B für die Lernrate. Dazu die Wechselwirkung (D−C)−(B−A). Effektgröße je Wiederholung und Fähigkeitsgruppe ausweisen, nicht nur Rangplätze. Die Änderung zwischen 15M, 50M und dem Zeitendpunkt zeigt, ob ein Effekt wächst, verschwindet oder umkehrt.

Die bisherigen Schwellen bleiben Referenz für einen Kandidaten: mindestens +2 Prozentpunkte Genauigkeit in beiden Gegenprüfungswiederholungen gegenüber der passenden Kontrolle, kein mittlerer Rückgang einer Fähigkeit über 5 Punkte und keine Verschlechterung von Genauigkeit/Loss gegen das unveränderte Elternmodell. Unabhängig davon alle Effekte berichten; kein Bestehen erforderlich, um eine Variante im Katalog zu behalten. Keine automatische Modellübernahme. Zwei Datenreihenfolgen erlauben weiterhin keine starke Aussage über Initialisierungsstreuung; längeres Training ersetzt keine größere unabhängige Auswertung. Ein verbesserter Loss allein belegt keine bessere freie Antwortqualität.

## Vollständiges Budget

| Teil | Obergrenze |
| --- | ---: |
| Startkontrollen, kurze Kalibrierung, Eingabeprüfung | 20 Minuten |
| Acht Trainings × 2 Stunden | 16 Stunden |
| 33 Auswertungen × 10 Minuten 30 Sekunden | 5 Stunden 46 Minuten 30 Sekunden |
| Abschlussbericht und CPU-Auswertung | 10 Minuten |
| Globale Reserve für Wiederherstellung und zusätzlichen Aufwand | 1 Stunde 43 Minuten 30 Sekunden |
| **Gesamt** | **24 Stunden** |

Dies ist ein neu vorgeschlagener 24h-Block, keine Verlängerung der abgeschlossenen Studie. Er besitzt noch keine Startfreigabe. Die globale Frist beginnt beim später ausdrücklich beauftragten Start; Kontrollen, Kinderprozesse, Wiederholungen und Abschluss zählen mit. Kein Budgetreset nach Störungen. Reserve vergrößert keine Trainingszelle. Bei schnellerer Auswertung oder ungenutzter Reserve endet der Block früher. GPU-Arbeit der SLM-Studie seriell; Monitoring light, zehn Aufwärmschritte, Flush alle 60 Sekunden und PowerWatch bleiben aktiv.

## Betriebsbedingungen und Evonn

Der Nutzer meldet jetzt Hochleistungsmodus. Bei der Planung ist am Netz `powermode 2` eingestellt; gegenüber früheren Läufen mit `powermode 1` ist dies ein geänderter Betriebszustand. Alle acht Läufe müssen unter derselben dokumentierten Einstellung stattfinden. Kein Rückschluss auf frühere Durchsatzmessungen aus der heutigen Einstellung. Die Tokenziele werden nach Freigabe in der eingeplanten Startkontrolle auf Erreichbarkeit geprüft.

Messfenster 10. September, 11:37:47–11:42:32: CPU im Mittel 26,3 %, GPU 8,45 % (Spitze 32 %), rund 37,9 GiB RAM verfügbar, thermischer Zustand normal, keine zusätzlichen Swap-outs im Fenster. Momentanwerte der letzten Probe: CPU 24,45 %, GPU 16 %. Rohzusammenfassung und Einstellungen in `resources-observation.json`; keine sechsstündigen Mittelwerte als aktuelle Last verwendet.

Die beobachtete Evonn-Contenders-Stufe ist CPU-basiert und verwendet einen Worker mit einem Thread. Das Kampagnenprotokoll verlangt auch für die MLX-basierten Prism-/Topograph-Läufe `device=cpu`. Quelle: die lokal geprüften Evonn-Dateien in der Ressourcenaufnahme. MLX im Namen bedeutet hier nicht GPU-Ausführung.

**Technisch erscheint Evonn auf CPU plus SLM auf GPU derzeit möglich; die GPU ist aktuell nicht ausgelastet.** Trotzdem teilen beide Projekte CPU, Unified Memory, Speicherbandbreite und thermisches/elektrisches Leistungsbudget. Aus einer geringen GPU-Prozentzahl lässt sich kein garantierter Durchsatz oder Gewinn durch Parallelbetrieb berechnen. Evonn hat ebenfalls Zeitlimits; zusätzliche Konkurrenz kann auch dessen Vergleich verändern.

Für diesen kontrollierten 24h-Vergleich ist deshalb Ausführung nach Evonn vorgesehen. Falls später explizit Parallelbetrieb gewünscht wird: zunächst zeitlich begrenzten Kontrollvergleich von SLM-Durchsatz allein und mit Evonn planen und dabei auch Evonn-Verlangsamung dokumentieren. Noch kein solcher Test ausgeführt. Der bestehende SLM-Prozessdetektor erkennt vor allem eigene Modulnamen und ist keine projektübergreifende Evonn-Sperre; die Startprüfung muss Fremdlast gesondert prüfen. Es wird jetzt nichts an Evonn verändert oder pausiert.

## Alle übrigen Varianten bleiben vorgesehen

`plans/long-horizon-24h-2026-09-10/variant-catalog.json` enthält alle 37 Adaptations-/Kontext-/Ausführungsvarianten, zwölf Kaltstartvarianten und acht bisherigen Kombinationen unverändert. Für Folgeblöcke Rotationsprinzip statt Gewinnerfilter: bislang wenig langfristig untersuchte Achsen erhalten eigene Stundenvergleiche mit einer gemeinsamen Kontrolle.

Vorgesehene Themen: höhere und sehr niedrige Lernrate/Schedule; Antwortgewicht einschließlich answer-only; Gewichtszerfall/Adam-Parameter/Gradientenbegrenzung; globale und Microbatches; FP32/BF16/eager; Kontext/Packung und Fähigkeitsgewichtung; Architektur/Größe/Initialisierung/Warmup mit eigenem Kaltstartblock. Die genaue Reihenfolge und das Budget späterer Blöcke werden gesondert geplant. Keine dieser Varianten erhält hier eine negative Ausschlussentscheidung.

## Vor einer Ausführung noch umzusetzen

Der bisherige `study.trial` bewertet nur ein erreichtes Tokenziel als vollständig. Für diesen Plan ist ein sauberer Zeitendpunkt samt reservierter Checkpoint-Zeit erforderlich. Ein sehr großes Tokenziel im alten Trainer wäre kein korrekter Ersatz: Es würde ein reguläres Zeitende fälschlich als Fehler markieren.

Ein neuer Supervisor muss genau diese acht Läufe und 33 Auswertungen ausführen, periodisch wiederaufnehmbare Checkpoints mit Adam/Sampler speichern, aktive Budgetzeit korrekt fortschreiben und die bestehende begrenzte GPU-Hang-Behandlung sowie sofortige Auswertungstimeout-Pause übernehmen. Keine pauschale Änderung von Präzision/Batchgröße bei einem Fehler. CPU-Tests für Zeitende, STOP, Wiederaufnahme, Budget, Suiten und Vergleichssignaturen; nach Startfreigabe kurze GPU-Kontrolle im 20-Minuten-Vorabudget. Anschließend Eingaben einfrieren.

Diese Implementierung und die neue Gegenprüfung sind noch offen. Dieser Auftrag erzeugt den überprüfbaren Plan, keinen startbereiten oder wartenden Trainingsdienst.
