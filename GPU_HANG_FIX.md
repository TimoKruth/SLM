# GPU-Hang: vorbereitete Fehlerbehandlung (10. September 2026)

Status: getestet und vorbereitet, nicht im laufenden Versuch aktiviert. Code im Worktree `/Users/timokruth/Projekte/SLM-gpu-hang-fix`, Branch `codex/gpu-hang-recovery`.

## Beleg und Grenze

Die aktive Fortsetzung meldete am 9. September um 23:54:48 bzw. 23:57:17 gestartete Stufen `adaptation-r1-weight_decay-0.3` und `adaptation-r1-effective-batch-8` als fehlgeschlagen. Beide Kindprozesse endeten mit -6 (SIGABRT) und derselben nativen MLX-Meldung:

```
[METAL] Command buffer execution failed: Caused GPU Hang Error (00000003:kIOGPUCommandBufferCallbackErrorHang)
```

Der vorhandene Klassifikator suchte unter anderem nach `MTLCommandBufferErrorDomain`, das in dieser Meldung fehlt. Daher wurde die GPU-Wiederherstellung übersprungen. Das folgende Microbatch-Training samt Auswertung gelang wieder. Ein dauerhaft unerreichbarer GPU-Dienst ist daraus nicht abzuleiten; die Ursache der Hänger bleibt offen.

Apple unterscheidet Metal-Fehler wie Timeout, Speicherfehler und entzogenes Gerätezugriffsrecht. Die lokale Meldung allein beweist weder einen bestimmten Kerneldefekt noch Speichermangel oder eine nötige Änderung an Batchgröße/Präzision. Quelle: https://developer.apple.com/documentation/metal/mtlcommandbuffererror-swift.struct

## Fix

`study/safety.py` erkennt nun die genaue Meldung `Caused GPU Hang Error` und das Treibersymbol `kIOGPUCommandBufferCallbackErrorHang` als `gpu_service`. Ein beliebiger nativer Abbruch oder generischer Command-Buffer-Fehler wird nicht pauschal so behandelt.

Damit greift die bestehende Begrenzung: frischer GPU-Gesundheitsprozess; nur bei Erfolg höchstens eine Wiederholung derselben Stufe innerhalb ihrer verbleibenden Zeit; höchstens zwei Recovery-Ereignisse pro Kampagne. Wiederholter Infrastrukturfehler oder gescheiterte Gesundheitsprüfung führt zur Pause mit STOP. Teilresultate werden archiviert. Es handelt sich um eine Reparatur der Fehlerbehandlung, nicht um einen nachgewiesenen Fix des auslösenden GPU-/Treiberfehlers.

## Prüfung

75 CPU-Tests bestanden. Die echten Supervisor-Funktionen wurden mit der vollständigen beobachteten Fehlermeldung und Exitcode -6 getestet: gescheiterte Gesundheitsprüfung stoppt sofort; wiederholter Hang nach erfolgreicher Prüfung pausiert; kein nächster Parameter startet; Teilresultate und Restbudget bleiben geschützt. Kontrolltests verhindern eine pauschale Zuordnung aller SIGABRT-Abbrüche zur GPU. Die numerischen Kernfunktionen stimmen mit dem aktiven Recovery-Code überein.

Keine zusätzlichen GPU-Tests, Paketupdates, Systemdienst-Neustarts oder Änderungen an der aktiven Kampagne vorgenommen.

## Verwendung nach einem eventuellen Abbruch

Zunächst den endgültigen `status.json` und die Eingabeintegrität der aktiven Kampagne prüfen. Erst nach Ende der Kampagne kann `study.recovery` aus diesem neuen Worktree eine eigene STOP-gesperrte Fortsetzung erzeugen: gültige Ergebnisse unabhängig übernehmen, verbrauchtes kumuliertes Budget und Prüfreserve abziehen, Eingaben neu einfrieren. Kein erneutes volles 24h-Budget. Kein Hot-Patch oder Neustart des laufenden Supervisors. Eine spätere Wiederaufnahme benötigt einen ausdrücklichen Startauftrag. Wenn die Studie regulär abschließt, dient der Fix zukünftigen Studien.
