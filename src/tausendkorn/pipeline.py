"""Frozen counting pipeline v1: one photo in, every kernel out.

1. Density-adaptive tiles over the photo (tausendkorn.adaptive), each with a halo.
2. Gemini 4 Argon marks kernel centres per tile in compact mode plus a confidence.
3. Seam merge between neighbouring tiles and removal of repeated coordinates.
4. Tiles with confidence below VERIFY_BELOW get a second look at their own numbered
   marks (tausendkorn.verify); the model's comments become the "please check" spots.

    uv run python -m tausendkorn.pipeline photo.jpg
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path

from tausendkorn.bench_vlm import run_image
from tausendkorn.eval import load_image
from tausendkorn.verify import verify_points

# Bump whenever behaviour changes; final.py refuses to mix results across versions.
PIPELINE_VERSION = "v1.0.2"
MODEL = "argon"
VERIFY_BELOW = 0.9
WORKERS = 16


class IncompleteCount(RuntimeError):
    """Some tiles got no usable answer; a partial sum would silently undercount."""

    def __init__(self, message: str, cost_usd: float = 0.0):
        super().__init__(message)
        self.cost_usd = cost_usd


def fingerprint() -> str:
    """Hash of the pipeline code: results are only comparable with the same code."""
    h = hashlib.sha256()
    for f in sorted(Path(__file__).parent.glob("*.py")):
        h.update(f.name.encode() + f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def count_kernels(path: str | Path, name: str | None = None) -> dict:
    path = Path(path)
    t0 = time.perf_counter()
    row = {"file_name": name or path.name, "path": path, "species": None, "camera": None,
           "count": 0, "kernel_points": [], "broken_points": [], "invalid_points": []}
    with tempfile.TemporaryDirectory() as tmp:
        first = run_image(row, MODEL, "compact", 0, WORKERS, Path(tmp))
    if first["failed_tiles"]:
        failed = [t for t in first["tiles"] if t["pred"] is None]
        raise IncompleteCount(
            f"{len(failed)} of {len(first['tiles'])} regions could not be counted "
            f"(last answer: {failed[-1].get('tail', '')[-120:]!r}); not returning a partial count",
            cost_usd=first["cost_usd"])
    # A failed second look keeps the first-pass marks and is listed in check_here, so the
    # count stays whole but flagged.
    points, notes, checked, spent = verify_points(first, load_image(path), MODEL, VERIFY_BELOW, WORKERS)
    uncertain = [n for n in notes if n.get("failed") or (n.get("confidence") or 0) < VERIFY_BELOW]
    return {
        "count": len(points),
        "points": points,
        "tiles": len(first["tiles"]),
        "verified_tiles": checked,
        "check_here": [{"region": n["core"], "confidence": n.get("confidence"),
                        "comment": n.get("comment")} for n in uncertain],
        "notes": notes,
        "cost_usd": round(first["cost_usd"] + spent, 4),
        "seconds": round(time.perf_counter() - t0, 1),  # wall time, both passes
        "request_seconds": first["seconds"],  # summed per-tile request time
        "version": PIPELINE_VERSION,
        "fingerprint": fingerprint(),
        "first_pass": {"count": first["pred"], "tiles": first["tiles"]},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("--out")
    args = ap.parse_args()
    res = count_kernels(args.photo)
    text = json.dumps(res, indent=1)
    if args.out:
        Path(args.out).write_text(text)
    print(f"{res['count']} kernels, {res['verified_tiles']}/{res['tiles']} tiles re-checked, "
          f"{len(res['check_here'])} spots to check, ${res['cost_usd']:.3f}")


if __name__ == "__main__":
    main()
