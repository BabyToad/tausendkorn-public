"""Zeichnet die Schrittbilder für die Seite /pipeline/ (site/img/stack/).

Beispiel ist das Holdout-Foto S02-008 (Hafer) aus dem eingefrorenen Lauf v1.0.2: Kacheln,
Punkte und Prüfstellen kommen aus results/argon_v1.0.2/holdout/, die Maske wird lokal neu
gerechnet. Kein API-Aufruf, keine Kosten.

    uv run python scripts/build_stack_images.py
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from tausendkorn.adaptive import kernel_length_px, kernel_mask
from tausendkorn.eval import DATA, load_image
from tausendkorn.match import match

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "site" / "img" / "stack"
RUN = REPO / "results" / "argon_v1.0.2" / "holdout" / "S02__S02-008_galaxy-s23_20261002_150020.jpg.json"

MARK = (0, 95, 184)
UNSURE = (224, 138, 0)
BAD = (163, 38, 27)
CORE = (255, 0, 0)
CROP = (0, 140, 255)
INK = (20, 24, 27)


def font(size: int):
    for name in ("seguisb.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def fit(im: Image.Image, long: int) -> tuple[Image.Image, float]:
    k = long / max(im.size)
    return im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS), k


def save(im: Image.Image, name: str) -> None:
    im.save(OUT / name, quality=80, optimize=True, progressive=True)
    print(name, im.size)


def dot(d: ImageDraw.ImageDraw, x: float, y: float, r: float, fill) -> None:
    d.ellipse((x - r - 2, y - r - 2, x + r + 2, y + r + 2), fill=(255, 255, 255))
    d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def side_by_side(a: Image.Image, b: Image.Image, gap: int = 24) -> Image.Image:
    h = max(a.height, b.height)
    out = Image.new("RGB", (a.width + b.width + gap, h), (244, 245, 243))
    out.paste(a, (0, (h - a.height) // 2))
    out.paste(b, (a.width + gap, (h - b.height) // 2))
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    run = json.loads(RUN.read_text(encoding="utf-8"))
    path = DATA / "train" / run["file_name"]
    row = next(json.loads(l) for l in open(DATA / "train" / "metadata.jsonl", encoding="utf-8")
               if json.loads(l)["file_name"] == run["file_name"])
    truth = [p[:2] for p in row["kernel_points"]]
    image = load_image(path)
    W, H = image.size
    L = kernel_length_px(image)
    tiles = run["first_pass"]["tiles"]
    points = run["points"]

    # 1 · EXIF: so liegt das Bild in der Datei, so nach exif_transpose
    raw = Image.open(path).convert("RGB")
    a, _ = fit(raw, 640)
    b, _ = fit(image, 640)
    save(side_by_side(a, b), "01_exif.jpg")

    # 2 · Maske: Foto | Black-Hat-Maske mit Blattumriss
    mask, scale, inside = kernel_mask(image)
    m = np.zeros((*mask.shape, 3), np.uint8)
    m[inside > 0] = (60, 66, 72)
    m[mask > 0] = (255, 255, 255)
    a, _ = fit(image, 760)
    b, _ = fit(Image.fromarray(m), 760)
    save(side_by_side(a, b), "02_maske.jpg")

    # 3 · Quadtree: echte Kernfelder des Laufs, Zahl = gezählte Körner im Kernfeld
    view, k = fit(image, 1400)
    over = Image.new("RGBA", view.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    f = font(22)
    for t in tiles:
        x0, y0, x1, y1 = (v * k for v in t["core"])
        if not t["pred"]:
            d.rectangle((x0, y0, x1, y1), fill=(20, 24, 27, 70))
        d.rectangle((x0, y0, x1, y1), outline=(255, 0, 0, 230), width=2)
        if t["pred"] and (x1 - x0) > 28:
            d.text(((x0 + x1) / 2, (y0 + y1) / 2), str(t["pred"]), font=f, anchor="mm",
                   fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(20, 24, 27, 255))
    save(Image.alpha_composite(view.convert("RGBA"), over).convert("RGB"), "03_quadtree.jpg")

    # 4 · Eine Kachel so, wie das Modell sie sieht: Ausschnitt mit Halo, rotes Kernfeld
    t = max(tiles, key=lambda t: t["pred"])
    cx0, cy0, cx1, cy1 = t["crop"]
    tile = image.crop(t["crop"])
    rel = [t["core"][0] - cx0, t["core"][1] - cy0, t["core"][2] - cx0, t["core"][3] - cy0]
    ImageDraw.Draw(tile).rectangle(rel, outline=CORE, width=4)
    model_view, _ = fit(tile, 620)
    marked = tile.copy()
    d = ImageDraw.Draw(marked)
    r = max(5, L * 0.07)
    for x, y in points:
        if cx0 <= x < cx1 and cy0 <= y < cy1:
            own = t["core"][0] <= x < t["core"][2] and t["core"][1] <= y < t["core"][3]
            if own:
                dot(d, x - cx0, y - cy0, r, MARK)
            else:
                d.ellipse((x - cx0 - r, y - cy0 - r, x - cx0 + r, y - cy0 + r),
                          outline=(255, 255, 255), width=3)
    marked, _ = fit(marked, 620)
    save(side_by_side(model_view, marked), "04_kachel.jpg")
    print("Kachel", t["core"], "pred", t["pred"], "raw", t["raw_points"])

    # 5 · Prüfstelle: die Naht-Doppelmarke, die das Modell im Prüfdurchgang fand
    reg = run["check_here"][0]["region"] if run["check_here"] else tiles[0]["core"]
    pad = 1.2 * L
    box = (max(reg[0] - pad, 0), max(reg[1] - pad, 0), min(reg[2] + pad, W), min(reg[3] + pad, H))
    zoom = image.crop(tuple(round(v) for v in box))
    z = 700 / max(zoom.size)
    zoom = zoom.resize((round(zoom.width * z), round(zoom.height * z)), Image.LANCZOS)
    d = ImageDraw.Draw(zoom)
    rx0, ry0, rx1, ry1 = ((reg[0] - box[0]) * z, (reg[1] - box[1]) * z,
                          (reg[2] - box[0]) * z, (reg[3] - box[1]) * z)
    d.rectangle((rx0, ry0, rx1, ry1), outline=UNSURE, width=5)
    for x, y in points:
        if box[0] <= x < box[2] and box[1] <= y < box[3]:
            dot(d, (x - box[0]) * z, (y - box[1]) * z, 9, MARK)
    save(zoom, "05_pruefstelle.jpg")

    # 6 · Ergebnis gegen die Labels: blau richtig, rot zu viel, orange übersehen
    res = match(points, truth)
    view, k = fit(image, 1400)
    d = ImageDraw.Draw(view)
    extra = {tuple(p) for p in res["extra"]}
    for x, y in points:
        if tuple([x, y]) not in extra:
            dot(d, x * k, y * k, 4, MARK)
    for x, y in res["extra"]:
        x, y = x * k, y * k
        d.line((x - 9, y - 9, x + 9, y + 9), fill=BAD, width=4)
        d.line((x - 9, y + 9, x + 9, y - 9), fill=BAD, width=4)
    for x, y in res["missed"]:
        x, y = x * k, y * k
        d.ellipse((x - 11, y - 11, x + 11, y + 11), outline=UNSURE, width=4)
    save(view, "06_ergebnis.jpg")
    print(f"count {len(points)} label {len(truth)} tp {res['tp']} fp {res['fp']} fn {res['fn']}"
          f" tiles {len(tiles)} empty {sum(not t['pred'] for t in tiles)} L {L:.0f}px {W}x{H}")


if __name__ == "__main__":
    main()
