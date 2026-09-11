# Parallelbetrieb: aktiver Kontrollversuch

Dauer: 505.6s. Zwei identische 3M-Token-Trainings mit Evonn, getrennt durch drei 60s-Abschnitte ohne SLM.

SLM-Durchsatz: 19371 und 19206 Tokens/s; gleiche Tokens und Batchhashes.
Mindestens 35.0 GiB RAM verfügbar, keine neuen Swap-outs, thermischer Zustand normal.
Evonn-Fortschritt: 7 auf 9 von 48 Kampagnenstufen.
20 vergleichbare Gruppen von Contender-Fits (Datensatz, Modell, Parameter, Zeilen- und Iterationszahl): medianes Verhältnis parallel/ohne SLM 1.094. Deskriptiv etwa 9.4% längere Fit-Zeit; wechselnde Seeds, wenige Proben und unterschiedliche Aufgabenphasen verhindern einen kausalen Gesamtdurchsatznachweis.

## Entscheidung

Two identical production trials complete without errors, stable throughput, EvoNN continues, normal thermal state and ample available RAM. Descriptive ~9% CPU-fit slowdown does not imply zero contention.

Keine isolierte SLM-Kontrolle bei identischem Hochleistungsmodus. Evonn wurde nicht angehalten oder verändert. CPU-Codevorbereitung und kurze Tests liefen zeitweise nebenher. System-GPU-Werte sind nicht pro Prozess zugeordnet; für ruhigere Phasenstatistik erste 15s jeder Phase ausgeschlossen.

Der Nutzer hat den anschließenden Start des gesamten 24h-Vergleichs bei erfolgreichem Paralleltest ausdrücklich autorisiert. Der Test gilt als bestandene technische Machbarkeitsprüfung, nicht als Nachweis kostenloser Parallelität. Ausführungszeit wird vom neuen 24h-Budget abgezogen.
