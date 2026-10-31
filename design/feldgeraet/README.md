# A · Feldgerät

Die App als Bedienterminal am Schlepper: Typenschild-Kopf, Signalgelb, schwarze
Rahmen, Zählwerk mit Walzenziffern. Laut, robust, aus zwei Metern lesbar.

**Leiht von:** ISOBUS-Terminals und Drillmaschinen-Rechnern (Kacheln, Anzeige mit
Einheit), Typenschildern und Schablonenschrift, Warnband (schwarz/orange) für
„hier hinsehen“.

## System

| | |
|---|---|
| Schrift | **Barlow Condensed** 600–800 für Labels, Zahlen, Knöpfe (DIN-nah, Straßenschild-Verwandtschaft); **Barlow** 500 für Fließtext. Ziffern tabellarisch. |
| Farbe | Papier `#F2F0E8`, Tinte `#111` (17:1), Stahl `#1C1D1F`, Signalgelb `#FFC400` nur mit schwarzer Schrift (≈ 13:1), gezählt `#0057B8`, unsicher `#E69F00` + Schraffur. |
| Raster | 4 / 8 / 12 / 16 / 24 / 32 / 48 px, Rahmen 3 px, Radius 3 px, Ziele ≥ 64 px. |
| Bewegung | mechanisch: `cubic-bezier(.2,.9,.1,1)`, 120 / 220 / 420 ms. Knöpfe drücken sich 4 px ein. |

## Bewegungssignatur

- **Zählen:** Zählwerk-Walzen rollen, Segmentleiste füllt sich Ausschnitt für
  Ausschnitt, der gerade fertige Ausschnitt blitzt gelb auf, seine Marken werden
  „gestempelt“ (Punkt 1,9× → 1×, 160 ms).
- **Unsicher:** Warnband-Rahmen, Füllung atmet orange (2,4 s), Nummer auf schwarzem Knopf.
- **Ergebnis:** kg/ha läuft hoch und rastet mit 4 % Überschlag ein, die Spanne erscheint danach.
- **Reduzierte Bewegung** (`prefers-reduced-motion` oder `?rm=1`): alles sofort, statt
  Atmen fest getönt.

## Stärken / Schwächen

- + Höchster Kontrast der drei, funktioniert in praller Sonne und mit Staub.
- + Sprache, die Landwirt:innen aus der Kabine kennen; Warnband ist ohne Farbe lesbar.
- + Zählwerk macht „Maschine arbeitet“ sofort verständlich, auch im Pitch.
- − Laut: alles ist gleich wichtig gerahmt; auf dem iPad schnell „Baustellenschild“.
- − Großbuchstaben-Kondensschrift kostet Lesetempo bei längeren Sätzen (nur Labels!).
- − Gelb als Fläche blendet in dunklen Hallen eher als die anderen Richtungen.

Gemeinsamer Kern (Daten, Rechner, Zoom, Tippen) liegt in `../shared/tk.js`.
