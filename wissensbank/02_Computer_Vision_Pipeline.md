# 02 – Computer-Vision-Pipeline für Körneranalyse

Umsetzung: `scripts/grain_segmentation.py` (klassisch: OpenCV, scikit-image, SciPy).
Teststatus: an synthetischen Bildern mit bekannter Wahrheit validiert (Abschnitt 6). **Auf echten Daten noch ungetestet**; Parameter werden dort neu justiert.

---

## 1. Entscheidungsbaum: Welche Daten liegen vor?

| Datenlage | Aufgabe | Empfohlener Weg |
|---|---|---|
| **0. Aktuelle Challenge: Foto auf weißem A4-Blatt, Datensatz `corn1000`** | Kornzahl (Hauptkriterium), TKG, Aussaatstärke, Bruchkorn | `05_Datensatz_corn1000.md`: A4-Entzerrung (`a4_sheet.py`), Export (`corn1000_data.py`), Auswertung (`evaluate_counting.py`); Baseline = klassische Pipeline dieses Dokuments, danach punktüberwachtes Zählnetz |
| **A. Foto einzelner, getrennter Körner auf einfarbigem Hintergrund** | zählen, vermessen, TKM | klassische Pipeline (dieses Dokument), Methode A/B/C aus Abschnitt 5 |
| **B. Foto mit sich berührenden/überlappenden Körnern** | zählen trotz Kontakt | Watershed (vorhanden) + Flächenteilung; bei Überlappung Deep Learning |
| **C. Runde Körner (Raps, Erbsen, Soja)** | zählen | zusätzlich `cv2.HoughCircles` oder Distanztransformation-Peaks |
| **D. Ähren/Feld, Drohnenbild** | Ähren/m², Körner/Ähre | Objekterkennung (YOLO) oder Dichte-Regression; deutlich aufwendiger |
| **E. Tabelle (Messwerte, Wetter, Sorte, Feld)** | TKM/Qualität vorhersagen | `eda_tabular.py` + `train_model.py` |
| **F. Bilder + Labels (TKM je Bild)** | Bild → TKM | Bildfeatures aggregieren (`image_features`) + Regression, ggf. CNN |
| **G. Video / Förderband** | Online-Messung | Einzelbild-Extraktion, Tracking gegen Doppelzählung |
| **H. Spektraldaten (NIR/Hyperspektral)** | Protein/Feuchte | PLS-Regression / 1D-CNN, nicht Fokus dieses Stacks |

Erste Aktion bei Datenerhalt: Bild öffnen, Hintergrund, Beleuchtung, Berührung der Körner, Maßstab, Label-Struktur prüfen (`notes/01_Datenset_Erstblick.md`).

---

## 2. Bildaufnahme (falls wir selbst fotografieren dürfen)

| Aspekt | Empfehlung | Begründung |
|---|---|---|
| Hintergrund | einfarbig, kontrastreich zum Korn (Weizen: blau oder schwarz matt) | einfache Schwellwerte, kein Schatten-/Glanzproblem |
| Beleuchtung | diffus, von oben/seitlich gleichmäßig, kein direkter Blitz | vermeidet Schlagschatten und Glanzlichter |
| Anordnung | Körner einzeln, nicht berührend (Abstand ≥ 1 Kornbreite) | spart Watershed-Fehler, höhere Zählgenauigkeit |
| Maßstab | Referenzobjekt (Münze, Lineal, Schachbrett/ArUco) in jedem Bild | mm/px, Vergleichbarkeit |
| Kamera | senkrecht, fester Abstand, Fokus fix, Belichtung manuell | konstanter Maßstab |
| Format | JPG hoher Qualität oder PNG, ≥ 20 Pixel je Kornbreite | genaue Konturen |
| Dichte | 100–300 Körner je Bild | genügend Statistik, noch auflösbar |
| Gewicht | Probe nach dem Foto wiegen, Masse notieren | Kalibrierung von Methode A/B |

