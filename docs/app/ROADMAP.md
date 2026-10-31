# Roadmap über das Zählen hinaus

Stand 27.10.2026. Sortiert nach **Nutzen für den Betrieb ÷ Aufwand**. Spalte „Pitch“:
✅ = passt bis 28.10. 12:00 (Demo oder Folie), 🗣 = nur als Ausblick erzählen, – = später.

## 1. Übersicht

| # | Thema | Nutzen für den Betrieb | Aufwand | Pitch |
|---|---|---|---|---|
| 1 | Foto-Qualitätsprüfung vor dem Zählen (Blatt, Unschärfe, Häufchen, Schatten) | hoch: spart Prüfarbeit und Kosten, macht die Zahl verlässlicher | klein (Blatt + Unschärfe), mittel (Häufchen) | ✅ Blatt + Unschärfe |
| 2 | Saatgutrechner mit Vorgaben je Kultur | sehr hoch: das ist die eigentliche Entscheidung (kg/ha) | klein | ✅ |
| 3 | Verlauf je Sorte/Partie, Export CSV | hoch: zehn Hänger in zwei Wochen, Nachweis gegenüber Berater/Händler | klein | ✅ Verlauf, Export 🗣 |
| 4 | Mehrere Proben einer Partie mitteln (2–3 Handvoll → Mittelwert + Streuung) | hoch: eine Handvoll ist eine Stichprobe; zwei zeigen, ob die Partie einheitlich ist | klein–mittel | 🗣 |
| 5 | Größenverteilung und Einheitlichkeit in mm aus dem A4-Maßstab | mittel: Zyklon sortiert schon; Uniformität ist laut Landwirt wertvoll | **groß** (Umrisse, Homographie, Validierung gegen echte Maße) | 🗣 nur erwähnen, kein Histogramm zeigen |
| 6 | Bruchkorn- und Fremdbesatz-Anteil | mittel–hoch: Saatgutqualität, Einstellung Mähdrescher/Reinigung; korrigiert TKG-Bias | mittel–groß | 🗣 |
| 7 | Kosten senken: Batch-API, Prüfschleife nur bei Bedarf | für uns hoch, für Landwirt indirekt (Preis) | klein | 🗣 eine Zeile „~0,30–0,55 $ pro Probe, mit Batch die Hälfte“ |
| 8 | Offline: eigener Detektor auf dem iPad | hoch, wo kein Netz ist | groß | 🗣 |
| 9 | Drillmaschinen-Anbindung (Abdrehprobe, ISOBUS/Hersteller-Apps) | hoch, aber Integration | groß | 🗣 Folie „bis zur Drillmaschine“ |

## 2. Details

### 2.1 Foto-Qualitätsprüfung (vor dem Pitch: Teil 1)

- **Blatt gefunden:** größtes helles Viereck (OpenCV `findContours` + `approxPolyDP`),
  vier Ecken gefunden (Seitenverhältnis erst nach Entzerrung prüfen, Perspektive verzerrt es). Ohne Blatt kein Maßstab (PF-05). Warnung, keine Sperre.
- **Unschärfe:** Varianz des Laplace-Operators im Blattbereich, Schwelle auf den
  corn1000-Fotos einstellen.
- **Häufchen:** Black-Hat-Maske aus `adaptive.py`; zusammenhängende Flecken größer als
  ~6 Kornflächen (20 mm² pro Korn im A4-Maßstab) markieren. Das sind genau die
  Stellen, an denen die Zählung Doppelpunkte setzt.
- **Schatten:** Helligkeitsgefälle über das Blatt (Blatt in 4×4 Felder, Median der
  Papierpixel, max/min > Schwelle).
- **Zu wenige Körner:** Schätzung aus Maskenfläche / 20 mm².

### 2.2 Mehrere Proben pro Partie

Eine Handvoll mit ~1000 Körnern hat einen Zählfehler von ~1 %; die Unsicherheit der
Stichprobe selbst (wie repräsentativ ist die Handvoll?) ist meist größer. Ein zweites
Foto einer zweiten Handvoll zeigt beides. Darstellung: „TKG 46,3 g (2 Proben:
46,0 / 46,6)“. Gemitteltes TKG = **1000 × Σ Gewicht / Σ Körner**, nicht Mittel der
TKGs; Einzelwerte daneben. Zwei Proben trennen Zählfehler und Stichprobenstreuung
nicht; eine Schwelle wie „> 3 % → dritte Probe“ erst nach Messung festlegen.
Datenseitig braucht das eine stabile Partie-ID (Freitext „Hänger 3“ vermischt
Betriebe/Jahre); eigene Tabelle `partien` erst dann (`DATA.md` 2).

### 2.3 Größenverteilung und Einheitlichkeit

- Voraussetzung: Maßstab aus dem Blatt (Homographie auf A4) und **Kornumrisse**. Punkte
  reichen nicht. Weg: SAM/SAM2 mit den Zählpunkten als Prompts (ein Punkt = eine Maske),
  oder Watershed mit den Punkten als Saat.
- Kennzahlen: **projizierte** Länge, Breite, Fläche je Korn (Draufsicht). Das ist
  keine Siebanalyse: Siebfraktionen sind Massenanteile und hängen von der Dicke ab,
  die ein Foto nicht sieht. Also kein „Vollgerstenanteil“, keine Siebgrößen.
  Einheitlichkeit als Variationskoeffizient der projizierten Breite.
