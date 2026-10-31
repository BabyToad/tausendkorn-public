"""Verification pass: show the model its own marks and let it correct them.

For every tile of a points result, the crop (core + halo) is rendered with the current
marks numbered. The model gets the purpose and the counting rules in plain language and
answers which kernels lack a mark, which marks are wrong or duplicated, how confident it
is, and anything it noticed. Only changes inside the tile's core are applied, so every
kernel still has exactly one owner.

    uv run python -m tausendkorn.verify runs/vlm/points-g0/argon/<image>.json --model argon
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import ImageDraw

from tausendkorn.adaptive import kernel_length_px
from tausendkorn.bench_vlm import DEDUP, MODELS, RUNS, USAGE, cost, dedup, log_call, valid_points
from tausendkorn.eval import load_image, load_split
from tausendkorn.match import match
from tausendkorn.tiles import in_core

PROMPT = """You are checking a kernel count for a farmer. The farmer photographed a sample of \
cereal kernels spread on a white A4 sheet; from the exact number of kernels and the sample's \
weight they compute the thousand-kernel weight and from that how many kg of seed per hectare \
to drill. One kernel more or less shifts the result, so precision matters more than speed.

Counting rules: every intact kernel counts, including small or shrivelled ones; barley and \
oats count with their husk; two kernels stuck together count as two. Broken pieces, chaff, \
awns, straw, stones, dust and foreign seeds never count.

This crop shows part of the sheet. The red rectangle is the region you are responsible for; \
the area around it is context only. Every coloured circle with a number is a kernel centre \
that a first pass detected. Please check the red rectangle carefully, kernel by kernel:
1. Intact kernels whose centre is inside the red rectangle but which have NO marker.
2. Markers that are wrong: on a broken piece, chaff, awn, paper or shadow, or a second \
marker on a kernel that already has one.
3. How confident you are that, after your corrections, the rectangle is counted exactly.
4. Anything a farmer or developer should know (photo quality, touching clusters, debris).

