# Ergebnisse auf count_1000 (Test-Split)

| Datum/Zeit | Wer | Methode | MAE | max. Fehler | Notiz |
|---|---|---|---|---|---|
| 27.10. 19:05 | Claude (RTX 3070 workstation) | YOLO11s eingefroren, `d70b248` | 25,4 | 108 | Bias −20,1; holdout MAE 4,2. Siehe GPU-Abschnitt |

## VLM-Kachel-Pilot (27.10., Nachmittag)

Bild `S05/S05-017_iphone-8_IMG_6629.jpg` (Hartweizen, 551 Körner, Punkt-Labels),
8×8-Raster mit rotem Kernfeld, 31 belegte + 4 leere Kacheln (0–49 Körner/Kachel).
Prompt: Zahl am Ende, keine Punkte. Wahrheit pro Kachel aus `kernel_points`.

| Modell | Weg | Summe vs. 551 | Kachel-MAE | exakt | Ø Zeit/Kachel |
|---|---|---|---|---|---|
| GPT-6 Astra (medium) | `codex exec -i` | 547 (−4) | 0,40 | siehe results.json | 31 s |
| Claude Opus 5.5 | Subagent | 521 (−30) | 0,91 | 20/35 | – |
| Claude Fable 5.1 | Subagent | 536 (−15) | 1,34 | 18/35 | – |

Fehler sitzen in den dichten Kacheln (33–49 Körner), meist zu niedrig (Auslassungen).
Leere und dünne Kacheln sind bei allen exakt. Nächster Hebel: ≤15 Körner pro Kachel,
Punkt-Ausgaben, Mehrheitsentscheid.

## Punkt-Modus auf dev4 (Stand ~18:30)

`runs/dev4.txt`: je ein Dev-Bild Hafer (440), Gerste (410), Weizen (493), Hartweizen (527).
Fehler = Vorhersage − `count`.

| Modell | Raster | Hafer | Gerste | Weizen | Hartweizen | Notiz |
|---|---|---|---|---|---|---|
| Gemini 4 Argon | 8×8 | −3 | −5 | −18 | −14 | P/R ≈ 0,97–1,0 |
| Gemini 4 Argon | adaptiv | +4 | +13 | +4 | +12 | R 0,97–0,99; FP fast nur Duplikate |
| **Gemini 4 Argon** | **adaptiv + Dedup 0,05 L** | **−8** | **−2** | **−7** | **−4** | nachträglich auf denselben Punkten |
| Gemini 3.8 Flash | 8×8 | +1 | −5 | | | |
| Opus 5.5 (API) | 8×8 | −47 | −24 | −15 | −4 | |
| Sol 6.1 (API) | 8×8 | +27 | +38 | +929 | −2 | ein Halluzinations-Ausreißer |
| Sonnet 5.5 (API) | 8×8 | −49 | −36 | −15 | −17 | |
| Astra (CLI) | 8×8 | +11 | +34 | −25* | −129* | *ausgefallene Kacheln |

Kosten gemessen (eine Kachel, 33 Körner): Argon 1.261 in / 864 out ≈ 1,1 ct (Promo $2/$10),
13 s; Astra API 530 in / 1.867 out ≈ 10 ct, 67 s. Dedup-Schwelle 0,05 Kornlängen auf dev4
gewählt (0,03–0,07 geprüft; ≥0,1 löscht parallel liegenden Hafer).

## Fleck-Zerlegung (Lane Fork 7b4b59, 27.10. ~18:00) — verworfen, ohne API-Kosten

`src/tausendkorn/blobs.py diagnose` auf `splits/dev.txt` (24 Bilder, 12.839 Label-Punkte),
Maske `adaptive.kernel_mask`. Idee: eindeutige Einzelkörner per Geometrie, nur Cluster
ans VLM. Befund: Bei 400–670 Körnern/A4 berühren sich die meisten Körner.

| Maske | Einzelflecken | davon genau 1 Punkt | Anteil Körner per Geometrie | Ø Körner/Cluster |
|---|---|---|---|---|
| kernel_mask (1200 px) | 1.068 | 90,1 % | 7,5 % | 5,7 |
| + Schließen + Löcher füllen | 559 | 94,5 % | 4,1 % | 13,5 |

