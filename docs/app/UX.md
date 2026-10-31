# UX der Feld-App

Stand 27.10.2026, 19:15 (nach Astras Kritik). Für die Builder-Session (`app/`). Die Entscheidungen stehen
oben, Begründungen und Wortlaut unten. Kritik von Astra: Abschnitt 9.

## 0. Entscheidungen auf einen Blick (für den MVP heute)

1. **Fünf Bildschirme, ein Pfad:** Probe → Foto → Zählen → Prüfen → Ergebnis.
   Verlauf ist die Startseite, nicht ein sechster Schritt.
2. **Pflichtfelder vor dem Foto: nur Kultur.** Sorte und Partie/Hänger sind optional
   und werden aus der letzten Probe vorbelegt. Gewicht kommt erst nach dem Zählen.
3. **Ergebnis = eine große Zahl**, darunter die Körnerzahl mit ehrlicher Spanne.
   Keine Prozent-Konfidenz, keine Ampel ohne Handlung.
4. **Prüfen ist nur Pflicht, wenn es Prüfstellen gibt**, und dann höchstens die
   Stellen aus `check_here`, eine nach der anderen, groß gezoomt. Alles andere ist
   optional („Alle Markierungen ansehen“).
5. **Korrektur = Tippen.** Tippen auf leere Stelle setzt ein Korn, Tippen auf eine
   Markierung entfernt sie. Kein Langdruck, keine Werkzeugwahl. Rückgängig-Knopf immer
   sichtbar.
6. **Rechner ist Teil des Ergebnisses,** kein eigener Menüpunkt: Gewicht eintippen →
   TKG; Keimfähigkeit (Pflicht, keine Vorgabe) + **Saatstärke in keimfähigen
   Körnern/m²** (vorbelegt je Kultur) → kg/ha. Pflanzen/m² + Feldaufgang nur als
   Zusatzmodus (`SAATGUTRECHNER.md` 2.3). Unter dem Ergebnis eine Rechenzeile
   („320 keimf. K./m² ÷ 95 % × 46,3 g = 156 kg/ha“) und „Drillmaschine auf 156 kg/ha
   abdrehen“.
9. **Gewogen wird die ganze Probe, wie sie auf dem Blatt liegt**, mit Bruch, Spreu und
   Fremdbesatz; gezählt werden nur ganze Körner. Ergebnis: Gewicht der Partie pro 1000
   ganze Körner, genau das, was die Drillmaschine ausbringt (bewusst kein Labor-TKG nach
   ISO, das ohne Besatz etwas niedriger liegt). Nach dem Foto alles vom Blatt in die
   tarierte Schale.
7. **Alles wird gespeichert, auch halbfertige Proben.** Nichts geht verloren, wenn das
   Netz weg ist oder die App geschlossen wird.
8. **Deutsch, Sie-Form, keine Fachbegriffe außer TKG, Keimfähigkeit, kg/ha, Körner/m².**

## 1. Feldprinzipien

