"""Benchmark VLMs on tiled images through subscription CLIs (no API keys).

Each image is cut into a grid of tiles with a red ownership core (tausendkorn.tiles).
Mode `count` asks for a number per tile; mode `points` asks for kernel centres, which
are mapped back, kept only inside the tile's core and matched 1:1 to the labels.

    uv run python -m tausendkorn.bench_vlm --images splits/dev.txt --limit 4 \
        --models astra opus --mode points --grid 8
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tausendkorn.eval import load_image, load_split
from tausendkorn.match import match
from tausendkorn.tiles import in_core, make_tiles

RUNS = Path(__file__).resolve().parents[2] / "runs" / "vlm"

TASK = (
    "This image is a crop of a photo of cereal kernels on white paper. A red rectangle "
    "is drawn on it. Consider only intact cereal kernels whose CENTRE lies inside the red "
    "rectangle; kernels cut by the rectangle edge count only if their centre is inside. "
    "Ignore broken kernel pieces, chaff, awns, stones, dust and other objects. "
    "Work carefully, e.g. row by row. "
)
PROMPTS = {
    "count": TASK + "End your answer with a last line exactly of the form COUNT: <integer>",
    "points": TASK + (
        "Give the centre of every such kernel as [x, y] with x and y normalised to 0-1000 "
        "relative to the whole image (0,0 = top left, 1000,1000 = bottom right). End your "
        "answer with a last line exactly of the form POINTS: [[x, y], [x, y], ...] "
        "(POINTS: [] if there are none)"
    ),
    # Same task, no prose: output tokens dominate the bill. The confidence decides which
    # tiles get the verification pass (tausendkorn.verify --below).
    "compact": (
        "A farmer counts a seed sample to set the seed drill; one kernel more or less "
        "matters. " + TASK +
        "Give the centre of every such kernel as [x, y] with x and y normalised to 0-1000 "
        "relative to the whole image (0,0 = top left). Reply with exactly two lines and "
        "nothing else:\nPOINTS: [[x, y], ...]\nCONFIDENCE: <0.0-1.0 that every kernel in "
        "the rectangle is marked exactly once>"
    ),
}


FOREIGN_TYPES = ["Spreu", "Granne", "Stein", "Fremdsame", "Sonstiges"]

# v1.1 experiment: same kernel task plus broken pieces and foreign material in one call.
# Coordinates are asked as [y, x] for every model (Gemini's native order); swap_points
# only rewrites POINTS lines, so these pass through unchanged and are swapped on parse.
PROMPTS["classes"] = (
    "A farmer checks a seed sample to set the seed drill; one kernel more or less "
    "matters, and so does how much broken grain and foreign material is in it. "
    "This image is a crop of a photo of cereal kernels on white paper. A red rectangle "
    "is drawn on it. Consider only objects whose CENTRE lies inside the red rectangle; "
    "objects cut by the rectangle edge count only if their centre is inside. "
    "Classify every object: KERNELS = intact cereal kernels (also small or shrivelled; "
    "husked barley/oats count; two stuck together are two). BROKEN = broken kernel "
    "pieces (clearly less than a whole kernel). FOREIGN = anything else that is not "
    "paper: chaff/husk without kernel (Spreu), awns or straw (Granne), stones (Stein), "
    "seeds of other plants (Fremdsame), dust or other things (Sonstiges). "
    "Give centres as [y, x] normalised to 0-1000 relative to the whole image "
    "(0,0 = top left). Reply with exactly four lines and nothing else:\n"
    "KERNELS: [[y, x], ...]\nBROKEN: [[y, x], ...]\n"
    'FOREIGN: [[y, x, "Spreu|Granne|Stein|Fremdsame|Sonstiges"], ...]\n'
    "CONFIDENCE: <0.0-1.0 that every kernel in the rectangle is marked exactly once>"
)


def _parse_list(text: str, key: str):
    """The JSON list directly after the last `key`, or None (same rule as parse_points)."""
    if key not in text:
        return None
    tail = text.rsplit(key, 1)[1].lstrip()
    if not tail.startswith("["):
        return None
    try:
        val, _ = json.JSONDecoder().raw_decode(tail)
    except json.JSONDecodeError:
        return None
    return val if isinstance(val, list) else None


def parse_classes(text: str) -> dict | None:
    """KERNELS/BROKEN/FOREIGN lines -> points as [x, y] (FOREIGN keeps its type).

    All three lists are required and validated like valid_points; one malformed entry
    rejects the whole answer, so the tile is retried instead of silently losing kernels.
    """
    kernels, broken = _parse_list(text, "KERNELS:"), _parse_list(text, "BROKEN:")
    foreign_raw = _parse_list(text, "FOREIGN:")
    if foreign_raw is None or not all(isinstance(p, list) and len(p) == 3 and
                                      isinstance(p[2], str) for p in foreign_raw):
        return None
    kernels, broken = valid_points(kernels), valid_points(broken)
    foreign = valid_points([p[:2] for p in foreign_raw])
    if kernels is None or broken is None or foreign is None:
        return None
    kinds = [p[2] if p[2] in FOREIGN_TYPES else "Sonstiges" for p in foreign_raw]
    return {"kernels": [[x, y] for y, x in kernels], "broken": [[x, y] for y, x in broken],
            "foreign": [[x, y, k] for (y, x), k in zip(foreign, kinds)]}


def parse_confidence(text: str) -> float | None:
    m = re.findall(r"CONFIDENCE:\s*(-?\d+(?:\.\d+)?)(?![\d.eE])", text)
    if not m:
        return None
    c = float(m[-1])
    return c if 0 <= c <= 1 else None  # out of range counts as missing -> verified


def run_claude(model: str, image: Path, prompt: str) -> str:
    # --allowedTools is variadic, so the prompt goes through stdin.
    cmd = [shutil.which("claude"), "-p", "--model", model, "--allowedTools", "Read"]
    return subprocess.run(cmd, input=f"{prompt}\n\nRead the image file at {image}",
                          capture_output=True, text=True, encoding="utf-8",
                          timeout=900).stdout


def run_codex(model: str, image: Path, prompt: str, effort: str = "medium") -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "last.txt"
        cmd = [shutil.which("codex"), "exec", "--skip-git-repo-check", "-s", "read-only",
               "-m", model, "-c", f"model_reasoning_effort={effort}", "-i", str(image),
               "-o", str(out), "-"]
        subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                       timeout=900)
        return out.read_text(encoding="utf-8") if out.exists() else ""


def run_gemini(model: str, image: Path, prompt: str, thinking: str | None = None) -> str:
    import base64
    import urllib.request

    import keyring

    key = keyring.get_password("tokenkit", "GEMINI_API_KEY")
    if not key:  # fail once, loudly, instead of one HTTP error per tile
        raise RuntimeError("GEMINI_API_KEY missing: uvx keyring set tokenkit GEMINI_API_KEY")

    # Gemini points natively as [y, x] on 0-1000; ask in that convention, swap on parse.
    prompt = prompt.replace("[x, y] with x and y", "[y, x] with y and x").replace(
        "POINTS: [[x, y], [x, y], ...]", "POINTS: [[y, x], [y, x], ...]").replace(
        "POINTS: [[x, y], ...]", "POINTS: [[y, x], ...]")
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "image/jpeg",
                         "data": base64.b64encode(image.read_bytes()).decode()}},
        {"text": prompt}]}]}
    if thinking:  # Flash models think a lot by default; thinking tokens bill as output
        body["generationConfig"] = {"thinkingConfig": {"thinkingLevel": thinking}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": key})
    for attempt in range(4):
        try:
            res = json.load(urllib.request.urlopen(req, timeout=600))
            u = res.get("usageMetadata", {})
            with _log_lock:  # billed output includes thinking tokens
                USAGE[model][0] += u.get("promptTokenCount", 0)
                USAGE[model][1] += u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
            cand = res["candidates"][0]
            if cand.get("finishReason", "STOP") != "STOP":  # truncated or blocked answer
                return f"ERROR finishReason={cand.get('finishReason')}"
            text = "".join(p.get("text", "") for p in cand["content"]["parts"])
            return swap_points(text)
        except Exception as e:  # rate limits and transient errors: back off and retry
            err = repr(e)
            time.sleep(5 * 2 ** attempt)
    return f"ERROR {err}"


def _post(url: str, body: dict, headers: dict) -> dict:
    import urllib.request

    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    for attempt in range(5):
        try:
            return json.load(urllib.request.urlopen(req, timeout=900))
        except Exception as e:  # rate limits and overload: back off and retry
            err = e
            time.sleep(5 * 2 ** attempt)
    raise err


def run_anthropic(model: str, image: Path, prompt: str) -> str:
    import base64

    import keyring

    body = {"model": model, "max_tokens": 16000, "messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.b64encode(image.read_bytes()).decode()}},
        {"type": "text", "text": prompt}]}]}
    try:
        res = _post("https://api.anthropic.com/v1/messages", body, {
            "x-api-key": keyring.get_password("tokenkit", "ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01"})
    except Exception as e:
        return f"ERROR {e!r}"
    return "".join(b.get("text", "") for b in res["content"])


def run_openai(model: str, image: Path, prompt: str, effort: str = "medium") -> str:
    import base64

    import keyring

    url = "data:image/jpeg;base64," + base64.b64encode(image.read_bytes()).decode()
    body = {"model": model, "reasoning": {"effort": effort}, "input": [{"role": "user", "content": [
        {"type": "input_image", "image_url": url, "detail": "high"},
        {"type": "input_text", "text": prompt}]}]}
    try:
        res = _post("https://api.openai.com/v1/responses", body, {
            "Authorization": "Bearer " + keyring.get_password("tokenkit", "OPENAI_API_KEY")})
    except Exception as e:
        return f"ERROR {e!r}"
    return "".join(c.get("text", "") for item in res.get("output", [])
                   if item.get("type") == "message" for c in item.get("content", []))


def swap_points(text: str) -> str:
    pts = parse_points(text)
    if pts is None:
        return text
    return text + "\nPOINTS: " + json.dumps([[x, y] for y, x in pts])


MODELS = {
    "api-astra": lambda p, q: run_openai("gpt-6-astra", p, q),
    "api-sol": lambda p, q: run_openai("gpt-6.1-sol", p, q),
    "api-opus": lambda p, q: run_anthropic("claude-opus-5-5", p, q),
    "api-fable": lambda p, q: run_anthropic("claude-fable-5-1", p, q),
    "api-sonnet": lambda p, q: run_anthropic("claude-sonnet-5-5", p, q),
    "argon": lambda p, q: run_gemini("gemini-4-argon", p, q),
    "flash": lambda p, q: run_gemini("gemini-3.8-flash", p, q),
    "flash-low": lambda p, q: run_gemini("gemini-3.8-flash", p, q, thinking="low"),
    "lite35": lambda p, q: run_gemini("gemini-3.5-flash-lite", p, q),
    "lite31": lambda p, q: run_gemini("gemini-3.1-flash-lite", p, q),
    "lite25": lambda p, q: run_gemini("gemini-2.5-flash-lite", p, q),
    "flash35-low": lambda p, q: run_gemini("gemini-3.5-flash", p, q, thinking="low"),
    "flash36-low": lambda p, q: run_gemini("gemini-3.6-flash", p, q, thinking="low"),
    "opus": lambda p, q: run_claude("opus", p, q),
    "fable": lambda p, q: run_claude("fable", p, q),
    "sonnet": lambda p, q: run_claude("sonnet", p, q),
    "astra": lambda p, q: run_codex("gpt-6-astra", p, q),
    "sol": lambda p, q: run_codex("gpt-5.6-sol", p, q),
}


def parse_count(text: str) -> int | None:
    m = re.findall(r"COUNT:\s*(\d+)", text)
    return int(m[-1]) if m else None


def parse_points(text: str) -> list[list[float]] | None:
    if "POINTS:" not in text:
        return None
    tail = text.rsplit("POINTS:", 1)[1].lstrip()
    if not tail.startswith("["):  # the list must follow directly, not be dug out of JSON
        return None
    start = 0
    try:
        pts, _ = json.JSONDecoder().raw_decode(tail[start:])
    except json.JSONDecodeError:
        return None
    return valid_points(pts)


def valid_points(pts) -> list[list[float]] | None:
    """Accept only a list of [a, b] pairs of finite numbers on the 0-1000 scale.

    Anything malformed (wrong shape, strings, NaN, far out of range) rejects the whole
    answer so the tile is retried instead of silently losing or inventing kernels.
    """
    if not isinstance(pts, list):
        return None
    out = []
    for p in pts:
        if not (isinstance(p, list) and len(p) == 2 and
                all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in p)):
            return None
        if not all(math.isfinite(v) and -50 <= v <= 1050 for v in p):
            return None
        out.append([float(p[0]), float(p[1])])
    return out


_log_lock = threading.Lock()
# Token totals per Gemini model and list prices (USD per 1M in/out, Argon promo to 30.11.).
USAGE: dict = defaultdict(lambda: [0, 0])
# Lite and 3.6 Flash prices checked on ai.google.dev/gemini-api/docs/pricing (27.10.);
# 3.5 Flash is no longer listed there, 2.5 Flash-Lite answers 404.
PRICES = {"gemini-4-argon": (2.0, 10.0), "gemini-3.8-flash": (0.75, 3.75),
          "gemini-3.5-flash": (1.5, 9.0), "gemini-3.5-flash-lite": (0.30, 2.50),
          "gemini-3.1-flash-lite": (0.25, 1.50), "gemini-2.5-flash-lite": (0.10, 0.40),
          "gemini-3.6-flash": (0.75, 3.75)}


def cost(model: str, tokens) -> float:
    p_in, p_out = PRICES.get(model, (0.0, 0.0))
    return (tokens[0] * p_in + tokens[1] * p_out) / 1e6


def log_call(**rec) -> None:
    """Append one line per model call to runs/vlm/calls.jsonl (see tausendkorn.status)."""
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    RUNS.mkdir(parents=True, exist_ok=True)
    with _log_lock, open(RUNS / "calls.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def seam_merge(points: list, length: float) -> list:
    """Merge duplicates from neighbouring tiles near their shared edge.

    Each tile keeps points up to a margin beyond its core, so a kernel on a seam is
    usually reported by both neighbours. A margin point and a point from another tile
    closer than ~half a kernel length are one kernel (averaged). Two points that each
    lie in their own tile's core are distinct kernels by ownership and never merge,
    even when close (narrow oats side by side across a seam). A margin point with no
    partner is dropped: the owning tile is responsible for it.
    """
    radius = 0.45 * length
    used, out = set(), []
    order = sorted(range(len(points)), key=lambda i: not points[i]["own"])
    for i in order:
        if i in used:
            continue
        p = points[i]
        partner = None
        for j in range(len(points)):
            q = points[j]
            if j != i and j not in used and q["tile"] != p["tile"] and \
                    not (p["own"] and q["own"]) and \
                    abs(q["x"] - p["x"]) < radius and abs(q["y"] - p["y"]) < radius and \
                    ((q["x"] - p["x"]) ** 2 + (q["y"] - p["y"]) ** 2) ** 0.5 < radius:
                partner = j
                break
        used.add(i)
        if partner is not None:
            used.add(partner)
            q = points[partner]
            out.append([(p["x"] + q["x"]) / 2, (p["y"] + q["y"]) / 2])
        elif p["own"]:
            out.append([p["x"], p["y"]])
    return out


# Models sometimes repeat a coordinate; two real kernel centres are never this close.
# Chosen on dev4 (0.03-0.07 sweep, docs/RESULTS.md); larger values eat parallel oats.
DEDUP = 0.05


def dedup(points: list, radius: float) -> list:
    out: list = []
    for p in points:
        if all(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 >= radius for q in out):
            out.append(p)
    return out


def run_image(row: dict, model: str, mode: str, grid: int, workers: int, tmp: Path) -> dict:
    before = {m: list(v) for m, v in USAGE.items()}
    before = defaultdict(lambda: [0, 0], before)
    image = load_image(row["path"])
    if grid == 0:  # density-adaptive quadtree, see tausendkorn.adaptive
        from tausendkorn.adaptive import kernel_length_px, make_adaptive_tiles
        length = kernel_length_px(image)
        source = ((r, c, core, crop, tile) for r, c, core, crop, tile, _ in make_adaptive_tiles(image))
    else:
        length = None
        source = make_tiles(image, grid)
    tiles = []
    for r, c, core, crop, tile in source:
        truth = in_core(row["kernel_points"], core)
        # Skip tiles that are both label-empty and visually blank paper would be cheating;
        # every tile is sent, so the method has to handle empty paper itself.
        path = tmp / f"tile_{r:02d}{c:02d}.jpg"
        tile.save(path, quality=92)
        tiles.append({"path": path, "core": core, "crop": crop, "truth": truth})

    parse = {"count": parse_count, "classes": parse_classes}.get(mode, parse_points)
    prompt = PROMPTS[mode]
    if mode != "count" and length is not None:
        prompt = prompt.replace(
            "Give the centre of every such kernel",
            "Also include kernels whose centre lies just outside the red rectangle, within "
            "about half a kernel length of its edge (neighbouring crops overlap there and "
            "duplicates are merged later). Give the centre of every such kernel").replace(
            "Give centres as",
            "For KERNELS also include kernels whose centre lies just outside the red "
            "rectangle, within about half a kernel length of its edge (neighbouring crops "
            "overlap there and duplicates are merged later). Give centres as")

    def work(t):
        t0 = time.perf_counter()
        for attempt in range(3):  # empty or unparsable answers get two more tries
            a0 = time.perf_counter()
            try:
                text = MODELS[model](t["path"].resolve(), prompt)
                status = "ok" if parse(text) is not None else (
                    "error" if text.startswith("ERROR") or not text.strip() else "parse_fail")
            except Exception as e:
                text, status = f"ERROR {e!r}", "exception"
            log_call(model=model, mode=mode, image=row["file_name"], tile=t["path"].stem,
                     attempt=attempt, status=status, seconds=round(time.perf_counter() - a0, 1),
                     truth=t["truth"], detail=None if status == "ok" else text[-200:])
            if status == "ok":
                break
        return t, text, round(time.perf_counter() - t0, 1)

    out_tiles, points, broken, foreign = [], [], [], []
    with ThreadPoolExecutor(workers) as ex:
        for t, text, secs in ex.map(work, tiles):
            rec = {"core": t["core"], "truth": t["truth"], "seconds": secs}
            if mode == "count":
                rec["pred"] = parse_count(text)
            else:
                cw, ch = t["crop"][2] - t["crop"][0], t["crop"][3] - t["crop"][1]
                if mode == "classes":
                    c = parse_classes(text)
                    pts = None if c is None else c["kernels"]
                    if c is not None:  # extra classes: owned by the core only, no seam merge
                        for x, y, *kind in c["broken"] + c["foreign"]:
                            q = [t["crop"][0] + x / 1000 * cw, t["crop"][1] + y / 1000 * ch]
                            if in_core([q], t["core"]):
                                (foreign if kind else broken).append(q + kind)
                else:
                    pts = parse_points(text)
                mapped = [[t["crop"][0] + x / 1000 * cw, t["crop"][1] + y / 1000 * ch]
                          for x, y in (pts or [])]
                owned = [p for p in mapped if in_core([p], t["core"])]
                rec["pred"] = None if pts is None else len(owned)
                rec["raw_points"] = None if pts is None else len(pts)
                rec["confidence"] = parse_confidence(text)
                rec["crop"] = t["crop"]
                if length is None:
                    points += owned
                else:  # keep a margin beyond the core for the seam merge
                    m = 0.35 * length
                    x0, y0, x1, y1 = t["core"]
                    points += [{"x": x, "y": y, "tile": str(t["path"].stem),
                                "own": in_core([[x, y]], t["core"])}
                               for x, y in mapped
                               if x0 - m <= x < x1 + m and y0 - m <= y < y1 + m]
            if rec["pred"] is None:
                rec["tail"] = text[-300:]
            out_tiles.append(rec)

    failed = sum(t["pred"] is None for t in out_tiles)
    total = sum(t["pred"] or 0 for t in out_tiles)
    if mode != "count" and length is not None:
        points = dedup(seam_merge(points, length), DEDUP * length)
        total = len(points)
    result = {"file_name": row["file_name"], "species": row["species"], "camera": row["camera"],
              "model": model, "mode": mode, "grid": grid, "count": row["count"],
              "n_points": len(row["kernel_points"]), "pred": total, "failed_tiles": failed,
              "tile_mae": sum(abs((t["pred"] or 0) - t["truth"]) for t in out_tiles) / len(out_tiles),
              "seconds": sum(t["seconds"] for t in out_tiles), "tiles": out_tiles}
    spent = {m: [USAGE[m][0] - before[m][0], USAGE[m][1] - before[m][1]] for m in USAGE}
    result["tokens"] = spent
    result["cost_usd"] = round(sum(cost(m, v) for m, v in spent.items()), 4)
    if mode != "count":
        m = match(points, row["kernel_points"])
        result.update({k: m[k] for k in ("tp", "fp", "fn", "precision", "recall", "radius")})
        result["points"] = points
    if mode == "classes":
        r = DEDUP * (length or 50)
        result["broken"], result["foreign"] = dedup(broken, r), dedup(foreign, r)
        for key, pred, labels in (("broken", result["broken"], row.get("broken_points")),
                                  ("foreign", [p[:2] for p in result["foreign"]],
                                   row.get("invalid_points"))):
            if labels is not None:  # labels are sparse (0-9 per dev image)
                mm = match(pred, labels, m["radius"])
                result[f"{key}_eval"] = {k: mm[k] for k in ("tp", "fp", "fn")} | {
                    "labels": len(labels)}
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, help="splits/<name>.txt")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--models", nargs="+", default=["astra"])
    ap.add_argument("--mode", choices=PROMPTS, default="points")
    ap.add_argument("--grid", type=int, default=8)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    names = Path(args.images).read_text().split()[: args.limit]
    rows = {r["file_name"]: r for r in load_split("train")}
    for model in args.models:
        outdir = RUNS / f"{args.mode}-g{args.grid}" / model
        outdir.mkdir(parents=True, exist_ok=True)
        for name in names:
            out = outdir / (name.replace("/", "__") + ".json")
            if out.exists():
                continue
            with tempfile.TemporaryDirectory() as tmp:
                res = run_image(rows[name], model, args.mode, args.grid, args.workers, Path(tmp))
            out.write_text(json.dumps(res, indent=1))
            extra = (f"  P={res['precision']:.3f} R={res['recall']:.3f}"
                     if args.mode != "count" else "")
            print(f"{model:6s} {name}: {res['pred']} vs {res['count']} ${res['cost_usd']:.3f} "
                  f"({res['pred'] - res['count']:+d}) tileMAE {res['tile_mae']:.2f} "
                  f"failed {res['failed_tiles']}{extra}", flush=True)


if __name__ == "__main__":
    main()
