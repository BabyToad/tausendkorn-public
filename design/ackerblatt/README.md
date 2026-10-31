# C · Ackerblatt

Die App als Feldbuch und Saatgutkatalog: Haferpapier, Tintenbraun, Serifen, ein
Bleistiftkreis um jede unsichere Stelle. Erzählt statt meldet: „Sechs Stellen,
bitte kurz ansehen“.

**Leiht von:** Feldbuch und Schlagkartei (Datum am Rand, Punktleitern zu den Werten),
Saatgutkatalogen und Fachzeitschriften (Serifen-Überschrift, Abbildung mit
Bildunterschrift), dem Schulheft (Rechenweg mit doppelt unterstrichenem Ergebnis),
dem Kraftpapier-Sack und dem Abreißzettel („Zettel für die Drillmaschine“).

## System

| | |
|---|---|
| Schrift | **Literata** 500–700 (opsz) für Überschriften, Zahlen, Randnotizen, kursiv für Einheiten; **Public Sans** 400–600 für Bedienung und Hinweise. Lining-Ziffern, tabellarisch. |
| Farbe | Hafer `#F3ECDD`, Karte `#FBF7EE`, Tinte `#241B12` (14:1), Text 2 `#4F4032` (8:1), Kraft `#C9A877` (nur Linien), Ackergrün `#233D2B` (Hauptknopf, Ergebnis), gezählt Preußischblau `#1D4E89`, unsicher Ocker `#C27A00` als Bleistiftkreis, Text dazu `#7A4A00`. |
| Raster | typografisch in 6er-Schritten: 6 / 12 / 18 / 24 / 36 / 54 px, Radius 6 px, Ziele ≥ 60 px. |
| Bewegung | Tinte und Hand: `cubic-bezier(.25,.8,.25,1)` und `(.45,.05,.35,1)`, 180 / 300 / 500 / 900 ms. |

## Bewegungssignatur

- **Zählen:** Marken „tropfen“ ein (Punkt wächst wie Tinte, der helle Ring folgt),
  Ausschnitt für Ausschnitt; die Zahl zählt mit, am Ende zieht ein Bleistiftstrich
  die Zahl unter.
- **Unsicher:** Bleistiftkreis wird gezogen (700 ms), dann atmet der Graphit langsam
  (3 s). Kreis statt Kasten: wirkt wie ein Hinweis eines Menschen, nicht wie ein Fehler.
- **Ergebnis:** kg/ha läuft weich ein, wird unterstrichen, danach erscheint die
  Spanne als Satz („ungefähr 145 bis 157 kg/ha, weil 6 Stellen ungeprüft sind“).
- **Reduzierte Bewegung:** Kreise und Striche sofort fertig, dicker statt atmend.

## Stärken / Schwächen

- + Am wärmsten und am wenigsten „Technik“: senkt die Hemmschwelle bei Älteren,
  passt zu Hofladen, Feldtag und Pitch vor Landwirt:innen.
- + Bleistiftkreis ist das klarste Bild für „hier bitte hinsehen“ der drei.
- + Sätze statt Kürzel erklären Spanne und Rechenweg ohne Fachbegriffe.
- − Serifen und Kursive verlieren in praller Sonne zuerst; Zahlen deshalb 600 und groß.
- − Mehr Text pro Bildschirm, langsamer zu überfliegen beim zehnten Hänger.
- − Risiko „Landlust“-Kitsch, wenn Ornamente dazukommen; nur Linien, keine Ähren.
