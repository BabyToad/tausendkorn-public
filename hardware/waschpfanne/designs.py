"""Pan designs as axisymmetric profiles: [(r_mm, z_mm), ...] of the inner surface from the
centre outward to the rim. Shared by simulate.py (physics) and build_pfannen.py (CAD/renders).
"""

import math

# Hand-panning motion (Astra: 15-25 mm orbit, 2-3 Hz; 20 mm at 2.5 Hz = 0.5 g). Phases of
# horizontal gyration (orbit radius mm, frequency Hz, tilt deg); R=0 is rest. The handful
# drops during the first rest phase. Shortened from Astra's 2+1+12+1+2 s to fit laptop runs.
SWIRL = [dict(t=1.5, R=0), dict(t=8.0, R=20, f=2.5, tilt=0), dict(t=1.5, R=0)]
DROP = [dict(t=11.0, R=0)]
# Gentle stop: the orbit fades out linearly over the last 4 s instead of 0.3 s
SWIRL_FADE = [dict(t=1.5, R=0), dict(t=8.0, R=20, f=2.5, tilt=0, decay=4.0), dict(t=1.5, R=0)]
# Astra's alternative technique: reverse direction halfway and wobble the pan by 3 degrees
SWIRL_REV = [dict(t=1.5, R=0), dict(t=4.0, R=20, f=2.5, tilt=3), dict(t=4.0, R=20, f=-2.5, tilt=3),
             dict(t=1.5, R=0)]

# Astra's shared geometry (mm): floor r <= 145 at z = 0, wall z = 2(r - 145) up to z = 20 at
# r = 155 (63.4 deg), flat rim flange to r = 180. Floor 3 mm, wall 2 mm.
R_FLOOR, R_WALL, H_WALL, R_RIM = 145.0, 155.0, 20.0, 180.0


def wall_and_rim(beads=()):
    """Wall from (145, 0) to (155, 20) with optional semicircular beads (centre r, z, radius)
    projecting inward from the wall, then the flange."""
    t = (1 / math.sqrt(5), 2 / math.sqrt(5))     # along the wall, upward
    nrm = (-2 / math.sqrt(5), 1 / math.sqrt(5))  # into the pan
    pts = []
    for (cr, cz, br) in beads:
        for i in range(9):
            a = math.pi * i / 8 - math.pi / 2     # -90 .. +90 deg around the bead
            pts.append((cr + br * (math.sin(a) * t[0] + math.cos(a) * nrm[0]),
                        cz + br * (math.sin(a) * t[1] + math.cos(a) * nrm[1])))
    pts.append((R_WALL, H_WALL))
    pts.append((R_RIM, H_WALL))
    return pts


def floor(fn=lambda r: 0.0, n=58):
    return [(R_FLOOR * i / n, fn(R_FLOOR * i / n)) for i in range(n + 1)]


def ridged(r):
    z = 0.0
    for ri in (40.0, 75.0, 110.0):
        if abs(r - ri) <= 1.5:
            z = 0.3 * (1 + math.cos(2 * math.pi * (r - ri) / 3.0))
    return z


def floor_ridged():
    rs = sorted({R_FLOOR * i / 58 for i in range(59)} |
                {ri + d / 4 for ri in (40.0, 75.0, 110.0) for d in range(-6, 7)})
    return [(r, ridged(r)) for r in rs]


DESIGNS = {
    "FLAT": dict(profile=[(0, 0), (150, 0), (150.5, 0)], motion=DROP,
                 label="A4-Blatt, nur hingeschüttet (Basis)"),
    "A0": dict(profile=floor() + wall_and_rim(), motion=SWIRL, label="Glatte Pfanne (Kontrolle)"),
    "A": dict(profile=floor() + wall_and_rim(beads=((149, 8, 0.75), (152, 14, 0.75))), motion=SWIRL,
              label="A: flacher Boden, Wandwülste"),
    "A_REV": dict(profile=floor() + wall_and_rim(beads=((149, 8, 0.75), (152, 14, 0.75))),
                  motion=SWIRL_REV, label="A mit Richtungswechsel und Kippeln"),
    "A_FADE": dict(profile=floor() + wall_and_rim(beads=((149, 8, 0.75), (152, 14, 0.75))),
                   motion=SWIRL_FADE, label="A mit sanftem Auslaufen"),
    "B": dict(profile=floor_ridged() + wall_and_rim(), motion=SWIRL,
              label="B: drei flache Ringstege"),
    "C": dict(profile=floor(lambda r: 2.0 * (1 - (r / R_FLOOR) ** 2)) + wall_and_rim(), motion=SWIRL,
              label="C: leicht gewölbter Boden"),
}


def floor_z_cm(name, r_cm):
    """Inner surface height (cm) at radius r_cm, linear between profile points."""
    prof = DESIGNS[name]["profile"]
    r = r_cm * 10
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        if r0 <= r <= r1:
            return (z0 + (z1 - z0) * (r - r0) / max(1e-9, r1 - r0)) / 10
    return prof[-1][1] / 10
