"""One-to-one matching of predicted kernel centres against labelled points."""

from __future__ import annotations

import math
import statistics

import numpy as np


def nn_spacing(points) -> float:
    """Median nearest-neighbour distance; a kernel-scale yardstick for the radius."""
    if len(points) < 2:
        return 50.0
    # Exact all-pairs search: <=1000 points, so O(n^2) in numpy is cheap. (A grid search
    # that stops at the first occupied ring overestimated spacing and the match radius.)
    p = np.asarray([pt[:2] for pt in points], dtype=float)
    d = np.sqrt(((p[:, None, :] - p[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    return float(statistics.median(d.min(axis=1)))


def match(pred, truth, radius: float | None = None) -> dict:
    """Greedy closest-pair matching within radius (default 0.6 x kernel spacing)."""
    radius = radius or 0.6 * nn_spacing(truth)
    pairs = sorted(
        (math.dist(p, t), i, j)
        for i, p in enumerate(pred)
        for j, t in enumerate(truth)
        if abs(p[0] - t[0]) <= radius and abs(p[1] - t[1]) <= radius
    )
    used_p, used_t = set(), set()
    for d, i, j in pairs:
        if d <= radius and i not in used_p and j not in used_t:
            used_p.add(i)
            used_t.add(j)
    tp = len(used_p)
    return {
        "tp": tp,
        "fp": len(pred) - tp,
        "fn": len(truth) - tp,
        "precision": tp / len(pred) if pred else 1.0,
        "recall": tp / len(truth) if truth else 1.0,
        "radius": radius,
        "missed": [truth[j] for j in range(len(truth)) if j not in used_t],
        "extra": [pred[i] for i in range(len(pred)) if i not in used_p],
    }