Nebenbefund für das Raster: Kornmittelpunkte außerhalb von `kernel_mask` — Gerste 27 %,
Hafer 36 %, Weizen/Durum ≈3 % (helle Kornmitte = Loch in der Maske). Weiter als 4 px
von der Maske entfernt sind aber nur 0,0–0,3 %: Für Kachelwahl geht kein Korn verloren;
wer Punkte per Maskenlabel zuordnet, muss Löcher füllen.

### Kompakt-Modus + gezielte Prüfschleife (Pipeline v1, eingefroren)

| Argon adaptiv, dev4 | Hafer | Gerste | Weizen | Hartweizen | $/Bild |
|---|---|---|---|---|---|
| ausführlich + Dedup + Prüfung aller Kacheln | −7 | −1 | −7 | ±0 | ~1,50 |
| **kompakt + Prüfung nur Konfidenz < 0,9** | **−4** | **+1** | **−4** (−1 ggü. 490 Punkt-Labels) | **+2** | **0,31–0,41** |

P/R kompakt: Hafer 0,95/0,95; Gerste 0,99/1,00; Weizen 1,00/1,00; Hartweizen 0,99/0,99.
Geprüfte Kacheln: 0/84, 6/66, 1/88, 2/100 (das Modell meldet selten Konfidenz < 0,9).

## Agentischer Zähler mit Gemini 4 Argon (27.10., Abend)

`src/tausendkorn/agentic.py`: Argon bekommt Zweck und Zählregeln (ISO 520) in Klartext
und Werkzeuge per Function Calling: `view` (vergrößerter Ausschnitt mit nummerierten
eigenen Marken), `mark` (Punkte relativ zu einem View, Duplikat-Sperre bei < 1/3
Kornlänge, `force` übersteuert), `remove`, `overview`, `submit(count,
uncertain_regions, comment)`. Die Marken sind die Vorhersage (1:1-Abgleich wie
`bench_vlm`). Zwei Varianten: *Regionen* (adaptive Quadtree-Kerne als Vorschlag,
150 Calls/$3) und *frei* (keine Regionen, selbst gewählte ~700-px-Views, 15 bzw. 60 Calls).
Nur `runs/dev4.txt`, je ein Lauf, Ergebnisse und Overlays in `runs/agentic/<tag>/`.
Preis $2/$10 pro 1M Token aus `usageMetadata`. Kachel-Kosten ≈ 1,1 ct/Kachel.

Fehler = Marken − `count` (TP/FP/FN gegen `kernel_points`):

| Methode | Hafer S02 (440) | Gerste S03 (410) | Weizen S04 (493) | Durum S05 (527) | $/Bild | Zeit/Bild |
|---|---|---|---|---|---|---|
| Kacheln g8 | −3 (P .97 R .96) | −5 (.98/.97) | −18 (1.0/.97) | −14 (.99/.97) | ~0,70 | ~11 min seriell |
| Kacheln g0 adaptiv | +4 (.95/.97) | +13 (.96/.99) | +4 (.98/.99) | +12 (.97/.99) | 0,73–1,10 | ~15 min seriell |
| Agent frei, 15 Calls | −53 (.87/.77) | −22 (.99/.94) | −5 (1.0/1.0) | +2 (.99/.99) | 0,15–0,26 | 2–3,5 min |
| **Agent frei, 60 Calls** | **+16** (.93/.97) | **+1** (.96/.97) | **−3** (.996/.996) | **±0** (.994/.994) | 0,42–0,94 | 4–6 min |
| Agent Regionen, 150 Calls | −41 (.88/.80), Abbruch nach 37 Calls | **−1** (.99/.99) | – | – | 0,30 / 1,17 | 3 / 8 min |

Selbst angegebene Zahl (`submit.count`) weicht teils von den Marken ab: bei knappem
Budget rechnet der Agent im letzten Prüf-View gesehene, nicht mehr markierte Körner
hinzu (frei15: Hafer 402, Gerste 392, Weizen 491, Durum 535). Das ist mal besser, mal
schlechter als die Marken, also keine verlässliche Korrektur.

Was der Agent selbst sagt (Zitate aus `comment`):

- Weizen S04, frei60: „Confidence is very high (>99.5%). A few clearly broken kernel
  fragments […], an empty pale chaff/glume with awn […] and a stem piece […] were
  excluded per ISO 520 rules, while thin/shrivelled full-length kernels […] were
  included." Er nennt konkrete Koordinaten für Bruch und Spreu; Ergebnis −3, 2 FP / 2 FN.