---

## 3. Pipeline-Schritte

```
Laden → Maßstab → Kanalwahl → (Flatfield) → Glätten → Schwellwert → Morphologie →
Hole-Fill → Labeling → (Referenzmünze) → Cluster-Erkennung → Watershed → Features → Filter → Overlay/CSV
```

| # | Schritt | Umsetzung im Code | Parameter (Startwert) | Typischer Fehler → Fix |
|---|---|---|---|---|
| 0 | **Laden** | `read_image` (`np.fromfile` + `cv2.imdecode`) | – | `cv2.imread` liefert `None` bei Umlauten/Windows-Pfaden → imdecode nutzen |
| 1 | **Maßstab** | `--mm-per-px`, Referenzmünze (`ref_diameter_mm`) oder **A4-Blatt** (`a4_sheet.rectify_a4`, 210 × 297 mm; entzerrt zugleich die Perspektive) | 2-€-Münze 25,75 mm; A4 mit 0,15 mm/px | Münze fehlt/nicht rund → mm/px manuell aus Lineal bestimmen |
| 2 | **Kanalwahl** | `channel="auto"`: wählt unter gray/S/b/a/L den Kanal mit bester Otsu-Trennbarkeit | auto | graue Objekte (Münze) fehlen im S-Kanal → Münze wird in mehreren Kanälen gesucht |
| 3 | **Beleuchtung** | `flatfield=True`: Division durch stark geglättetes Bild | aus | Gradient im Hintergrund → einschalten; Schwellwert `adaptive` als Alternative |
| 4 | **Glätten** | Gauß, `blur_sigma` | 1,5 | zu stark → Körner verschmelzen; zu schwach → Rauschen |
| 5 | **Schwellwert** | Otsu / adaptiv / fix | Otsu | mehrere Helligkeitsmodi → adaptiv oder GrabCut/K-Means |
| 5b | **Polarität** | `invert="auto"`: Vordergrund = kleinerer Anteil | auto | Körner > 50 % der Fläche → `invert` explizit setzen |
| 6 | **Morphologie** | Opening/Closing mit Ellipsenkern, `open_px`, `close_px` | 2 / 2 | Opening entfernt Staub; Closing füllt Furche/Glanzlicht |
| 7 | **Hole-Fill** | `binary_fill_holes` | – | Furchen/Glanz als Loch → gefüllt |
| 8 | **Labeling** | `skimage.measure.label` (4er-Nachbarschaft) | – | 8er-Nachbarschaft verbindet diagonal berührende Körner |
| 9 | **Cluster-Verdacht** | Fläche > 1,45 × Median-Einzelkorn oder Solidität < 0,88 | `max_rel_area_single` | Median robust aus „unauffälligen“ Objekten (`robust_single_stats`) |
| 10 | **Watershed** | Distanztransformation → Gauß(1) → h-Maxima → `watershed(-dist)` nur für Verdachtsobjekte | `h_frac=0,25` × Innenradius | Übersegmentierung (ein Korn in 2) → `h_frac` ↑; Untersegmentierung → `h_frac` ↓ |
| 11 | **Blob-Korrektur** | `n_est_blob = round(Fläche / Median)` für ungelöste Cluster | – | Zählung = Σ `n_est_blob` |
| 12 | **Features** | Geometrie, Farbe (Lab, HSV) je Korn | siehe Abschnitt 4 | – |
| 13 | **Filter** | Rauschen < 30 % Medianfläche, Randkörner raus | `min_rel_area`, `drop_border` | Randkörner abgeschnitten → verfälschen Fläche |
| 14 | **Overlay/CSV** | grün Einzelkorn, orange getrennt, rot ungelöst | – | visuelle Plausibilitätsprüfung immer machen |

