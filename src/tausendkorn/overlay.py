"""Draw labels and a run's predictions onto the photo.

Green ring = matched kernel, red cross = extra point (false positive),
yellow ring = missed kernel (false negative), blue dot = label only (no run given).
Orange/violet marks show the broken/invalid labels. Thin lines show the tile grid.

    uv run python -m tausendkorn.overlay runs/vlm/points-g8/astra/<image>.json
    uv run python -m tausendkorn.overlay --image S02/S02-014_galaxy-s23_20261002_160345.jpg
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import ImageDraw

from tausendkorn.eval import load_image, load_split
from tausendkorn.match import match

OUT = Path(__file__).resolve().parents[2] / "runs" / "overlays"


def draw(row: dict, result: dict | None, width: int = 2400) -> "Image":
    image = load_image(row["path"])
    d = ImageDraw.Draw(image)
    s = max(image.size) / 1000  # marker scale

    def ring(p, color, r=9):
        d.ellipse([p[0] - r * s, p[1] - r * s, p[0] + r * s, p[1] + r * s], outline=color, width=int(2.5 * s))

    def cross(p, color, r=9):
        d.line([p[0] - r * s, p[1] - r * s, p[0] + r * s, p[1] + r * s], fill=color, width=int(3 * s))
        d.line([p[0] - r * s, p[1] + r * s, p[0] + r * s, p[1] - r * s], fill=color, width=int(3 * s))

    for p in row["broken_points"] or []:
        cross(p, (255, 140, 0), 6)
    for p in row["invalid_points"] or []:
        cross(p, (160, 60, 220), 6)

    title = f"{row['file_name']}  count {row['count']}"
    if result is None:
        for p in row["kernel_points"]:
            d.ellipse([p[0] - 3 * s, p[1] - 3 * s, p[0] + 3 * s, p[1] + 3 * s], fill=(30, 90, 255))
    else:
        for t in result["tiles"]:
            x0, y0, x1, y1 = t["core"]
            d.rectangle([x0, y0, x1, y1], outline=(120, 120, 120), width=max(1, int(s)))
        m = match(result["points"], row["kernel_points"])
        missed = {tuple(p) for p in m["missed"]}
        extra = {tuple(p) for p in m["extra"]}
        for p in row["kernel_points"]:
            if tuple(p) not in missed:
                ring(p, (0, 200, 60))
        for p in missed:
            ring(p, (255, 210, 0), 12)
        for p in extra:
            cross(p, (230, 20, 20))
        title += (f"  | {result['model']} {result['mode']}-g{result['grid']}: pred {result['pred']}"
                  f"  TP {m['tp']}  FP {m['fp']}  FN {m['fn']}")
    d.rectangle([0, 0, image.size[0], 34 * s], fill=(0, 0, 0))
    d.text((10 * s, 6 * s), title, fill=(255, 255, 255), font_size=int(20 * s))
    if image.size[0] > width:
        image = image.resize((width, int(image.size[1] * width / image.size[0])))
    return image


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="*", help="result JSON files from bench_vlm")
    ap.add_argument("--image", action="append", default=[], help="label-only overlay")
    args = ap.parse_args()
    rows = {r["file_name"]: r for r in load_split("train")}
    OUT.mkdir(parents=True, exist_ok=True)
    for name in args.image:
        out = OUT / ("labels__" + name.replace("/", "__"))
        draw(rows[name], None).save(out, quality=88)
        print(out)
    for f in args.results:
        res = json.loads(Path(f).read_text())
        out = OUT / f"{res['model']}__{res['mode']}-g{res['grid']}__{res['file_name'].replace('/', '__')}"
        draw(rows[res["file_name"]], res).save(out, quality=88)
        print(out)


if __name__ == "__main__":
    main()