- Durum S05, frei60: schließt mehrere Hüllspelzen aus und schlägt vor, Marken knapp
  außerhalb des Views mitzuzeichnen, weil Randkörner sonst „unmarked" aussehen.
- Hafer, mehrfach: Die Duplikat-Sperre (1/3 Kornlänge, ~25 px) ist für schmale,
  nebeneinander liegende Haferkörner zu groß, „requiring force=true"; umgekehrt rutschen
  Markierungen an beiden Enden eines langen Korns über View-Nähte durch. Vorschlag:
  elliptischer Radius entlang der Kornachse. Genau dort liegen die Haferfehler (+16, −41).
- Gerste S03, Regionen: „All 66 suggested regions were systematically inspected and
  marked in batches, followed by a 4-quadrant medium-zoom verification" → −1, P/R .99.
- Mehrere Läufe: Budget pro *Tool-Call* statt pro Runde bremst; der Agent würde größere
  Views und Batch-Marking bevorzugen.
- Selbstvertrauen ist **nicht** kalibriert: Hafer-Regionen meldet „High confidence in the
  count of 399" bei −41 und hört nach 37 von 150 Calls auf.

Ein Harness-Bug in der ersten Runde (Bildverlauf auf 4 Bilder gekürzt, obwohl der Agent
6 Views pro Runde öffnete → markierte 2 Views blind) ist behoben; die Läufe davor liegen
in `runs/agentic/buggy_prune/` und zählen nicht.

**Fazit:** Der Agent ist auf diesen 4 Dev-Bildern mit 60 Calls genauer als beide
Kachel-Pipelines (|Fehler| Summe 20 vs. 40 bei g0/g8, Weizen/Durum fast fehlerfrei) und
billiger und schneller (1 Gespräch statt 64–100 Kacheln). Er beurteilt Bruch/Spreu
explizit und liefert brauchbare Hinweise zu Werkzeugen und Foto. Schwächen: hohe
Lauf-zu-Lauf-Varianz (Hafer +16 / −41 / −53 je nach Variante), unkalibriertes
Selbstvertrauen, vorzeitiges `submit`. Nächste Schritte auf Dev: ovale Duplikat-Sperre,
Budget pro Runde, `submit` erst nach `overview` erlauben, 2–3 Läufe pro Bild mischen
(Median der Marken oder Punktkonsens) und alle 24 Dev-Bilder statt 4, bevor das in die
eingefrorene Pipeline geht.

## Spezialmodelle auf dem GPU-Rechner (RTX 3070 workstation, RTX 3070, 27.10. Abend)

Nur `splits/dev.txt` (24 Bilder). Code in `src/tausendkorn/gpu/`, Punkt-JSONs pro Bild in
`runs/gpu/<lauf>/`. Fehler = Vorhersage − `count`; P/R aus `tausendkorn.match`.

| Methode | Summe | MAE | Bias | max. | ±1 / ±5 | Precision | Recall | s/Bild |
|---|---|---|---|---|---|---|---|---|
| **YOLO11s, Kacheln 1024, conf 0,4** | **+19** | **3,0** | **+0,8** | **14** | **9 / 21** | **0,989** | **0,995** | **0,4** |
| YOLO26s, gleiche Daten, best.pt, conf 0,35 | −9 | 3,3 | −0,4 | 15 | 8 / 19 | 0,991 | 0,995 | 0,4 |
| GeCo2, 3×3 Kacheln, 3 Exemplare | −4495 | 187 | −187 | 421 | 0 / 0 | 0,978 | 0,641 | 5,2 |
| SAM3 | – | – | – | – | – | – | – | – |
| CountGD++ | – | – | – | – | – | – | – | – |

YOLO11s pro Art (MAE / Bias): Gerste 2,8 / +1,8 · Hartweizen 2,7 / +2,7 · Hafer 2,2 / +1,5 ·
Weizen 4,5 / −2,8.

