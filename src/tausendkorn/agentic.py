"""Agentic kernel counter: Gemini as an agent with view/mark/remove/overview/submit tools.

Instead of a fixed tile pipeline the model gets the purpose and the counting rules in
plain language, a list of suggested regions (adaptive quadtree cores, no counts) and
tools to look at any part of the photo, set and delete numbered marks, check its own
marks on the image and finally submit a count with its confidence and opinion. The
marks are the prediction; they are matched 1:1 to `kernel_points` afterwards.

    uv run python -m tausendkorn.agentic --images runs/dev4.txt --limit 2
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import time
import urllib.request
from pathlib import Path

from PIL import ImageDraw

from tausendkorn.adaptive import kernel_length_px, make_adaptive_tiles
from tausendkorn.eval import load_image, load_split
from tausendkorn.match import match

RUNS = Path(__file__).resolve().parents[2] / "runs" / "agentic"
PRICE_IN, PRICE_OUT = 2e-6, 10e-6  # USD per token, Gemini 4 Argon
VIEW_PX = 1024  # long side of every image sent to the model
KEEP_IMAGES = 4  # older images in the history are replaced by a note

SYSTEM = """\
You are counting cereal kernels on a photo of a sheet of A4 paper. A farmer has taken a
random sample from a seed bag (a "thousand-kernel sample"); the count together with the
sample weight gives the thousand-kernel weight and from that the seeding rate of the
drill. Every kernel matters: the goal is the exact count, 99.9 % accuracy.

Counting rules (ISO 520):
- Count every intact kernel, including shrivelled or small ones. Barley and oats count
  with their husk.
- Twins (two kernels grown together) count as two.
- Never count broken kernel pieces (clearly less than a whole kernel), chaff, husks
  without a kernel, awns, weed seeds, stones, dust, or office material (paper clips,
  pens, markers, labels).

The photo is {W} x {H} pixels; a kernel is about {L:.0f} px long. Coordinates in tool
arguments and texts are full-image pixels (x to the right, y down) unless stated.

Tools:
- view(x0, y0, x1, y1) or view(region=i): shows that part of the photo enlarged, with
  your existing marks drawn as numbered magenta dots. A region view shows the suggested
  region with a one-kernel halo and its core as a red rectangle.
- mark(view, points): adds kernel centres given as [y, x] normalised 0-1000 relative to
  the image of the view with that id (your usual pointing convention). A point within
  a third of a kernel length of an existing mark is rejected as a likely duplicate
  unless force=true; this protects you from double-marking at region seams.
- remove(ids): deletes marks.
- overview(): the whole sheet downscaled with all marks and the region outlines, plus
  the number of marks per region.
- submit(count, uncertain_regions, comment): ends the task. Your marks are the result;
  count should equal the number of marks unless you deliberately disagree.

{workflow}In the comment of submit, give your honest opinion: how confident you are, where the
hard spots were, and anything about the photo or the task that made counting hard or
that you would change (lighting, layout, rules, tools).

{regions}"""

REGION_WORKFLOW = """Suggested way of working: go through the regions below (they cover every kernel; each
kernel centre lies in exactly one core). For each, view it, mark every kernel whose
centre is inside the red core, then view it again or zoom into dense clusters to check
that every kernel has exactly one dot (touching kernels, twins, kernels lying on top of
each other, kernels at the core edge). You may call several tools in one turn, e.g. view
two regions at once. When done, check the overview for gaps and stray marks. You have a
budget of about {calls} tool calls and ${usd:.0f}; plan for it.

"""
FREE_WORKFLOW = """Choose your own views; squares of about 600-800 px side work well. Let neighbouring
views overlap a little; the duplicate check catches kernels marked twice at a seam.
Mark every kernel in a view, then view it again to check that every kernel has exactly
one dot (touching kernels, twins, kernels lying on top of each other), and zoom into
dense clusters. You may call several tools in one turn. When done, check the overview
for gaps and stray marks. You have a budget of about {calls} tool calls and ${usd:.0f};
plan for it.

