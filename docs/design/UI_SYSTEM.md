# UI-System der Feld-App

Stand 27.10.2026 abends. Gewählt: **Richtung B „Labor“**. Jonas: „die sauberste,
einfachste“. Studie und Alternativen: `docs/design/STUDY.md`, Mockups `design/`.

Dateien in `design/system/`:

| Datei | Inhalt |
|---|---|
| `tokens.css` | alle Werte als CSS-Variablen (Farbe, Schrift, Raum, Form, Marken, Bewegung) |
| `tausendkorn.css` | Komponenten. **Drop-in für `app/static/style.css`**: stylt genau die Klassen, die `app.js` heute erzeugt |
| `motion.js` | `TKMotion`: `countTo`, `revealMarks`, `markSize`, `zoomViewBox`, `fitRegion`, `reduced` |
| `index.html` | Referenzseite mit allen Bausteinen und echtem Foto (`/system/` auf dem Design-Server) |

## 1. Haltung

Ein ruhiges Messinstrument. Eine Hauptzahl pro Moment, viel Luft, Graphit auf kühlem
Papier, **ein** Blau für „gezählt / bestätigt“. Nichts Dekoratives: keine Emoji,
keine Verläufe, keine Schatten außer am Segment-Schalter. Wenn etwas unklar ist:
weglassen.

**Fünf Regeln**

1. Ein Blau (`--mark`). Es heißt „gezählt“ oder „bestätigt“, sonst nichts (auch
   Fokusring). Hauptknöpfe sind Graphit, nicht blau.
2. Unsicher ist immer **gestrichelt + nummeriert + benannt**, nie nur orange.
3. Jede Zahl in Plex Mono 600, Einheit klein in Plex Sans daneben.
4. Haarlinien (`--rule`) gliedern, tragen aber nie Inhalt. Text nie in `--rule`.
5. Bewegung nur für die vier Momente in §6. Sonst still.

## 2. Übernahme in `app/` (für tk-app)

1. In `index.html` vor dem Stylesheet die Schrift laden (§3), dann
   `tokens.css` + `tausendkorn.css` statt `style.css` einbinden (kopieren nach
   `app/static/`). `theme-color` auf `#F4F5F3`.
2. Bestehende Klassen funktionieren sofort: `.bar .brand .demo .step .muted .btn
   (.big .secondary .danger .solid .tool) .row .chips .chip(.on) label.field .unit
   .guide .card(.warn .bad) .progress(.indet) .thumb .big-num .result .label .val
   .card.main .formula .count-head .viewer .hint .spot(.n .active) .item(.t .s .k)
   .badge(.warn .bad) .toast`.
3. In `app.js` drei kleine Änderungen, damit das System greift:
   - **Marken** (Zeile ~317): statt `fill="#0047ff"` je Punkt
     `<g class="mk" transform="translate(x y) scale(k)"><circle class="mk-halo" r="halo"/><circle class="mk-dot" r="dot"/></g>`,
     Größen aus `TKMotion.markSize(k)` (§5). Neu gesetzt: `mk added`, entfernt: `mk removed`.
   - **Prüfstellen** (Zeile ~325): `<g class="ck [active|done]"><rect class="ck-back" …/><rect class="ck-box" …/>`
     (gleiche Maße, Unterlage zuerst), ohne Inline-Farben, Nummernknopf als `<g class="ck-tag">`. Am `<svg>` die
     Variable `--k` setzen (Bild-px je Bildschirm-px), dann bleiben Strichstärken gleich.
   - **Bildschirmwechsel**: nach dem Rendern `main.classList.add('enter')` (und vorher entfernen).
4. Neue, optionale Bausteine: `.eyebrow` (Label über Werten), `.link` (Nebenweg
   als Textlink), `.seg` (Segment-Schalter, z. B. 1/40 ha | 1/10 ha, Rechner-Modus),
   `.help` (Hinweis unter Feldern), `.ok` (✓ bestätigt), `.scale` (Messbalken, §4).
5. Kein Dunkelmodus im MVP (UX.md §6). Die Tokens sind so gebaut, dass er später
   nur ein zweiter `:root`-Block ist.

## 3. Schrift