- **YOLO11s** (`gpu/yolo.py`): trainiert 40 Epochen auf `train` (49 Fotos → 847 Kacheln
  1024 px, Schritt 768), `dev` als Validierung. Punkt-Labels → Boxen: einzelne Körner
  per Schwellwertmaske, Körner in Clustern mit der Median-Box des Bildes. Klassen
  kernel/broken/invalid, gezählt wird nur `kernel`, Kernfeld-Ownership zwischen den
  Kacheln. Wahl auf dev: `last.pt` statt `best.pt`, conf 0,4 (0,35–0,45 ist ein Plateau,
  MAE 3,0–3,5; conf 0,25 überzählt um +90). Gewichte liegen nur auf RTX 3070 workstation unter
  `runs/yolo/yolo11s/weights/last.pt` (gitignored).
- **GeCo2** (`gpu/geco2.py`): Exemplare = die drei isoliertesten Label-Punkte mit
  Otsu-Box (im Produkt tippt der Nutzer drei Körner an); die Exemplar-Ausschnitte
  werden neben jede Kachel geklebt. Hohe Precision, verfehlt aber aneinanderliegende
  Körner systematisch: Die Dichtekarte hat dort keine getrennten Maxima. Raster 1–7,
  NMS 0,5–0,95, Score-Schwelle und Peak-Schwelle ändern daran nichts. Deformable-
  Attention ohne CUDA-Toolkit über die PyTorch-Referenz (lokaler Patch im Klon).
