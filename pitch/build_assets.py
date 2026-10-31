"""Prepare pitch images: real Argon v1.0.2 marks from the frozen final runs, drawn in the
B · Labor look (blue dot with white ring = counted, dashed orange box with number = check).

    uv run --no-project --with pillow python pitch/build_assets.py

Photos: SmartFarmingLab/corn1000 (CC BY-NC 4.0). Marks: results/argon_v1.0.2/{holdout,test} (committed).
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "corn1000" / "data"
RUNS = ROOT / "results" / "argon_v1.0.2"
OUT = ROOT / "pitch" / "web" / "img"
WEB = ROOT / "pitch" / "web" / "img"
OUT.mkdir(parents=True, exist_ok=True)
WEB.mkdir(parents=True, exist_ok=True)

MARK, UNSURE, INK, WHITE = (0, 95, 184), (224, 138, 0), (20, 24, 27), (255, 255, 255)
try:
    MONO = ImageFont.truetype("DejaVuSansMono.ttf", 64)
except OSError:
    MONO = ImageFont.load_default(size=64)


def load(split, name, run=None):
    res = json.loads((RUNS / (run or split) / f"{name.replace('/', '__')}.json").read_text())
    img = ImageOps.exif_transpose(Image.open(DATA / split / name)).convert("RGB")
    return img, res


def bbox(points, pad):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def dashed_rect(d, box, color, width, dash):
    x0, y0, x1, y1 = box
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        length = max(abs(bx - ax), abs(by - ay))
        for s in range(0, int(length), dash * 2):
            e = min(s + dash, length)
            f0, f1 = s / length, e / length
            d.line([(ax + (bx - ax) * f0, ay + (by - ay) * f0),
                    (ax + (bx - ax) * f1, ay + (by - ay) * f1)], fill=color, width=width)


def draw_marks(img, points, r, checks=(), offset=(0, 0)):
    d = ImageDraw.Draw(img)
    ox, oy = offset
    ring = max(2, r * 0.45)
    for x, y in points:
        x, y = x - ox, y - oy
        d.ellipse((x - r - ring, y - r - ring, x + r + ring, y + r + ring), fill=WHITE)
        d.ellipse((x - r, y - r, x + r, y + r), fill=MARK)
    for i, c in enumerate(checks, 1):
        x0, y0, x1, y1 = c["region"]
        box = (x0 - ox, y0 - oy, x1 - ox, y1 - oy)
        dashed_rect(d, box, UNSURE, int(r * 1.1), int(r * 3))
        tr = r * 3.2
        cx, cy = box[0], box[1]
        d.ellipse((cx - tr - 6, cy - tr - 6, cx + tr + 6, cy + tr + 6), fill=WHITE)
        d.ellipse((cx - tr, cy - tr, cx + tr, cy + tr), fill=UNSURE)
        d.text((cx, cy), str(i), font=MONO, fill=INK, anchor="mm")
    return img


def save(img, name, size=None, quality=86):
    if size:
        img = img.resize(size, Image.LANCZOS)
    img.save(OUT / name, quality=quality)
    print(name, img.size)


# 1) Test day, rye (never seen in development): 997 marks, label 1000. Full sheet + crop.
img, res = load("test", "count_1000/count_1000-002_galaxy-s23_IMG_20261026_184810.jpg")
x0, y0, x1, y1 = (int(v) for v in bbox(res["points"], 60))
sheet = draw_marks(img.copy(), res["points"], r=9).crop((x0, y0, x1, y1))
w = 1200
save(sheet, "roggen_997.jpg", (w, int(w * sheet.height / sheet.width)))
# portrait crop for the title slide (centre of the sheet, 4:5)
cw, ch = int((x1 - x0) * 0.62), int((x1 - x0) * 0.62 * 1.25)
cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
hero = draw_marks(img.copy(), res["points"], r=11).crop((cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2))
save(hero, "titel_roggen.jpg", (1200, 1500))
print("rye:", res["count"], "of", res["true"])

# 2) Holdout, oats: 256 marks vs 253, one check spot the model flagged itself.
img, res = load("train", "S02/S02-008_galaxy-s23_20261002_150020.jpg", run="holdout")
x0, y0, x1, y1 = (int(v) for v in bbox(res["points"], 90))
full = draw_marks(img.copy(), res["points"], r=10, checks=res["check_here"]).crop((x0, y0, x1, y1))
save(full, "hafer_pruefstelle.jpg", (1200, int(1200 * full.height / full.width)))
rx0, ry0, rx1, ry1 = res["check_here"][0]["region"]
m = 170
zoom = draw_marks(img.copy(), res["points"], r=7, checks=res["check_here"])
zoom = zoom.crop((rx0 - m, ry0 - m, rx1 + m, ry1 + m))
save(zoom, "hafer_zoom.jpg", (900, int(900 * zoom.height / zoom.width)))
print("oats:", res["count"], "of", res["true"], "check:", res["check_here"][0]["comment"])

# 3) Kornwaschpfanne render (hardware/waschpfanne, prototype A after 8 s of swirling)
st = Image.open(ROOT / "hardware" / "waschpfanne" / "out" / "10_pfannen_aufstellung_kontakte.png").convert("RGB")
save(st, "pfanne.jpg", (1200, 800))
