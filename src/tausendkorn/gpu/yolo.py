"""YOLO kernel detector trained on the train split, counted on dev (CUDA machine).

Labels are points, so boxes are derived: an isolated kernel gets the bounding box of
its threshold blob; a kernel whose blob holds other labelled points (a cluster) gets the
image's median isolated box, centred on its point. Counting only needs centres.
Training and inference use 1024 px tiles; at inference a detection counts only if its
centre lies in the tile's core (ownership as in tausendkorn.tiles).

    uv run --group gpu python -m tausendkorn.gpu.yolo prep
    uv run --group gpu python -m tausendkorn.gpu.yolo train --model yolo11s.pt --epochs 40
    # Unschärfe-Robustheit (nach Abgabe trainiert, nur dev gemessen; docs/RESULTS.md):
    uv run --group gpu python -m tausendkorn.gpu.yolo prep-blur
    uv run --group gpu python -m tausendkorn.gpu.yolo train --blur --epochs 30 --name yolo11s-blur
    uv run --group gpu python -m tausendkorn.gpu.yolo count --weights <best.pt> --images runs/dev4.txt
    ... count --weights <w> --images splits/holdout.txt --final   (bzw. --images test)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from tausendkorn.eval import load_image, load_split
from tausendkorn.match import match

ROOT = Path(__file__).resolve().parents[3]
DS = ROOT / "runs" / "yolo" / "data"
OUT = ROOT / "runs" / "gpu"
CLASSES = ["kernel", "broken", "invalid"]
TILE, STRIDE = 1024, 768


def point_boxes(gray: np.ndarray, groups: list[list]) -> list[tuple[int, float, float, float, float]]:
    """(cls, x0, y0, x1, y1) for every labelled point, from an Otsu mask of the image."""
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    # Not Otsu: the dark background around the sheet would pull the split down. Kernels
    # are anything clearly darker than paper (75th percentile minus 35).
    paper = np.percentile(blur, 75)
    mask = (blur < paper - 35).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask)
    H, W = gray.shape
    owners: dict[int, int] = {}
    for pts in groups:
        for x, y in pts:
            c = lab[min(int(y), H - 1), min(int(x), W - 1)]
            owners[c] = owners.get(c, 0) + 1
    iso = []
    for pts in groups[:1]:
        for x, y in pts:
            c = lab[min(int(y), H - 1), min(int(x), W - 1)]
            if c and owners[c] == 1:
                iso.append(stats[c][2:4])
    mw, mh = (np.median(iso, 0) if iso else (60, 60))
    out = []
    for cls, pts in enumerate(groups):
        for x, y in pts:
            c = lab[min(int(y), H - 1), min(int(x), W - 1)]
            if c and owners[c] == 1 and stats[c][2] < 4 * mw and stats[c][3] < 4 * mh:
                bx, by, bw, bh, _ = stats[c]
                out.append((cls, bx, by, bx + bw, by + bh))
            else:
                out.append((cls, x - mw / 2, y - mh / 2, x + mw / 2, y + mh / 2))
    return out


def tiles(W: int, H: int):
    xs = list(range(0, max(W - TILE, 0) + 1, STRIDE)) or [0]
    ys = list(range(0, max(H - TILE, 0) + 1, STRIDE)) or [0]
    if xs[-1] + TILE < W:
        xs.append(W - TILE)
    if ys[-1] + TILE < H:
        ys.append(H - TILE)
    return [(x, y) for y in ys for x in xs]


def prep() -> None:
    rows = {r["file_name"]: r for r in load_split("train")}
    for split, src in (("train", "splits/train.txt"), ("val", "splits/dev.txt")):
        (DS / split / "images").mkdir(parents=True, exist_ok=True)
        (DS / split / "labels").mkdir(parents=True, exist_ok=True)
        for name in (ROOT / src).read_text().split():
            row = rows[name]
            image = load_image(row["path"])
            arr = np.asarray(image)
            W, H = image.size
            groups = [row["kernel_points"] or [], row["broken_points"] or [], row["invalid_points"] or []]
            boxes = point_boxes(cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY), groups)
            stem = name.replace("/", "__").rsplit(".", 1)[0]
            for tx, ty in tiles(W, H):
                lines = []
                for cls, x0, y0, x1, y1 in boxes:
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                    if not (tx <= cx < tx + TILE and ty <= cy < ty + TILE):
                        continue
                    a, b = max(x0, tx) - tx, max(y0, ty) - ty
                    c, d = min(x1, tx + TILE) - tx, min(y1, ty + TILE) - ty
                    lines.append(f"{cls} {(a + c) / 2 / TILE:.6f} {(b + d) / 2 / TILE:.6f} "
                                 f"{(c - a) / TILE:.6f} {(d - b) / TILE:.6f}")
                if not lines and split == "train" and (tx + ty) % 3:
                    continue  # keep some empty background tiles, not all
                tile = f"{stem}_{tx}_{ty}"
                cv2.imwrite(str(DS / split / "images" / f"{tile}.jpg"),
                            cv2.cvtColor(arr[ty:ty + TILE, tx:tx + TILE], cv2.COLOR_RGB2BGR))
                (DS / split / "labels" / f"{tile}.txt").write_text("\n".join(lines))
            print(split, name, len(boxes), flush=True)
    (DS / "data.yaml").write_text(
        f"path: {DS.as_posix()}\ntrain: train/images\nval: val/images\nnames: {CLASSES}\n")


def degrade(tile: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """One random focus/motion degradation; labels stay valid (no geometry change).

    count_1000 undercounts where the far end of an oblique shot is out of focus
    (docs/RESULTS.md, docs/AUDIT_*.md): YOLO keeps the kernels but loses confidence.
    """
    kind = rng.integers(4)
    if kind == 0:
        out = cv2.GaussianBlur(tile, (0, 0), rng.uniform(0.8, 4.0))
    elif kind == 1:  # defocus: disk kernel
        r = int(rng.integers(2, 7))
        k = np.zeros((2 * r + 1, 2 * r + 1), np.float32)
        cv2.circle(k, (r, r), r, 1, -1)
        out = cv2.filter2D(tile, -1, k / k.sum())
    elif kind == 2:  # motion blur at a random angle
        n = int(rng.integers(5, 16))
        k = np.zeros((n, n), np.float32)
        k[n // 2] = 1
        rot = cv2.getRotationMatrix2D((n / 2 - 0.5, n / 2 - 0.5), rng.uniform(0, 180), 1)
        k = cv2.warpAffine(k, rot, (n, n))
        out = cv2.filter2D(tile, -1, k / k.sum())
    else:  # depth-of-field ramp: sharp at one edge, blurred towards the other
        soft = cv2.GaussianBlur(tile, (0, 0), rng.uniform(2.0, 4.5))
        ramp = np.linspace(0, 1, tile.shape[0], dtype=np.float32)[:, None, None]
        if rng.random() < 0.5:
            ramp = ramp[::-1]
        out = (tile * (1 - ramp) + soft * ramp).astype(np.uint8)
    if rng.random() < 0.3:  # JPEG on top of soft detail, as phones do
        _, enc = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(55, 90))])
        out = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    return out


def prep_blur(share: float = 0.6, seed: int = 0) -> None:
    """data_blur: all train tiles plus a degraded copy of `share` of them; same val."""
    import shutil

    rng = np.random.default_rng(seed)
    blur = DS.parent / "data_blur"
    for sub in ("images", "labels"):
        (blur / "train" / sub).mkdir(parents=True, exist_ok=True)
    for img in sorted((DS / "train" / "images").glob("*.jpg")):
        lab = DS / "train" / "labels" / f"{img.stem}.txt"
        shutil.copy(img, blur / "train" / "images" / img.name)
        shutil.copy(lab, blur / "train" / "labels" / lab.name)
        if rng.random() < share:
            out = degrade(cv2.imread(str(img)), rng)
            cv2.imwrite(str(blur / "train" / "images" / f"{img.stem}_blur.jpg"), out)
            shutil.copy(lab, blur / "train" / "labels" / f"{img.stem}_blur.txt")
    (blur / "data.yaml").write_text(
        f"path: {DS.as_posix()}\ntrain: {(blur / 'train' / 'images').as_posix()}\n"
        f"val: val/images\nnames: {CLASSES}\n")
    print(len(list((blur / "train" / "images").glob("*.jpg"))), "train tiles")


def train(model: str, epochs: int, batch: int, name: str, data: Path = DS) -> None:
    from ultralytics import YOLO

    YOLO(model).train(data=str(data / "data.yaml"), imgsz=TILE, epochs=epochs, batch=batch,
                      max_det=1000, project=str(ROOT / "runs" / "yolo"), name=name,
                      workers=2, close_mosaic=5, degrees=90, flipud=0.5, fliplr=0.5,
                      exist_ok=True, plots=False)


def count(weights: str, images: str, conf: float, name: str, final: bool = False) -> None:
    """Count a list of train-split images, or with --final the holdout / count_1000 once."""
    import subprocess

    from ultralytics import YOLO

    split = "test" if images == "test" else "train"
    if ("holdout" in images or split == "test") and not final:
        sys.exit("Nur dev: holdout/test nur mit --final und eingefrorener Pipeline (docs/PROTOCOL.md)")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True, cwd=ROOT).stdout.strip()
    if final and subprocess.run(["git", "status", "--porcelain", "src"], capture_output=True,
                                text=True, cwd=ROOT).stdout.strip():
        sys.exit("--final braucht einen sauberen Commit von src/")
    model = YOLO(weights)
    rows = {r["file_name"]: r for r in load_split(split)}
    out = OUT / name
    out.mkdir(parents=True, exist_ok=True)
    total = []
    names = list(rows) if split == "test" else (ROOT / images).read_text().split()
    for fname in names:
        row = rows[fname]
        arr = np.asarray(load_image(row["path"]))
        H, W = arr.shape[:2]
        t0 = time.perf_counter()
        grid = tiles(W, H)
        xs = sorted({x for x, _ in grid})
        ys = sorted({y for _, y in grid})
        points, broken = [], 0
        for tx, ty in grid:
            # Core: the half-way lines between neighbouring tile origins.
            i, j = xs.index(tx), ys.index(ty)
            cx0 = 0 if i == 0 else (xs[i - 1] + TILE + tx) / 2
            cx1 = W if i == len(xs) - 1 else (tx + TILE + xs[i + 1]) / 2
            cy0 = 0 if j == 0 else (ys[j - 1] + TILE + ty) / 2
            cy1 = H if j == len(ys) - 1 else (ty + TILE + ys[j + 1]) / 2
            res = model.predict(arr[ty:ty + TILE, tx:tx + TILE, ::-1], imgsz=TILE, conf=conf,
                                max_det=1000, verbose=False)[0]
            for (x0, y0, x1, y1), cls in zip(res.boxes.xyxy.tolist(), res.boxes.cls.tolist()):
                gx, gy = tx + (x0 + x1) / 2, ty + (y0 + y1) / 2
                if cx0 <= gx < cx1 and cy0 <= gy < cy1:
                    if int(cls) == 0:
                        points.append([gx, gy])
                    elif int(cls) == 1:
                        broken += 1
        secs = time.perf_counter() - t0
        truth = row["kernel_points"] or []
        m = match(points, truth) if truth else {"tp": None, "fp": None, "fn": None,
                                                 "precision": None, "recall": None}
        rec = {"file_name": fname, "species": row["species"], "count": row["count"],
               "pred": len(points), "error": len(points) - row["count"], "seconds": round(secs, 2),
               "weights": weights, "conf": conf, "commit": commit, "broken": broken, "points": points,
               **{k: m[k] for k in ("tp", "fp", "fn", "precision", "recall")}}
        (out / (fname.replace("/", "__") + ".json")).write_text(json.dumps(rec))
        total.append(rec)
        print(f"{fname}: {rec['pred']} vs {rec['count']} ({rec['error']:+d})  {secs:.1f}s", flush=True)
    errs = [r["error"] for r in total]
    print(f"n={len(errs)}  Summe {sum(errs):+d}  MAE {sum(map(abs, errs)) / len(errs):.2f}  "
          f"Bias {sum(errs) / len(errs):+.2f}  max {max(map(abs, errs))}  "
          f"exakt {sum(e == 0 for e in errs)}  ±1 {sum(abs(e) <= 1 for e in errs)}  "
          f"±5 {sum(abs(e) <= 5 for e in errs)}")
    pts = [r for r in total if r["tp"] is not None]
    if pts:
        print(f"P {sum(r['tp'] for r in pts) / max(sum(r['pred'] for r in pts), 1):.3f}  "
              f"R {sum(r['tp'] for r in pts) / sum(r['tp'] + r['fn'] for r in pts):.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prep")
    b = sub.add_parser("prep-blur", help="Train-Kacheln plus Unschärfe-Kopien (data_blur)")
    b.add_argument("--share", type=float, default=0.6)
    t = sub.add_parser("train")
    t.add_argument("--model", default="yolo11s.pt")
    t.add_argument("--epochs", type=int, default=40)
    t.add_argument("--batch", type=int, default=6)
    t.add_argument("--name", default="yolo11s")
    t.add_argument("--blur", action="store_true", help="mit data_blur trainieren (vorher prep-blur)")
    c = sub.add_parser("count")
    c.add_argument("--weights", required=True)
    c.add_argument("--images", default="runs/dev4.txt")
    c.add_argument("--conf", type=float, default=0.25)
    c.add_argument("--name", default="yolo11s")
    c.add_argument("--final", action="store_true", help="holdout/test, einmal, eingefroren")
    args = ap.parse_args()
    if args.cmd == "prep":
        prep()
    elif args.cmd == "prep-blur":
        prep_blur(args.share)
    elif args.cmd == "train":
        train(args.model, args.epochs, args.batch, args.name,
              DS.parent / "data_blur" if args.blur else DS)
    else:
        count(args.weights, args.images, args.conf, args.name, args.final)


if __name__ == "__main__":
    main()
