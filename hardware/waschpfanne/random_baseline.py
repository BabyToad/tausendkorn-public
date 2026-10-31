"""Reference: touching fraction when the same grains are scattered at random (no overlap) on
the pan floor or an A4 sheet. Same 2D gap test as simulate.py. Plain Python.

  uv run --no-project python random_baseline.py
"""
import json
import math
import random
from pathlib import Path

GAP = 0.2  # mm


def ellipse(cx, cy, a, b, th, n=12):
    c, s = math.cos(th), math.sin(th)
    return [(cx + a * math.cos(t) * c - b * math.sin(t) * s, cy + a * math.cos(t) * s + b * math.sin(t) * c)
            for t in (math.tau * i / n for i in range(n))]


def separated(a, b, gap):
    for poly in (a, b):
        for i in range(len(poly)):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
            nx, ny = y1 - y0, x0 - x1
            ln = math.hypot(nx, ny) or 1.0
            nx, ny = nx / ln, ny / ln
            pa = [x * nx + y * ny for x, y in a]
            pb = [x * nx + y * ny for x, y in b]
            if max(pa) + gap < min(pb) or max(pb) + gap < min(pa):
                return True
    return False


def run(shape, n_whole=792, n_broken=53, seed=1):
    rnd = random.Random(seed)
    sizes = [(3.3, 1.65)] * n_whole + [(1.9, 1.65)] * n_broken  # semi-axes mm
    placed = []
    for a, b in sizes:
        while True:
            if shape == "disk":
                r, t = 145 * math.sqrt(rnd.random()), rnd.uniform(0, math.tau)
                x, y = r * math.cos(t), r * math.sin(t)
                if r > 145 - a:
                    continue
            else:
                x, y = rnd.uniform(-105 + a, 105 - a), rnd.uniform(-148.5 + a, 148.5 - a)
            p = ellipse(x, y, a, b, rnd.uniform(0, math.pi))
            if all((x - q[0]) ** 2 + (y - q[1]) ** 2 > 7.0 ** 2 or separated(p, q[2], 0.0) for q in placed):
                placed.append((x, y, p))
                break
    touching = set()
    for i, (x, y, p) in enumerate(placed):
        for j in range(i + 1, len(placed)):
            q = placed[j]
            if (x - q[0]) ** 2 + (y - q[1]) ** 2 < 7.5 ** 2 and not separated(p, q[2], GAP):
                touching |= {i, j}
    return len(touching) / len(placed)


if __name__ == "__main__":
    res = {s: [round(run(s, seed=k), 3) for k in range(3)] for s in ("disk", "a4")}
    print(json.dumps(res))
    Path("out/sim/RANDOM.json").write_text(json.dumps(res, indent=2))