- Fallen: Seitenverhältnis 1:√2 gilt erst nach Entzerrung; Überlappung, Schatten und
  verschmolzene Masken verfälschen Maße; SAM liefert nicht garantiert genau ein Korn
  pro Punkt. Darum: unpassende Masken verwerfen, **Abdeckung angeben** („gemessen: 870
  von 982 Körnern“), an einzeln liegenden Körnern gegen Messschieber validieren.
- Anzeige: ein Balkendiagramm der Breiten + ein Satz („93 % der Körner zwischen 2,5
  und 3,2 mm breit: sehr einheitlich“). Keine Statistik-Begriffe.

### 2.4 Bruchkorn und Fremdbesatz

- Labels vorhanden: `broken_points`, `invalid_points` in 158 Punkt-gelabelten
  corn1000-Bildern; `pollution` (none/light/heavy) als Bildlabel.
- Zusatzdaten: GrainSet (Lizenz laut Autoren **CC BY-NC-SA 4.0**, nicht BY 4.0 wie in `EXISTING_SOLUTIONS.md`; 200k Weizen-Einzelkörner, Klassen u. a. BN broken,
  IM impurities), anderer Bildbereich (≈ 860 dpi Industriekamera vs. ≈ 340 dpi Handy),
  also herunterskalieren.
- **Falle:** Heute setzt die Zählung nur Punkte auf ganze Körner. Bruch und Fremdbesatz
  erreichen einen Klassifikator „pro Punkt“ also nie. Es braucht eine eigene **Suche**
  nach Nicht-Korn-Objekten (Zählung fragt zusätzlich nach Bruch/Fremd-Punkten, wie
  `broken_points`/`invalid_points` gelabelt sind), gemessen auf session-getrennten
  corn1000-Bildern.
- Weg 1 (schnell): Die Zählung setzt pro Ausschnitt zusätzlich Punkte für Bruch und
  Fremdbesatz. Kostet wenig, Genauigkeit unbekannt → auf den 158 Bildern messen.
- Weg 2: kleiner Klassifikator auf Ausschnitten um jeden Punkt (corn1000 + GrainSet).
- **Warum es auch für das TKG zählt:** Gewogen werden alle Körner auf dem Blatt; gezählt
  werden nur ganze. Liegt Bruch mit auf der Waage, ist das TKG zu hoch. Die App sagt
  heute „ohne Bruch und Fremdbesatz wiegen“; mit Erkennung kann sie stattdessen sagen
  „3 Bruchstücke gefunden, bitte vor dem Wiegen entfernen“ (markiert im Foto).
- Anzeige: Markierungen + „3 Bruchstücke gefunden, bitte entfernen und neu
  fotografieren“ bzw. „kein Bruch gefunden“ (nicht „kein Bruch“). Keine
  Prozentangabe: Stückanteil ≠ Massenanteil, und GrainSet (Industriekamera, einzelne
  Körner) ersetzt keine Messung auf Handyfotos.

### 2.5 Kosten und Offline

| Option | Wirkung | Aufwand | Wann |
|---|---|---|---|
| Batch-API (−50 %) | Proben, die nicht sofort gebraucht werden (Verlauf, Nachzählen) | klein | nach dem Pitch |
| Prüfschleife nur bei Konfidenz < 0,9 | schon umgesetzt | – | – |
| Kleineres Modell für leichte Ausschnitte, Argon nur für dichte | −30–60 % geschätzt | mittel | messen |
| Server im Hof-WLAN (Laptop) | ohne Internet, aber mit lokalem Netz | klein, aber Zählung braucht trotzdem ein Modell lokal | nur mit eigenem Detektor |
| Eigener Detektor (YOLO o. ä.) auf dem iPad, ONNX/CoreML | offline, kostenlos pro Probe | groß: Training, Export, Test auf Gerät | später; Argon-Punkte + Korrekturen sind die Trainingsdaten |
| Hybrid: Detektor offline sofort, Cloud-Zählung nachträglich zur Bestätigung | beste Nutzererfahrung | groß | Zielbild |

Ehrlich im Pitch: heute **braucht die Zählung Netz**. Foto und Eingaben gehen offline
nicht verloren.

### 2.6 Drillmaschine

Die App endet bei kg/ha. Der nächste Schritt wäre die Abdrehprobe: kg/ha + Arbeitsbreite
→ Sollgewicht für die Abdrehprobe (z. B. auf 1/10 ha). Herstellerrechner (Väderstad,
Horsch, Amazone) machen das schon; Anbindung erst, wenn jemand danach fragt.

## 3. Für den Pitch morgen

Zeigen (Demo): Foto → Punkte → eine Prüfstelle → Gewicht → kg/ha → Verlauf mit zwei
Hängern derselben Sorte und unterschiedlichem TKG („gleiche Sorte, 4 g Unterschied,
bei 350 keimfähigen Körnern/m² und 95 % Keimfähigkeit sind das 15 kg/ha“).
Das überzeugt beide Juroren mehr als ein Histogramm: Zählgenauigkeit (gemessen),
eine echte Korrektur, exakt gewogene Probe, nachvollziehbares TKG, zwei Partien mit
verschiedener Aussaatmenge. Erzählen (eine Folie): Bruchkorn/Fremdbesatz, Einheitlichkeit,
offline. Nicht versprechen: Siebanalyse, Laborgenauigkeit, Offline-Zählung.