"""

TOOLS = [{"functionDeclarations": [
    {"name": "view", "description": "Show part of the photo enlarged with existing marks.",
     "parameters": {"type": "object", "properties": {
         "region": {"type": "integer", "description": "suggested region index"},
         "x0": {"type": "number"}, "y0": {"type": "number"},
         "x1": {"type": "number"}, "y1": {"type": "number"}}}},
    {"name": "mark", "description": "Add kernel centres as [y, x] on 0-1000 relative to a view image.",
     "parameters": {"type": "object", "properties": {
         "view": {"type": "integer", "description": "view id the points refer to"},
         "points": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
         "force": {"type": "boolean", "description": "add even if near an existing mark"}},
         "required": ["view", "points"]}},
    {"name": "remove", "description": "Delete marks by id.",
     "parameters": {"type": "object", "properties": {
         "ids": {"type": "array", "items": {"type": "integer"}}}, "required": ["ids"]}},
    {"name": "overview", "description": "Whole sheet with all marks and per-region mark counts.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "submit", "description": "Finish with the final count, uncertain regions and an opinion.",
     "parameters": {"type": "object", "properties": {
         "count": {"type": "integer"},
         "uncertain_regions": {"type": "array", "items": {"type": "object", "properties": {
             "box": {"type": "array", "items": {"type": "number"}},
             "reason": {"type": "string"}}}},
         "comment": {"type": "string"}}, "required": ["count", "comment"]}},
]}]


def jpeg(image) -> dict:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, "JPEG", quality=90)
    return {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}


class Sheet:
    """The photo, the agent's marks and the views it has seen."""

    def __init__(self, image, regions, length):
        self.image, self.regions, self.length = image, regions, length
        self.marks: dict[int, tuple[float, float]] = {}
        self.next_id = 1
        self.views: dict[int, tuple] = {}

    def region_of(self, p) -> int | None:
        for i, (x0, y0, x1, y1) in enumerate(self.regions):
            if x0 <= p[0] < x1 and y0 <= p[1] < y1:
                return i
        return None

    def view(self, region=None, x0=None, y0=None, x1=None, y1=None):
        W, H = self.image.size
        core = None
        if region is not None:
            if not 0 <= int(region) < len(self.regions):
                return {"error": f"no region {region}"}, None
            core = self.regions[int(region)]
            h = self.length
            box = (core[0] - h, core[1] - h, core[2] + h, core[3] + h)
        elif None in (x0, y0, x1, y1):
            return {"error": "give region or x0, y0, x1, y1"}, None
        else:
            box = (x0, y0, x1, y1)
        box = [max(0, min(box[0], box[2])), max(0, min(box[1], box[3])),
               min(W, max(box[0], box[2])), min(H, max(box[1], box[3]))]
        for a, b in ((0, 2), (1, 3)):  # at least two kernel lengths per side
            lim = W if a == 0 else H
            if box[b] - box[a] < 2 * self.length:
                c = (box[a] + box[b]) / 2
                box[a], box[b] = max(0, c - self.length), min(lim, c + self.length)
        box = [round(v) for v in box]
        crop = self.image.crop(box)
        s = VIEW_PX / max(crop.size)
        crop = crop.resize((round(crop.size[0] * s), round(crop.size[1] * s)))
        d = ImageDraw.Draw(crop)
        if core is not None:
            d.rectangle([(core[0] - box[0]) * s, (core[1] - box[1]) * s,
                         (core[2] - box[0]) * s, (core[3] - box[1]) * s], outline=(255, 0, 0), width=3)
        inside = []
        for i, (x, y) in self.marks.items():
            if box[0] <= x < box[2] and box[1] <= y < box[3]:
                inside.append(i)
                u, v = (x - box[0]) * s, (y - box[1]) * s
                d.ellipse([u - 5, v - 5, u + 5, v + 5], fill=(255, 0, 255), outline=(255, 255, 255))
                d.text((u + 6, v - 7), str(i), fill=(255, 0, 255), font_size=14,
                       stroke_width=2, stroke_fill=(255, 255, 255))
        vid = len(self.views) + 1
        self.views[vid] = tuple(box)
        info = {"view": vid, "box": box, "scale": round(s, 2), "marks_in_view": inside}
        if core is not None:
            info["region"] = int(region)
            info["core"] = list(core)
            info["marks_in_core"] = [i for i in inside if self.region_of(self.marks[i]) == int(region)]
        return info, crop

    def mark(self, view, points, force=False):
        if view not in self.views:
            return {"error": f"unknown view {view}"}
        x0, y0, x1, y1 = self.views[view]
        added, rejected = [], []
        for p in points:
            if not isinstance(p, list) or len(p) < 2:
                continue
            y, x = p[0], p[1]
            fx, fy = x0 + x / 1000 * (x1 - x0), y0 + y / 1000 * (y1 - y0)
            near = min(self.marks, default=None,
                       key=lambda i: math.dist(self.marks[i], (fx, fy)))
            if not force and near is not None and \
                    math.dist(self.marks[near], (fx, fy)) < self.length / 3:
                rejected.append({"point": p, "near_mark": near})
                continue
            self.marks[self.next_id] = (fx, fy)
            added.append(self.next_id)
            self.next_id += 1
        return {"added": added, "rejected_as_duplicate": rejected, "total_marks": len(self.marks)}

    def remove(self, ids):
        gone = [i for i in ids if self.marks.pop(int(i), None) is not None]
        return {"removed": gone, "unknown": [i for i in ids if i not in gone],
                "total_marks": len(self.marks)}

    def overview(self):
        img = self.image.copy()
        d = ImageDraw.Draw(img)
        s = max(img.size) / 1000
        for i, (x0, y0, x1, y1) in enumerate(self.regions):
            d.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=max(1, int(1.5 * s)))
            d.text((x0 + 3 * s, y0 + 2 * s), str(i), fill=(255, 0, 0), font_size=int(12 * s))
        for x, y in self.marks.values():
            d.ellipse([x - 3 * s, y - 3 * s, x + 3 * s, y + 3 * s], fill=(255, 0, 255))
        f = VIEW_PX / max(img.size)
        img = img.resize((round(img.size[0] * f), round(img.size[1] * f)))
        per = {}
        for p in self.marks.values():
            r = self.region_of(p)
            per[r] = per.get(r, 0) + 1
        return {"total_marks": len(self.marks),
                "marks_per_region": {str(k): v for k, v in sorted(per.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))},
                "regions_without_marks": [i for i in range(len(self.regions)) if i not in per]}, img


