# Gestaltungsstudie: Tausendkorn Feld-App

Stand 27.10.2026 abends. Grundlage für drei Richtungen unter `design/` und danach
das UI-System. Bedienlogik und Wortlaut kommen aus `docs/app/UX.md`; hier geht es um
Aussehen, Typografie und Bewegung.

## 1. Was die Gestaltung tragen muss

| Bedingung | Gestalterische Folge |
|---|---|
| Pralle Sonne, Staub auf dem Glas | Heller Grund, Text ≥ 7:1, keine feinen Grautöne für Inhalt, keine Haarlinien unter 1,5 px. Dunkle Flächen nur für kurze Labels. |
| Dämmriger Schuppen | Kein reines Weiß als Riesenfläche (blendet), leicht getöntes Papier; Zahlen groß statt kontrastarm-elegant. |
| Handschuhe, eine Hand frei | Ziele ≥ 56 pt, Hauptknopf unten volle Breite, nichts nur per Geste. |
| Rosa gebeiztes Saatgut, braune und gelbe Körner | Markierungen dürfen nicht rot/orange/braun sein. Blau (Okabe-Ito #0072B2 und dunkler) mit hellem Rand trägt auf allen Kornfarben. |
| Farbenblindheit (≈ 8 % der Männer, Landwirtschaft überwiegend männlich) | Status = Form + Wort + Farbe. „Sicher“ = gefüllter Punkt, „unsicher“ = Rahmen mit Muster; Blau/Orange statt Grün/Rot. |
| Wenig Geduld, Deutsch | Eine Zahl pro Bildschirm dominiert. Kurze Verben auf Knöpfen. Komma-Dezimalen, tabellarische Ziffern, damit Zahlen beim Zählen nicht springen. |
| Vertrauen in eine KI-Zahl | Die Maschine zeigt ihre Arbeit: jedes Korn bekommt sichtbar eine Marke. Unsicherheit wird als Ort gezeigt, nicht als Prozent. |

## 2. Referenzen

- **Landtechnik-Terminals (ISOBUS-Bedienterminals, Drillmaschinen-Rechner):** große
  Kacheln, Kondensschrift, harte Rahmen, Sicherheitsgelb, Zahlen als „Anzeige“ mit
  Einheit klein daneben. Stärke: Landwirt:innen kennen die Sprache. Schwäche: oft
  überladen, dunkel, blendanfällig.
- **Maschinenbeschriftung und Typenschilder:** gestanzte Schablonenschrift, DIN-ähnliche
  Groteske, Warnstreifen, Nummernfelder mit Rahmen. Lesbar aus Distanz, robust.
- **Saatgutsack und Z-Saatgut-Etikett:** das blaue amtliche Etikett, gedruckte
  Felder („Sorte“, „Partie“, „Keimfähigkeit“), Kraftpapier, Stempel. Sprache, die
  Landwirt:innen beim Säen in der Hand halten — und wo die Keimfähigkeit steht.
- **Laborwaagen und Messgeräte (Feinwaage, Mikroskop-Software, Rams/Braun):** ein
  ruhiges Feld, eine Anzeige, Millimeterraster, Messbalken. Präzision durch Weglassen.
- **Feldbuch, Saatgutkataloge, Fachzeitschrift:** Serifen für Überschriften,
  Bleistift-Strichliste, Randnotizen, Tabellen mit Haarlinien. Wärme und Erzählung.
- **Kartografie und Messtischblatt:** Raster, Koordinaten, Lupenausschnitte —
  passend zum „Ausschnitt“, den die Zählung tatsächlich abarbeitet.
- **Sonnenlicht-UIs (Bootsplotter, Baustellen-Tablets):** hoher Luminanzkontrast,
  dicke Strokes, Farbe nur als Zusatz.

## 3. Prinzipien für alle drei Richtungen

1. **Das Foto ist der Held.** Im Prüfen-Schritt gehört der Bildschirm dem Foto; Rahmen
   und Chrome treten zurück.
2. **Eine Marke pro Korn, eine Form pro Bedeutung.** Gezählt = gefüllter blauer Punkt
   mit weißem Ring. Unsicher = orangefarbener Rahmen mit Strichmuster und Nummer.
   Neu gesetzt = Punkt mit Plus-Ring. Entfernt = verblasst mit Strich.
3. **Zahlen sind Instrumente.** Tabellarische Ziffern, Einheit klein und daneben,
   Spanne direkt unter der Zahl, nie als Fußnote.
4. **Kontrast vor Stimmung.** Jede Richtung besteht den Sonnentest: Fließtext ≥ 7:1,
   Hauptknopf ≥ 7:1, Statusfarbe nie alleiniger Träger.

## 4. Bewegungssprache

Bewegung erklärt, was die Maschine tut. Vier Momente, sonst nichts:

| Moment | Bedeutung | Regel |
|---|---|---|
| Zählen sichtbar | „Die Zählung arbeitet Ausschnitt für Ausschnitt.“ | Marken erscheinen gruppiert nach Ausschnitt, Zähler läuft mit. ≤ 2,5 s im Mockup, echte Dauer in der App. |
| Marke erscheint | „Dieses Korn ist gezählt.“ | ≤ 180 ms, kein Nachfedern über 10 %. |
| Unsichere Stelle | „Bitte hier hinsehen.“ | Langsames Atmen (2–3 s Zyklus), nur Deckkraft/Strichversatz, nie Größe über 4 %. Hört auf, sobald die Stelle bestätigt ist. |
| Ergebnis setzt sich | „Diese Zahl ist fertig.“ | Zahl läuft auf und rastet ein (≤ 700 ms), Spanne erscheint danach. |

Übergänge zwischen Bildschirmen ≤ 250 ms. Zoom auf eine Prüfstelle ist eine Kamera-
fahrt (≤ 450 ms), damit der Ort im Gesamtbild verständlich bleibt.

**`prefers-reduced-motion`:** alle Marken sofort, Atmen ersetzt durch statischen
doppelten Rahmen, Zahlen ohne Hochzählen, Zoom als Schnitt.

## 5. Drei Richtungen

| | A · Feldgerät | B · Labor | C · Ackerblatt |
|---|---|---|---|
| Idee | Robustes Bedienterminal am Schlepper | Ruhiges Präzisionsinstrument | Feldbuch und Saatgutkatalog |
| Leiht von | ISOBUS-Terminals, Typenschilder, Warnstreifen, Z-Saatgut-Etikett | Feinwaagen-Anzeige, Millimeterpapier, Rams | Fachzeitschrift, Strichliste, Kraftpapier-Sack |
| Schrift | Barlow Condensed + Barlow | IBM Plex Sans + Plex Mono | Literata + Public Sans |
| Farbe | Signalgelb, Schwarz, Papierweiß | Kühles Weiß, Graphit, ein Blau | Hafer-Papier, Tintenbraun, Preußischblau |
| Bewegung | mechanisch: Raster-Scan, Stempel, Zählwerk | präzise: Linien ziehen, weich abbremsen | handgemacht: Strich für Strich, Bleistiftkreis |
| Risiko | wirkt laut, „Spielzeug-Baustelle“ | wirkt kühl, Laien fühlen sich geprüft | Serifen klein bei Sonne schwächer, „Hofladen“ |

## 6. Bewusste Abweichung von `UX.md`

`UX.md` §3 sagt „keine ± Zahl in der App“. Der Auftrag für diese Mockups verlangt kg/ha
mit Spanne, wenn Prüfstellen übersprungen werden. Die Mockups zeigen die Spanne nur
dann und mit dem Wort „ca.“; die Breite ist ein Platzhalter (1 % gezählt + 0,5 % je
ungeprüfter Stelle), bis eine gemessene Spanne aus Holdout vorliegt. Vor dem Einbau
in `app/` mit der UX-Session klären.