**IBM Plex Sans** 400/500/600 für Text, **IBM Plex Mono** 400/500/600 für Zahlen,
Labels und die Rechenzeile (Lizenz OFL).

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
```

Offline auf dem Hof fällt das auf die Systemschrift zurück (Stapel in `tokens.css`),
das bleibt lesbar. Besser für die PWA: die sechs woff2-Dateien nach `app/static/fonts/`
legen und per `@font-face` laden (Folgeaufgabe).

| Rolle | Token | Größe | Schrift |
|---|---|---|---|
| Titel | `--fs-h1` | 34 | Sans 600, −0,02 em |
| Zwischentitel | `--fs-h2` | 24 | Sans 600 |
| Fließtext | `--fs-body` | 18 | Sans 400, Zeilenhöhe 1,5 |
| Label / Schritt | `--fs-label` | 13 | Mono 500, VERSALIEN, +0,08 em |
| Eingabezahl | `--fs-num` | 40 | Mono 600 |
| Körner, TKG | `--fs-num-l` | 54 | Mono 600 |
| Aussaatmenge | `--fs-num-xl` | 88 (72 unter 420 px) | Mono 600 |

Nie unter 15 px, Zahlen nie dünner als 600. Deutsch formatieren:
`toLocaleString('de-DE')`, Komma, tabellarische Ziffern (ist global gesetzt).

## 4. Farbe, Raum, Komponenten

Farben mit Kontrast auf `--bg`: Text `--ink` 16:1, Nebentext `--ink-2` 8:1,
Unsicher-Text `--unsure-ink` 7:1. Blau `#005FB8` und Orange `#E08A00` sind auch bei
Rot-Grün-Schwäche unterscheidbar; trotzdem trägt jede Bedeutung ein Zeichen:

| Zustand | Form | Zeichen | Farbe |
|---|---|---|---|
| gezählt | gefüllter Punkt, weißer Ring | – | `--mark` |
| neu gesetzt | weißer Punkt, blauer Ring | – | `--mark` |
| entfernt | hohler Punkt auf dunklem Kreis | – | grau |
| unsicher | orange Striche auf Graphit-Unterlage, Nummernknopf | ◌ | `--unsure` auf `--ink` |
| bestätigt | durchgezogener Rahmen, Knopf blau | ✓ | `--mark` |
| hat nicht geklappt | Karte mit Rahmen | ✕ | `--bad` |

Raum 4 / 8 / 16 / 24 / 40 / 64 px (`--s1…--s6`), eine Spalte bis 600 px,
Seitenrand 16 px. Tippziele ≥ 60 px, Hauptknopf 72 px, Abstand zwischen Knöpfen ≥ 8 px.
Radius 12 px (Karten, Knöpfe), 8 px (Foto), Pille für Chips und Plaketten.

Komponenten-Kurzreferenz (Aussehen auf `design/system/index.html`):

- **Hauptknopf** `.btn` Graphit, weiß, volle Breite unten; **Nebenknopf**
  `.btn.secondary` weiß mit Graphit-Linie; **Nebenweg** `.link` als Textlink
  („Trotzdem zählen“). Ein Hauptknopf pro Bildschirm.
- **Eingabe**: Zahl auf einer Linie wie eine Waagenanzeige (kein Kasten), Einheit
  daneben, Fokus = blaue Linie. `inputmode="decimal"` bekommt automatisch Mono 40.
- **Ergebnis** `.result`: Körner und TKG als zwei Karten, Aussaatmenge `.card.main`
  mit 2 px Graphit-Rahmen und 88 px Zahl, darunter `.scale` und `.formula`.
- **Messbalken** `.scale`: Achse ±12 % um den Wert, Band = Spanne, Strich = Wert,
  Ticks alle 10 kg/ha. Nur zeigen, wenn eine Spanne angezeigt werden darf (§8).
- **Verlauf** `.item`: Zeilen mit Haarlinie statt Kästen; rechts TKG und kg/ha in Mono.

## 5. Foto, Marken, Prüfstellen

- Foto auf `--photo-bg`, Radius 8 px. Marken im SVG über dem Bild.
- **Markengröße folgt dem Zoom** (`TKMotion.markSize(k)`, k = Bild-px je Bildschirm-px):
  Punkt-Radius = 5,5/k, begrenzt auf 2–10 px; Ring = 2/k, begrenzt auf 0,8–3 px.
  Auf dem ganzen Foto bleibt so das Korn sichtbar; in der Prüfstelle ist ein Punkt
  ≥ 20 px groß (UX.md §4). Umsetzung: `transform="translate(x y) scale(k)"` je Marke,
  Radien in Bildschirm-px.
- **Treffer beim Tippen**: nächster Punkt innerhalb 24 Bildschirm-px (`--mk-hit`)
  wird entfernt, sonst wird ein Korn gesetzt. Tippen nur im Zoom.