def gemini(model: str, contents: list, system: str, tools: list, thinking: str | None) -> dict:
    import keyring

    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents, "tools": tools}
    if thinking:
        body["generationConfig"] = {"thinkingConfig": {"thinkingLevel": thinking}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": keyring.get_password("tokenkit", "GEMINI_API_KEY")})
    for attempt in range(6):
        try:
            return json.load(urllib.request.urlopen(req, timeout=600))
        except Exception as e:  # rate limits and transient errors: back off and retry
            err = e
            detail = e.read().decode()[:500] if hasattr(e, "read") else ""
            print(f"  retry {attempt}: {e!r} {detail}", flush=True)
            time.sleep(5 * 2 ** attempt)
    raise err


def prune_images(contents: list) -> None:
    """Keep the newest turn's images plus KEEP_IMAGES older ones; replace the rest by a note.

    The newest turn is never pruned: a turn with six views must show all six.
    """
    seen = 0
    for c in reversed(contents[:-1]):
        for k, part in enumerate(c["parts"]):
            if "inline_data" in part:
                seen += 1
                if seen > KEEP_IMAGES:
                    c["parts"][k] = {"text": "[older image removed to save context; view again if needed]"}


def run_image(row: dict, model: str, max_calls: int, max_usd: float, thinking: str | None,
              trace_path: Path, use_regions: bool = True) -> dict:
    t0 = time.perf_counter()
    image = load_image(row["path"])
    length = kernel_length_px(image)
    regions = [core for _, _, core, *_ in make_adaptive_tiles(image)] if use_regions else []
    sheet = Sheet(image, regions, length)
    workflow = (REGION_WORKFLOW if regions else FREE_WORKFLOW).format(calls=max_calls, usd=max_usd)
    listing = ("Suggested regions (core boxes x0, y0, x1, y1):\n" + "\n".join(
        f"{i}: {list(r)}" for i, r in enumerate(regions)) + "\n") if regions else ""
    system = SYSTEM.format(W=image.size[0], H=image.size[1], L=length, workflow=workflow,
                           regions=listing)
    contents = [{"role": "user", "parts": [
        {"text": "Here is the whole photo. Start counting; finish with submit."},
        jpeg(sheet.overview()[1])]}]
    usage = {"prompt": 0, "output": 0, "thoughts": 0, "cached": 0}
    cost, calls, turns, submitted, warned = 0.0, 0, 0, None, False
    trace = open(trace_path, "w", encoding="utf-8")

    def log(**rec):
        trace.write(json.dumps(rec, ensure_ascii=False) + "\n")
        trace.flush()

    while submitted is None:
        res = gemini(model, contents, system, TOOLS, thinking)
        turns += 1
        um = res.get("usageMetadata", {})
        usage["prompt"] += um.get("promptTokenCount", 0)
        usage["output"] += um.get("candidatesTokenCount", 0)
        usage["thoughts"] += um.get("thoughtsTokenCount", 0)
        usage["cached"] += um.get("cachedContentTokenCount", 0)
        cost = usage["prompt"] * PRICE_IN + (usage["output"] + usage["thoughts"]) * PRICE_OUT
        cand = (res.get("candidates") or [{}])[0]
        content = cand.get("content") or {"role": "model", "parts": []}
        content.setdefault("parts", [])
        content["role"] = "model"
        contents.append(content)
        texts = [p["text"] for p in content["parts"] if "text" in p and not p.get("thought")]
        fcalls = [p["functionCall"] for p in content["parts"] if "functionCall" in p]
        log(turn=turns, cost=round(cost, 4), prompt_tokens=um.get("promptTokenCount"),
            finish=cand.get("finishReason"), text=texts,
            calls=[{"name": f["name"], "args": f.get("args", {})} for f in fcalls])
        print(f"  turn {turns:3d} calls {calls:3d} marks {len(sheet.marks):4d} ${cost:.2f} "
              f"{[f['name'] for f in fcalls]} {(' '.join(texts))[:120]!r}", flush=True)
        if not fcalls:
            if warned or turns > max_calls:
                break
            contents.append({"role": "user", "parts": [{"text": "Please continue with the tools "
                             "and finish with submit."}]})
            continue
        replies, images = [], []
        for f in fcalls:
            calls += 1
            name, args = f["name"], f.get("args", {}) or {}
            img = None
            try:
                if name == "view":
                    out, img = sheet.view(**{k: args.get(k) for k in ("region", "x0", "y0", "x1", "y1")})
                elif name == "mark":
                    out = sheet.mark(int(args.get("view", 0)), args.get("points", []), bool(args.get("force")))
                elif name == "remove":
                    out = sheet.remove(args.get("ids", []))
                elif name == "overview":
                    out, img = sheet.overview()
                elif name == "submit":
                    submitted = args
                    out = {"ok": True, "marks": len(sheet.marks)}
                else:
                    out = {"error": f"unknown tool {name}"}
            except Exception as e:
                out = {"error": repr(e)}
            if img is not None:
                out["image"] = f"attached below as image {len(images) + 1} of this turn"
                images.append(img)
            log(turn=turns, tool=name, result={k: v for k, v in out.items() if k != "image"})
            part = {"functionResponse": {"name": name, "response": out}}
            if "id" in f:
                part["functionResponse"]["id"] = f["id"]
            replies.append(part)
        parts = replies + [jpeg(i) for i in images]
        if submitted is None and (calls >= max_calls or cost >= max_usd):
            if warned:
                log(turn=turns, event="budget exhausted, forced stop")
                break
            warned = True
            parts.append({"text": f"Budget used up ({calls} tool calls, ${cost:.2f}). Call submit now "
                                  "with your current marks, uncertain regions and comment."})
        contents.append({"role": "user", "parts": parts})
        prune_images(contents)
    trace.close()

    points = [list(p) for p in sheet.marks.values()]
    m = match(points, row["kernel_points"])
    submitted = submitted or {}
    return {"file_name": row["file_name"], "species": row["species"], "camera": row["camera"],
            "model": f"agentic-{model}", "mode": "agent", "grid": 0, "count": row["count"],
            "n_points": len(row["kernel_points"]), "pred": len(points),
            "submitted_count": submitted.get("count"),
            **{k: m[k] for k in ("tp", "fp", "fn", "precision", "recall", "radius")},
            "seconds": round(time.perf_counter() - t0, 1), "cost_usd": round(cost, 4),
            "usage": usage, "tool_calls": calls, "turns": turns,
            "comment": submitted.get("comment"), "uncertain_regions": submitted.get("uncertain_regions"),
            "points": points, "tiles": [{"core": list(r)} for r in regions]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default="runs/dev4.txt")
    ap.add_argument("--only", nargs="*", help="file_names to run (default: --limit first)")
    ap.add_argument("--limit", type=int, default=2)
    ap.add_argument("--model", default="gemini-4-argon")
    ap.add_argument("--max-calls", type=int, default=150)
    ap.add_argument("--max-usd", type=float, default=3.0)
    ap.add_argument("--thinking", choices=["low", "medium", "high"])
    ap.add_argument("--no-regions", action="store_true", help="no suggested regions, free views")
    ap.add_argument("--tag", default="argon")
    args = ap.parse_args()

    names = args.only or Path(args.images).read_text().split()[: args.limit]
    rows = {r["file_name"]: r for r in load_split("train")}
    outdir = RUNS / args.tag
    outdir.mkdir(parents=True, exist_ok=True)
    for name in names:
        out = outdir / (name.replace("/", "__") + ".json")
        if out.exists():
            continue
        print(name, flush=True)
        res = run_image(rows[name], args.model, args.max_calls, args.max_usd, args.thinking,
                        out.with_suffix(".trace.jsonl"), not args.no_regions)
        out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
        print(f"{name}: {res['pred']} vs {res['count']} ({res['pred'] - res['count']:+d}) "
              f"P={res['precision']:.3f} R={res['recall']:.3f} ${res['cost_usd']:.2f} "
              f"{res['tool_calls']} calls {res['seconds']:.0f}s", flush=True)


if __name__ == "__main__":
    main()
