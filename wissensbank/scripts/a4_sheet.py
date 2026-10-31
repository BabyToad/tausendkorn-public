"""
a4_sheet.py - A4-Blatt im Foto finden, entzerren, Massstab ableiten.

Die corn1000-Fotos zeigen Koerner auf einem weissen A4-Blatt (210 x 297 mm) vor dunklem/kontrastreichem
Untergrund. Das Blatt liefert den Massstab (mm/px) und schneidet den Hintergrund weg.

    warped, info = rectify_a4(img_bgr)           # None-Info, falls kein Blatt gefunden
    info["H"]            3x3 Homographie Original -> entzerrt
    info["mm_per_px"]    Massstab im entzerrten Bild
    to_original(pts, info)   Punkte aus dem entzerrten Bild ins Originalbild zurueckrechnen
"""
from __future__ import annotations

import cv2
import numpy as np

A4_W_MM, A4_H_MM = 210.0, 297.0


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Sortiert 4 Punkte: oben-links, oben-rechts, unten-rechts, unten-links."""
    pts = np.asarray(pts, np.float32).reshape(4, 2)
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], np.float32)


def find_a4_corners(img_bgr: np.ndarray, min_area_frac: float = 0.15, max_side: int = 1200):
    """
    Findet das hellste grosse Viereck (Papier). Rueckgabe: 4x2 Eckpunkte im Originalmassstab oder None.
    Rechnet auf verkleinertem Bild (schnell); Koerner im Papier stoeren nicht (Kontur wird gefuellt).
    """
    h, w = img_bgr.shape[:2]
    f = min(1.0, max_side / max(h, w))
    small = cv2.resize(img_bgr, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else img_bgr
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (0, 0), 3)
    _, m = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area = None, 0.0
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area_frac * small.shape[0] * small.shape[1] or area <= best_area:
            continue
        hull = cv2.convexHull(c)
        peri = cv2.arcLength(hull, True)
        quad = None
        for eps in (0.02, 0.03, 0.05, 0.08):
            ap = cv2.approxPolyDP(hull, eps * peri, True)
            if len(ap) == 4:
                quad = ap
                break
        if quad is None:                                   # Notnagel: gedrehtes Rechteck
            quad = cv2.boxPoints(cv2.minAreaRect(hull)).reshape(-1, 1, 2)
        q = _order_corners(quad)
        e = [np.linalg.norm(q[i] - q[(i + 1) % 4]) for i in range(4)]
        long_s, short_s = max(e[0], e[2], e[1], e[3]), min(e[0], e[2], e[1], e[3])
        ratio = long_s / max(short_s, 1e-6)
        if not (1.15 <= ratio <= 1.75):                    # A4 = 1,414; Perspektive streut
            continue
        best, best_area = q, area
    return None if best is None else best / f


def rectify_a4(img_bgr: np.ndarray, mm_per_px: float = 0.1, margin_mm: float = 0.0):
    """
    Entzerrt das Blatt auf feste Groesse (Hochformat, 210 x 297 mm). Rueckgabe (bild, info) oder (None, None).
    mm_per_px = 0.1 -> 2100 x 2970 px (reicht fuer ca. 60 px je Kornbreite; kleiner = schneller).
    """
    q = find_a4_corners(img_bgr)
    if q is None:
        return None, None
    e01, e12 = np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[1])
    if e01 > e12:                                          # Blatt liegt quer -> Ecken so rotieren, dass lange Seite vertikal wird
        q = np.roll(q, -1, axis=0)
    W, H = int(round(A4_W_MM / mm_per_px)), int(round(A4_H_MM / mm_per_px))
    dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], np.float32)
    Hm = cv2.getPerspectiveTransform(q.astype(np.float32), dst)
    warped = cv2.warpPerspective(img_bgr, Hm, (W, H), flags=cv2.INTER_AREA if mm_per_px > 0.05 else cv2.INTER_LINEAR)
    if margin_mm > 0:                                      # Papierkante (Schatten, Rand) wegschneiden
        m = int(round(margin_mm / mm_per_px))
        warped = warped[m:H - m, m:W - m]
    return warped, {"H": Hm, "mm_per_px": mm_per_px, "corners": q, "margin_px": int(round(margin_mm / mm_per_px))}


def to_original(points_xy, info) -> np.ndarray:
    """Punkte (N,2) aus dem entzerrten Bild ins Originalbild zurueckrechnen."""
    pts = np.asarray(points_xy, np.float32).reshape(-1, 1, 2)
    if len(pts) == 0:
        return np.zeros((0, 2), np.float32)
    pts = pts + info.get("margin_px", 0)
    inv = np.linalg.inv(info["H"])
    return cv2.perspectiveTransform(pts, inv).reshape(-1, 2)


def to_rectified(points_xy, info) -> np.ndarray:
    """Punkte (N,2) aus dem Originalbild ins entzerrte Bild."""
    pts = np.asarray(points_xy, np.float32).reshape(-1, 1, 2)
    if len(pts) == 0:
        return np.zeros((0, 2), np.float32)
    out = cv2.perspectiveTransform(pts, info["H"]).reshape(-1, 2)
    return out - info.get("margin_px", 0)
