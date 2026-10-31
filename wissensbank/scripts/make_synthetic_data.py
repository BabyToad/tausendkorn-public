"""
make_synthetic_data.py - Synthetische Koernerbilder MIT bekannter Wahrheit (Anzahl, Masse, TKM).

Zweck: Pipeline testen/entwickeln, bevor das echte Datenset da ist; Pitch-Demo-Fallback.
Aufruf: python make_synthetic_data.py --out ../data/synthetic --n-images 8 --seed 42
Erzeugt: <out>/images/*.png  und  <out>/labels.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

DENSITY_MG_MM3 = 1.30          # Korndichte ~1.3 g/cm3
COIN_DIAMETER_MM = 25.75       # 2-Euro-Muenze


def make_image(rng, n_grains, length_mm, width_mm, mm_per_px=0.1, size=(1500, 2000),
               touch_prob=0.15, with_coin=True, touch_dist=0.82, return_centers=False, paper=None):
    h, w = size
    bg = np.full((h, w, 3), paper if paper is not None else (205, 208, 210), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    grad = 1.0 - 0.18 * ((xx / w) * 0.6 + (yy / h) * 0.4)            # Beleuchtungsgradient
    img = bg * grad[..., None]

    centers, gt = [], []
    coin_r = COIN_DIAMETER_MM / mm_per_px / 2
    coin_c = max(200, int(coin_r + 40))                                 # Muenze voll im Bild
    margin = 120
    tries = 0
    while len(centers) < n_grains and tries < n_grains * 200:
        tries += 1
        L = max(rng.normal(length_mm, 0.07 * length_mm), 0.6 * length_mm)
        W = max(rng.normal(width_mm, 0.07 * width_mm), 0.6 * width_mm)
        Lpx, Wpx = L / mm_per_px, W / mm_per_px
        if centers and rng.random() < touch_prob:                    # beruehrend platzieren
            base = np.array(centers[rng.integers(len(centers))])
            ang = rng.uniform(0, 2 * np.pi)
            c = base + touch_dist * Lpx * np.array([np.cos(ang), np.sin(ang)])   # 0.82 = deutlich ueberlappend, 1.0 = beruehrend
        else:
            c = np.array([rng.uniform(margin, w - margin), rng.uniform(margin, h - margin)])
            if any(np.hypot(*(c - np.array(o))) < 1.15 * Lpx for o in centers):
                continue
        if not (margin / 2 < c[0] < w - margin / 2 and margin / 2 < c[1] < h - margin / 2):
            continue
        if with_coin and c[0] < 360 and c[1] < 360:                    # Muenzenecke freihalten
            continue
        if with_coin and mm_per_px < 0.08 and \
                np.hypot(c[0] - coin_c, c[1] - coin_c) < coin_r + 1.2 * Lpx:
            continue                                                   # grosse Muenze (kleiner mm/px): Zone mitskalieren
        angle = rng.uniform(0, 180)
        base_col = np.array([rng.normal(95, 8), rng.normal(140, 8), rng.normal(185, 8)])  # BGR goldbraun
        cv2.ellipse(img, (int(c[0]), int(c[1])), (int(Lpx / 2), int(Wpx / 2)), angle, 0, 360,
                    base_col.tolist(), -1, cv2.LINE_AA)
        # Laengsfurche + Glanzlicht
        a = np.radians(angle)
        d = np.array([np.cos(a), np.sin(a)]) * Lpx * 0.38
        cv2.line(img, tuple((c - d).astype(int)), tuple((c + d).astype(int)),
                 (base_col * 0.7).tolist(), 2, cv2.LINE_AA)
        centers.append(tuple(c))
        T = 0.85 * W * rng.normal(1.0, 0.05)                            # Dicke
        vol = np.pi / 6 * L * W * T
        gt.append(vol * DENSITY_MG_MM3)                                 # mg

    if with_coin:
        cv2.circle(img, (coin_c, coin_c), int(coin_r), (150, 155, 158), -1, cv2.LINE_AA)
        cv2.circle(img, (coin_c, coin_c), int(coin_r), (110, 112, 115), 4, cv2.LINE_AA)

    img += rng.normal(0, 3.0, img.shape)                                # Sensorrauschen
    img = cv2.GaussianBlur(img, (0, 0), 1.0)
    out = np.clip(img, 0, 255).astype(np.uint8)
    if return_centers:
        return out, np.array(gt), np.array(centers, np.float32)
    return out, np.array(gt)


def make_a4_scene(rng, n_grains, mm_per_px=0.1, out_size=(3000, 4000)):
    """
    Foto-aehnliche Szene: weisses A4-Blatt (210 x 297 mm) mit Koernern, perspektivisch verzerrt, leicht gedreht,
    auf dunklem Untergrund. Rueckgabe: (bild, masse_mg_je_korn, kornmitten_xy_im_bild).
    """
    L, W = rng.uniform(5.8, 7.6), rng.uniform(2.7, 3.6)
    sheet_h, sheet_w = int(297 / mm_per_px), int(210 / mm_per_px)
    sheet, gt, centers = make_image(rng, n_grains, L, W, mm_per_px, size=(sheet_h, sheet_w), touch_prob=0.04,
                                    with_coin=False, touch_dist=1.0, return_centers=True, paper=(232, 235, 236))
    Wd, Hd = out_size
    ang = np.radians(rng.uniform(-12, 12))
    sx, sy = rng.uniform(0.62, 0.72) * Wd / sheet_w, rng.uniform(0.62, 0.72) * Hd / sheet_h
    base = np.array([[0, 0], [sheet_w, 0], [sheet_w, sheet_h], [0, sheet_h]], np.float32) - [sheet_w / 2, sheet_h / 2]
    R = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]], np.float32)
    dst = (base * [sx, sy]) @ R.T + [Wd / 2, Hd / 2] + rng.uniform(-0.03, 0.03, (4, 2)) * [Wd, Hd]
    dst += rng.uniform(-0.025, 0.025, (4, 2)).astype(np.float32) * [Wd, Hd]                # Perspektive
    Hm = cv2.getPerspectiveTransform(np.array([[0, 0], [sheet_w, 0], [sheet_w, sheet_h], [0, sheet_h]], np.float32), dst.astype(np.float32))
    table = np.full((Hd, Wd, 3), (38, 42, 40), np.uint8)
    table = np.clip(table + rng.normal(0, 4, table.shape), 0, 255).astype(np.uint8)
    warped = cv2.warpPerspective(sheet, Hm, (Wd, Hd), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT)
    mask = cv2.warpPerspective(np.full(sheet.shape[:2], 255, np.uint8), Hm, (Wd, Hd), flags=cv2.INTER_NEAREST)
    scene = np.where(mask[..., None] > 0, warped, table)
    pts = cv2.perspectiveTransform(centers.reshape(-1, 1, 2), Hm).reshape(-1, 2)
    return scene, gt, pts


def make_corn1000_mock(out: Path, n_images=6, seed=7):
    """Attrappe im Exportformat von corn1000_data.py (images/, metadata.csv, points.jsonl) fuer Tests ohne echte Daten."""
    import json
    rng = np.random.default_rng(seed)
    out = Path(out)
    rows = []
    with open(out / "points.jsonl", "w") as fp:
        (out / "images" / "S90").mkdir(parents=True, exist_ok=True)
        for i in range(n_images):
            n = int(rng.integers(180, 420))
            img, gt, pts = make_a4_scene(rng, n)
            rel = f"images/S90/mock_{i:02d}.jpg"
            cv2.imwrite(str(out / rel), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            has_pts = i % 2 == 0
            fp.write(json.dumps({"file": rel, "kernel_points": pts.tolist() if has_pts else None,
                                 "broken_points": None, "invalid_points": None}) + "\n")
            rows.append({"file": rel, "row": i, "width": img.shape[1], "height": img.shape[0], "scale": 1.0, "count": len(gt),
                         "arrangement_id": f"S90-{i:02d}", "session": "S90", "step": i, "take": 0, "species": "wheat-w",
                         "pollution": "none", "camera": "mock", "taken_at": "", "n_kernel_points": len(pts) if has_pts else np.nan,
                         "n_broken_points": np.nan, "n_invalid_points": np.nan})
    pd.DataFrame(rows).to_csv(out / "metadata.csv", index=False)
    print(f"{n_images} Attrappen-Bilder -> {out.resolve()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../data/synthetic")
    ap.add_argument("--n-images", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--mm-per-px", type=float, default=0.1)
    ap.add_argument("--corn1000-mock", action="store_true", help="A4-Fotoszenen im corn1000-Exportformat statt Muenzbilder")
    a = ap.parse_args()
    if a.corn1000_mock:
        make_corn1000_mock(Path(a.out), a.n_images, a.seed)
        return

    rng = np.random.default_rng(a.seed)
    out = Path(a.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(a.n_images):
        # unterschiedliche "Sorten/Partien" -> unterschiedliche TKM
        L = rng.uniform(5.8, 7.6)
        W = rng.uniform(2.7, 3.6)
        n = int(rng.integers(70, 160))
        img, masses_mg = make_image(rng, n, L, W, a.mm_per_px)
        name = f"synth_{i:02d}.png"
        cv2.imwrite(str(out / "images" / name), img)
        rows.append({"image": name, "n_grains_true": len(masses_mg),
                     "total_mass_g": masses_mg.sum() / 1000,
                     "tkm_true_g": masses_mg.mean(),          # mg/Korn == g/1000 Koerner
                     "mm_per_px_true": a.mm_per_px, "mean_length_mm_true": L, "mean_width_mm_true": W})
        print(name, "n =", len(masses_mg), "TKM =", round(masses_mg.mean(), 1), "g")
    pd.DataFrame(rows).to_csv(out / "labels.csv", index=False)
    print("->", out.resolve())


if __name__ == "__main__":
    main()
