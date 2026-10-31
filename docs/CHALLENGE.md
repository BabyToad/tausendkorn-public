# Challenge und Anforderungen

Quellen: Handout Team 1 (Google Drive, Smart Farming Lab) und Jonas' Notizen aus
„Ask the Farmer“ (Vault: `Tausendkorn Hackathon.md`).

## Aufgabe

Landwirt:innen zählen in der Aussaatphase mühsam 1000 Körner, um das
Tausendkorngewicht und damit die Aussaatstärke zu bestimmen. In der Ernte entscheidet
die Qualitätseinschätzung (Vollkornanteil > 90 %, Fremdbesatz, Schrumpfkörner), an
welchen Händler die Ware geht und ob die Mähdrescher-Einstellung passt.

Ziel: aus **einem Foto der Körner auf einem A4-Blatt** automatisch die Anzahl
bestimmen und optische Merkmale auswerten.

## Bewertung (je 1/3)

1. **Technikjury** Smart Farming Lab: prüft Genauigkeit und weitere Kriterien.
   KI ist erlaubt, erhöht aber die Anforderungen.
2. **Fachjury Landwirtschaft:** Vertreter aus Landwirtschaft und Saatgutpraxis;
   Schwerpunkt UI und Nutzbarkeit. Dies beschreibt die Challenge, keine Zustimmung
   oder Produktbewertung durch einzelne Personen.
3. **Live-Voting** des Publikums der SMUL-Werkstatt (Landwirt:innen, Berater:innen,
   Wissenschaft, Politik; eher niedriger Vorwissensstand).

Format frei (App etc.), muss für Landwirt:innen simpel nutzbar sein.

## Aus „Ask the Farmer“

- **Die Crux ist das Zählen.** Je genauer, desto besser.
- Zielgrößen: Gewicht pro 1000 Korn und Keimrate. Am Ende geht es um
  ca. **200 Körner/m²**; daraus folgt die kg/ha-Einstellung (Dosierrate) der
  Drillmaschine.
- Verschiedene Sorten und Hänger → für jeden Hänger und jede Sorte neu zählen.
  Saatzeitraum ca. 2 Wochen. Gerste und Weizen.
- Ablauf: in den Sack greifen, zufällig ~1000 Körner nehmen (Abdrehprobe).
- Körner laufen vorher durch einen Zyklon und sind schon größensortiert;
  Uniformität ist wertvoll.
- Bruchkorn und Fremdbesatz (Nicht-Korn-Bestandteile) zu erkennen ist nützlich.
- Keimfähigkeit: 100 Körner in einer Schale keimen lassen (nicht aus dem Foto
  bestimmbar, aber als Eingabe für den Rechner sinnvoll).
- Hilfsmittel vor Ort: iPad. Internet/Cloud auf dem Hof ist offen → Offline-Fähigkeit
  prüfen.
- Hersteller von Sämaschinen haben gute Informationen zu Saatstärkerechnern.

## Saatstärke

Gängige Formel:

```
Aussaatmenge [kg/ha] = Körner/m² × TKG [g] / Keimfähigkeit [%]
```

(bei Keimfähigkeit als Prozentzahl, z. B. 200 × 45 / 95 ≈ 94,7 kg/ha;
ggf. zusätzlich Feldaufgang berücksichtigen).

## Datensatz `SmartFarmingLab/corn1000`

- 836 Bilder, 128 Arrangements, 170–1000 Körner pro Bild; JPEG, viele mit
  EXIF-Rotation (`PIL.ImageOps.exif_transpose` nötig, `datasets`/`cv2` machen es selbst).
- Arten: `rye-w`, `durum-w`, `barley-w`, `oats-s`, `wheat-w`. Kameras: Galaxy S23,
  iPhone 8, Galaxy Tab S6 Lite, Pixel 9.
- Label `count` nach ISO 520:2010: intakte Körner inkl. Schrumpfkörner, Gerste/Hafer
  mit Spelze, Zwillinge zählen doppelt. **Nicht** gezählt: Bruchkorn, Spreu, Grannen,
  Fremdsamen, Steine, Staub, Büromaterial (`pollution` = none/light/heavy).
- 158 Bilder mit Punkt-Labels (Kornmitte, Pixel im aufrechten Bild):
  `kernel_points`, `broken_points`, `invalid_points`. `count` bleibt das Label.
- **Split nach `session`**, nie nach Bild oder Arrangement allein (Arrangements werden
  mehrfach fotografiert, aufeinanderfolgende teilen die meisten Körner).
- `train` = S02–S05, `test` = `count_1000` (jedes Bild genau 1000 Körner).
- Lizenz CC BY-NC 4.0.

## Infrastruktur

Kaggle-Notebook mit GPU T4 ×2 (Telefonverifizierung nötig, ca. 30 h/Woche/Person).
Ergebnisse mit „Save Version“ sichern.
