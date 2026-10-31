"""Cut an image into overlapping tiles with a red 'core' box for VLM counting.

A kernel belongs to the tile whose core contains its centre, so summing per-tile
counts over the grid counts every kernel exactly once.

    uv run python -m tausendkorn.tiles <file_name> --split train --grid 4 --out runs/tiles/x
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import ImageDraw

from tausendkorn.eval import load_image, load_split


def make_tiles(image, grid: int, margin: float = 0.12):
    W, H = image.size
    tw, th = W / grid, H / grid
    mx, my = int(tw * margin), int(th * margin)
    for r in range(grid):
        for c in range(grid):
            core = (int(c * tw), int(r * th), int((c + 1) * tw), int((r + 1) * th))
            crop = (max(core[0] - mx, 0), max(core[1] - my, 0),
                    min(core[2] + mx, W), min(core[3] + my, H))
            tile = image.crop(crop)
            box = (core[0] - crop[0], core[1] - crop[1], core[2] - crop[0], core[3] - crop[1])
            ImageDraw.Draw(tile).rectangle(box, outline=(255, 0, 0), width=4)
            yield r, c, core, crop, tile


def in_core(points, core) -> int:
    return sum(core[0] <= x < core[2] and core[1] <= y < core[3] for x, y in points or [])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file_name")
    ap.add_argument("--split", default="train")
    ap.add_argument("--grid", type=int, default=4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    row = next(r for r in load_split(args.split) if r["file_name"] == args.file_name)
    image = load_image(row["path"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for r, c, core, crop, tile in make_tiles(image, args.grid):
        name = f"tile_{r:02d}{c:02d}.jpg"
        tile.save(out / name, quality=92)
        manifest.append({"tile": name, "core": core, "crop": crop,
                         "truth": in_core(row["kernel_points"], core),
                         "broken": in_core(row["broken_points"], core),
                         "invalid": in_core(row["invalid_points"], core)})
    meta = {"file_name": row["file_name"], "count": row["count"], "species": row["species"],
            "n_points": len(row["kernel_points"] or []), "tiles": manifest}
    (out / "manifest.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: v for k, v in meta.items() if k != "tiles"}),
          "sum truth:", sum(t["truth"] for t in manifest))


if __name__ == "__main__":
    main()
