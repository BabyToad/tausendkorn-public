"""
classical_counter.py - Adapter: klassische Pipeline als Zaehler fuer `python -m tausendkorn.eval` (src/tausendkorn/eval.py).

Schnittstelle des Teams: count(image: PIL.Image.Image) -> int | {"count": int, "points": [[x, y], ...]}
Die Punkte liegen im Originalbild (aufrecht), wie die Labels.

    cd <Repo-Wurzel>
    PYTHONPATH=wissensbank/scripts uv run python -m tausendkorn.eval classical_counter:count --split test --name classical-otsu
(opencv-python, scipy, scikit-image, pandas muessen installiert sein: pip install -r wissensbank/requirements.txt)

Einstellungen per Umgebungsvariable: CC_MM_PER_PX (0.15), CC_MARGIN_MM (8), CC_CHANNEL (auto).
"""
from __future__ import annotations

import os
from dataclasses import replace

import cv2
import numpy as np

from a4_sheet import rectify_a4, to_original
from grain_segmentation import SegConfig, analyze_image

_MM = float(os.environ.get("CC_MM_PER_PX", "0.15"))
_MARGIN = float(os.environ.get("CC_MARGIN_MM", "8"))
_CFG = SegConfig(channel=os.environ.get("CC_CHANNEL", "auto"), drop_border=False)


def count(image) -> dict:
    bgr = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    warped, info = rectify_a4(bgr, mm_per_px=_MM, margin_mm=_MARGIN)
    if warped is None:                                          # Blatt nicht gefunden: ganzes Bild, ohne Massstab
        df, _, s = analyze_image(bgr, replace(_CFG, mm_per_px=None))
        pts = df[["cx", "cy"]].to_numpy() if len(df) else np.zeros((0, 2))
    else:
        df, _, s = analyze_image(warped, replace(_CFG, mm_per_px=_MM))
        pts = to_original(df[["cx", "cy"]].to_numpy(), info) if len(df) else np.zeros((0, 2))
    return {"count": int(s["n_grains_blob_corrected"]), "points": pts.round(1).tolist()}
