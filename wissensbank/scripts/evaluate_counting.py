"""
evaluate_counting.py - Zaehl-Baseline (klassische Pipeline) auf corn1000 auswerten.

Pro Bild: A4-Blatt finden und entzerren -> segmentieren -> Kornzahl (Cluster-korrigiert) vs. Label `count`.
Optional: Treffergenauigkeit gegen Punkt-Labels (Precision/Recall, wenn kernel_points vorhanden).

    python evaluate_counting.py --meta ../../data/corn1000_export/metadata.csv --out ../outputs/count_baseline
    python evaluate_counting.py --meta ... --sessions S04 --limit 30 --jobs 4
    python evaluate_counting.py --meta ... --channel gray --margin-mm 10 --mm-per-px 0.12

Ausgabe: predictions.csv · metrics.json · results_row.md (Zeile fuer docs/RESULTS.md) · overlays/*.png (schlechteste + erste)
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree

from a4_sheet import rectify_a4, to_original
from corn1000_data import load_meta, load_points
from grain_segmentation import SegConfig, analyze_image, read_image, write_image


# --------------------------------------------------------------------------- #
# Pro Bild
# --------------------------------------------------------------------------- #
def predict_image(path: str, cfg: SegConfig, mm_per_px: float, margin_mm: float, want_overlay: bool = False):
    img = read_image(path)
    warped, info = rectify_a4(img, mm_per_px=mm_per_px, margin_mm=margin_mm)
    sheet_found = warped is not None
    if not sheet_found:                                    # Fallback: ganzes Bild, kein Massstab
        warped, info = img, None
        c = replace(cfg, mm_per_px=None)
    else:
        c = replace(cfg, mm_per_px=mm_per_px)
    t0 = time.time()
    df, ov, s = analyze_image(warped, c)
    out = {"sheet_found": sheet_found, "pred_count": int(s["n_grains_blob_corrected"]), "pred_raw": int(s["n_grains"]),
           "n_split": int(s.get("n_split", 0)), "channel": s["channel"], "seconds": round(time.time() - t0, 2),
           "median_area_mm2": float(df["area_mm2"].median()) if len(df) and "area_mm2" in df else np.nan,
           "pts_orig": None, "overlay": ov if want_overlay else None}
    if len(df) and info is not None:
        out["pts_orig"] = to_original(df[["cx", "cy"]].to_numpy(), info)
        out["n_est"] = df["n_est_blob"].to_numpy()
    return out


def _work(args):
    return predict_image(*args)


# --------------------------------------------------------------------------- #
# Metriken
# --------------------------------------------------------------------------- #
def count_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    e = p - y
    ae = np.abs(e)
    return {"n": int(len(y)), "MAE": float(ae.mean()), "RMSE": float(np.sqrt((e ** 2).mean())),
            "MAPE_pct": float((ae / y).mean() * 100), "bias": float(e.mean()), "max_abs_err": float(ae.max()),
            "within_1pct": float((ae / y <= 0.01).mean() * 100), "within_2pct": float((ae / y <= 0.02).mean() * 100),
            "within_5pct": float((ae / y <= 0.05).mean() * 100)}


def point_scores(pred_xy: np.ndarray, gt_xy: np.ndarray):
    """Precision/Recall/F1 mit eindeutiger Zuordnung (ungarisch); Radius = 0,5 x medianer Nachbarabstand der GT-Punkte."""
    gt_xy = np.asarray(gt_xy, float)
    if len(gt_xy) < 3 or len(pred_xy) == 0:
        return None
    d, _ = cKDTree(gt_xy).query(gt_xy, k=2)
    r = 0.5 * float(np.median(d[:, 1]))
    D = np.linalg.norm(pred_xy[:, None, :] - gt_xy[None, :, :], axis=2)
    D[D > r] = 1e6
    ri, ci = linear_sum_assignment(D)
    tp = int((D[ri, ci] < 1e6).sum())
    prec, rec = tp / len(pred_xy), tp / len(gt_xy)
    return {"tp": tp, "precision": prec, "recall": rec, "f1": 2 * prec * rec / max(prec + rec, 1e-9), "radius_px": r}


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--meta", required=True, help="metadata.csv aus corn1000_data.py export")
    ap.add_argument("--out", default="../outputs/count_baseline")
    ap.add_argument("--sessions", nargs="*", default=None)
    ap.add_argument("--splits", nargs="*", default=None, help="nur bei `index`-Metadaten: z.B. test")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--mm-per-px", type=float, default=0.15, help="Aufloesung des entzerrten Blatts (kleiner = genauer, langsamer)")
    ap.add_argument("--margin-mm", type=float, default=8.0, help="Blattrand abschneiden (Schatten, Papierkante)")
    ap.add_argument("--channel", default="auto")
    ap.add_argument("--method", default="otsu")
    ap.add_argument("--no-watershed", action="store_true")
    ap.add_argument("--n-overlays", type=int, default=12)
    a = ap.parse_args()

    meta = load_meta(a.meta)
    if a.sessions:
        meta = meta[meta["session"].isin(a.sessions)]
    if a.splits and "split" in meta.columns:
        meta = meta[meta["split"].isin(a.splits)]
    if a.limit:
        meta = meta.head(a.limit)
    meta = meta.reset_index(drop=True)
    points = load_points(a.meta)
    cfg = SegConfig(channel=a.channel, method=a.method, watershed=not a.no_watershed, drop_border=False)
    out = Path(a.out)
    (out / "overlays").mkdir(parents=True, exist_ok=True)

    jobs = [(p, cfg, a.mm_per_px, a.margin_mm, False) for p in meta["path"]]
    t0 = time.time()
    if a.jobs > 1:
        with ProcessPoolExecutor(a.jobs) as ex:
            res = list(ex.map(_work, jobs, chunksize=2))
    else:
        res = []
        for k, j in enumerate(jobs):
            res.append(_work(j))
            if (k + 1) % 20 == 0:
                print(f"  {k + 1}/{len(jobs)} ({time.time() - t0:.0f} s)")
    print(f"{len(res)} Bilder in {time.time() - t0:.0f} s")

    pred = meta[["file", "session", "species", "pollution", "camera", "count"]].copy()
    for key in ["sheet_found", "pred_count", "pred_raw", "n_split", "channel", "seconds", "median_area_mm2"]:
        pred[key] = [r[key] for r in res]
    pred["error"] = pred["pred_count"] - pred["count"]
    pred["abs_error"] = pred["error"].abs()
    pred["rel_error_pct"] = pred["error"] / pred["count"] * 100

    # Punkt-Treffer
    ps = []
    for r, f in zip(res, meta["file"]):
        gt = points.get(f, {}).get("kernel_points")
        ps.append(point_scores(r["pts_orig"], gt) if (gt and r["pts_orig"] is not None) else None)
    for k in ["precision", "recall", "f1"]:
        pred[f"pt_{k}"] = [s[k] if s else np.nan for s in ps]

    pred.to_csv(out / "predictions.csv", index=False)
    y, p = pred["count"].to_numpy(float), pred["pred_count"].to_numpy(float)
    metrics = {"overall": count_metrics(y, p),
               "per_session": {s: count_metrics(g["count"].to_numpy(float), g["pred_count"].to_numpy(float))
                               for s, g in pred.groupby("session")},
               "per_species": {s: count_metrics(g["count"].to_numpy(float), g["pred_count"].to_numpy(float))
                               for s, g in pred.groupby("species")},
               "sheet_found_pct": float(pred["sheet_found"].mean() * 100),
               "seconds_per_image": float(pred["seconds"].mean()),
               "points": {k: float(np.nanmean(pred[f"pt_{k}"])) for k in ["precision", "recall", "f1"]} if pred["pt_f1"].notna().any() else None,
               "config": {"mm_per_px": a.mm_per_px, "margin_mm": a.margin_mm, "channel": a.channel, "method": a.method,
                          "watershed": not a.no_watershed}}
    json.dump(metrics, open(out / "metrics.json", "w"), indent=2)

    m = metrics["overall"]
    row = (f"| {time.strftime('%Y-%m-%d %H:%M')} | (Name) | Klassisch: A4-Entzerrung + Otsu + Watershed "
           f"({'/'.join(a.sessions) if a.sessions else 'alle Sessions'}, n={m['n']}) | {m['MAE']:.1f} | {m['max_abs_err']:.0f} | "
           f"MAPE {m['MAPE_pct']:.1f} %, Bias {m['bias']:+.1f}, ±2 %: {m['within_2pct']:.0f} % der Bilder |")
    (out / "results_row.md").write_text(row + "\n", encoding="utf-8")

    # Overlays: schlechteste zuerst, dann die ersten
    order = list(pred.sort_values("abs_error", ascending=False).index[:a.n_overlays // 2]) + list(pred.index[:a.n_overlays - a.n_overlays // 2])
    for idx in dict.fromkeys(order):
        r = predict_image(meta.loc[idx, "path"], cfg, a.mm_per_px, a.margin_mm, want_overlay=True)
        ov = r["overlay"]
        cv2.putText(ov, f"label {int(pred.loc[idx, 'count'])}  pred {int(pred.loc[idx, 'pred_count'])}", (10, ov.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3, cv2.LINE_AA)
        write_image(out / "overlays" / f"{Path(meta.loc[idx, 'file']).stem}.jpg", cv2.resize(ov, None, fx=0.5, fy=0.5))

    print(f"\nGesamt: MAE {m['MAE']:.2f} | MAPE {m['MAPE_pct']:.2f} % | Bias {m['bias']:+.2f} | max {m['max_abs_err']:.0f} | "
          f"Blatt gefunden {metrics['sheet_found_pct']:.0f} %")
    for s, v in metrics["per_session"].items():
        print(f"  {s}: MAE {v['MAE']:.2f}, MAPE {v['MAPE_pct']:.2f} %, Bias {v['bias']:+.2f} (n={v['n']})")
    print("Zeile fuer docs/RESULTS.md:\n" + row)
    print("->", out.resolve())


if __name__ == "__main__":
    main()
