"""Calibrate the photo pre-check thresholds on dev (never holdout/test).

    uv run python -m app.calibrate_precheck            # dev only (docs/PROTOCOL.md)
    uv run python -m app.calibrate_precheck dev train  # wider look, not for thresholds

Prints the metrics per photo, plus the sharpness of artificially blurred copies, so
MIN_SHARPNESS can sit between real photos and blurred ones, and CLUMP_SHARE flags only
the most clumped photos.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import ImageFilter

from app.precheck import measure
from tausendkorn.eval import load_image

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "corn1000" / "data" / "train"


def main() -> None:
    splits = sys.argv[1:] or ["dev"]
    assert not {"holdout", "test"} & set(splits), "holdout/test only with a frozen pipeline"
    names = [l.strip() for f in splits for l in (ROOT / "splits" / f"{f}.txt").read_text().splitlines() if l.strip()]
    rows, blurred = [], []
    for name in names:
        im = load_image(DATA / name)
        m = measure(im)
        rows.append((name, m))
        b = measure(im.filter(ImageFilter.GaussianBlur(radius=max(im.size) / 600)))  # ~2 px at 1200
        blurred.append(b.get("sharpness", 0))
        print(f"{name:55s} sheet={m.get('sheet')} frac={m.get('sheet_fraction')} border={m.get('border')} "
              f"rect={m.get('rectangularity')} aspect={m.get('aspect')} "
              f"sharp={m.get('sharpness')} blur={b.get('sharpness')} est={m.get('kernels_est')} "
              f"clump={m.get('clump_share')} largest={m.get('largest_blob')}", flush=True)
    sharp = np.array([m.get("sharpness", 0) for _, m in rows])
    clump = np.array([m.get("clump_share", 0) for _, m in rows])
    print("sharpness real: min %.1f p5 %.1f median %.1f" % (sharp.min(), np.percentile(sharp, 5), np.median(sharp)))
    print("sharpness blurred: max %.1f p95 %.1f median %.1f" % (max(blurred), np.percentile(blurred, 95), np.median(blurred)))
    print("clump share: median %.2f p80 %.2f p90 %.2f max %.2f" % (np.median(clump), *np.percentile(clump, [80, 90]), clump.max()))
    largest = np.array([m.get("largest_blob", 0) for _, m in rows])
    rect = np.array([m.get("rectangularity", 0) for _, m in rows])
    aspect = np.array([m.get("aspect", 0) for _, m in rows])
    print("largest blob (kernels): median %.0f p80 %.0f p90 %.0f max %.0f" % (np.median(largest), *np.percentile(largest, [80, 90]), largest.max()))
    print("rectangularity: min %.3f p5 %.3f   aspect: min %.3f max %.3f" % (rect.min(), np.percentile(rect, 5), aspect.min(), aspect.max()))
    print("no sheet:", [n for n, m in rows if not m.get("sheet")])


if __name__ == "__main__":
    main()
