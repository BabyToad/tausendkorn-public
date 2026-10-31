"""Evaluate a kernel counter on a corn1000 split.

A counter is any callable ``count(image: PIL.Image.Image) -> int | dict`` given as
``module:function``. A dict must contain ``count`` and may contain ``points``
(list of ``[x, y]`` in upright image pixels) for overlays.

    uv run python -m tausendkorn.eval my_counter:count --split test --name gemini-tiles
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageOps

DATA = Path(__file__).resolve().parents[2] / "data" / "corn1000" / "data"
RUNS = Path(__file__).resolve().parents[2] / "runs"


def load_split(split: str) -> list[dict]:
    rows = []
    with open(DATA / split / "metadata.jsonl", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            row["path"] = DATA / split / row["file_name"]
            rows.append(row)
    return rows


def load_image(path: Path) -> Image.Image:
    # Phones store most photos sideways; labels refer to the upright image.
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def resolve(spec: str):
    module, _, func = spec.partition(":")
    return getattr(importlib.import_module(module), func or "count")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("counter", help="module:function")
    ap.add_argument("--split", default="test")
    ap.add_argument("--name", required=True, help="run name, used for runs/<name>.csv")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--species")
    ap.add_argument("--session", help="e.g. S04; test split is all 1000s, so also check train sessions")
    args = ap.parse_args()

    rows = load_split(args.split)
    if args.species:
        rows = [r for r in rows if r["species"] == args.species]
    if args.session:
        rows = [r for r in rows if r["session"] == args.session]
    rows = rows[: args.limit]

    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"{args.name}.csv"
    done = {}
    if out.exists():
        with open(out, encoding="utf-8") as f:
            done = {r["file_name"]: r for r in csv.DictReader(f)}

    counter = resolve(args.counter)
    fields = ["file_name", "species", "camera", "count", "pred", "error", "seconds"]
    with open(out, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not done:
            writer.writeheader()
        for i, row in enumerate(rows, 1):
            if row["file_name"] in done:
                continue
            t0 = time.perf_counter()
            result = counter(load_image(row["path"]))
            pred = result["count"] if isinstance(result, dict) else int(result)
            rec = {
                "file_name": row["file_name"],
                "species": row["species"],
                "camera": row["camera"],
                "count": row["count"],
                "pred": pred,
                "error": pred - row["count"],
                "seconds": round(time.perf_counter() - t0, 2),
            }
            writer.writerow(rec)
            f.flush()
            done[row["file_name"]] = rec
            print(f"[{i}/{len(rows)}] {row['file_name']}: {pred} vs {row['count']}")

    report([done[r["file_name"]] for r in rows if r["file_name"] in done])


def report(recs: list[dict]) -> None:
    errs = [int(r["error"]) for r in recs]
    rel = [abs(int(r["error"])) / int(r["count"]) * 100 for r in recs]
    print(f"\nn={len(errs)}  MAE={statistics.mean(map(abs, errs)):.2f}  "
          f"MAPE={statistics.mean(rel):.2f}%  bias={statistics.mean(errs):+.2f}  "
          f"max|err|={max(map(abs, errs))}")
    by = defaultdict(list)
    for r in recs:
        by[r["species"]].append(int(r["error"]))
    for sp, e in sorted(by.items()):
        print(f"  {sp:10s} n={len(e):3d}  MAE={statistics.mean(map(abs, e)):.2f}  "
              f"bias={statistics.mean(e):+.2f}")


if __name__ == "__main__":
    main()