Faustregeln:
1. Immer zuerst Overlay ansehen, dann Zahlen vertrauen.
2. Genau eine Stellschraube ändern, dann Zählfehler auf 5 Bildern neu messen.
3. Schwellwert/Kanal pro Aufbau festlegen, nicht pro Bild nachjustieren (sonst nicht reproduzierbar).

---

## 4. Feature-Katalog (pro Korn und pro Bild)

### Pro Korn (`grains.csv`)

| Feature | Definition | Quelle | Nutzen |
|---|---|---|---|
| `area_px` / `area_mm2` | Fläche | `regionprops.area` × (mm/px)² | Größe, Masse-Proxy |
| `length_mm`, `width_mm` | Haupt-/Nebenachse der Ellipse (Momente) | `axis_major/minor_length` | Sortierung, Siebfraktion (Breite) |
| `aspect` | Länge / Breite | – | Sorte, Bruchkorn |
| `solidity` | Fläche / konvexe Hülle | – | Bruch/Defekt, Cluster-Indikator |
| `circularity` | 4π·A / P² | – | Rundheit (Raps/Erbse) |
| `extent` | Fläche / Bounding-Box | – | Form |
| `eccentricity`, `orientation_deg` | Ellipsenexzentrizität, Lage | – | Form, Ausrichtung |
| `L`, `a`, `b` | Mittelwert im Lab-Raum | `cv2.COLOR_BGR2LAB` | Farbe, Verfärbung |
| `hue`, `sat`, `val` | Mittelwert im HSV-Raum | `cv2.COLOR_BGR2HSV` | Farbe |
| `was_split`, `n_est_blob`, `touches_border` | Qualitätsflags | – | Filter, Fehleranalyse |

### Pro Bild (`summary.csv` = Bild-Feature-Tabelle)

`aggregate_image_features`: Mittelwert, Std, 10./90. Perzentil für alle Kornfeatures, dazu `area15_mean` (Mittel von A^1,5, Volumen-Proxy) und `lw2_mean` (Mittel von L·B², Ellipsoid-Proxy), Kornzahlen (`n_single`, `n_blob_corrected`). Diese Tabelle geht direkt in `train_model.py`.

---

## 5. TKM-Schätzung aus Bildern: drei Methoden

Kernproblem: Ein Bild liefert **2D-Fläche**, die TKM ist eine **Masse**. Masse ≈ Dichte × Volumen, Volumen hängt von der Kornform (Dicke!) und Feuchte ab.

| Methode | Prinzip | Voraussetzung | Stärke | Schwäche |
|---|---|---|---|---|
| **A: Wiegen + Zählen** | `TKM = Probenmasse / gezählte Körner × 1000` | Probe gewogen | sehr genau, robust, einfach | Waage nötig; nur Mittelwert |
| **B: Flächenmodell** | Einzelkornmasse `m = k · A^1,5`, `k` aus gewogener Probe kalibriert | gewogene Kalibrierprobe | liefert Massenverteilung je Korn | `k` ist Sorten-/Formabhängig (siehe Test) |
| **C: Regression** | Bild-Features → TKM (Ridge/RF/GBM) aus vielen gewogenen Proben | ≥ 20–30 Proben mit TKM-Label | lernt Form/Dicke-Effekte implizit | braucht Labels, Gefahr der Überanpassung |
| **D (optional): CNN** | Bild → TKM direkt (Transfer Learning) | viele Bilder + Labels, GPU | kein Feature-Engineering | Datenhunger, schwer erklärbar |

Tipp zur Genauigkeit: Eine **Seitenaufnahme** (zweite Kamera/Spiegel) liefert die Kornhöhe und löst das Dickenproblem. Als Verbesserungsvorschlag im Pitch nennen, nicht als geleistete Arbeit.

---

## 6. Validierung auf synthetischen Daten (gemessene Ergebnisse)

