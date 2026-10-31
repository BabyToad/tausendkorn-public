"""Blob decomposition: geometry counts the obvious single kernels, a VLM counts the rest.

The kernel mask (adaptive.kernel_mask) is split into connected blobs. A blob whose area
is close to one kernel and whose shape is convex is a single kernel and counted as 1.
Everything else (touching clusters, small fragments, chaff, odd shapes) is cropped and
sent to a VLM, where each crop holds only a handful of objects.

    uv run python -m tausendkorn.blobs diagnose --images splits/dev.txt
    uv run python -m tausendkorn.blobs run --images splits/dev.txt --model argon
"""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import ImageDraw

from tausendkorn.adaptive import kernel_mask
from tausendkorn.eval import load_image, load_split

RUNS = Path(__file__).resolve().parents[2] / "runs" / "blobs"
A4_MM2 = 210 * 297
KERNEL_MM2 = 20.0                       # prior; refined per image from single blobs
SINGLE = (0.65, 1.45)                   # area ratio band for a single kernel
SOLIDITY = 0.90                         # area / convex hull area


def decompose(image) -> dict:
    mask, scale, inside = kernel_mask(image)
    # Light husks (barley, oats) leave the bright kernel centre out of the mask: close
    # small gaps, then fill holes so each kernel is one solid region.
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(mask)
    cv2.drawContours(mask, cnts, -1, 1, thickness=cv2.FILLED)
    px_per_mm2 = inside.sum() / A4_MM2
    n, labels, stats, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    prior = KERNEL_MM2 * px_per_mm2
    areas = stats[1:, cv2.CC_STAT_AREA].astype(float)
    band = areas[(areas > 0.5 * prior) & (areas < 1.6 * prior)]
    a1 = float(np.median(band)) if len(band) >= 20 else prior
    blobs = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 0.08 * a1:            # dust and speckle, far below any kernel
            continue
        comp = (labels[y:y + h, x:x + w] == i).astype(np.uint8)
        cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hull = cv2.contourArea(cv2.convexHull(cnts[0])) or 1.0
        ratio, solidity = area / a1, area / hull
        kind = "single" if SINGLE[0] <= ratio <= SINGLE[1] and solidity >= SOLIDITY else "vlm"
        blobs.append({"id": i, "bbox": [int(x), int(y), int(w), int(h)], "area_ratio": round(ratio, 3),
                      "solidity": round(solidity, 3), "kind": kind,
                      "centroid": [float(cents[i][0] * scale), float(cents[i][1] * scale)],
                      "contour": (cnts[0].reshape(-1, 2) + [x, y]).tolist()})
    return {"labels": labels, "scale": scale, "a1": a1, "blobs": blobs}


def diagnose(rows: list[dict]) -> None:
    """How often is a geometry 'single' really one labelled kernel? No API calls."""
    tot = {"single_blobs": 0, "single_ok": 0, "single_0": 0, "single_2plus": 0,
           "vlm_blobs": 0, "vlm_points": 0, "points": 0, "points_unmasked": 0}
    for row in rows:
        d = decompose(load_image(row["path"]))
        lab, s = d["labels"], d["scale"]
        per_blob = {}
        for x, y in row["kernel_points"]:
            xi, yi = int(x / s), int(y / s)
            k = int(lab[min(yi, lab.shape[0] - 1), min(xi, lab.shape[1] - 1)])
            tot["points"] += 1
            if k == 0:
                tot["points_unmasked"] += 1
            per_blob[k] = per_blob.get(k, 0) + 1
        img = {"single_ok": 0, "single_bad": 0}
        for b in d["blobs"]:
            c = per_blob.get(b["id"], 0)
            if b["kind"] == "single":
                tot["single_blobs"] += 1
                tot["single_ok"] += c == 1
                tot["single_0"] += c == 0
                tot["single_2plus"] += c >= 2
                img["single_ok" if c == 1 else "single_bad"] += 1
            else:
                tot["vlm_blobs"] += 1
                tot["vlm_points"] += c
        n_vlm = sum(b["kind"] == "vlm" for b in d["blobs"])
        print(f"{row['file_name']:55s} n={row['count']:4d} singles={img['single_ok'] + img['single_bad']:4d} "
              f"bad={img['single_bad']:2d} vlm_blobs={n_vlm:3d}")
    print("\n" + json.dumps(tot, indent=1))
    print(f"single precision {tot['single_ok'] / max(tot['single_blobs'], 1):.4f}; "
          f"share of points handled by geometry {tot['single_ok'] / tot['points']:.3f}; "
          f"points outside mask {tot['points_unmasked']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["diagnose"])
    ap.add_argument("--images", required=True)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    names = Path(args.images).read_text().split()[: args.limit]
    by_name = {r["file_name"]: r for r in load_split("train")}
    rows = [by_name[n] for n in names]
    if args.cmd == "diagnose":
        diagnose(rows)


if __name__ == "__main__":
    main()