| Bedingung | Folge für das Design |
|---|---|
| Handschuhe, staubige oder nasse Finger | Tippziele ≥ 56 pt, Hauptknopf über die volle Breite unten (Daumenzone), Abstand ≥ 12 pt zwischen Knöpfen. Keine Wischgesten als einziger Weg, kein Langdruck, kein Doppeltippen. |
| Sonne, Hallenlicht, Staub auf dem Display | Heller Modus mit hohem Kontrast (Text #111 auf #FFF, ≥ 7:1). Schrift ≥ 17 pt, Zahlen im Ergebnis ≥ 48 pt. Farbe nie allein als Signal: immer Symbol + Wort. |
| Eine Hand am Sack, eine am Gerät | Ein Hauptknopf pro Bildschirm, unten. Zurück oben links. |
| iPad im Hochformat (Hauptgerät), iPhone geht auch | Eine Spalte, max. 600 pt breit, zentriert. Querformat wird nur toleriert, nicht gestaltet. |
| Netz auf dem Hof unsicher | Foto und Eingaben sofort lokal speichern. Zählen braucht Netz (Pipeline in der Cloud): klar sagen, Probe als „wartet auf Netz“ ablegen, später automatisch zählen. |
| Zählen dauert (≈ 1–2 min, ungemessen in der App) | Fortschritt ehrlich anzeigen (Ausschnitte fertig / gesamt), Bildschirm darf verlassen werden, Probe zählt im Hintergrund weiter. |
| Zehn Hänger in zwei Wochen | Wiederholung muss schnell gehen: „Nächste Probe“ übernimmt Kultur und Sorte. |
| Unterbrechung (Telefon, Hänger kommt) | Jeder Schritt ist ein gespeicherter Zustand. Wiedereinstieg über den Verlauf. |

**Eine Entscheidung pro Bildschirm.** Wenn ein Bildschirm zwei Fragen stellt, wird er
geteilt oder eine Frage bekommt einen Vorgabewert.

## 2. Ablauf

```
Verlauf (Start) ──[+ Neue Probe]──► 1 Probe ──► 2 Foto ──► 3 Zählen ──► 4 Prüfen* ──► 5 Ergebnis
       ▲                                         ▲   │ Warnung                          │
       │                                         └───┘ „Neu aufnehmen“                 │
       └───────────────────────────────[Speichern / Nächste Probe]─────────────────────┘
* nur wenn Prüfstellen vorhanden
```

### 0 · Verlauf (Startseite)

- Oben: großer Knopf **„+ Neue Probe“**.
- Darunter Liste, neueste zuerst. Zeile: Kultur-Symbol, **Sorte · Partie**, Datum,
  rechts groß **TKG** und **kg/ha**. Status-Plakette, wenn nicht fertig:
  „Wartet auf Netz“, „Wird gezählt“, „Prüfen“, „Gewicht fehlt“.
- Tippen öffnet die Probe im Ergebnis (bzw. im offenen Schritt).
- Leerer Zustand: „Noch keine Proben. Legen Sie eine Handvoll Körner auf ein weißes
  A4-Blatt und tippen Sie auf ‚Neue Probe‘.“

### 1 · Probe

Titel: **Was zählen wir?**

- Kultur als große Kacheln (Pflicht, eine Auswahl): Winterweizen, Sommerweizen,
  Durum, Wintergerste, Sommergerste, Winterroggen, Hafer. Vorbelegt mit der letzten.
- Sorte (Freitext mit Vorschlägen aus dem Verlauf), optional.
- Partie / Hänger (Freitext, z. B. „Hänger 3“), optional. Feld ist **leer** (nicht
  „letzte + 1“ raten); Vorschläge aus dem Verlauf als Chips.
- Bei Wintergerste und Winterroggen eine Zusatzfrage (Kacheln): mehrzeilig /
  zweizeilig / Hybrid bzw. Population / Hybrid. Bestimmt die Vorgabe der Saatstärke.
- Knopf: **„Weiter zum Foto“**.

Warum Kultur Pflicht ist: sie bestimmt Vorgaben im Rechner (Pflanzen/m², Feldaufgang)
und die Plausibilitätsprüfung des TKG.

### 2 · Foto

Titel: **Körner fotografieren**

Vor dem ersten Foto (danach einklappbar als „Anleitung“), drei Bilder mit je einer Zeile:

1. „Aus mehreren Stellen von Sack oder Hänger je eine kleine Menge nehmen und mischen.
   Davon eine Handvoll (500–1000 Körner).“
2. „Nichts heraussuchen, die Probe bleibt, wie sie ist. Körner auf weißem A4-Blatt
   verteilen, ohne Häufchen, mit der flachen Hand glattstreichen.“
3. „Von oben fotografieren, das ganze Blatt im Bild, kein eigener Schatten.“

Kamera: Kamera-Ansicht mit A4-Umriss als Hilfslinie (Hochformat). Auslöser groß
unten. Alternativ „Foto aus Galerie“ (klein, sekundär).

**Prüfung vor dem Zählen** (lokal, schnell, < 2 s; nur Warnung, nie Sperre):

| Befund | Text | Knöpfe |
|---|---|---|
| Blatt nicht vollständig gefunden | „Das Blatt ist nicht ganz zu sehen. Bitte alle vier Ecken ins Bild nehmen.“ | **Neu aufnehmen** · Trotzdem zählen |
| Häufchen / Körner übereinander | „Einige Körner liegen übereinander (markiert). Kurz auseinanderstreichen, dann neu fotografieren.“ Markierung der Stellen im Foto. | **Neu aufnehmen** · Trotzdem zählen |
| Starker Schatten / zu dunkel | „Schatten auf dem Blatt. Stellen Sie sich so, dass die Sonne/Lampe nicht hinter Ihnen steht.“ | **Neu aufnehmen** · Trotzdem zählen |
| Unscharf | „Das Foto ist unscharf. Gerät ruhig halten und neu aufnehmen.“ | **Neu aufnehmen** · Trotzdem zählen |
| Sehr wenige Körner (< 300) | „Nur etwa {n} Körner. Für ein genaues TKG besser 500–1000 Körner.“ | **Mehr Körner** · Trotzdem zählen |
| alles gut | (kein Dialog) „Foto sieht gut aus.“ + automatisch weiter | – |

Hauptknopf je Warnung ist „Neu aufnehmen“ (das kostet 10 s und spart Prüfarbeit).
„Trotzdem zählen“ ist nur ein Textlink. Höchstens die wichtigste Warnung zeigen.
Bei **starken** Häufchen oder abgeschnittenem Blatt (Körner können fehlen) zeigt das
Ergebnis die Körnerzahl als „ca.“, **aber keine Aussaatmenge**: „Für die Aussaatmenge
bitte Körner auseinanderstreichen und neu fotografieren.“ Fehlende Körner kann auch
„ca.“ nicht eingrenzen (Astra, Runde 2).

Hinweis für den Builder: Wenn die lokale Vorprüfung heute nicht fertig wird, reichen
Blatt-gefunden und Unschärfe. Häufchen-Erkennung kann über die Black-Hat-Maske aus
`adaptive.py` laufen (große zusammenhängende Flecken), falls schon serverseitig.

### 3 · Zählen

Titel: **Körner werden gezählt**

- Foto groß, darauf erscheinen die Punkte, sobald Ausschnitte fertig sind (macht die
  Wartezeit verständlich und zeigt, was die Maschine tut).
- Fortschritt: „{fertig} von {gesamt} Bildausschnitten“ + Balken. Kein Countdown in
  Sekunden, wenn wir ihn nicht kennen.
- Drei ehrliche Zustände, als Schrittanzeige: **Gespeichert** (auf dem Gerät) →
  **Gesendet** (Server hat das Foto bestätigt) → **Wird gezählt**.
- Erst ab „Gesendet“: „Sie können die App schließen. Das Ergebnis erscheint im
  Verlauf.“ Vorher: „Bitte warten, bis das Foto gesendet ist.“
- Ohne Netz: „Kein Netz. Das Foto ist auf diesem Gerät gespeichert. Tippen Sie auf
  ‚Senden‘, sobald Sie Empfang haben.“ Knöpfe **„Senden“** · Zum Verlauf.
  Erneutes Senden darf keine zweite Zählung starten (Probe-ID clientseitig erzeugen,
  Server nimmt sie idempotent an).
- Fehler beim Zählen: „Das Zählen hat nicht geklappt. Ihr Foto ist gespeichert.“
  Knöpfe **„Nochmal versuchen“** · Zum Verlauf.

### 4 · Prüfen (nur wenn `check_here` nicht leer)

Titel: **{k} Stellen bitte kurz prüfen**

Untertitel: „An diesen Stellen war sich die Zählung unsicher. Das dauert etwa
{k × 10} Sekunden.“

Pro Stelle ein Bildschirm (Karte), Zähler „Stelle 2 von 5“:

- Ausschnitt groß gezoomt (Region aus `check_here[i].region` + Rand), so weit, dass
  **ein Korn ≥ 44 pt lang** ist; dann ist das Korn selbst das Tippziel. Punkte als
  Kreis mit Kontrastrand (≥ 20 pt), Trefferfläche für „Punkt entfernen“ ≥ 44 pt.
  Ausschnitt zu groß dafür → in zwei Karten teilen.
- Darüber der Kommentar des Modells, übersetzt in Klartext, z. B.
  „Hier liegen mehrere Körner übereinander. Fehlt eines, oder ist eins doppelt?“
  (Kommentar kommt aus dem Modell; die App kürzt auf eine Zeile und stellt ihn als
  Frage, nicht als Befund.)
- Bedienhinweis einmalig: „Tippen Sie auf ein Korn ohne Punkt, um es hinzuzufügen.
  Tippen Sie auf einen falschen Punkt, um ihn zu entfernen.“
- Zähler live: „In diesem Ausschnitt: 14 Körner“.
- Knöpfe: **„Stimmt so“** (Hauptknopf, nächste Stelle) · Rückgängig · Zoom per
  Zwei-Finger ist erlaubt, aber nicht nötig.
- Oben rechts „Später prüfen“: Ergebnis wird angezeigt, Probe behält Plakette „Prüfen“.

Nach der letzten Stelle direkt zum Ergebnis, Meldung kurz: „Danke. {n} Körner.“

Optional, aus dem Ergebnis erreichbar: **„Alle Markierungen ansehen“**, das ganze Foto
mit allen Punkten, gleiche Tipp-Bedienung, für Misstrauische und für den Pitch.

### 5 · Ergebnis + Rechner

Titel: **Sorte · Partie** (oder Kultur, wenn leer)

Blöcke von oben nach unten, jeder Block erscheint erst, wenn der vorige ausgefüllt ist
(eine Entscheidung pro Moment, trotzdem ein Bildschirm):

1. **Körner:** „**982 Körner**“ groß. Darunter je nach Lage (Abschnitt 3):
   „Prüfstellen bestätigt“ oder „ca. – 3 Stellen ungeprüft“. Klein: Vorschaubild,
   Tippen öffnet „Alle Markierungen ansehen“.
2. **Gewicht:** „Wie viel wiegen diese Körner?“ Zahlenfeld in g, eine Nachkommastelle,
   numerische Tastatur, Hinweis „Alle Körner vom Blatt in die tarierte Schale. Waage
   mit 0,1 g.“ Bei < 500 Körnern und Gewicht ohne Nachkommastelle: „Ihre Waage zeigt
   ganze Gramm. Das sind hier bis zu {0,5/m × 100} % Abweichung. Besser eine Waage mit
   0,1 g oder mehr Körner.“
   → sobald eingetragen: **„TKG 46,3 g“** groß.
   Plausibilität: liegt TKG außerhalb 5.–95. Perzentil der Kultur
   (`wissensbank/01_Domain_Wissen.md` 4.1): „Ungewöhnlich für Winterweizen (meist 39–59 g).
   Gewicht und Kultur prüfen.“ Nur Hinweis.
   Ohne Gewicht ist hier Schluss (Probe ist trotzdem gespeichert, Plakette
   „Gewicht fehlt“).
3. **Aussaat:** zwei Felder: **Saatstärke (keimfähige Körner/m²)**, vorbelegt je
   Kultur mit Spanne darunter („üblich 310–350 bei normaler Saatzeit“), ±10-Knöpfe;
   **Keimfähigkeit %**, leer und Pflicht („steht auf dem Sacketikett“). „Mehr ›“ öffnet
   den Pflanzen-Modus (Ziel-Pflanzen/m² + Feldaufgang, Vorgabe 90 %).
   Ohne Keimfähigkeit keine kg/ha.
   → **„Aussaatmenge 156 kg/ha“** sehr groß, darunter die Rechenzeile und
   „= 337 Körner/m² ablegen · Drillmaschine auf 156 kg/ha abdrehen“.
4. Knöpfe: **„Speichern“** (Hauptknopf) · „Nächste Probe (gleiche Sorte)“.

## 3. Was wir zeigen, wenn die Zählung unsicher ist

Grundsatz: **Die Unsicherheit wird in eine Handlung übersetzt, nicht in eine Zahl.**

| Lage | Anzeige beim Ergebnis | Rechner |
|---|---|---|
| Keine Prüfstellen | „982 Körner“ + „automatisch gezählt“ + Link „Markierungen ansehen“ | normal |
| Prüfstellen, alle bestätigt | „982 Körner“ + Häkchen „Prüfstellen bestätigt“ | normal |
| Prüfstellen, nicht alle bestätigt | „ca. 982 Körner“ + „{k} Stellen ungeprüft“ (Knopf Prüfen) | TKG und kg/ha mit „ca.“ |
| Vorprüfung: leichte Warnung (Schatten, wenig Körner), trotzdem gezählt | wie oben + Zeile mit dem Befund | wie oben |
| Vorprüfung: starke Häufchen oder Blatt abgeschnitten, trotzdem gezählt | „ca. 982 Körner“ + „Foto hatte Häufchen“ | TKG mit „ca.“, **keine kg/ha** |
| Zählen teilweise fehlgeschlagen (Ausschnitte `failed`) | „Zählung unvollständig“ + **Nochmal zählen** | gesperrt |

**Wortwahl:** nie „geprüft“ oder „sicher“ ohne Zusatz. „Keine Prüfstellen“ heißt nur,
dass die Zählung sich nicht unsicher war, nicht, dass sie stimmt. Darum ist „Alle
Markierungen ansehen“ immer einen Tap entfernt.

**Keine ± Zahl und keine Prozent-Genauigkeit in der App**, solange wir keine pro Probe
kalibrierte Spanne haben. Gemessene Fehler auf Holdout/Test gehören in den Pitch
(getrennt: automatisch vs. nach Korrektur), nicht in die App.

Größenordnung für uns (nicht für die App): ein Zählfehler von e % verschiebt TKG und
kg/ha um etwa −e % (TKG ∝ 1/n). Die Drillmaschine wird ohnehin per Abdrehprobe
eingestellt; die App ersetzt die Abdrehprobe nicht und sagt das.

## 4. Wortliste

| Statt | Sagen wir |
|---|---|
| Inferenz, Modell, KI | „die Zählung“ |
| Konfidenz, Score | „unsicher“ / „sicher“ |
| Kachel, Tile | „Ausschnitt“ |
| Upload | „senden“ (oder gar nicht erwähnen) |
| TKM / TGW | **TKG** (Tausendkorngewicht) |
| Saatstärke / Saatmenge / Aussaatrate | **Aussaatmenge (kg/ha)** |
| Batch / Charge / Lot | **Partie** (Hänger als Beispiel) |
| Fehler 500 / Timeout | „hat nicht geklappt“ + was jetzt |

Zahlen deutsch: Komma als Dezimaltrennzeichen, Tausenderpunkt nur ab 10.000.

## 5. Kleinigkeiten mit großer Wirkung

- Zahlenfelder: `inputmode="decimal"`, Komma und Punkt akzeptieren.
- Kamera: `<input type="file" accept="image/*" capture="environment">` reicht für den
  MVP; eigene Live-Kamera mit A4-Umriss erst, wenn Zeit bleibt.
- Foto vor dem Senden auf ≈ 4000 px lange Kante begrenzen, EXIF-Drehung beachten.
- Bildschirm nicht sperren lassen während des Zählens (Wake Lock, wenn verfügbar).
- „Zum Home-Bildschirm“ (PWA) mit Symbol, damit es wie eine App startet.

## 6. Nicht im MVP (bewusst)

Konto/Login, Betriebsverwaltung, Export (kommt in `ROADMAP.md`), Dunkelmodus,
Mehrsprachigkeit, Bruchkorn/Fremdbesatz-Anzeige, Live-Kamera mit Echtzeit-Warnung.

## 7. Pitch-Demo (5 min, Laienpublikum)

Die Zählung dauert ≈ 1–2 min, das passt nicht live in 5 min mit Erklärung. Darum:

1. Live: Handvoll aufs Blatt, Foto, „Gesendet“ (10 s). Zählung läuft im Hintergrund.
2. Weiter mit einer **vorher gezählten Probe** aus dem Verlauf (ausdrücklich so
   ansagen): Punkte zeigen → eine Prüfstelle, ein Korn ergänzen → Gewicht →
   **„156 kg/ha“** mit Rechenzeile.
3. Am Ende zurück zum Verlauf: die Live-Probe ist inzwischen fertig.

Rückfall bei Netzausfall: Schritt 2 allein. Für Proben vorab `TK_MOCK=1` nicht im Pitch
benutzen, sondern echte gezählte Proben.

## 8. Offene Fragen an Jonas / Leon

- Hat der Hof eine Waage mit 0,1 g, oder eher 1 g? (Bestimmt Nachkommastellen.)
- Wird Keimfähigkeit vom Saatgutsack (Z-Saatgut-Etikett) übernommen oder selbst
  bestimmt? Für Nachbau: eigene Schalenprobe.
- Rechnet Leon in Körnern/m² oder Pflanzen/m²? (Rechner kann beides, Vorgabe wählen.)

## 9. Kritik von Astra und wo wir anderer Meinung sind

Runde 1 am 27.10. abends (Volltext in den Session-Notizen). Astras drei wichtigste
Punkte, alle übernommen:

1. **Rechner vermischte Pflanzen/m², keimfähige Körner/m² und abgelegte Körner/m².**
   Empfehlungen nennen keimfähige Körner/m²; wer dann noch Feldaufgang abzieht, sät
   zu dick. → Standard ist jetzt „keimfähige Körner/m²“, Pflanzen-Modus nur unter
   „Mehr“ (Entscheidung 6, `SAATGUTRECHNER.md`).
2. **Zählung und Wägung können verschiedene Proben beschreiben** („nichts aussortieren“
   vs. „ohne Bruch wiegen“). → Entschieden 27.10. abends: die ganze Probe vom Blatt wiegen,
   inklusive Besatz, und nur ganze Körner zählen (Entscheidung 9). Ergibt das Partie-Gewicht
   pro 1000 Körner; Grenze: Probe repräsentativ und vollständig gewogen.
3. **„Keine Prüfstellen“ ist nicht „richtig“**, die Konfidenz kommt vom selben Modell;
   „~1 %“ ist keine Kalibrierung. → „automatisch gezählt“ / „Prüfstellen bestätigt“,
   keine ± Zahl, Markierungen immer einen Tap entfernt (Abschnitt 3).

Ebenfalls übernommen: Probe aus mehreren Stellen mischen; Partie nicht raten;
Unterart bei Gerste/Roggen abfragen; Waagen-Genauigkeit ansprechen; drei ehrliche
Sendezustände und idempotentes Senden; Rechenzeile und „Drillmaschine abdrehen“;
Pitch-Demo mit vorher gezählter Probe statt Live-Wartezeit.

**Wo wir anderer Meinung sind:**

| Astra | Wir | Warum |
|---|---|---|
| Bei starken Häufchen, Blatt abgeschnitten oder Unschärfe **neu fotografieren erzwingen** | Warnen, „Neu aufnehmen“ als Hauptknopf, „Trotzdem zählen“ als Textlink; Ergebnis dann „ca.“ | Die Vorprüfung ist heuristisch und noch nicht gemessen; eine falsche Sperre im Hof ist schlimmer als eine markierte Zahl. **Runde 2, Einigung:** Zählen bleibt möglich, aber bei starken Häufchen / abgeschnittenem Blatt gibt es keine kg/ha. |
| Markierungen anzeigen und Auswahl trennen, eigene große Korrektur-Bedienelemente | Tippen direkt aufs Korn, aber erst nach starkem Zoom (Korn ≥ 44 pt) | Ein zweiter Bedienmodus kostet Erklärung. Zoom löst das Zielproblem. Mit echten Handschuhen testen wir morgen; normale Arbeitshandschuhe bedienen kein iPad, das löst auch eine andere Bedienung nicht. **Runde 2:** Astra akzeptiert vorläufig; mehrdeutige Taps (zwei Punkte im Trefferbereich) → nächster Punkt gewinnt, Rückgängig bleibt groß. |
| Live-Overlay, lokale Häufchen-Erkennung, Verlauf und Hintergrund-Wiederaufnahme sind heute zu viel | Verlauf bleibt im MVP; Live-Overlay und Häufchen-Erkennung optional | Der Verlauf ist das, was Landwirte bei zehn Hängern brauchen, und ist im Backend schon da (`samples`). **Runde 2:** geklärt. |
