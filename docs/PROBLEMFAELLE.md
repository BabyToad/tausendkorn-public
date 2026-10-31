# Problemfälle der Zweitmeinung

Bekannte Schwächen, Risiken und offene Fälle zum Konzept
[`ZWEITMEINUNG.md`](ZWEITMEINUNG.md). Jeder Fall hat eine ID (`PF-xx`), ein GitHub-Issue
(Label `zweitmeinung`, Sammel-Issue [#1](https://github.com/BabyToad/tausendkorn/issues/1)) und einen **Beleg-Status**:

- **belegt:** steht in Datensatz-Card, Challenge oder bisherigen Messungen
- **Hypothese:** plausibel, aber noch nicht gemessen. Beim Messen Status hier ändern.

Neue Fälle: nächste freie ID, Issue anlegen, hier eintragen. Erledigte Fälle nicht
löschen, sondern Status auf `gelöst` setzen und den Commit nennen.

| ID | Titel | Beleg | Schwere | Issue |
|---|---|---|---|---|
| PF-01 | Beide Zähler machen denselben Fehler | Hypothese | hoch | [#3](https://github.com/BabyToad/tausendkorn/issues/3) |
| PF-02 | Prüfer liegt bei dichten Blättern systematisch daneben | Hypothese | hoch | [#4](https://github.com/BabyToad/tausendkorn/issues/4) |
| PF-03 | Test ist dichter als Training, Roggen kommt nur im Test vor | belegt | hoch | [#5](https://github.com/BabyToad/tausendkorn/issues/5) |
| PF-04 | Schwellen auf kleinem Dev-Set, `count_1000` ist konstant 1000 | belegt | mittel | [#6](https://github.com/BabyToad/tausendkorn/issues/6) |
| PF-05 | A4-Blatt wird nicht gefunden, Maßstab fehlt | Hypothese | mittel | [#7](https://github.com/BabyToad/tausendkorn/issues/7) |
| PF-06 | Kachelränder: Doppelzählung und Auslassung | Hypothese | mittel | [#8](https://github.com/BabyToad/tausendkorn/issues/8) |
| PF-07 | Punkt-Labels weichen von `count` ab | belegt | niedrig | [#9](https://github.com/BabyToad/tausendkorn/issues/9) |
| PF-08 | Hinweistexte sind nicht handlungsleitend | Hypothese | mittel | [#10](https://github.com/BabyToad/tausendkorn/issues/10) |
| PF-09 | Kamera- und Entwicklungsunterschiede verschieben die Signale | belegt | mittel | [#11](https://github.com/BabyToad/tausendkorn/issues/11) |

---

## PF-01 Beide Zähler machen denselben Fehler

- **Issue:** [#3](https://github.com/BabyToad/tausendkorn/issues/3)
- **Symptom:** Ampel ist grün, die Zahl ist trotzdem falsch.
- **Ursache:** Der Prüfer hilft nur bei *unabhängigen* Fehlern. Gemeinsame Ursachen sind
  z. B. Spreu oder Grannen, die beide mitzählen (sie zählen laut ISO 520 nie), dunkle
  Körner auf dunklem Untergrund, Bruchkorn.
- **Erkennung:** Fehleranalyse auf `dev` mit Punktabgleich (`tausendkorn.match`): wo
  liegen A und B im selben Bereich falsch?
- **Gegenmaßnahmen:** Klassen Korn/Bruch/Fremd im Detektor getrennt (`pollution` in den
  Metadaten nutzen), Hinweis in der UI "weißes Blatt, kontrastreicher Untergrund",
  die Grenze im Pitch offen nennen.
- **Abnahme:** In der Auswertung je Ampelstufe steht die Fehlerrate im grünen Bereich
  mit aufgeführt, nicht nur der Mittelwert.

## PF-02 Prüfer liegt bei dichten Blättern systematisch daneben

> Hinweis 18:10: `STATUS.md` führt klassische Bildverarbeitung als Zähler als verworfen
> (zu ungenau). Das spricht dafür, dass dieser Fall eintritt. Prüfer-Rolle neu entscheiden
> (siehe `ZWEITMEINUNG.md`, Abgleich am Anfang).

- **Issue:** [#4](https://github.com/BabyToad/tausendkorn/issues/4)
- **Symptom:** Ampel ist fast immer rot oder gelb, auch bei guten Fotos.
- **Ursache:** Die klassische Pipeline wurde bisher **nur an synthetischen Bildern**
  getestet (`wissensbank/README.md`). Bei 1000 Körnern berühren sich viele Körner, ein
  Blob ist dann mehrere Körner und die Flächenkorrektur ist grob.
- **Erkennung:** `classical_counter:count` auf `dev` und `test` laufen lassen, Bias und
  MAE je Art notieren. Genau dafür ist der Lauf im Issue "Prüfer messen" vorgesehen.
- **Gegenmaßnahmen:** Prüfer verbessern (Watershed-Parameter), oder die Gewichtung
  umstellen: weniger Gewicht auf S01, mehr auf S02–S08. Als letzter Ausweg einen zweiten,
  anderen Prüfer (z. B. GeCo2 mit visuellen Beispielen) statt der klassischen Pipeline.
- **Abnahme:** Bias des Prüfers auf `dev` bekannt und im Entscheidungslog
  (`wissensbank/notes/02_Entscheidungslog.md`) festgehalten.

## PF-03 Test ist dichter als Training, Roggen kommt nur im Test vor

- **Issue:** [#5](https://github.com/BabyToad/tausendkorn/issues/5)
- **Symptom:** Schwellen, die auf `dev` gut aussehen, passen nicht zu `count_1000`.
- **Beleg:** `train` hat 170–800 Körner je Bild, `test` genau 1000. Roggen (`rye-w`)
  kommt nur im Test vor ([`CHALLENGE.md`](CHALLENGE.md), [`PROTOCOL.md`](PROTOCOL.md)).
- **Folge:** Signal S08 (Kornzahl außerhalb des geprüften Bereichs) greift im Test
  immer. Das ist ein Artefakt des Splits, kein Fehler der App.
- **Gegenmaßnahmen:** Für den Testlauf S08 mit höherer Obergrenze ausweisen und in
  `RESULTS.md` vermerken. Roggen separat berichten. Nicht auf den Test nachschärfen.
- **Abnahme:** `RESULTS.md` nennt für S08 die verwendete Obergrenze.

## PF-04 Schwellen auf kleinem Dev-Set, `count_1000` ist konstant 1000

- **Issue:** [#6](https://github.com/BabyToad/tausendkorn/issues/6)
- **Beleg:** `dev` hat 24 Bilder (`PROTOCOL.md`). Jedes Bild in `count_1000` hat 1000
  Körner, ein konstanter Zähler hätte Fehler 0.
- **Risiko:** Überanpassung der Schwellen. Ampel wirkt gut, weil sie auf wenigen Bildern
  zurechtgebogen wurde.
- **Gegenmaßnahmen:** Schwellen einfach und konservativ halten (eine Zahl je Signal).
  Unsicherheit der Kalibrierung angeben (Anzahl Bilder je Stufe). `holdout` genau einmal.
  Die Vorgabe "1000 im Test" nie als Signal nutzen.
- **Abnahme:** Ergebnis je Ampelstufe enthält die Fotozahl je Stufe.

## PF-05 A4-Blatt wird nicht gefunden, Maßstab fehlt

- **Issue:** [#7](https://github.com/BabyToad/tausendkorn/issues/7)
- **Symptom:** Prüfer fällt auf das ganze Bild ohne Maßstab zurück
  (`classical_counter.py`: `rectify_a4` liefert `None`). Ohne Maßstab ist die
  Flächenkorrektur schwach und die Größenverteilung nicht in mm.
- **Ursache (Hypothese):** Blatt angeschnitten, weißes Blatt auf hellem Untergrund,
  starke Perspektive.
- **Gegenmaßnahmen:** Signal S05 mit Hinweis "ganzes Blatt, von oben". Auf `dev` zählen,
  wie oft der Fall auftritt, und danach die A4-Erkennung verbessern.
- **Abnahme:** Anteil `sheet_found == False` auf `dev` und `test` in `RESULTS.md`.

## PF-06 Kachelränder: Doppelzählung und Auslassung

- **Issue:** [#8](https://github.com/BabyToad/tausendkorn/issues/8)
- **Symptom:** Zählung schwankt, wenn das Kachelraster verschoben wird.
- **Hintergrund:** `tiles.py` zählt ein Korn in der Kachel, deren Kern seine Mitte
  enthält. Bei Körnern auf der Naht oder bei unscharfen Detektionen am Kachelrand
  entstehen trotzdem Abweichungen. Der letzte Commit (`adaptive.py`) führt ein adaptives
  Raster mit Halo und Nahtabgleich ein.
- **Gegenmaßnahmen:** Signal S02: gleiches Modell auf um eine halbe Kachel versetztem
  Raster zählen und vergleichen. Kostet Rechenzeit, aber kein zweites Modell.
- **Abnahme:** S02-Abweichung auf `dev` gemessen, Schwelle begründet.

## PF-07 Punkt-Labels weichen von `count` ab

- **Issue:** [#9](https://github.com/BabyToad/tausendkorn/issues/9)
- **Beleg:** `len(kernel_points)` kann um wenige Körner von `count` abweichen (dichte
  Blätter, Randkörner). `count` bleibt das Label (Dataset-Card, `PROTOCOL.md`).
- **Folge:** Beim Punktabgleich (Precision/Recall) ist ein kleiner Rest an
  "Fehlern" Referenzrauschen. Nicht als Modellfehler lesen.
- **Gegenmaßnahmen:** Für Summenfehler immer `count` nehmen, Punkte nur für die
  Fehleranalyse. Toleranz bei der Interpretation von kleinen Abweichungen mitdenken.

## PF-08 Hinweistexte sind nicht handlungsleitend

- **Issue:** [#10](https://github.com/BabyToad/tausendkorn/issues/10)
- **Symptom:** Landwirt sieht "gelb" und weiß nicht, was er tun soll, oder ignoriert die
  Warnung.
- **Gegenmaßnahmen:** Jeder Hinweis nennt **eine konkrete Handlung** (siehe Texte in
  `agreement.py`). Mit landwirtschaftlichen Testpersonen prüfen: Welche Wörter versteht er
  sofort? Maximal ein Satz in der Hauptansicht, der Rest ausklappbar.
- **Abnahme:** Kurzer Test mit einer fachfremden Person am iPad vor der Abgabe.

## PF-09 Kamera- und Entwicklungsunterschiede verschieben die Signale

- **Issue:** [#11](https://github.com/BabyToad/tausendkorn/issues/11)
- **Beleg:** Vier Kameras (Galaxy S23, iPhone 8, Galaxy Tab S6 Lite, Pixel 9). DNG-Fotos
  wurden mit LibRaw entwickelt, Farben weichen von der Handy-JPEG-Verarbeitung ab. Das
  Tablet verpasste bzw. verdatierte Fotos einzelner Karten (Dataset-Card).
- **Folge:** Schärfe (S06), Helligkeit (S07) und Konfidenzen (S03) hängen vom Gerät ab.
  Schwellen von einem Gerät passen nicht automatisch zum nächsten.
- **Gegenmaßnahmen:** Schwellen je Kamera ansehen, nicht nur global. Im Zweifel
  konservativer einstellen. Die Test-Kameras (S23, iPhone 8) und die Ziel-Kamera (iPad
  des Landwirts) sind nicht dieselben: kurze Messung mit iPad-Foto vor dem Pitch.
- **Abnahme:** Mindestens ein Foto von einem echten iPad durch die Pipeline gelaufen.