Testaufbau: 24 künstlich erzeugte Bilder (`make_synthetic_data.py`, Seed 42), 73–158 Körner je Bild, 15 % berührende Körner, Beleuchtungsgradient, Sensorrauschen, 2-€-Referenzmünze. Wahrheit (Kornzahl, Masse) bekannt.

| Prüfgröße | Ergebnis | Kommentar |
|---|---|---|
| Kornzahl, Rohzählung (nur getrennte Objekte) | mittlerer Fehler 4,3 Körner, bis −10 | untersegmentierte Cluster |
| Kornzahl, Blob-korrigiert (Σ `n_est_blob`) | Fehler −2 bis +1 Korn, mittlerer Betrag 0,6 Körner (0,5 %) | Rest: ungelöste Cluster (rot im Overlay) |
| Maßstab über Münze | +1,7 % Überschätzung des Durchmessers | Ursache: 4 px breiter Münzrand im synthetischen Bild; bei Messung am Lineal ggf. besser |
| **Methode A** (Wiegen + Zählen) | mittlerer TKM-Fehler **0,5 %** (max. 1,7 %) | robusteste Methode |
| **Methode B** (k aus *einem* Bild kalibriert) | mittlerer Fehler **4,1 %**, max. **−9,7 %** (23 Bilder, Kalibrierung auf Bild 1) | `k` überträgt sich nicht auf Partien mit anderem Seitenverhältnis |
| **Methode C** (Ridge, Leave-One-Out, n = 24) | **MAPE 1,4 %**, R² 0,987; Baseline (Mittelwert) 15,6 % | Datensatz idealisiert (Dicke ∝ Breite), echte Daten werden schlechter |
| Runde Körner (raps-ähnlich, 40 px Durchmesser, berührend) | Zählfehler −0,8 % / −4,0 % / −7,3 % bei 250 / 400 / 600 Körnern je Bild | Pipeline funktioniert ohne Hough-Kreise; bei dichter Belegung Unterzählung → Körner vereinzeln, Anzahl je Bild begrenzen |
| Referenzmünze am Bildrand angeschnitten | Maßstab wird verworfen (`ref_found = False`) | verhindert stillschweigend falschen Maßstab (vorher +6 % Fehler) |

Ehrliche Einordnung für den Pitch:
- Die Kette Bild → Segmentierung → Features → TKM funktioniert technisch.
- Die synthetischen Werte sind eine **Obergrenze**; auf echten Daten sind Schatten, Spiegelungen, Staub, Kornüberlappung und variable Kornform zu erwarten.
- Methode B nie mit einem einzigen Kalibrierfaktor über verschiedene Sorten/Partien verwenden. Kalibrierung je Sorte/Partie oder Regression (C).

---

## 7. Qualitätsmerkmale aus Bildern (zusätzliche Mehrwerte)

| Ziel | Ansatz | Hinweis |
|---|---|---|
| **Bruchkorn** | niedrige `solidity`, Fläche deutlich < Median, unregelmäßige Kontur | Schwellen aus Verteilung ableiten (z. B. < 5. Perzentil) |
| **Schmachtkorn / Siebfraktion** | `sieve_fractions(width_mm)` | Kornbreite ≈ Spaltsiebweite |
| **Verfärbung / Fusariumverdacht** | K-Means (k = 2–3) im Lab-Raum über alle Körner; Cluster mit abweichender Farbe | unüberwacht, mit Landwirt/Label validieren |
| **Fremdbesatz** | Ausreißer in (Fläche, Form, Farbe) via `IsolationForest` | Landwirt zeigt, wie Besatz aussieht |
| **Auswuchs** | sichtbarer Keimling → Formabweichung | schwierig, nur bei guter Auflösung |
| **Sortenreinheit / Einheitlichkeit** | Variationskoeffizient von Länge/Breite je Probe | `area_cv_pct` im Summary |
| **Plausibilitätswarnung** | `plausibility_check(kultur, tkm)` gegen 5.–95.-Perzentil | verhindert absurde Ausgaben in der Demo |

