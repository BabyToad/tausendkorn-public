"""Overlays der finalen Läufe (Argon v1.0.2) neu erzeugen. Braucht data/corn1000.

Holdout (Punkt-Labels vorhanden): grün = Treffer, rot = Fehlalarm, gelb = übersehen.
Test count_1000 (keine Punkt-Labels): blaue Punkte = gesetzte Marken.

    uv run python results/make_overlays.py                 # alle
    uv run python results/make_overlays.py S02-000 S05     # nur passende Dateinamen
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import ImageDraw

from tausendkorn.eval import load_image, load_split
from tausendkorn.overlay import draw

HERE = Path(__file__).resolve().parent
RUNS = HERE / "argon_v1.0.2"
OUT = HERE / "overlays"


def draw_pred_only(row: dict, res: dict, width: int = 1600):
    image = load_image(row["path"])
    d = ImageDraw.Draw(image)
    s = max(image.size) / 1000
    for p in res["points"]:
        d.ellipse([p[0] - 4 * s, p[1] - 4 * s, p[0] + 4 * s, p[1] + 4 * s], fill=(0, 95, 184), outline=(255, 255, 255))
    title = f"{row['file_name']}  Label {row['count']}  | Argon v1.0.2: {res['count']} Marken"
    d.rectangle([0, 0, image.size[0], 34 * s], fill=(0, 0, 0))
    d.text((10 * s, 6 * s), title, fill=(255, 255, 255), font_size=int(20 * s))
    if image.size[0] > width:
        image = image.resize((width, int(image.size[1] * width / image.size[0])))
    return image


def main() -> None:
    wanted = sys.argv[1:]
    OUT.mkdir(exist_ok=True)
    for split in ("holdout", "test"):
        rows = {r["file_name"]: r for r in load_split("test" if split == "test" else "train")}
        for f in sorted((RUNS / split).glob("*.jpg.json")):
            if wanted and not any(w in f.name for w in wanted):
                continue
            res = json.loads(f.read_text(encoding="utf-8"))
            row = rows[res["file_name"]]
            if row.get("kernel_points"):
                res = {**res, "model": "Argon", "mode": "v1.0.2", "grid": "adaptiv", "pred": res["count"], "tiles": []}
                image = draw(row, res, width=1600)
            else:
                image = draw_pred_only(row, res)
            out = OUT / f"{split}__{f.name.removesuffix('.json')}"
            image.save(out, quality=82)
            print(out.relative_to(HERE))


if __name__ == "__main__":
    main()
