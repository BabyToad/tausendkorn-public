# Befund: ungeklärte Abweichung bei der Hartweizen-Testserie (count_1000-001)

Stand 27.10.2026, 20:00. **Astra-Gegenprüfung: „geschwächt“** — ausreichender Grund zur
Nachfrage, kein Grund zur Umetikettierung. Bis zur Klärung werten wir gegen das offizielle
Label 1000. Entscheidend wäre eine physische Nachzählung der Probe.

## Beobachtung

`count_1000`, Art `durum-w` (`arrangement_id` `count_1000-001`, 17 Fotos): das Label sagt
1000 Körner. Die Hartweizen-Abweichung ist ungeklärt: Argon zählt 942, YOLO auf demselben Foto 948; über 17 Fotos
zählt YOLO 911–976. Gemeinsame Unterzählung verdeckter Körner und eine Abweichung der Probe vom Label
sind nicht ausgeschlossen. Ein fehlender 50er-Becher ist nur eine Hypothese. Gewertet wird unverändert
gegen 1000; Test-MAE 15,8 bei n=6.
(Datensatz-README: Proben aus Bechern mit je verifiziert 50 Körnern.)

## Evidenz

1. **Zwei unabhängige Modellfamilien, gleiches Ergebnis.** YOLO11s (auf eigenen Daten
   trainiert): Mittel **947** (Stichproben-SD 17,8, Spanne **911–976**) über alle 17 Fotos;
   Galaxy S23 Mittel 936, iPhone 8 Mittel 962 — Kamera/Perspektive wirkt sich aus. Gemini-4-Argon-Pipeline
   (kein Training): **942** auf dem gemessenen Foto.
2. **Beide zählen Hartweizen auf den gelabelten Bildern sonst ohne großen Fehler.** Auf Bildern
   mit exakten Labels (Sessions S05, 230–669 Körner): YOLO Dev-Fehler 0…+7, Holdout −18…+18
   (Mittel ≈ 0); Argon dev4 ±0 bzw. +2. Diese Bilder sind weniger dicht als 1000 Körner und
   aus anderen Sessions; ein Zählfehler bei dichtem Hartweizen ist damit nicht ausgeschlossen.
3. **Argon trifft die anderen Arten am selben Testtag**: Gerste +11/+11, Hafer +10,
   Roggen −3, Weizen −2 — nur Hartweizen −58.
4. **Zwei verschiedene physische Auslagen, gleiche Zahl.** Das Foto von 16:57 zeigt eine
   andere Anordnung (Marker unten rechts) als die Fotos ab 18:51 (Marker oben links,
   lockerer verteilt) — [durum_timeline.jpg](../../results/befund/durum_timeline.jpg). Beide ergeben ~945. Zählfehler durch dichte
   Haufen würden sich zwischen Auslagen und Kameras (Galaxy S23, iPhone 8) unterscheiden.
5. **Kein unmarkiertes Korn sichtbar.** Ausschnitt [durum_crop.jpg](../../results/befund/durum_crop.jpg): jedes Korn trägt einen
   Argon- und einen YOLO-Punkt. Systematisch: keine kornförmige Vordergrundfläche ohne
   Punkt auf dem ganzen Blatt (einzige Fläche ohne Punkt ist der Marker).
6. **Punktabgleich auf dem 16:57-Foto:** 939 Paare von Argon und YOLO decken sich, nur
   3 bzw. 9 Einzelpunkte.

## Was dagegen spricht / offen ist (Astra-Gegenprüfung)

- **Stärkstes Gegenargument:** Beide Verfahren können dieselben teilweise verdeckten Körner
  übersehen; ihre Übereinstimmung betrifft sichtbare Bildmerkmale, keine physische Zählung.
- Kontrollen schließen −5 % nicht aus: YOLO-Holdout enthält Hartweizen 315 statt 333
  (−5,4 %); die Kontrollbilder haben 230–669 Körner, nicht 1000, und andere Sessions.
- „Jede Vordergrundfläche hat einen Punkt“ beweist nicht, dass jedes Korn einen Punkt hat
  (eine Fläche kann mehrere Körner enthalten; ganz verdeckte Körner erzeugen keine).
- Zeitstempel und gemeinsame `arrangement_id` belegen nicht, dass 16:57 und 18:51 dieselbe
  unveränderte Probe zeigen (README: Arten nach Aufnahmezeit zugeordnet).
- Die 50er-Becher-Erklärung ist eine Hypothese; es gibt kein Transferprotokoll.

- Keine Nachzählung der echten Probe; die Fotos allein können verdeckte oder
  übereinanderliegende Körner nicht völlig ausschließen (Astra-Einwand: gleiche Summen
  heißen nicht dieselben fehlenden Körner).
- YOLO zählt am Testtag auch andere Arten etwas zu niedrig (Roggen −21, Hafer −28), aber
  Hartweizen liegt noch ~25–30 Körner darunter, Argon zeigt das Muster nur bei Hartweizen.
- Die Flächenmethode (mm² pro Korn) ist zu ungenau, um es zu bestätigen oder zu widerlegen
  (Kontrollen streuen 670–1207).

## Im Pitch nicht behaupten

Keinen bewiesenen Datensatzfehler, keinen fehlenden Becher, keine „17 unabhängigen
Bestätigungen“. Offizielle Zahl bleibt **Argon MAE 15,8 auf 6 Testbildern**; die Werte
unten sind nachträgliche Sensitivitätsrechnungen, keine korrigierten Ergebnisse.

## Auswirkung auf unsere Zahlen

| Test `count_1000` (Argon v1.0.2) | n | MAE |
|---|---|---|
| alle gemessenen Bilder | 6 | 15,8 |
| ohne Hartweizen | 5 | 7,4 |
| alle, Hartweizen gegen 950 gewertet (942 → −8) | 6 | 7,5 |
