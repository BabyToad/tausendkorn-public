"""KornKlapp photo station (Astra's design, see ASTRA_DESIGN.md): parametric model.

A4 sample cassette with rim on a charcoal base, four ArUco markers (DICT_4X4_50, IDs 0-3),
folding telescopic camera gantry with phone rest (main lens 340 mm above the paper),
removable translucent hood, spreading paddle, front pour opening with plug, clip-on spout
and 250 ml cup.

  blender --background --python-exit-code 1 --python hardware/station/build_station.py [-- --draft]

Units: millimetres. Origin: centre of the A4 sheet on the table plane. Outputs in out/.
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scene_kit as k  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
DRAFT = "--draft" in sys.argv

# --- parameters (Astra's spec; deviations noted) ---------------------------------------
A4 = (210.0, 297.0)
BASE = (300.0, 380.0, 2.0)          # aluminium plate
FOOT_D, FOOT_H = 20.0, 4.0
CAS_OUT = (230.0, 317.0)            # sample cassette outer
CAS_FLOOR, RIM_H, RIM_T = 2.0, 8.0, 2.0
BACKING = 0.3                       # low-tack backing + paper
POUR_W, POUR_H = 40.0, 8.0          # front rim opening
MARKER, QUIET = 18.0, 3.0
# Astra: centres (+-125, +-170). Moved to (+-131, +-176) so the 24 mm white pads clear the
# cassette rim (outer x = 115) and stay on the 300 x 380 base.
MARKER_C = (131.0, 176.0)
ARUCO_4X4_50 = {  # inner 4x4 bits (row 0 = top), from cv2.aruco DICT_4X4_50
    0: ((1, 0, 1, 1), (0, 1, 0, 1), (0, 0, 1, 1), (0, 0, 1, 0)),
    1: ((0, 0, 0, 0), (1, 1, 1, 1), (1, 0, 0, 1), (1, 0, 1, 0)),
    2: ((0, 0, 1, 1), (0, 0, 1, 1), (0, 0, 1, 0), (1, 1, 0, 1)),
    3: ((1, 0, 0, 1), (1, 0, 0, 1), (0, 1, 0, 0), (0, 1, 1, 0)),
}
POST_X, POST_Y = 140.0, 80.0
OUTER_TUBE, OUTER_L = 20.0, 200.0
INNER_TUBE, INNER_L = 16.0, 220.0
CROSSBAR = (280.0, 20.0)
LENS_H = 340.0                      # main lens above paper
PLATE = (115.0, 200.0, 4.0)
RIB_H, RIB_T = 6.0, 4.0
NOTCH = 65.0
HOOD = (312.0, 392.0, 300.0)        # Astra: 300 x 380; enlarged so the posts stay inside
HOOD_T, APERTURE = 0.5, 100.0
SPOUT_L, SPOUT_OUT = 50.0, 30.0
CUP_D, CUP_H = 74.0, 70.0           # ~250 ml PP cup

Z_BASE = FOOT_H
Z_CAS = Z_BASE + BASE[2]
Z_PAPER = Z_CAS + CAS_FLOOR + BACKING
Z_LENS = Z_PAPER + LENS_H
Z_PLATE_TOP = Z_LENS + 2.0          # lens protrudes ~2 mm below the phone back
Z_BAR_TOP = Z_PLATE_TOP - PLATE[2] - RIB_H

# --- materials --------------------------------------------------------------------------
M = {}


def mats():
    M["char"] = k.material("Anthrazit_matt", (0.035, 0.037, 0.04), 0.8)
    M["pp"] = k.material("PP_dunkelgrau", (0.07, 0.075, 0.08), 0.6)
    M["alu"] = k.material("Alu_eloxiert", (0.55, 0.56, 0.58), 0.35, 0.9)
    M["orange"] = k.material("Signalorange", (0.95, 0.30, 0.03), 0.45)
    M["paper"] = k.material("Papier", (0.92, 0.92, 0.90), 0.9)
    M["white"] = k.material("Marker_weiss", (0.9, 0.9, 0.9), 0.8)
    M["black"] = k.material("Marker_schwarz", (0.01, 0.01, 0.01), 0.8)
    M["rubber"] = k.material("Silikon", (0.10, 0.10, 0.10), 0.9)
    h = k.material("Haube_PP_transluzent", (0.95, 0.95, 0.93), 0.55)
    p = h.node_tree.nodes["Principled BSDF"]
    p.inputs["Transmission Weight"].default_value = 1.0
    p.inputs["Roughness"].default_value = 0.32
    p.inputs["IOR"].default_value = 1.2
    M["hood"] = h
    M["cup"] = k.material("Becher_PP", (0.9, 0.9, 0.9), 0.12)
    M["cup"].node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.95


# --- helpers ----------------------------------------------------------------------------
def boolean(obj, cutter, op="DIFFERENCE"):
    m = obj.modifiers.new("b", "BOOLEAN")
    m.operation, m.object, m.solver = op, cutter, "EXACT"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter)
    return obj


def cyl(name, r, h, loc, coll, mat, axis="Z", seg=40):
    bpy.ops.mesh.primitive_cylinder_add(vertices=seg, radius=r, depth=h, location=loc)
    o = bpy.context.active_object
    o.name = name
    for c in o.users_collection:
        c.objects.unlink(o)
    coll.objects.link(o)
    if axis == "X":
        o.rotation_euler = (0, math.pi / 2, 0)
    elif axis == "Y":
        o.rotation_euler = (math.pi / 2, 0, 0)
    if mat:
        o.data.materials.append(mat)
    return o


def knob(name, loc, coll, axis="X"):
    o = cyl(name, 15.0, 10.0, loc, coll, M["orange"], axis, seg=12)  # 12 flutes read as grip
    b = o.modifiers.new("bevel", "BEVEL")
    b.width, b.segments = 1.5, 2
    return o


def bevel(o, w, seg=3):
    b = o.modifiers.new("bevel", "BEVEL")
    b.width, b.segments, b.limit_method = w, seg, "ANGLE"
    return o


def parent(children, p):
    bpy.context.view_layer.update()  # fresh empties have no world matrix yet
    for c in children:
        mw = c.matrix_world.copy()
        c.parent = p
        c.matrix_world = mw


def empty(name, loc, coll):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    coll.objects.link(e)
    return e


# --- parts ------------------------------------------------------------------------------
def base(coll):
    W, L, T = BASE
    o = bevel(k.box("Basisplatte", -W / 2, W / 2, -L / 2, L / 2, Z_BASE, Z_BASE + T, coll, M["char"]), 0.8)
    feet = [cyl("Fuss", FOOT_D / 2, FOOT_H, (sx * (W / 2 - 22), sy * (L / 2 - 22), FOOT_H / 2), coll,
                M["rubber"]) for sx in (-1, 1) for sy in (-1, 1)]
    return o, feet


def cassette(coll, name="Kassette"):
    W, L = CAS_OUT
    z0, z1 = Z_CAS, Z_CAS + CAS_FLOOR + RIM_H
    o = k.box(name, -W / 2, W / 2, -L / 2, L / 2, z0, z1, coll, M["pp"])
    iw, il = W - 2 * RIM_T, L - 2 * RIM_T
    boolean(o, k.box("cut", -iw / 2, iw / 2, -il / 2, il / 2, z0 + CAS_FLOOR, z1 + 5, coll))
    boolean(o, k.box("cut", -POUR_W / 2, POUR_W / 2, -L / 2 - 1, -il / 2 + 0.01,
                     z0 + CAS_FLOOR, z1 + 5, coll))
    bevel(o, 0.6, 2)
    paper = k.box(name + "_A4", -A4[0] / 2, A4[0] / 2, -A4[1] / 2, A4[1] / 2,
                  z0 + CAS_FLOOR, z0 + CAS_FLOOR + BACKING, coll, M["paper"])
    plug = bevel(k.box(name + "_Stopfen", -POUR_W / 2 + 0.2, POUR_W / 2 - 0.2, -L / 2 - 4, -il / 2,
                       z0 + CAS_FLOOR, z1, coll, M["orange"]), 0.6, 2)
    # pull tab on the plug
    tab = bevel(k.box(name + "_Stopfen_Lasche", -8, 8, -L / 2 - 12, -L / 2 - 3, z1 - 3, z1, coll,
                      M["orange"]), 1.0, 2)
    return o, paper, plug, tab


def markers(coll):
    out = []
    corners = {0: (-1, 1), 1: (1, 1), 2: (1, -1), 3: (-1, -1)}  # clockwise from upper-left
    cell = MARKER / 6
    z = Z_PAPER  # shimmed to the paper plane
    for mid, (sx, sy) in corners.items():
        cx, cy = sx * MARKER_C[0], sy * MARKER_C[1]
        pad = k.box(f"Marker_{mid}_Sockel", cx - MARKER / 2 - QUIET, cx + MARKER / 2 + QUIET,
                    cy - MARKER / 2 - QUIET, cy + MARKER / 2 + QUIET, Z_BASE + BASE[2], z, coll,
                    M["white"])
        sq = k.box(f"Marker_{mid}", cx - MARKER / 2, cx + MARKER / 2, cy - MARKER / 2, cy + MARKER / 2,
                   z, z + 0.05, coll, M["black"])
        bm = bmesh.new()
        for r, row in enumerate(ARUCO_4X4_50[mid]):
            for c, bit in enumerate(row):
                if bit:
                    x = cx - MARKER / 2 + (c + 1) * cell
                    y = cy + MARKER / 2 - (r + 1) * cell
                    k.add_box(bm, x, x + cell, y - cell, y, z + 0.05, z + 0.1)
        bits = k.mesh_obj(f"Marker_{mid}_Bits", bm, coll, M["white"])
        out += [pad, sq, bits]
    return out


def gantry(coll):
    """Returns (post pivots, crossbar group). Each post pivots at its hinge pin about X."""
    pivots, parts = [], []
    z_pin = Z_BASE + BASE[2] + 14.0
    z_inner_top = Z_BAR_TOP - CROSSBAR[1]
    for sx in (-1, 1):
        x = sx * POST_X
        piv = empty(f"Gelenk_{'L' if sx < 0 else 'R'}", (x, POST_Y, z_pin), coll)
        cheeks = [bevel(k.box(f"Gelenkwange_{sx}_{sy}", x - 10, x + 10,
                              POST_Y + sy * (OUTER_TUBE / 2 + 0.4) + (0 if sy > 0 else -5),
                              POST_Y + sy * (OUTER_TUBE / 2 + 0.4) + (5 if sy > 0 else 0),
                              Z_BASE + BASE[2], z_pin + 10, coll, M["char"]), 1.0)
                  for sy in (-1, 1)]
        pin = cyl("Stift_M5", 2.5, OUTER_TUBE + 14, (x, POST_Y, z_pin), coll, M["alu"], "Y", 16)
        pk = knob(f"Gelenkknauf_{sx}", (x, POST_Y - OUTER_TUBE / 2 - 12, z_pin), coll, "Y")
        h = OUTER_TUBE / 2
        outer = k.box(f"Aussenrohr_{sx}", x - h, x + h, POST_Y - h, POST_Y + h, z_pin - 8,
                      z_pin - 8 + OUTER_L, coll, M["alu"])
        boolean(outer, k.box("cut", x - h + 1.5, x + h - 1.5, POST_Y - h + 1.5, POST_Y + h - 1.5,
                             z_pin - 20, z_pin + OUTER_L + 20, coll))
        hi = INNER_TUBE / 2
        inner = k.box(f"Innenrohr_{sx}", x - hi, x + hi, POST_Y - hi, POST_Y + hi,
                      z_inner_top - INNER_L, z_inner_top, coll, M["alu"])
        clamp = bevel(k.box(f"Klemme_{sx}", x - h - 3, x + h + 3, POST_Y - h - 3, POST_Y + h + 3,
                            z_pin - 8 + OUTER_L - 18, z_pin - 8 + OUTER_L, coll, M["char"]), 1.5)
        ck = knob(f"Klemmknauf_{sx}", (x - sx * 0 , POST_Y - h - 3 - 5, z_pin - 8 + OUTER_L - 9),
                  coll, "Y")
        tele = empty(f"Teleskop_{sx}", (x, POST_Y, z_pin), coll)
        parent([inner], tele)
        parent([outer, clamp, ck, tele], piv)
        parts += cheeks + [pin, pk]
        pivots.append((piv, tele))

    # crossbar + phone rest, removable as one unit
    bar = empty("Querholm_Gruppe", (0, POST_Y, Z_BAR_TOP), coll)
    W, D = CROSSBAR
    xb = k.box("Querholm", -W / 2, W / 2, POST_Y - D / 2, POST_Y + D / 2, Z_BAR_TOP - D, Z_BAR_TOP,
               coll, M["alu"])
    caps = [bevel(k.box(f"Querholm_Kappe_{sx}", sx * W / 2 - 14, sx * W / 2 + 14, POST_Y - 14,
                        POST_Y + 14, Z_BAR_TOP - D - 22, Z_BAR_TOP + 2, coll, M["char"]), 2.0)
            for sx in (-1, 1)]
    bks = [knob(f"Holmknauf_{sx}", (sx * (W / 2 + 14 + 5), POST_Y, Z_BAR_TOP - D - 8), coll, "X")
           for sx in (-1, 1)]
    plate = phone_rest(coll)
    parent([xb, *caps, *bks, *plate], bar)
    return pivots, bar, parts


def phone_rest(coll):
    pw, pl, pt = PLATE
    # plate spans the crossbar (y = 70..90) and reaches past the paper centre
    x0, x1 = -32.0, -32.0 + pw
    y0, y1 = POST_Y + 12 - pl, POST_Y + 12
    z1, z0 = Z_PLATE_TOP, Z_PLATE_TOP - pt
    o = k.box("Handyauflage", x0, x1, y0, y1, z0, z1, coll, M["char"])
    bm = bmesh.new()
    for xr in (x0 + 4, x1 - 4 - RIB_T):  # two longitudinal ribs
        k.add_box(bm, xr, xr + RIB_T, y0 + 4, y1 - 4, z0 - RIB_H, z0 + 0.01)
    ribs = k.mesh_obj("rippen", bm, coll)
    boolean(o, ribs, "UNION")
    # open notch from the left edge around the camera cluster (centred on the lens at 0,0)
    boolean(o, k.box("cut", x0 - 5, NOTCH / 2, -NOTCH / 2, NOTCH / 2, z0 - 20, z1 + 5, coll))
    bevel(o, 1.0, 2)
    stops = [bevel(k.box(f"Anschlag_{i}", *xy, z1, z1 + 10, coll, M["rubber"]), 1.0)
             for i, xy in enumerate(((x1 - 4, x1, -40, 0), (x1 - 4, x1, -110, -90),
                                     (-12, 40, y0 - 2, y0 + 2)))]
    strap = k.box("Halteband", x0 - 1.5, x1 + 1.5, -86, -71, z1 - 0.5, z1 + 10.0, coll, M["orange"])
    boolean(strap, k.box("cut", x0, x1, -90, -67, z1 - 1, z1 + 8.5, coll))
    return [o, *stops, strap]


def hood(coll):
    W, L, H = HOOD
    t = HOOD_T
    parts = []
    for sx in (-1, 1):
        parts.append(k.box(f"Haube_Seite_{sx}", sx * W / 2 - t / 2, sx * W / 2 + t / 2, -L / 2, L / 2,
                           0, H, coll, M["hood"]))
    parts.append(k.box("Haube_Rueck", -W / 2, W / 2, L / 2 - t / 2, L / 2 + t / 2, 0, H, coll, M["hood"]))
    roof = k.box("Haube_Dach", -W / 2, W / 2, -L / 2, L / 2, H, H + t, coll, M["hood"])
    boolean(roof, k.box("cut", -APERTURE / 2, APERTURE / 2, -APERTURE / 2, APERTURE / 2, H - 5, H + 5, coll))
    for sx in (-1, 1):
        boolean(roof, k.box("cut", sx * POST_X - 13, sx * POST_X + 13, POST_Y - 13, POST_Y + 13,
                            H - 5, H + 5, coll))
    parts.append(roof)
    # front flap hinged at the roof edge, opens upward/outward
    hinge = empty("Haube_Front_Scharnier", (0, -L / 2, H), coll)
    flap = k.box("Haube_Front", -W / 2, W / 2, -L / 2 - t / 2, -L / 2 + t / 2, 0, H, coll, M["hood"])
    tab = bevel(k.box("Haube_Zuglasche", -12.5, 12.5, -L / 2 - 1.5, -L / 2 - 0.25, -18, 2, coll,
                      M["orange"]), 1.0)
    parent([flap, tab], hinge)
    side_tabs = [bevel(k.box(f"Haube_Lasche_{sx}", sx * (W / 2 + 0.25), sx * (W / 2 + 1.5), -12.5, 12.5,
                             -2, 18, coll, M["orange"]), 1.0) for sx in (-1, 1)]
    for o in side_tabs:  # bottom pull tabs on the side walls
        o.location.z = 0
    hood_root = empty("Haube", (0, 0, 0), coll)
    parent(parts + side_tabs + [hinge], hood_root)
    return hood_root, hinge


def paddle(coll):
    bm = bmesh.new()
    k.add_box(bm, 0, 100, -11, 11, 0, 6)
    handle = k.mesh_obj("Spatel_Griff", bm, coll, M["orange"])
    bevel(handle, 2.5, 3)
    blade = bevel(k.box("Spatel_Blatt", -58, 2, -10, 10, 1.5, 2.5, coll, M["rubber"]), 0.4, 2)
    tip = cyl("Spatel_Spitze", 2.0, 1.0, (-58, 0, 2.0), coll, M["rubber"], seg=16)
    root = empty("Spatel", (0, 0, 0), coll)
    parent([handle, blade, tip], root)
    return root


def spout(coll):
    """Clip-on pour spout: open-top trough 40 -> 30 mm wide, 50 long, with cup collar."""
    bm = bmesh.new()
    t, h = 1.6, 10.0
    w0, w1 = POUR_W / 2, SPOUT_OUT / 2
    prof = [(-w0 - t, 0), (w0 + t, 0), (w0 + t, h), (w0, h), (w0, t), (-w0, t), (-w0, h), (-w0 - t, h)]
    ring0 = [bm.verts.new((x, 0, z)) for x, z in prof]
    s = w1 / w0
    ring1 = [bm.verts.new((x * s, -SPOUT_L, z)) for x, z in prof]
    n = len(prof)
    for i in range(n):
        bm.faces.new((ring0[i], ring0[(i + 1) % n], ring1[(i + 1) % n], ring1[i]))
    bm.faces.new(list(reversed(ring0)))
    bm.faces.new(ring1)
    o = k.mesh_obj("Ausgiesser", bm, coll, M["orange"])
    root = empty("Ausgiesser_Gruppe", (0, 0, 0), coll)
    parent([o], root)
    return root, o


def cup(coll, loc):
    o = cyl("Becher_250ml", CUP_D / 2, CUP_H, (loc[0], loc[1], loc[2] + CUP_H / 2), coll, M["cup"], seg=64)
    boolean(o, cyl("cut", CUP_D / 2 - 1.2, CUP_H, (loc[0], loc[1], loc[2] + CUP_H / 2 + 1.2), coll, None, seg=64))
    return o


def pocket_scale(coll, loc, text):
    x, y, z = loc
    body = bevel(k.box("Waage", x - 65, x + 65, y - 80, y + 80, z, z + 18, coll, M["char"]), 4.0)
    pan = bevel(k.box("Waage_Schale", x - 60, x + 60, y - 50, y + 75, z + 18, z + 20, coll, M["alu"]), 1.0)
    disp = k.box("Waage_Display", x - 35, x + 35, y - 75, y - 57, z + 18, z + 18.3, coll,
                 k.material("LCD", (0.25, 0.32, 0.25), 0.3))
    bpy.ops.object.text_add(location=(x, y - 66, z + 18.4))
    t = bpy.context.active_object
    t.data.body, t.data.size, t.data.align_x, t.data.align_y = text, 11, "CENTER", "CENTER"
    t.data.materials.append(M["black"])
    for c in t.users_collection:
        c.objects.unlink(t)
    coll.objects.link(t)
    return [body, pan, disp, t]


def phone_with_screen(coll, count_text):
    ph = k.phone(coll)
    # lens cluster centre sits over the paper centre
    ph.location = (24.0, -60.0, Z_PLATE_TOP + 1.8)
    bpy.ops.object.text_add(location=(0, 0, 8.6))
    t = bpy.context.active_object
    t.data.body, t.data.size, t.data.align_x, t.data.align_y = count_text, 9.5, "CENTER", "CENTER"
    t.rotation_euler = (0, 0, math.pi / 2)
    t.data.materials.append(k.material("Screen_text", (1, 1, 1), 0.3, emit=((1, 1, 1), 3.0)))
    for c in t.users_collection:
        c.objects.unlink(t)
    coll.objects.link(t)
    t.parent = ph
    return ph


def kernel_pile(coll, centre, r, z0, n, seed=9):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=1)
    proto = bpy.context.active_object
    proto.scale = (1.65, 3.3, 1.4)
    bpy.ops.object.transform_apply(scale=True)
    proto.data.materials.append(bpy.data.materials["Korn_wheat"])
    rnd = random.Random(seed)
    for i in range(n):
        a, rr = rnd.uniform(0, math.tau), r * math.sqrt(rnd.random())
        o = bpy.data.objects.new("Korn_Becher", proto.data)
        o.location = (centre[0] + rr * math.cos(a), centre[1] + rr * math.sin(a),
                      z0 + 1.5 + rnd.uniform(0, 14) * (1 - 0.6 * rr / r))
        o.rotation_euler = [rnd.uniform(0, math.tau) for _ in range(3)]
        coll.objects.link(o)
    bpy.data.objects.remove(proto)


# --- export -----------------------------------------------------------------------------
def export_stl(objs, fn):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.wm.stl_export(filepath=str(OUT / "stl" / fn), export_selected_objects=True,
                          apply_modifiers=True, global_scale=1.0)


def descend(o):
    return [o] + [d for c in o.children for d in descend(c)]


def main():
    k.reset()
    OUT.mkdir(exist_ok=True)
    (OUT / "stl").mkdir(exist_ok=True)
    mats()
    sc = bpy.context.scene
    coll = bpy.data.collections.new("KornKlapp")
    sc.collection.children.link(coll)

    plate, feet = base(coll)
    cas, paper, plug, tab = cassette(coll)
    mk = markers(coll)
    pivots, bar, hinge_parts = gantry(coll)
    hood_root, flap = hood(coll)
    ph = phone_with_screen(coll, "Tausendkorn\n812 Körner\nTKG 47,3 g")
    pad = paddle(coll)
    sp_root, sp = spout(coll)
    sp_root.location = (0, -CAS_OUT[1] / 2 - 4, Z_CAS + CAS_FLOOR)
    for o in descend(sp_root):  # spout only appears in the transfer shot
        o.hide_render = True

    n = k.kernels(coll, 812, (-A4[0] / 2 + 3, A4[0] / 2 - 3, -A4[1] / 2 + 3, A4[1] / 2 - 3), Z_PAPER,
                  seed=7, min_gap=0.0)
    print(f"kernels on sheet: {n}")

    # STL: fabricated / printed parts (one file each)
    export_stl([plate], "basisplatte_300x380x2.stl")
    export_stl([cas], "kassette_230x317.stl")
    export_stl([plug, tab], "stopfen.stl")
    export_stl([sp], "ausgiesser.stl")
    export_stl([o for o in descend(bar) if o.type == "MESH" and o.name.startswith(("Handyauflage",))],
               "handyauflage.stl")
    export_stl([o for o in hinge_parts if o.name.startswith("Gelenkwange_-1")], "gelenkwangen_paar.stl")
    export_stl([o for o in descend(pad) if o.name == "Spatel_Griff"], "spatel_griff.stl")

    # --- scene ---
    cam = k.studio(sc, res=(960, 640) if DRAFT else (2400, 1600))
    sc.cycles.samples = 24 if DRAFT else 96
    for o in bpy.data.objects:
        if o.name == "Boden":
            o.data.materials[0] = k.material("Boden", (0.42, 0.40, 0.37), 0.95)  # wooden bench tone

    # 1 hero: assembled, hood front flap open, phone mounted
    flap.rotation_euler.x = math.radians(-95)
    pad.location = (150 + 40, -150, 0)
    pad.rotation_euler.z = math.radians(-20)
    k.shoot(OUT / "01_kornklapp_hero.png", cam, (560, -760, 640), (0, -10, 150), lens=42)

    # 2 spreading: hood off, paddle on the sheet, top three-quarter
    hood_root.hide_render = True
    for o in descend(hood_root):
        o.hide_render = True
    pad.location = (40, -70, Z_PAPER)
    pad.rotation_euler.z = math.radians(-35)
    k.shoot(OUT / "02_kornklapp_offen.png", cam, (-380, -560, 520), (10, -30, 60), lens=45)

    # 3 what the phone sees: main camera, 26 mm equivalent, from the lens position
    pad.location = (150 + 60, -120, 0)
    for o in descend(ph):
        o.hide_render = True
    sc.render.resolution_x, sc.render.resolution_y = ((480, 640) if DRAFT else (1500, 2000))
    cam.data.sensor_fit = "AUTO"
    cam.data.sensor_width = 43.27 * 0.8  # 4:3 frame with the 36x24 diagonal (26 mm eq.)
    cam.location = (0, 0, Z_LENS)
    cam.rotation_euler = (0, 0, 0)
    cam.data.lens = 26.0
    sc.render.filepath = str(OUT / "03_handyperspektive.png")
    bpy.ops.render.render(write_still=True)
    sc.render.resolution_x, sc.render.resolution_y = (960, 640) if DRAFT else (2400, 1600)
    cam.data.sensor_width = 36.0
    for o in descend(ph):
        o.hide_render = False

    # GLB of the assembled station (hood on, front flap open)
    for o in descend(hood_root):
        o.hide_render = False
    bpy.ops.object.select_all(action="DESELECT")
    for o in coll.all_objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT / "kornklapp.glb"), use_selection=True,
                              export_apply=True, export_yup=True)

    # 4 transfer: second cassette tilted into the cup, then the scale
    tcoll = bpy.data.collections.new("Umfuellen")
    sc.collection.children.link(tcoll)
    for o in descend(hood_root):
        o.hide_render = True
    c2, p2, pl2, t2 = cassette(tcoll, "Kassette_kippen")
    s2, s2o = spout(tcoll)
    s2.location = (0, -CAS_OUT[1] / 2 - 1, Z_CAS + CAS_FLOOR)
    tilt = empty("Kippen", (0, -CAS_OUT[1] / 2, Z_CAS), tcoll)
    parent([c2, p2, s2], tilt)
    for o in (pl2, t2):
        bpy.data.objects.remove(o)
    tilt.rotation_euler.x = math.radians(48)  # back edge up, pour toward -y
    tilt.location = (520, 30, 120)
    bpy.context.view_layer.update()
    out_pt = s2o.matrix_world @ Vector((0, -SPOUT_L, 0))
    cupo = cup(tcoll, (out_pt.x, out_pt.y - 18, 0))
    kernel_pile(tcoll, (out_pt.x, out_pt.y - 18), CUP_D / 2 - 6, 1.2, 420)
    grain = next(ob for ob in tcoll.objects if ob.name.startswith("Korn_Becher")).data
    for i, (dx, dz) in enumerate(((0, -6), (2, -20), (-1, -34), (1, -46))):  # grains in flight
        o = bpy.data.objects.new("Korn_fallend", grain)
        o.location = (out_pt.x + dx, out_pt.y - 6 - i * 2.5, out_pt.z + dz)
        o.rotation_euler = (i, 2 * i, i * 0.5)
        tcoll.objects.link(o)
    pocket_scale(tcoll, (out_pt.x + 180, out_pt.y - 10, 0), "38,42 g")
    k.shoot(OUT / "04_umfuellen_wiegen.png", cam, (out_pt.x + 420, out_pt.y - 560, 520),
            (out_pt.x + 60, out_pt.y + 80, 90), lens=40)
    tcoll.hide_render = True

    # 5 folded: crossbar off, inner tubes down, posts folded flat toward the front
    for piv, tele in pivots:
        tele.location.z -= 150
        piv.rotation_euler.x = math.radians(90)  # top swings toward the front (-y)
    bar.location = (0, -40, 72)  # crossbar + rest laid across the folded posts
    for o in descend(ph):
        o.hide_render = True
    pad.location = (60, -200 - 10, 0)
    k.shoot(OUT / "05_zusammengeklappt.png", cam, (520, -640, 420), (0, -20, 30), lens=50)

    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "kornklapp.blend"))


main()