- **Prüfstelle**: Graphit-Unterlage 4,5 px (`.ck-back`), darauf orange Striche 2,5 px
  (`.ck-box`), Nummernknopf (Orange, Graphit-Ziffer, weißer Rand) oben links. Die
  Unterlage trägt den Kontrast nach WCAG 1.4.11: Graphit hat 6:1 auf rosa gebeiztem
  Korn und 14:1 auf dem Blatt; Orange allein hat 2,7:1 auf Weiß und 1,1:1 auf dem Korn
  (Befund aus Astras Review zu PR #18). Ein dunkleres Orange löst das nicht und rückt
  nur näher ans Blau. Aktive Stelle: Atmen stoppt, andere Stellen auf 20 %
  Deckkraft. Bestätigt: Rahmen durchgezogen blau, Knopf blau.
- **Prüfkarte** unter dem Foto: „Stelle 2 von 6“ (Label), Kommentar als Frage,
  „Körner in diesem Ausschnitt 15“ (Mono, live), Hinweis zum Tippen, Hauptknopf
  „Stimmt so“, darunter Rückgängig | Später.
- Optional aus Mockup B: kleine **Lagekarte** (84 px) unten rechts im Foto, zeigt
  den Ausschnitt im Gesamtbild. Hilft beim Wechsel zwischen Stellen.

## 6. Bewegung

Bewegung erklärt, was die Zählung tut. Vier Momente, sonst nichts.

| Moment | Was passiert | Dauer / Kurve | Umsetzung |
|---|---|---|---|
| 1 Zählung sichtbar | Marken erscheinen Ausschnitt für Ausschnitt, Zahl und dünne Fortschrittslinie laufen mit | ≈ 2,8 s gesamt, `--e-out` | `TKMotion.revealMarks()` |
| 2 Marke erscheint | einblenden, kein Skalieren | 240 ms | `.mk.reveal.in` |
| 3 Unsichere Stelle | orange Füllung atmet 0 → 20 % → 0; Rahmen bleibt voll deckend, keine Größenänderung; endet mit `.done` | 2,8 s Zyklus, `--e-io` | `.ck-box` |
| 4 Ergebnis setzt sich | Zahl steht sofort als gemessener Wert da; danach zeichnet sich der Messbalken von der Mitte auf | 700 ms | `.scale` |
| Kamerafahrt | viewBox fährt auf die Prüfstelle und zurück, Marken ziehen ihre Größe nach | 460 ms, `--e-io` | `TKMotion.zoomViewBox()` |
| Bildschirmwechsel | 6 px hoch + einblenden | 280 ms | `main.enter` |

**Gemessene Zahlen zählen nicht hoch.** Körnerzahl, TKG und kg/ha stehen sofort
als Endwert da. Eine laufende Zahl sieht aus wie Zählfortschritt, den es nicht gibt
(Astra, PR #18). `TKMotion.countTo()` bleibt nur für reine Vorführungen.

**Ehrlichkeit:** Die Pipeline meldet heute keine Ausschnitte einzeln. Während
gezählt wird, also nur `.progress.indet` und „Wird gezählt“, keinen erfundenen
Fortschritt. Moment 1 läuft **einmal, wenn das Ergebnis da ist**, als Vorführung
der fertigen Marken; die Zahl „411 Körner gefunden“ steht dabei von Anfang an. Kommt später ein Callback
pro Ausschnitt, übergibt man die echten Ausschnitte an `revealMarks({ tiles })`.

**Reduzierte Bewegung** (`prefers-reduced-motion: reduce`): `tausendkorn.css`
schaltet alle Animationen auf den Endzustand, Prüfrahmen werden statt Atmen 4 px
dick; `TKMotion` springt sofort ans Ende. Nichts davon darf Information tragen,
die ohne Bewegung fehlt.

## 7. Wortlaut im System

Labels in Mono-Versalien sind kurz und sachlich: „GEWICHT DIESER KÖRNER“,
„AUSSAATMENGE“, „STELLE 2 VON 6“. Sätze bleiben Sie-Form und Wortliste aus UX.md §4.
Einheiten immer ausgeschrieben neben der Zahl (g, %, kg/ha, keimf. K./m²).

## 8. Offen

- **± Spanne:** `UX.md` §3 sagt „keine ± Zahl in der App“. Die Mockups zeigen eine
  Spanne nur bei ungeprüften Stellen, Breite als Platzhalter. `.scale` erst nutzen,
  wenn die UX-Session entschieden hat und eine gemessene Spanne aus Holdout vorliegt.
- **Schriften offline** in `app/static/fonts/` ablegen (§3).
- **Handschuh- und Sonnentest** steht für alle Größen noch aus.
