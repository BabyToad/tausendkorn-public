# Ergebnis-Archiv

Alle Vorhersagen der finalen Messung, die Vergleichsläufe auf `dev4` und die Bilder dazu.
Zum Durchklicken ohne Python: [`index.html`](index.html) im Browser öffnen.
Zahlen und Einordnung: [`docs/RESULTS.md`](../docs/RESULTS.md), Messregeln:
[`docs/PROTOCOL.md`](../docs/PROTOCOL.md).

| Pfad | Inhalt |
|---|---|
| `index.html` | Galerie: Übersicht, je Art ein Holdout-Overlay, Hartweizen-Befund, Tabellen aller Bilder |
| `argon_v1.0.2/holdout/` | Eingefrorene Pipeline v1.0.2 (Gemini 4 Argon), 30 Holdout-Bilder: ein JSON pro Bild mit `count`, `points` (Pixel im aufrechten Bild), Prüfstellen `check_here`, Kosten, Zeit, TP/FP/FN, Precision/Recall; `manifest.json` = Bildauswahl und Commit |
| `argon_v1.0.2/test/` | Dieselbe Pipeline auf 6 Bildern von `count_1000` (keine Punkt-Labels, nur Zahl) |
| `argon_v1.0.2/*.log` | Konsolen-Logs der beiden Läufe (inkl. Budget-Stopp) |
| `yolo11s/holdout/`, `yolo11s/test/` | YOLO11s eingefroren (Commit `d70b248`), alle 40 Holdout- und 85 Testbilder, `pred` und Punkte |
| `overlays/` | Overlays der Argon-Läufe: **grün** Treffer, **rot (Kreuz)** Fehlalarm, **gelb (Ring)** übersehen; Testbilder: **blau** = gesetzte Marken |
| `befund/` | Bilder zur ungeklärten Hartweizen-Abweichung (`docs/befund/DURUM_COUNT_1000.md`) |
| `dev4/` | Vergleichsläufe auf 4 Dev-Bildern (`dev4.txt`): Kachel-Varianten (`kacheln-*`, ein JSON pro Bild und Modell), agentischer Zähler (`agent-*`, mit Trace); ältere Overlay-JPGs sind zur Größenreduktion nicht enthalten |

Gewichte des eingefrorenen YOLO11s: `models/yolo11s-dev.pt` (SHA-256 wie in `docs/RESULTS.md`); neue Trainingspipeline mit Unschärfe-Augmentierung noch nicht trainiert/gemessen.

## Overlays und Galerie neu erzeugen

Braucht den Datensatz unter `data/corn1000` (siehe Haupt-README):

```bash
uv run python results/make_overlays.py      # alle 36 Overlays
uv run python results/build_index.py        # index.html aus den JSONs
```

Für die `dev4`-Läufe: `uv run python -m tausendkorn.overlay results/dev4/kacheln-points-g8/<modell>/<bild>.json`
(Ausgabe nach `runs/overlays/`).

## Daten

Fotos und Punkt-Labels (`kernel_points`) stammen aus
[`SmartFarmingLab/corn1000`](https://huggingface.co/datasets/SmartFarmingLab/corn1000),
Lizenz **CC BY-NC 4.0**. Die Overlays sind daraus abgeleitet und stehen unter derselben
Lizenz. Der Datensatz selbst (≈ 9 GB) liegt nicht bei.
