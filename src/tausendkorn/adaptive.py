"""Density-adaptive tiling: split the kernel area until each tile holds few kernels.

The colour mask is only a tiling aid: it decides where to cut and how small, never
what the count is. Leaves of a quadtree over the kernel bounding box partition it,
so every kernel centre has exactly one owning core. Each crop adds a halo of about
one kernel length so kernels cut by a core edge are fully visible.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import ImageDraw

WORK = 1200  # long side of the analysis image


def kernel_mask(image) -> tuple[np.ndarray, float]:
    """Binary kernel mask at analysis scale and the scale factor to full resolution."""
    scale = max(image.size) / WORK
    small = np.asarray(image.resize((round(image.size[0] / scale), round(image.size[1] / scale))))
    lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab[..., 0]
    # Paper: the largest bright region, filled so kernels on it are inside.
    bright = (L > np.percentile(L, 60)).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(bright, connectivity=8)
    if n < 2 or stats[1:, cv2.CC_STAT_AREA].max() < 0.05 * bright.size:
        raise ValueError("no white sheet found in the photo")
    paper = (labels == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    hull = cv2.convexHull(cv2.findNonZero(paper))
    inside = np.zeros_like(paper)
    cv2.fillConvexPoly(inside, hull, 1)
    inside = cv2.erode(inside, np.ones((5, 5), np.uint8))
    # Kernels are darker than the paper around them: black-hat (closing minus image) is
    # independent of slow lighting gradients across the sheet.
    L8 = L.astype(np.uint8)
    blackhat = cv2.morphologyEx(L8, cv2.MORPH_BLACKHAT,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
    vals = blackhat[inside > 0]
    thr, _ = cv2.threshold(vals.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Not clipped to the paper: the paper outline is fragile and losing a kernel is worse
    # than sending an extra tile of background. L>35 drops the marker and black cloth.
    mask = ((blackhat > max(thr, 12)) & (L > 35)).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return mask, scale, inside


A4_MM2 = 210 * 297
KERNEL_MM2 = 20  # projected area of a typical cereal kernel; only sets tile sizes


def kernel_area(inside: np.ndarray) -> float:
    """Kernel area in analysis pixels from the A4 scale (blob sizes split on pale grain)."""
    return KERNEL_MM2 * float(inside.sum()) / A4_MM2


def estimate(mask: np.ndarray, area: float, box) -> float:
    x0, y0, x1, y1 = box
    return float(mask[y0:y1, x0:x1].sum()) / area


def quadtree(mask, area, box, max_k: float, min_side: int, out: list) -> None:
    x0, y0, x1, y1 = box
    est = estimate(mask, area, box)
    if est < 0.05:
        # Looks empty to the mask, but the mask is only a cutting aid: a pale kernel can
        # hide here. Keep the region as one coarse tile so every pixel has an owner.
        out.append((box, est))
        return
    if est <= max_k or min(x1 - x0, y1 - y0) < 2 * min_side:
        out.append((box, est))
        return
    mx, my = (x0 + x1) // 2, (y0 + y1) // 2
    for b in ((x0, y0, mx, my), (mx, y0, x1, my), (x0, my, mx, y1), (mx, my, x1, y1)):
        quadtree(mask, area, b, max_k, min_side, out)


def make_adaptive_tiles(image, max_k: float = 15, halo_kernels: float = 1.0):
    """Yield (r, c, core, crop, tile, est) like tiles.make_tiles, plus the estimate."""
    mask, scale, inside = kernel_mask(image)
    area = kernel_area(inside)
    length = 1.7 * area ** 0.5  # elongated kernel: length from area, analysis pixels
    # Root = the whole photo, so no kernel centre can fall outside every core.
    root = (0, 0, mask.shape[1], mask.shape[0])
    leaves: list = []
    quadtree(mask, area, root, max_k, int(1.2 * length), leaves)
    W, H = image.size
    halo = int(halo_kernels * length * scale)
    for i, (box, est) in enumerate(leaves):
        core = tuple(round(v * scale) for v in box)
        # Anchor outer edges to the real image size; rounding the analysis scale could
        # otherwise leave the last row/column of pixels without an owner.
        core = (core[0], core[1], W if box[2] >= mask.shape[1] else core[2],
                H if box[3] >= mask.shape[0] else core[3])
        crop = (max(core[0] - halo, 0), max(core[1] - halo, 0),
                min(core[2] + halo, W), min(core[3] + halo, H))
        tile = image.crop(crop)
        rel = (core[0] - crop[0], core[1] - crop[1], core[2] - crop[0], core[3] - crop[1])
        ImageDraw.Draw(tile).rectangle(rel, outline=(255, 0, 0), width=4)
        yield i, 0, core, crop, tile, est


def kernel_length_px(image) -> float:
    mask, scale, inside = kernel_mask(image)
    return 1.7 * kernel_area(inside) ** 0.5 * scale
