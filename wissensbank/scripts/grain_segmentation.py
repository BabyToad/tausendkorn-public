"""
grain_segmentation.py - Klassische CV-Pipeline: Koerner zaehlen, vermessen, TKM schaetzen.

Pipeline:  Bild laden -> Kanal waehlen -> (Flatfield) -> Blur -> Schwellwert (Otsu/adaptiv/fix)
           -> Morphologie -> Hole-Fill -> Labeling -> Referenzobjekt (Muenze) optional
           -> Cluster-Splitting (Distanztransformation + h-Maxima + Watershed)
           -> Features je Korn (Geometrie, Farbe) -> Overlay + CSV.

CLI-Beispiele:
  python grain_segmentation.py --input ../data/raw --out ../outputs/seg --mm-per-px 0.1
  python grain_segmentation.py --input bild.jpg --out ../outputs/seg --ref-diameter-mm 25.75
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage import measure, morphology, segmentation

IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def _axes(p):
    """(Hauptachse, Nebenachse) - kompatibel mit alten und neuen scikit-image-Versionen."""
    maj = getattr(p, "axis_major_length", None)
    mino = getattr(p, "axis_minor_length", None)
    if maj is None:
        maj, mino = p.major_axis_length, p.minor_axis_length
    return maj, mino


def _remove_small(labels: np.ndarray, min_px: int) -> np.ndarray:
    counts = np.bincount(labels.ravel())
    small = counts < min_px
    small[0] = False
    out = labels.copy()
    out[small[labels]] = 0
    return out


# --------------------------------------------------------------------------- #
# I/O (Windows-/Umlaut-sicher: cv2.imread scheitert an Nicht-ASCII-Pfaden)
# --------------------------------------------------------------------------- #
def read_image(path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Bild nicht lesbar: {path}")
    return img


def write_image(path, img: np.ndarray) -> None:
    ext = Path(path).suffix or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise ValueError(f"Bild nicht schreibbar: {path}")
    buf.tofile(str(path))


def list_images(path) -> list[Path]:
    p = Path(path)
    if p.is_file():
        return [p]
    return sorted(f for f in p.rglob("*") if f.suffix.lower() in IMG_EXT)


# --------------------------------------------------------------------------- #
# Konfiguration
# --------------------------------------------------------------------------- #
@dataclass
class SegConfig:
    channel: str = "auto"            # auto | gray | L | a | b | S | R | G | B
    method: str = "otsu"             # otsu | adaptive | fixed
    fixed_threshold: int = 128
    invert: str = "auto"             # auto | yes | no  (Vordergrund = Koerner)
    flatfield: bool = False          # Beleuchtungsgradient herausrechnen
    blur_sigma: float = 1.5
    open_px: int = 2
    close_px: int = 2
    min_area_px: int = 40
    min_rel_area: float = 0.30       # < 30 % der Median-Kornflaeche -> Rauschen
    max_rel_area_single: float = 1.45  # groesser -> Cluster-Verdacht
    watershed: bool = True
    h_frac: float = 0.25             # h-Maxima-Hoehe als Anteil des Korn-Innenradius
    drop_border: bool = True         # angeschnittene Koerner am Bildrand ausschliessen
    mm_per_px: float | None = None
    ref_diameter_mm: float | None = None  # z.B. 2-Euro-Muenze 25.75 mm


# --------------------------------------------------------------------------- #
# Vorverarbeitung
# --------------------------------------------------------------------------- #
def get_channel(img_bgr: np.ndarray, name: str) -> np.ndarray:
    if name == "gray":
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    if name in ("L", "a", "b"):
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        return lab[..., {"L": 0, "a": 1, "b": 2}[name]]
    if name == "S":
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)[..., 1]
    if name in ("R", "G", "B"):
        return img_bgr[..., {"B": 0, "G": 1, "R": 2}[name]]
    raise ValueError(f"Unbekannter Kanal: {name}")


def otsu_separability(ch: np.ndarray) -> float:
    """Anteil der Varianz, den Otsu erklaert (0..1). Hoeher = besser trennbar."""
    t, _ = cv2.threshold(ch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    fg, bg = ch[ch > t], ch[ch <= t]
    if len(fg) == 0 or len(bg) == 0:
        return 0.0
    w1 = len(fg) / ch.size
    return float(w1 * (1 - w1) * (fg.mean() - bg.mean()) ** 2 / (ch.var() + 1e-9))


def choose_channel(img_bgr: np.ndarray) -> str:
    cands = ["gray", "S", "b", "a", "L"]
    scores = {c: otsu_separability(get_channel(img_bgr, c)) for c in cands}
    return max(scores, key=scores.get)


def flatfield(ch: np.ndarray) -> np.ndarray:
    """Teilt durch stark geglaettetes Hintergrundbild (korrigiert Beleuchtungsgradient)."""
    sigma = max(ch.shape) / 6
    bg = cv2.GaussianBlur(ch.astype(np.float32), (0, 0), sigma)
    out = ch.astype(np.float32) / (bg + 1e-6) * float(np.mean(bg))
    return np.clip(out, 0, 255).astype(np.uint8)


def make_mask(img_bgr: np.ndarray, cfg: SegConfig) -> tuple[np.ndarray, str]:
    name = choose_channel(img_bgr) if cfg.channel == "auto" else cfg.channel
    ch = get_channel(img_bgr, name)
    if cfg.flatfield:
        ch = flatfield(ch)
    if cfg.blur_sigma > 0:
        ch = cv2.GaussianBlur(ch, (0, 0), cfg.blur_sigma)

    if cfg.method == "otsu":
        _, m = cv2.threshold(ch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif cfg.method == "adaptive":
        block = int(min(ch.shape) / 8) // 2 * 2 + 1
        m = cv2.adaptiveThreshold(ch, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, block, 5)
    elif cfg.method == "fixed":
        _, m = cv2.threshold(ch, cfg.fixed_threshold, 255, cv2.THRESH_BINARY)
    else:
        raise ValueError(cfg.method)

    mask = m > 0
    if cfg.invert == "yes" or (cfg.invert == "auto" and mask.mean() > 0.5):
        mask = ~mask

    mu8 = mask.astype(np.uint8) * 255
    if cfg.open_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * cfg.open_px + 1,) * 2)
        mu8 = cv2.morphologyEx(mu8, cv2.MORPH_OPEN, k)
    if cfg.close_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * cfg.close_px + 1,) * 2)
        mu8 = cv2.morphologyEx(mu8, cv2.MORPH_CLOSE, k)
    return ndi.binary_fill_holes(mu8 > 0), name


# --------------------------------------------------------------------------- #
# Referenzobjekt (Muenze) fuer Massstab
# --------------------------------------------------------------------------- #
def find_reference_disc(labels: np.ndarray, med_area: float):
    """Groesstes sehr rundes, sehr konvexes Objekt (> 4x Kornflaeche) = Muenze."""
    best = None
    H, W = labels.shape
    for r in measure.regionprops(labels):
        if r.area < 4 * med_area or r.perimeter == 0:
            continue
        minr, minc, maxr, maxc = r.bbox
        if minr == 0 or minc == 0 or maxr == H or maxc == W:
            continue                      # am Bildrand angeschnitten -> Durchmesser unzuverlaessig
        circ = 4 * np.pi * r.area / r.perimeter ** 2
        if circ > 0.85 and r.solidity > 0.97 and (best is None or r.area > best.area):
            best = r
    return best


def detect_scale_disc(img_bgr, med_area, cfg, main_channel):
    """Sucht die Referenzmuenze in mehreren Kanaelen (graue Muenze fehlt z.B. im S-Kanal)."""
    from dataclasses import replace
    tried = []
    for ch_name in [main_channel, "gray", "L", "S", "b"]:
        if ch_name in tried:
            continue
        tried.append(ch_name)
        m, _ = make_mask(img_bgr, replace(cfg, channel=ch_name))
        ref = find_reference_disc(measure.label(m, connectivity=1), med_area)
        if ref is not None:
            return ref
    return None


# --------------------------------------------------------------------------- #
# Cluster-Splitting
# --------------------------------------------------------------------------- #
def robust_single_stats(labels: np.ndarray) -> tuple[float, float]:
    """(Median-Einzelkornflaeche, Median-Innenradius) aus 'unauffaelligen' Objekten."""
    props = measure.regionprops(labels)
    areas = np.array([p.area for p in props], dtype=float)
    if len(areas) == 0:
        return 0.0, 0.0
    med = float(np.median(areas))
    singles = [p for p in props if 0.6 * med <= p.area <= 1.4 * med and p.solidity >= 0.9]
    if len(singles) >= 5:
        med = float(np.median([p.area for p in singles]))
    else:
        singles = props
    radii = []
    for p in singles:
        crop = np.pad(p.image, 1)
        radii.append(ndi.distance_transform_edt(crop).max())
    return med, float(np.median(radii))


def split_clusters(mask: np.ndarray, labels: np.ndarray, med_area: float,
                   r_single: float, cfg: SegConfig):
    """Gibt (neue Labels, Menge der gesplitteten Label-IDs) zurueck."""
    out = np.zeros_like(labels)
    next_id = 1
    split_ids: set[int] = set()
    for p in measure.regionprops(labels):
        suspect = (p.area > cfg.max_rel_area_single * med_area) or \
                  (p.solidity < 0.88 and p.area > 1.1 * med_area)
        minr, minc, maxr, maxc = p.bbox
        sl = (slice(minr, maxr), slice(minc, maxc))
        region = p.image
        if not (cfg.watershed and suspect):
            out[sl][region] = next_id
            next_id += 1
            continue
        crop = np.pad(region, 2)
        dist = ndi.distance_transform_edt(crop)
        dist_s = ndi.gaussian_filter(dist, 1.0)
        h = max(cfg.h_frac * r_single, 0.5)
        markers = measure.label(morphology.h_maxima(dist_s, h))
        if markers.max() <= 1:
            out[sl][region] = next_id
            next_id += 1
            continue
        ws = segmentation.watershed(-dist_s, markers, mask=crop)[2:-2, 2:-2]
        for k in range(1, ws.max() + 1):
            piece = (ws == k) & region
            if piece.sum() == 0:
                continue
            out[sl][piece] = next_id
            split_ids.add(next_id)
            next_id += 1
    return out, split_ids


# --------------------------------------------------------------------------- #
# Features
# --------------------------------------------------------------------------- #
def extract_features(img_bgr: np.ndarray, labels: np.ndarray, split_ids: set[int],
                     med_area: float, mm_per_px: float | None) -> pd.DataFrame:
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    H, W = labels.shape
    rows = []
    for p in measure.regionprops(labels):
        rr, cc = p.coords[:, 0], p.coords[:, 1]
        minr, minc, maxr, maxc = p.bbox
        per = p.perimeter if p.perimeter > 0 else np.nan
        maj, mino = _axes(p)
        row = {
            "grain_id": p.label,
            "cx": p.centroid[1], "cy": p.centroid[0],
            "area_px": p.area,
            "perimeter_px": per,
            "major_px": maj,
            "minor_px": mino,
            "aspect": maj / max(mino, 1e-6),
            "eccentricity": p.eccentricity,
            "solidity": p.solidity,
            "extent": p.extent,
            "circularity": 4 * np.pi * p.area / per ** 2 if per == per else np.nan,
            "orientation_deg": np.degrees(p.orientation),
            "touches_border": bool(minr == 0 or minc == 0 or maxr == H or maxc == W),
            "was_split": p.label in split_ids,
            "n_est_blob": max(1, int(round(p.area / med_area))) if med_area > 0 else 1,
            "L": lab[rr, cc, 0].mean() * 100 / 255, "a": lab[rr, cc, 1].mean() - 128,
            "b": lab[rr, cc, 2].mean() - 128,
            "hue": hsv[rr, cc, 0].mean() * 2, "sat": hsv[rr, cc, 1].mean() / 255,
            "val": hsv[rr, cc, 2].mean() / 255,
        }
        if mm_per_px:
            row["area_mm2"] = p.area * mm_per_px ** 2
            row["length_mm"] = maj * mm_per_px
            row["width_mm"] = mino * mm_per_px
        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Haupt-Analyse
# --------------------------------------------------------------------------- #
def analyze_image(img_bgr: np.ndarray, cfg: SegConfig | None = None):
    """Gibt (df, overlay_bgr, summary_dict) zurueck."""
    cfg = cfg or SegConfig()
    mask, ch_name = make_mask(img_bgr, cfg)
    labels = measure.label(mask, connectivity=1)
    labels = _remove_small(labels, cfg.min_area_px)
    labels, _, _ = segmentation.relabel_sequential(labels)

    mm_per_px = cfg.mm_per_px
    ref_info = None
    if cfg.ref_diameter_mm and labels.max() > 0:
        med0 = float(np.median([p.area for p in measure.regionprops(labels)]))
        ref = detect_scale_disc(img_bgr, med0, cfg, ch_name)
        if ref is not None:
            d_px = getattr(ref, "equivalent_diameter_area", None) or ref.equivalent_diameter
            cy, cx = ref.centroid
            mm_per_px = cfg.ref_diameter_mm / d_px
            ref_info = {"ref_diameter_px": float(d_px), "ref_center": (cx, cy)}
            # evtl. in der Kornmaske enthaltene Muenze entfernen
            for p in measure.regionprops(labels):
                if np.hypot(p.centroid[0] - cy, p.centroid[1] - cx) < 0.6 * d_px:
                    labels[labels == p.label] = 0
            labels, _, _ = segmentation.relabel_sequential(labels)

    if labels.max() == 0:
        return pd.DataFrame(), img_bgr.copy(), {"n_grains": 0, "channel": ch_name}

    med_area, r_single = robust_single_stats(labels)
    labels, split_ids = split_clusters(mask, labels, med_area, r_single, cfg)

    df = extract_features(img_bgr, labels, split_ids, med_area, mm_per_px)
    # Rauschen raus (relativ zur Median-Kornflaeche)
    df = df[df["area_px"] >= cfg.min_rel_area * med_area].copy()
    if cfg.drop_border:
        df = df[~df["touches_border"]].copy()
    df = df.reset_index(drop=True)

    summary = {
        "n_grains": int(len(df)),
        "n_grains_blob_corrected": int(df["n_est_blob"].sum()) if len(df) else 0,
        "n_split": int(df["was_split"].sum()) if len(df) else 0,
        "median_area_px": float(df["area_px"].median()) if len(df) else np.nan,
        "area_cv_pct": float(df["area_px"].std() / df["area_px"].mean() * 100) if len(df) > 1 else np.nan,
        "channel": ch_name,
        "mm_per_px": mm_per_px,
        "ref_found": ref_info is not None,
    }
    if mm_per_px and len(df):
        summary.update({
            "mean_length_mm": float(df["length_mm"].mean()),
            "mean_width_mm": float(df["width_mm"].mean()),
            "mean_area_mm2": float(df["area_mm2"].mean()),
        })
    overlay = draw_overlay(img_bgr, labels, df, summary)
    return df, overlay, summary


def draw_overlay(img_bgr: np.ndarray, labels: np.ndarray, df: pd.DataFrame, summary: dict) -> np.ndarray:
    ov = img_bgr.copy()
    keep = set(df["grain_id"]) if len(df) else set()
    status = dict(zip(df["grain_id"], zip(df["was_split"], df["n_est_blob"]))) if len(df) else {}
    for gid in keep:
        m = (labels == gid).astype(np.uint8)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        was_split, n_est = status[gid]
        color = (0, 200, 0)              # gruen: einzelnes Korn
        if was_split:
            color = (0, 165, 255)        # orange: per Watershed getrennt
        if n_est > 1:
            color = (0, 0, 255)          # rot: ungeloester Cluster
        cv2.drawContours(ov, cnts, -1, color, 2)
    txt = f"n={summary['n_grains']} (blob-korr. {summary.get('n_grains_blob_corrected', '-')})"
    cv2.rectangle(ov, (5, 5), (5 + 11 * len(txt), 38), (255, 255, 255), -1)
    cv2.putText(ov, txt, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
    return ov


# --------------------------------------------------------------------------- #
# TKM-Schaetzung
# --------------------------------------------------------------------------- #
def calibrate_mass_factor(df: pd.DataFrame, total_mass_g: float,
                          col: str = "area_mm2", power: float = 1.5) -> float:
    """
    Modell Einzelkornmasse m_i = k * A_i^power (Volumen ~ Flaeche^1.5).
    k wird so kalibriert, dass Summe(m_i) = gewogene Gesamtmasse (nur Einzelkoerner).
    Rueckgabe: k in g / mm^(2*power).
    """
    d = df[df["n_est_blob"] == 1]
    return total_mass_g / float((d[col] ** power).sum())


def estimate_tkm(df: pd.DataFrame, k: float, col: str = "area_mm2", power: float = 1.5):
    """TKM [g] mit Bootstrap-95%-KI aus dem kalibrierten Flaechenmodell."""
    from tkm_utils import bootstrap_ci
    d = df[df["n_est_blob"] == 1]
    m_g = k * d[col] ** power
    mean_g, lo, hi = bootstrap_ci(m_g.values)
    return mean_g * 1000, lo * 1000, hi * 1000


# --------------------------------------------------------------------------- #
# Aggregation: ein Feature-Vektor je Bild/Probe (Eingabe fuer Regression auf TKM)
# --------------------------------------------------------------------------- #
def aggregate_image_features(df: pd.DataFrame) -> dict:
    """Aggregiert Einzelkorn-Features zu einer Zeile je Bild (nur Einzelkoerner, n_est_blob == 1)."""
    if len(df) == 0:
        return {}
    d = df[df["n_est_blob"] == 1]
    if len(d) == 0:
        d = df
    out = {"n_objects": int(len(df)), "n_single": int(len(d)),
           "n_blob_corrected": int(df["n_est_blob"].sum())}
    cols = [c for c in ["area_mm2", "length_mm", "width_mm", "area_px", "major_px", "minor_px",
                        "aspect", "solidity", "circularity", "L", "a", "b", "hue", "sat", "val"]
            if c in d.columns]
    for c in cols:
        out[f"{c}_mean"] = float(d[c].mean())
        out[f"{c}_std"] = float(d[c].std())
        out[f"{c}_p10"] = float(d[c].quantile(0.10))
        out[f"{c}_p90"] = float(d[c].quantile(0.90))
    if "area_mm2" in d.columns:
        out["area15_mean"] = float((d["area_mm2"] ** 1.5).mean())            # Volumen-Proxy A^1.5
        out["lw2_mean"] = float((d["length_mm"] * d["width_mm"] ** 2).mean())  # Ellipsoid-Proxy L*W^2
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Koerner segmentieren und vermessen")
    ap.add_argument("--input", required=True, help="Bild oder Ordner")
    ap.add_argument("--out", default="../outputs/seg")
    ap.add_argument("--mm-per-px", type=float, default=None)
    ap.add_argument("--ref-diameter-mm", type=float, default=None)
    ap.add_argument("--channel", default="auto")
    ap.add_argument("--method", default="otsu", choices=["otsu", "adaptive", "fixed"])
    ap.add_argument("--no-watershed", action="store_true")
    ap.add_argument("--flatfield", action="store_true")
    ap.add_argument("--keep-border", action="store_true")
    a = ap.parse_args()

    cfg = SegConfig(channel=a.channel, method=a.method, mm_per_px=a.mm_per_px,
                    ref_diameter_mm=a.ref_diameter_mm, watershed=not a.no_watershed,
                    flatfield=a.flatfield, drop_border=not a.keep_border)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    all_rows, summaries = [], []
    for f in list_images(a.input):
        img = read_image(f)
        df, ov, s = analyze_image(img, cfg)
        write_image(out / f"{f.stem}_overlay.png", ov)
        if len(df):
            df.insert(0, "image", f.name)
            all_rows.append(df)
        s["image"] = f.name
        s.update(aggregate_image_features(df))
        summaries.append(s)
        print(f"{f.name}: n={s['n_grains']} (blob-korr. {s.get('n_grains_blob_corrected')}), "
              f"Kanal={s['channel']}, mm/px={s.get('mm_per_px')}")
    if all_rows:
        pd.concat(all_rows).to_csv(out / "grains.csv", index=False)
    pd.DataFrame(summaries).to_csv(out / "summary.csv", index=False)  # = Bild-Feature-Tabelle
    print(f"-> {out.resolve()}")


if __name__ == "__main__":
    main()
