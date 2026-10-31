# B · Labor

Die App als ruhiges Präzisionsinstrument: eine Anzeige pro Moment, viel Luft,
Graphit auf kühlem Papier, ein einziges Blau für gezählte Körner. Das A4-Blatt ist
der Maßstab, darum hat das Foto ein Millimeterlineal.

**Leiht von:** Feinwaagen-Anzeigen (Monospace-Zahl, Einheit klein daneben),
Mikroskop-Software (Navigator-Minikarte zeigt, wo im Gesamtbild man gerade prüft),
Millimeterpapier, Dieter Rams’ „so wenig Design wie möglich“.

## System

| | |
|---|---|
| Schrift | **IBM Plex Sans** 400–600 für Text und Überschriften; **IBM Plex Mono** 500–600 für alle Zahlen, Labels, Rechenzeile. |
| Farbe | Papier `#F4F5F3`, Fläche `#FFF`, Graphit `#14181B` (16:1), Text 2 `#434A50` (8:1), Haarlinie `#B9C0C4`, gezählt `#005FB8`, unsicher `#E08A00` gestrichelt, Text dazu `#8A4B00`. |
| Raster | 4 / 8 / 16 / 24 / 40 / 64 px, Haarlinien 1,5 px, Radius 12 px, Ziele ≥ 60 px. |
| Bewegung | weich abbremsen ohne Überschwingen: `cubic-bezier(.16,1,.3,1)`, 160 / 280 / 460 / 700 ms. |

## Bewegungssignatur

- **Zählen:** gestricheltes Raster der Ausschnitte liegt über dem Foto; jeder fertige
  Ausschnitt löst sich auf, seine Marken blenden ein und ziehen ihren weißen Ring.
  Dünne Fortschrittslinie, Zahl in Mono zählt mit.
- **Unsicher:** gestrichelter Rahmen „schaut“: Deckkraft atmet 2,8 s, keine Größenänderung.
- **Prüfen:** Kamerafahrt in die Stelle; der Navigator unten rechts zeigt die Lage.
- **Ergebnis:** Zahl läuft weich ein; danach zieht sich der Messbalken (Spanne als
  Band auf einer Skala) von der Mitte auf.
- **Reduzierte Bewegung:** alles sofort, Rahmen statt Atmen doppelt so dick.

## Stärken / Schwächen

- + Vertrauen durch Ruhe: wirkt wie ein Messgerät, nicht wie ein Spiel. Passt zur
  ehrlichen Spanne und zur Rechenzeile.
- + Navigator und Lineal erklären „Ausschnitt“ und „A4 als Maßstab“ ohne Worte.
- + Skaliert am besten auf iPad und in ein späteres Web-Dashboard.
- − Kühl; für Laien eher „Labor prüft mich“ als „Werkzeug für mich“.
- − Dünne Linien und Grautöne sind die ersten Opfer von Staub und Sonne; Haarlinien
  dürfen nie Inhalt tragen (hier eingehalten, aber leicht zu verletzen).
- − Lineal ist im Mockup Dekor; in der App müsste es aus dem erkannten Blatt kommen.