---

## 8. Deep-Learning-Optionen (nur wenn Zeit/GPU vorhanden)

Nicht vorinstalliert; Verfügbarkeit, Versionen und APIs vor dem Einsatz prüfen. Zeitbudget heute: ca. 6,5 h netto.

| Option | Wann sinnvoll | Aufwand | Risiko |
|---|---|---|---|
| **Cellpose / StarDist** (generalistische Instanzsegmentierung) | Körner überlappen stark, Watershed scheitert | gering (vortrainiert), Modell-Download | Installation, CPU langsam |
| **SAM / SAM 2** (Zero-Shot-Masken) | schnelle Masken ohne Training | mittel | langsam, Übersegmentierung, Filter nötig |
| **YOLO-seg** (Ultralytics) | eigene Labels vorhanden, Echtzeit | hoch (Labeln!) | Labelaufwand sprengt Zeitbudget |
| **CNN-Regression Bild → TKM** | viele Bilder mit TKM-Label | mittel | Überanpassung bei < 100 Bildern |
| **Dichte-Regression (Zählen ohne Segmentieren)** | extrem dichte Haufen | hoch | selten nötig |

Empfehlung: **Zuerst klassische Pipeline bis lauffähig (Meilenstein M1), dann nur bei klarem Defizit DL nachrüsten.** Pro Option eine harte Zeitbox (45 min), danach Entscheidung.

---

## 9. Fehlerdiagnose

| Symptom | Wahrscheinliche Ursache | Maßnahme |
|---|---|---|
| Nur Hintergrund/zu große Maske | Polarität falsch | `--invert yes` bzw. `SegConfig(invert="yes")` |
| Körner fehlen | Kontrast im gewählten Kanal gering | `channel` testen (S, b, L), Schwellwert adaptiv |
| Schatten als Korn | Seitenlicht, Kanal gray | Kanal S/b, `flatfield`, diffuseres Licht |
| Rauschpunkte als Körner | Staub, JPEG-Artefakte | `open_px` ↑, `min_area_px` ↑ |
| Ein Korn doppelt gezählt | Furche/Glanz → zwei Maxima | `h_frac` ↑ (0,35–0,5), `close_px` ↑ |
| Zwei Körner als eins | zu geringe Distanzeinschnürung | `h_frac` ↓ (0,15), Bild schärfer; Overlay rot prüfen |
| Münze verfälscht Zählung | als Korn mitgezählt | `ref_diameter_mm` setzen (Münze wird entfernt) |
| Skalierung unplausibel | Münze falsch erkannt | `mm_per_px` aus Lineal manuell setzen |
| TKM-Modell streut stark | wenige Trainingsproben | Ridge statt RF, Features reduzieren, Gruppen-CV |
| Windows: `imread` gibt `None` | Umlaut/Leerzeichen im Pfad | `read_image` benutzen |

---

## 10. Evaluationsprotokoll (für Abgabe und Pitch)

1. **Zählung:** manuelle Zählung auf ≥ 5 Bildern (verschiedene Dichten); Metriken: mittlere absolute Abweichung (Körner), prozentuale Abweichung.
2. **TKM:** gegen Referenzmessung (Waage + Zähler); Metriken: MAE [g], MAPE [%], R², Bland-Altman-Plot (Bias und Übereinstimmungsgrenzen).
3. **Validierung ohne Leckage:** Gruppen-CV nach Feld/Partie/Probe (nicht dieselbe Probe in Train und Test).
4. **Fehlerbeispiele zeigen:** 2–3 Overlays mit Fehlern und Erklärung (Ehrlichkeit punktet).
5. **Zeit:** Sekunden je Bild vs. manuelles Verfahren.
6. **Reproduzierbarkeit:** Zufallssaat fix, Parameter in einer Konfiguration, ein Befehl von Rohdaten bis Ergebnis.