Answer with a short reasoning, then a last line exactly of the form
VERIFY: {"add": [[y, x], ...], "remove": [numbers], "confidence": 0.0-1.0, "comment": "..."}
where y and x are normalised to 0-1000 relative to this whole crop image (0,0 = top left)."""


def render(image, crop, core, marks) -> "Image":
    tile = image.crop(crop)
    d = ImageDraw.Draw(tile)
    rel = (core[0] - crop[0], core[1] - crop[1], core[2] - crop[0], core[3] - crop[1])
    d.rectangle(rel, outline=(255, 0, 0), width=4)
    r = max(6, int(max(tile.size) / 90))
    for n, (x, y) in marks:
        x, y = x - crop[0], y - crop[1]
        d.ellipse([x - r, y - r, x + r, y + r], outline=(0, 140, 255), width=3)
        d.text((x + r + 2, y - r), str(n), fill=(0, 60, 200), font_size=int(r * 1.8))
    return tile


def parse_verify(text: str) -> dict | None:
    if "VERIFY:" not in text:
        return None
    tail = text.rsplit("VERIFY:", 1)[1]
    start = tail.find("{")
    try:
        obj, _ = json.JSONDecoder().raw_decode(tail[start:])
    except (ValueError, json.JSONDecodeError):
        return None
    # All four fields must be present and well-formed; otherwise the tile is retried and,
    # if it never validates, keeps its first-pass marks and is flagged for checking.
    if not isinstance(obj, dict) or not {"add", "remove", "confidence"} <= obj.keys():
        return None
    add = valid_points(obj["add"])
    conf = obj["confidence"]
    if add is None or not isinstance(obj["remove"], list) or \
            not all(isinstance(n, int) and not isinstance(n, bool) for n in obj["remove"]) or \
            not isinstance(conf, (int, float)) or isinstance(conf, bool) or not 0 <= conf <= 1:
        return None
    return dict(obj, add=add)


def verify_points(res: dict, image, model: str = "argon", below: float = 1.01,
                  workers: int = 16) -> tuple[list, list, int, float]:
    """Second look at tiles below a confidence; returns points, notes, tiles checked, cost."""
    W, H = image.size
    points = [list(p) for p in res["points"]]
    numbered = list(enumerate(points, 1))
    used0 = {m: list(v) for m, v in USAGE.items()}

    jobs = []
    for t in res["tiles"]:
        if (t.get("confidence") if t.get("confidence") is not None else 0) >= below:
            continue
        core = t["core"]
        halo = int(0.35 * max(core[2] - core[0], core[3] - core[1]))
        crop = (max(core[0] - halo, 0), max(core[1] - halo, 0),
                min(core[2] + halo, W), min(core[3] + halo, H))
        marks = [(n, p) for n, p in numbered
                 if crop[0] <= p[0] < crop[2] and crop[1] <= p[1] < crop[3]]
        jobs.append((t, core, crop, marks))

    def work(job):
        t, core, crop, marks = job
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verify.jpg"
            render(image, crop, core, marks).save(path, quality=92)
            for attempt in range(3):
                t0 = time.perf_counter()
                text = MODELS[model](path, PROMPT)
                v = parse_verify(text)
                if v and not set(v["remove"]) <= {n for n, _ in marks}:
                    v = None  # refers to markers that are not in this crop: retry
                log_call(model=model, mode="verify", image=res["file_name"], tile=str(core),
                         attempt=attempt, status="ok" if v else "parse_fail",
                         seconds=round(time.perf_counter() - t0, 1), truth=t.get("truth"),
                         detail=None if v else text[-200:])
                if v:
                    return job, v
        return job, None

    removed, added, notes = set(), [], []
    with ThreadPoolExecutor(workers) as ex:
        for (t, core, crop, marks), v in ex.map(work, jobs):
            if v is None:
                notes.append({"core": core, "failed": True})
                continue
            owned = {n for n, p in marks if in_core([p], core)}
            removed |= {int(n) for n in v.get("remove", []) if int(n) in owned}
            cw, ch = crop[2] - crop[0], crop[3] - crop[1]
            for y, x in v.get("add", []):
                p = [crop[0] + x / 1000 * cw, crop[1] + y / 1000 * ch]
                if in_core([p], core):
                    added.append(p)
            notes.append({"core": core, "truth": t.get("truth"), "confidence": v.get("confidence"),
                          "comment": v.get("comment"), "added": len(v.get("add", [])),
                          "removed": len(v.get("remove", []))})

    new_points = dedup([p for n, p in numbered if n not in removed] + added,
                       DEDUP * kernel_length_px(image))
    spent = sum(cost(m, [v[0] - used0.get(m, [0, 0])[0], v[1] - used0.get(m, [0, 0])[1]])
                for m, v in USAGE.items())
    return new_points, notes, len(jobs), spent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("result", help="points result JSON from bench_vlm")
    ap.add_argument("--model", default="argon")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--below", type=float, default=1.01,
                    help="only verify tiles whose first-pass confidence is below this")
    args = ap.parse_args()

    res = json.loads(Path(args.result).read_text())
    row = next(r for r in load_split("train") if r["file_name"] == res["file_name"])
    image = load_image(row["path"])
    points = res["points"]
    new_points, notes, n_jobs, spent = verify_points(res, image, args.model, args.below, args.workers)
    m = match(new_points, row["kernel_points"])
    before = match(points, row["kernel_points"])
    out = dict(res, model=f"{res['model']}+verify-{args.model}", mode="verify",
               points=new_points, pred=len(new_points), notes=notes,
               verified_tiles=n_jobs, cost_usd=round(res.get("cost_usd", 0) + spent, 4),
               **{k: m[k] for k in ("tp", "fp", "fn", "precision", "recall", "radius")})
    outdir = RUNS / f"verify-{res['mode']}-g{res['grid']}" / args.model
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / Path(args.result).name).write_text(json.dumps(out, indent=1))
    print(f"{res['file_name']}: before {len(points)} (FP {before['fp']} FN {before['fn']}) -> "
          f"after {len(new_points)} (FP {m['fp']} FN {m['fn']})  true {res['count']}  "
          f"verified {n_jobs}/{len(res['tiles'])} tiles  total ${res.get('cost_usd', 0) + spent:.3f}")


if __name__ == "__main__":
    main()