- **SAM3**: übersprungen (Gewichte gated, kein HF-Login auf RTX 3070 workstation; Jonas' Entscheidung).
- **CountGD++**: nicht versucht; braucht Detectron2 und GroundingDINO-Ops, kompiliert mit
  CUDA-Toolkit, das auf RTX 3070 workstation fehlt.

### Eingefroren für holdout und count_1000

YOLO26s ist auf dev nicht besser (MAE 3,3–4,7 je nach conf), daher eingefroren:
YOLO11s `last.pt`, conf 0,4, Kacheln 1024/768, Code-Stand dieses Commits.
Gewichte auf RTX 3070 workstation: `runs/frozen/yolo11s-dev.pt`,
SHA-256 `7c823bf82e1ca24332e77eb08cc282a28d48bfac594bb0c3d8a0070bf5418cbc`.

### Einmaliger Lauf holdout und count_1000 (Commit `d70b248`, nicht nachjustiert)

| Split | n | Summe | MAE | Bias | max. | exakt / ±1 / ±5 | P / R |
|---|---|---|---|---|---|---|---|
| holdout | 40 | +80 | 4,2 | +2,0 | 21 | 5 / 18 / 32 | 0,976 / 0,987 |
| count_1000 | 85 | −1710 | 25,4 | −20,1 | 108 | 5 / 15 / 29 | – |

holdout pro Art (MAE / Bias): Hafer 0,9 / −0,1 · Weizen 2,5 / +1,5 · Gerste 6,3 / +6,1 ·
Hartweizen 7,1 / +0,5.

count_1000 pro Art und Kamera (MAE / Bias):

| Art | Galaxy S23 | iPhone 8 |
|---|---|---|
| Gerste | 20,7 / −19,3 (9) | 3,5 / +2,5 (11) |
| Hartweizen | 63,8 / −63,8 (10) | 37,6 / −37,6 (7) |
| Hafer | 43,2 / −43,2 (9) | 7,5 / +7,5 (4) |
| Roggen (nie trainiert) | 38,7 / −38,7 (9) | 7,7 / −7,2 (12) |
| Weizen | 13,0 / +8,3 (9) | 11,2 / +11,2 (5) |

Diagnose (nur angesehen, nichts verändert): Der Testtag zeigt gebeiztes, rosa Saatgut,
schräge Aufnahmen mit Markierung und 1000 Körner pro Blatt, also deutlich dichter als
train/dev. Auf dem schlechtesten Bild (S23, Gerste, −108) fehlen Körner vor allem im
hinteren, perspektivisch kleinen und dichten Bereich. Die Unterzählung ist ein
Domänenwechsel (Farbe, Perspektive, Dichte), kein Kachelfehler; iPhone-8-Bilder liegen
außer Hartweizen nahe am holdout. Nächster Hebel wäre Training mit Farb-/Perspektiv-
Augmentierung oder Kacheln nach Kornmaßstab statt fester 1024 px, das geht aber
wieder über dev (PROTOCOL Regel 2).

## Finale Messung Pipeline v1.0.2 (27.10., 18:50–19:20, eingefroren, Commit d2ced75)

Einmalig nach `docs/PROTOCOL.md`; Budget-Stopps begrenzen die Abdeckung (Kosten real).

| Satz | Bilder | MAE | rel. Fehler | Bias | max. | Kosten |
|---|---|---|---|---|---|---|
| Holdout (Within-Session, 170–482 Körner) | 30/40 (Hafer, Gerste, Weizen; **Hartweizen fehlt**, Budget-Stopp) | 5,9 | 1,85 % | +2,5 | 14 | 9,43 $ |
| Test `count_1000` (anderer Tag, Roggen neu) | 6/10, alle 5 Arten | 15,8 | 1,58 % | −5,2 | 58 | 3,94 $ |

Pro Art Holdout: Gerste +6, +6, +14, +7, +6, +11, +8, +10, +5, +14 (zu hoch) · Hafer +5, +5, −1,
+2, +5, +3, +4, +4, +3, +8 · Weizen −1, 0, −9, −8, −5, −4, −6, −6, −5, −7 (zu niedrig).
Test: Gerste +11, +11 · Hartweizen **−58** · Hafer +10 · **Roggen −3** · Weizen −2.

Befunde: Fehler sind je Art gerichtet (Gerste zu hoch, Weizen zu niedrig). Die Hartweizen-Abweichung ist ungeklärt: Argon zählt 942, YOLO auf demselben Foto 948; über 17 Fotos
zählt YOLO 911–976. Gemeinsame Unterzählung verdeckter Körner und eine Abweichung der Probe vom Label
sind nicht ausgeschlossen. Ein fehlender 50er-Becher ist nur eine Hypothese. Gewertet wird unverändert
gegen 1000; Test-MAE 15,8 bei n=6.
Auf diesem Bild meldete Argon kaum Unsicherheit (3/166 Kacheln < 0,9 Konfidenz), die
Prüfschleife griff dort also nicht. Vergleich YOLO11s (RTX 3070 workstation, trainiert auf `train`): Holdout MAE 4,2, aber Test
MAE 25,4 / Bias −20 / max. 108 — besser innerhalb der Sessions, schlechter auf neuem Tag.

## Günstigeres Modell und v1.1 Bruch/Fremd (27.10., ~20:00–21:00, nur dev)

Budget 5 $ (gebraucht 1,40 $: A 0,49, B 0,91). Kosten aus `cost_usd` bzw. Token × Listenpreis.
Lite-Preise und 3.6 Flash auf ai.google.dev/gemini-api/docs/pricing geprüft (stimmen mit
`PRICES`); 3.5 Flash steht dort nicht mehr, 2.5 Flash-Lite antwortet 404.

### A) Günstigeres Modell als Argon: keins ist Pareto-besser

Stufe 1, 4 dichte Kacheln aus `runs/pilot/S05-017-g8`, Prompt `compact`. Wahrheit im Kern
37/21/33/40 (Rohzahlen enthalten auch Randkörner, Argon trifft trotzdem fast genau).

| Modell | Körner je Kachel | Σ (131) | $/Kachel | s/Kachel |
|---|---|---|---|---|
| **Argon (Standard)** | 37 / 21 / 31 / 40 | **129** | 0,0059 | 6 |
| Argon thinking low | 37 / 22 / 31 / 40 | 130 | 0,0060 (gleiche Token) | 6 |
| 3.5 Flash-Lite | 52 / 24 / 42 / 51 | 169 | 0,0015 | 2 |
| 3.1 Flash-Lite | 38 / 42 / 22 / 33 | 135 (je Kachel ±20) | 0,0008 | 2 |
| 3.1 Flash-Lite thinking high | 37 / 23 / 41 / 59 | 160 | 0,015 | 23 |
| 3.5 Flash-Lite thinking high | 32 / 21 / 37 / 47 | 137 | 0,019 | 18 |
| 3.5 Flash low | 40 / 25 / 29 / 44 | 138 | 0,0050 (Preis ungeprüft) | 3 |
| 3.6 Flash low | 41 / 25 / 34 / 42 | 142 | 0,0033 | 4 |
| 2.5 Flash-Lite | 404, Modell weg | – | – | – |

Stufe 2, nur der einzige billigere Kandidat mit plausiblen Zahlen (3.6 Flash low) auf
dem Hafer-Dev-Bild S02-014 (440), `--mode compact --grid 0`:

| Variante (dev4) | Hafer | Gerste | Weizen | Hartweizen | $/Bild |
|---|---|---|---|---|---|
| **Argon kompakt + Prüfung (v1.0.2)** | −4 | +1 | −4 | +2 | 0,31–0,41 |
| Argon kompakt ohne Prüfung | −4 | +3 | −4 | +1 | 0,27–0,39 |
| 3.6 Flash low kompakt | **+144** (P 0,66, R 0,87) | | | | 0,21 |
| 3.1 Flash-Lite kompakt | **+762** (P 0,20, R 0,55) | | | | 0,05 |

3.1 Flash-Lite schwankt schon in Stufe 1 stark (zweiter Lauf derselben Kacheln:
33/16/29/34). Als Hybrid mit Argon-Prüfung taugt es nicht: nur 4 von 91 Kacheln melden
Konfidenz < 0,9, die falschen Kacheln würden nicht geprüft. Stufe 3 entfällt. Billiger geht nur mit deutlich schlechterer Zählung; Argon bleibt.
Argon zahlt ~1.270 Eingabe- und ~340 Ausgabe-Token je Kachel, Denken lässt sich nicht
weiter drücken (`minimal` → 400). Hebel für Kosten wären weniger/größere Kacheln, das ist
ein eigener Dev-Versuch.

### B) v1.1 Bruch und Fremdbesatz (`--mode classes`, Argon)

Ein Aufruf je Kachel liefert `KERNELS`, `BROKEN`, `FOREIGN` (mit Typ). Parser so streng wie
v1.0.2: alle drei Listen Pflicht, Prüfung wie `valid_points`, sonst Retry. Bruch/Fremd
zählt nur im Kachelkern, Dedup 0,05 L, Abgleich mit `broken_points`/`invalid_points` im
Radius 0,6 × Kornabstand. Die zwei Dev-Bilder mit den meisten Labels:

| Bild | Körner kompakt → classes | P / R Körner | Bruch tp/fp/fn (Labels) | Fremd tp/fp/fn (Labels) | $/Bild |
|---|---|---|---|---|---|
| Hartweizen S05-014 (527) | +1 → **±0** | 0,994 / 0,994 | 1 / 4 / 0 (1) | 3 / 4 / 5 (8) | 0,39 → 0,50 |
| Weizen S04-014 (493) | −4 → **−6** | 1,000 / 0,994 | 2 / 4 / 0 (2) | 1 / 3 / 3 (4) | 0,35 → 0,42 |

- **Kornzahl:** nicht systematisch schlechter (+1→0, −4→−6), bei n=2 nicht unterscheidbar.
  Kosten +20–27 % (mehr Ausgabe-Token).
- **Bruch:** Recall 3/3, Precision 3/11. **Fremd:** Recall 4/12, Precision 4/11.
- **Labels sind dünn** (1–8 je Bild, 15 insgesamt), die Zahlen sind daher grob.
- Ansicht der Ausschnitte (`classes-g0`-Punkte): Ein Teil der Fremd-„FP/FN“ ist dasselbe
  Objekt (Granne, Spreu), nur am anderen Ende markiert. Der Kornabstand-Radius ist für
  lange Objekte zu eng. Ein Teil ist Klassenverwechslung (Bruchstück als Fremd gelabelt
  und umgekehrt). Echte Fehler: Mehrere Bruch-FP sind ganze, schräg liegende Weizenkörner.
- **Fazit:** Fremdbesatz/Bruch als *Hinweis* („ca. n Bruchstücke, Spreu gesehen“) auf zwei
  Dev-Bildern vielversprechend; ob die Kornzahl leidet, ist damit nicht belegt. Als
  Messwert noch nicht. Nächster Dev-Schritt: Abgleich
  für Fremd mit Objekt- statt Punktradius, 3–4 weitere gelabelte Dev-Bilder, Bruch-Regel im
  Prompt schärfen („ganzes Korn auch schräg/kurz von oben gesehen ist KERNEL“).

## Live-Tests aus der App (27.10. abends, Einzeltests, keine Messreihe)

| Test | Weg | Ergebnis | Zeit | Kosten |
|---|---|---|---|---|
| Dev-Foto S04-014 (Weizen, 493) | PC-Upload, echter Modus | 488 (−5, −1,0 %), 0 Prüfstellen | 47 s | 0,39 $ |
| Eigenes Foto, Wintergerste (Team) | iPad-Kamera über Handy-Hotspot → Laptop-Server | 233 gezählt, laut Sichtprüfung 2 Körner doppelt markiert (≈ 231, +0,9 %), 0 Prüfstellen | 54 s | 0,36 $ |

Beide Läufe liefen ohne Fehler durch (alle Kacheln beantwortet). Die zwei Doppelpunkte sind der bekannte
Fehlertyp in engen Gruppen; die Prüfschleife hat sie nicht gemeldet (Konfidenz ≥ 0,9) — das passt zur
App-Grenze „Prüfstellen bestätigt ≠ richtige Zahl“. Netz: Uni-WLAN blockiert Geräte untereinander,
Handy-Hotspot funktioniert (Windows-Netzwerkprofil „Privat“ nötig).

### Korrektur der Diagnose (Audits Fable und Astra, 27.10. abends)

Unabhängige Audits: `docs/AUDIT_FABLE.md`, `docs/AUDIT_ASTRA.md`. Die Unterzählung auf
count_1000 kommt vor allem von **Unschärfe**, nicht von Farbe (rosa Gerste und Marker gibt
es schon im Training). Gleiche Anordnung, gleiche S23, 5 s auseinander: von oben +1, schräg
−108; hinten liegt außerhalb der Schärfentiefe. Auf dev mit dem eingefrorenen Modell
nachgestellt (Fable): Gauß-Unschärfe σ=3 px → MAE 22,4, Bias −21; Perspektive/Maßstab
allein MAE ≤ 5,4. YOLO verliert unscharfe Körner nicht, sondern Konfidenz.
Weitere Befunde: count_1000 hat effektiv n = 5 Anordnungen (Art/Anordnung/Licht
konfundiert); Splits nach Dichte sortiert (holdout am leichtesten); dev war zugleich
Validierung beim Training; Punkt-Labels in train summieren sich 341 unter `count`.

Gewichte des eingefrorenen Modells wurden im Entwicklungsarchiv gesichert; sie werden im öffentlichen Snapshot nicht verteilt: `models/yolo11s-dev.pt`
(SHA-256 wie oben). Damals geplanter und anschließend ausgeführter Schritt (nach der Abgabe): `yolo prep-blur` und
`yolo train --blur` (Unschärfe-/Defokus-/Bewegungs- und Schärfeverlauf-Augmentierung),
Bewertung nur auf dev und geblurrtem dev; count_1000 ist verbraucht.

### Nachtraining mit Unschärfe-Augmentierung (nach der Abgabe, 27.10. ~22:20)

`yolo prep-blur` (60 % der Train-Kacheln zusätzlich als Gauß-/Defokus-/Bewegungs-/
Schärfeverlauf-Kopie, 1386 Kacheln) + `yolo train --blur`, 40 Epochen, YOLO11s, `last.pt`.
Private, nicht mitgelieferte Gewichte: `models/yolo11s-blur.pt` (SHA-256 `7b3d0d5882b729fe0f81dea9366a42ede19260900a4d4e360cf06c0874e46f22`).
Bewertung nur auf dev (24) mit `gpu/perturb.py` (Labels mittransformiert), conf 0,4:

| dev-Variante | eingefroren MAE / Bias | Blur-Modell MAE / Bias |
|---|---|---|
| unverändert | 3,0 / +0,8 | 4,1 / +1,3 |
| Gauß σ=2 | 10,4 / −8,5 | 3,9 / +0,9 |
| Gauß σ=3 | 22,4 / −20,9 | 2,9 / −0,1 |
| Gauß σ=4 | 48,1 / −46,7 | 4,9 / −2,4 |
| Keystone 0,45 | 5,4 / −1,2 | 4,6 / +1,4 |

conf 0,3 überzählt (+2 bis +7 Bias), conf 0,5 bringt die Unschärfe-Schwäche zurück; 0,4 bleibt.
Vorbehalt: Die Prüf-Unschärfe ist Gauß wie ein Teil der Augmentierung, also teils im
Verteilungsbereich des Trainings; echte Defokusbilder sind die ehrliche Prüfung. Auf
count_1000 nicht gemessen (verbraucht); dafür braucht es neue Fotos.
