"""Foto-Vorprüfung vor der bezahlten Zählung (docs/app/ROADMAP.md 2.1, UX.md 2).

Schnell (< 1 s) und nur lokal: heller Bereich (Blatt) gefunden und ganz im Bild, Schärfe,
Häufchen (zusammenhängende Kornflecken über mehrere Kornflächen), sehr wenige Körner.
Ergebnis sind Warnungen, nie eine Sperre: die App bietet „Neu aufnehmen“ und
„Trotzdem zählen“ an. Nutzt nur lesend die Kornmaske der Pipeline
(tausendkorn.adaptive); Schwellen sind nur auf dev von corn1000 eingestellt
(siehe app/calibrate_precheck.py).
"""

from __future__ import annotations

import cv2
import numpy as np

from tausendkorn.adaptive import kernel_area, kernel_mask

# Schwellen, kalibriert mit app/calibrate_precheck.py nur auf dev (24 Fotos, PROTOCOL.md):
# Blatt in allen gefunden, Anteil am Bild >= 0,37; Schärfe echter Fotos >= 117 (p5 223),
# künstlich weichgezeichneter Kopien <= 9; Häufchen-Anteil Median 0,81, p90 0,92;
# größter Fleck Median 230, p90 588 Kornflächen. Der Datensatz legt Körner absichtlich
# eng und die Zählung kommt damit klar; gewarnt wird nur beim engsten Zehntel.
# Die Blattprüfung prüft nur, ob ein großer heller Bereich da ist, NICHT ob es ein A4-Blatt
# ist: eine Formprüfung (Rechteckigkeit, Seitenverhältnis) warnte auf dev auch bei
# lockeren Schwellen bei 3 von 24 echten Fotos (heller Hintergrund verschmilzt mit dem
# Blatt). Form wird darum nur gemessen und gespeichert, nicht bewertet.
MIN_SHEET_FRACTION = 0.12   # heller Bereich füllt weniger als 12 % des Bildes: zu weit weg
BORDER_TOUCH = 0.15         # Blattrand liegt auf > 15 % einer Bildkante: abgeschnitten
MIN_SHARPNESS = 40.0        # Laplace-Varianz der Helligkeit im Blatt (Analysegröße 1200 px)
CLUMP_KERNELS = 6           # Fleck größer als 6 Kornflächen (20 mm²) gilt als Häufchen
CLUMP_SHARE = 0.92          # warnen, wenn mehr Kornfläche in Häufchen liegt (dev p90)
LARGEST_CLUMP = 590         # oder ein einzelner Fleck größer ist (dev p90, in Kornflächen)
MIN_KERNELS = 300           # darunter: Hinweis „mehr Körner“ (UX.md 2)


def measure(image) -> dict:
    """Raw numbers for one upright RGB PIL image; regions in full-resolution pixels."""
    try:
        out = kernel_mask(image)
    except ValueError:  # newer pipeline versions raise when no sheet is found
        return {"sheet": False}
    mask, scale, inside = out[0], out[1], out[2]
    h, w = inside.shape
    sheet_fraction = float(inside.sum()) / inside.size
    if sheet_fraction < 0.02:
        return {"sheet": False}
    edges = [inside[0, :], inside[-1, :], inside[:, 0], inside[:, -1]]
    border = max(float(e.mean()) for e in edges)
    # A4 shape: the sheet outline should fill its rotated bounding box (a rectangle,
    # not a plate) with a side ratio near 1.41 (perspective shifts it a little).
    contour = cv2.findContours(inside, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    outline = max(contour, key=cv2.contourArea)
    (_, _), (rw, rh), _ = cv2.minAreaRect(outline)
    rectangularity = float(cv2.contourArea(outline)) / max(rw * rh, 1.0)
    aspect = max(rw, rh) / max(min(rw, rh), 1.0)

    small = np.asarray(image.resize((w, h)).convert("L"), dtype=np.float32)
    core = cv2.erode(inside, np.ones((25, 25), np.uint8)) > 0
    lap = cv2.Laplacian(small, cv2.CV_32F)
    sharpness = float(lap[core].var()) if core.any() else 0.0

    area = kernel_area(inside)
    kernels = mask & inside
    n, labels, stats, _ = cv2.connectedComponentsWithStats(kernels, connectivity=8)
    blob_area = stats[1:, cv2.CC_STAT_AREA].astype(float)
    total = float(blob_area.sum()) or 1.0
    big = np.where(blob_area > CLUMP_KERNELS * area)[0]
    clumps = [[round(float(v) * scale) for v in (stats[i + 1, 0], stats[i + 1, 1],
               stats[i + 1, 0] + stats[i + 1, 2], stats[i + 1, 1] + stats[i + 1, 3])]
              for i in big[np.argsort(-blob_area[big])][:12]]
    return {"sheet": True, "sheet_fraction": round(sheet_fraction, 3), "border": round(border, 3),
            "rectangularity": round(rectangularity, 3), "aspect": round(aspect, 3),
            "sharpness": round(sharpness, 1), "kernels_est": round(total / area),
            "clump_share": round(float(blob_area[big].sum()) / total, 3),
            "largest_blob": round(float(blob_area.max()) / area, 1) if len(blob_area) else 0.0,
            "clumps": clumps}


def check(m: dict) -> list[dict]:
    """At most the most important warning first (UX.md: show one at a time)."""
    if not m.get("sheet"):
        return [{"kind": "blatt", "text": "Das weiße Blatt ist nicht zu erkennen. Bitte das ganze A4-Blatt ins Bild nehmen."}]
    out = []
    if m["border"] > BORDER_TOUCH or m["sheet_fraction"] < MIN_SHEET_FRACTION:
        out.append({"kind": "blatt", "text": "Das Blatt ist nicht ganz zu sehen oder zu klein. "
                    "Bitte alle vier Ecken ins Bild nehmen, Gerät gerade darüber halten."})
    if m["sharpness"] < MIN_SHARPNESS:
        out.append({"kind": "unscharf", "text": "Das Foto ist unscharf. Gerät ruhig halten und neu aufnehmen."})
    if m["clump_share"] > CLUMP_SHARE or m["largest_blob"] > LARGEST_CLUMP:
        # a connected blob only shows kernels touching; overlap is likely, not proven
        out.append({"kind": "haufen", "text": "Viele Körner liegen dicht an dicht (markiert), "
                    "vermutlich liegen einige übereinander. Kurz auseinanderstreichen, dann neu fotografieren.",
                    "regions": m["clumps"]})
    if m["kernels_est"] < MIN_KERNELS:
        out.append({"kind": "wenig", "text": f"Nur etwa {m['kernels_est']} Körner. "
                    "Für ein genaues TKG besser 500 bis 1000 Körner."})
    return out
