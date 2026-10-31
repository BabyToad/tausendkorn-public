"""Baut die statische Projektseite unter site/ (Cloudflare Pages).

Liest die eingefrorenen Läufe v1.0.2 (results/argon_v1.0.2/{holdout,test}/*.jpg.json),
YOLO11s zum Vergleich (results/yolo11s/…) und die Fotos aus data/corn1000, verkleinert die Fotos, rechnet Marken und Prüfstellen auf
Anzeige-Pixel um und schreibt site/img/s/*.jpg und site/data/*.json. Kopiert pitch/web
nach site/pitch/. Kein API-Aufruf, keine Kosten.

    uv run python scripts/build_site.py [--src <dataset-checkout>]

--src: Checkout mit data/corn1000 (Standard: dieses Repo).
"""

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
LONG = 1600  # Anzeigebild, lange Seite
THUMB = 360
QUALITY = 74

SPECIES = {
    "oats-s": "Hafer",
    "barley-w": "Wintergerste",
    "wheat-w": "Winterweizen",
    "durum-w": "Hartweizen",
    "rye-w": "Winterroggen",
}

# Hervorgehobene Beispiele für die Demo, in dieser Reihenfolge.
FEATURED = [
    "S02-008",          # Hafer, Prüfstelle vom Modell gemeldet (wie im Pitch)
    "count_1000-002_galaxy-s23",   # Roggen, Testfoto 26.10., nie trainiert
    "S03-008",          # Gerste mit Prüfstelle
    "count_1000-003_galaxy-s23",   # Weizen, Testfoto 26.10.
    "S04-001",          # Weizen, exakt
]


def short_id(file_name: str) -> str:
    stem = Path(file_name).name
    parts = stem.split("_")
    # Testbilder: Nummer + Kamera, sonst überschreiben sich z. B. die beiden Gerste-Fotos 000
    return parts[0] if not stem.startswith("count_1000") else "_".join(parts[:3])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=REPO)
    args = ap.parse_args()
    src = args.src

    for d in (SITE / "img" / "s", SITE / "data" / "s"):
        shutil.rmtree(d, ignore_errors=True)
    (SITE / "img" / "s").mkdir(parents=True, exist_ok=True)
    (SITE / "data" / "s").mkdir(parents=True, exist_ok=True)

    index = []
    for split in ("holdout", "test"):
        for f in sorted((REPO / "results" / "argon_v1.0.2" / split).glob("*.jpg.json")):
            run = json.loads(f.read_text(encoding="utf-8"))
            yf = REPO / "results" / "yolo11s" / split / f.name
            yolo = json.loads(yf.read_text(encoding="utf-8")).get("pred") if yf.exists() else None
            sid = short_id(run["file_name"])
            sub = "test" if split == "test" else "train"
            photo = src / "data" / "corn1000" / "data" / sub / run["file_name"]
            im = ImageOps.exif_transpose(Image.open(photo)).convert("RGB")
            w0, h0 = im.size
            k = LONG / max(w0, h0)
            im = im.resize((round(w0 * k), round(h0 * k)), Image.LANCZOS)
            im.save(SITE / "img" / "s" / f"{sid}.jpg", quality=QUALITY, optimize=True, progressive=True)
            th = im.copy()
            th.thumbnail((THUMB, THUMB), Image.LANCZOS)
            th.save(SITE / "img" / "s" / f"{sid}_t.jpg", quality=70, optimize=True)

            pts = [[round(x * k, 1), round(y * k, 1)] for x, y in run["points"]]
            checks = [
                {
                    "box": [round(v * k, 1) for v in c["region"]],
                    "confidence": c.get("confidence"),
                    "comment_en": c.get("comment"),
                }
                for c in run.get("check_here", [])
            ]
            detail = {"id": sid, "w": im.width, "h": im.height, "points": pts, "checks": checks}
            (SITE / "data" / "s" / f"{sid}.json").write_text(
                json.dumps(detail, separators=(",", ":")), encoding="utf-8"
            )
            index.append({
                "id": sid,
                "split": split,
                "species": SPECIES.get(run["species"], run["species"]),
                "camera": run["camera"],
                "truth": run["true"],
                "count": run["count"],
                "yolo": yolo,
                "checks": len(checks),
                "w": im.width,
                "h": im.height,
                "featured": FEATURED.index(sid) if sid in FEATURED else None,
            })

    commit = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    meta = {
        "version": "v1.0.2",
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "commit": commit,
        "samples": index,
    }
    (SITE / "data" / "samples.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    pitch = SITE / "pitch"
    if pitch.exists():
        shutil.rmtree(pitch)
    shutil.copytree(REPO / "pitch" / "web", pitch)
    deck = pitch / "index.html"
    html = deck.read_text(encoding="utf-8")
    # Auf der Projektseite führt "/" nicht zur Feld-App, sondern zur Startseite.
    html = html.replace(">Zur App →<", ">Zur Projektseite →<").replace(">Zur App<", ">Zur Projektseite<")
    deck.write_text(html, encoding="utf-8")
    shutil.copy(REPO / "design" / "system" / "tokens.css", SITE / "tokens.css")

    # App-Screenshots (Mock-Modus) aus docs/app/screens, oberer Teil, verkleinert
    (SITE / "img" / "app").mkdir(parents=True, exist_ok=True)
    for name in ("02_foto", "04_gezaehlt", "05_pruefkarte", "07_ergebnis"):
        im = Image.open(REPO / "docs" / "app" / "screens" / f"{name}.png").convert("RGB")
        im = im.crop((0, 0, im.width, min(im.height, round(im.width * 2.05))))
        im = im.resize((390, round(390 * im.height / im.width)), Image.LANCZOS)
        im.save(SITE / "img" / "app" / f"{name}.jpg", quality=78, optimize=True)

    # Vorschaubild für Link-Vorschauen (1200 × 630) aus dem Titelfoto des Pitches
    og = ImageOps.fit(Image.open(REPO / "pitch" / "web" / "img" / "titel_roggen.jpg").convert("RGB"),
                      (1200, 630), Image.LANCZOS, centering=(0.5, 0.45))
    og.save(SITE / "img" / "og.jpg", quality=80, optimize=True)
    print(f"{len(index)} Bilder, Pitch kopiert, Commit {commit}")


if __name__ == "__main__":
    main()
