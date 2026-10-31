"""GeCo2 exemplar counter on corn1000 (runs on the CUDA machine).

Three example kernels stand in for the three kernels the user taps in the product:
here they are the three most isolated label points, boxed by an Otsu mask around each.
The image is cut into tiles with a halo; the three exemplar crops are pasted in a strip
beside every tile, so each tile sees its prototypes, and a detection counts only if
its centre lies in the tile's core (same ownership rule as tausendkorn.tiles).

Needs the GeCo2 repo with weights in runs/ext/GECO2 (see docs/RESULTS.md):

    uv run --group gpu python -m tausendkorn.gpu.geco2 --images runs/dev4.txt --grid 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from tausendkorn.eval import load_image, load_split
from tausendkorn.match import match, nn_spacing

ROOT = Path(__file__).resolve().parents[3]
GECO2 = ROOT / "runs" / "ext" / "GECO2"
OUT = ROOT / "runs" / "gpu"

_model = None
# Parallel diagonal kernels have strongly overlapping axis-aligned boxes; the demo's
# IoU 0.5 suppresses real neighbours in dense clusters.
NMS = 0.5


def load_model():
    global _model
    if _model is None:
        import torch
        from torch.nn import DataParallel

        sys.path.insert(0, str(GECO2))
        cwd = os.getcwd()
        os.chdir(GECO2)  # hydra resolves its configs relative to the repo
        try:
            from models.counter_infer import build_model
            from utils.arg_parser import get_argparser

            args = get_argparser().parse_args([])
            args.zero_shot = True
            model = DataParallel(build_model(args).cuda())
            state = torch.load(GECO2 / "weights" / "CNTQG_multitrain_ca44.pth", weights_only=True)
            model.load_state_dict(state["model"], strict=False)
            model.eval()
            model.module.return_masks = False
        finally:
            os.chdir(cwd)
        _model = model
    return _model


def exemplar_boxes(image: Image.Image, points, k: int = 3) -> list[tuple[int, int, int, int]]:
    """Boxes around the k most isolated labelled kernels, from an Otsu mask."""
    pts = np.asarray(points, dtype=float)
    spacing = nn_spacing(points)
    d = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    order = np.argsort(-d.min(1))
    gray = np.asarray(image.convert("L"))
    H, W = gray.shape
    boxes = []
    for i in order:
        if len(boxes) == k:
            break
        x, y = pts[i]
        r = int(1.5 * spacing)
        x0, y0, x1, y1 = max(int(x) - r, 0), max(int(y) - r, 0), min(int(x) + r, W), min(int(y) + r, H)
        crop = cv2.GaussianBlur(gray[y0:y1, x0:x1], (5, 5), 0)
        _, mask = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(mask)
        cx, cy = int(x) - x0, int(y) - y0
        comp = lab[cy, cx]
        if comp == 0:
            continue
        bx, by, bw, bh, _ = stats[comp]
        # A box touching the window edge means the blob merged with neighbours.
        if bx == 0 or by == 0 or bx + bw >= crop.shape[1] or by + bh >= crop.shape[0]:
            continue
        boxes.append(tuple(int(v) for v in (x0 + bx, y0 + by, x0 + bx + bw, y0 + by + bh)))
    return boxes


def detect(canvas: Image.Image, boxes, threshold: float, nms: float = NMS):
    """Run GeCo2 on one canvas; returns boxes (canvas pixels) and scores."""
    import torch
    import torchvision.ops as ops
    from torchvision import transforms as T

    model = load_model()
    from utils.data import resize_and_pad

    img = torch.from_numpy(np.asarray(canvas)).cuda().permute(2, 0, 1).float() / 255.0
    img = T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])(img)
    bb = torch.tensor(boxes, dtype=torch.float32).cuda()
    img, bb, scale = resize_and_pad(img, bb, size=1024.0)
    with torch.no_grad():
        outputs, *_ = model(img.unsqueeze(0), bb.unsqueeze(0))
    pred = outputs[0]["pred_boxes"].detach().float().cpu()
    score = outputs[0]["box_v"].detach().float().cpu()
    if pred.dim() == 3:
        pred, score = pred[0], score[0]
    sel = score > score.max() * threshold
    pred, score = pred[sel], score[sel]
    keep = ops.nms(pred, score, nms)
    pred = torch.clamp(pred[keep], 0, 1) / scale * img.shape[-1]
    return pred.numpy(), score[keep].numpy()


def count_image(image: Image.Image, boxes, grid: int, halo: float, threshold: float,
                nms: float = NMS) -> list:
    W, H = image.size
    if grid == 1:
        pred, _ = detect(image, boxes, threshold, nms)
        return [[float(b[0] + b[2]) / 2, float(b[1] + b[3]) / 2] for b in pred]

    # Exemplar strip: the three crops stacked on paper-white, right of the tile.
    pad = 8
    crops = [image.crop(b) for b in boxes]
    sw = max(c.width for c in crops) + 2 * pad
    paper = tuple(int(v) for v in np.median(np.asarray(image).reshape(-1, 3), 0))
    points = []
    tw, th = W / grid, H / grid
    for r in range(grid):
        for c in range(grid):
            core = (c * tw, r * th, (c + 1) * tw, (r + 1) * th)
            hx, hy = halo * tw, halo * th
            crop = (int(max(core[0] - hx, 0)), int(max(core[1] - hy, 0)),
                    int(min(core[2] + hx, W)), int(min(core[3] + hy, H)))
            tile = image.crop(crop)
            sh = max(tile.height, sum(cr.height + pad for cr in crops) + pad)
            canvas = Image.new("RGB", (tile.width + sw, sh), paper)
            canvas.paste(tile, (0, 0))
            ex, y = [], pad
            for cr in crops:
                canvas.paste(cr, (tile.width + pad, y))
                ex.append((tile.width + pad, y, tile.width + pad + cr.width, y + cr.height))
                y += cr.height + pad
            pred, _ = detect(canvas, ex, threshold, nms)
            for b in pred:
                x, y = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                if x >= tile.width or y >= tile.height:
                    continue  # strip or padding
                gx, gy = x + crop[0], y + crop[1]
                if core[0] <= gx < core[2] and core[1] <= gy < core[3]:
                    points.append([float(gx), float(gy)])
    return points


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default="runs/dev4.txt")
    ap.add_argument("--grid", type=int, default=3)
    ap.add_argument("--halo", type=float, default=0.1)
    ap.add_argument("--threshold", type=float, default=0.33)
    ap.add_argument("--nms", type=float, default=0.85)
    ap.add_argument("--name", help="output folder under runs/gpu, default geco2-g<grid>")
    args = ap.parse_args()

    if "holdout" in args.images or "test" in args.images:
        sys.exit("Nur dev: siehe docs/PROTOCOL.md")
    names = [n.strip() for n in (ROOT / args.images).read_text().splitlines() if n.strip()]
    rows = {r["file_name"]: r for r in load_split("train")}
    out = OUT / (args.name or f"geco2-g{args.grid}")
    out.mkdir(parents=True, exist_ok=True)
    total = []
    for name in names:
        row = rows[name]
        image = load_image(row["path"])
        t0 = time.perf_counter()
        boxes = exemplar_boxes(image, row["kernel_points"])
        points = count_image(image, boxes, args.grid, args.halo, args.threshold, args.nms)
        secs = time.perf_counter() - t0
        m = match(points, row["kernel_points"])
        rec = {"file_name": name, "species": row["species"], "count": row["count"],
               "pred": len(points), "error": len(points) - row["count"], "seconds": round(secs, 2),
               "exemplars": boxes, "grid": args.grid, "halo": args.halo,
               "threshold": args.threshold, "nms": args.nms, "points": points,
               **{k: m[k] for k in ("tp", "fp", "fn", "precision", "recall")}}
        (out / (name.replace("/", "__") + ".json")).write_text(json.dumps(rec))
        total.append(rec)
        print(f"{name}: {rec['pred']} vs {rec['count']} ({rec['error']:+d})  "
              f"P={m['precision']:.3f} R={m['recall']:.3f}  {secs:.1f}s", flush=True)
    err = sum(r["error"] for r in total)
    mae = sum(abs(r["error"]) for r in total) / len(total)
    print(f"Summe {err:+d}  MAE {mae:.1f}  "
          f"P {sum(r['tp'] for r in total) / max(sum(r['pred'] for r in total), 1):.3f}  "
          f"R {sum(r['tp'] for r in total) / sum(r['tp'] + r['fn'] for r in total):.3f}")


if __name__ == "__main__":
    main()
