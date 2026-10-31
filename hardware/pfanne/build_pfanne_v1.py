"""Tausendkorn-Pfanne v1 (after Astra review, see ASTRA_REVIEW_v0.md).

500-well wheat cassette (used twice), carrier tray with open front apron, separate
handle, and six 5x4 test coupons (width 4.0/4.4/4.8 x depth 1.6/2.0).
Wells are real cut-outs: rounded rectangles with a 45-degree entry chamfer, made by one
exact boolean against a joined cutter mesh.

  blender --background --python-exit-code 1 --python hardware/pfanne/build_pfanne_v1.py [-- --fill]

Units: millimetres. Outputs in hardware/pfanne/out_v1/.
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WHEAT = dict(cols=25, rows=20, w=4.4, l=8.2, d=1.8, r=1.0)
RIB = 1.2
CHAMFER = 0.4                  # each side, 45 degrees -> 0.4 mm crest
FLOOR = 1.2
PAD = 10.0
CLEARANCE = 0.3
WALL = 2.0
RIM_H = 12.0
BASE_T = 1.6
APRON = 25.0
LIP_T = 0.8
HANDLE_LEN, HANDLE_W, HANDLE_T, HANDLE_DEG = 110.0, 34.0, 18.0, 12.0
COUPONS = [(w, d) for d in (1.6, 2.0) for w in (4.0, 4.4, 4.8)]

OUT = Path(__file__).resolve().parent / "out_v1"
FILL = "--fill" in sys.argv


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    u = bpy.context.scene.unit_settings
    u.system, u.scale_length, u.length_unit = "METRIC", 0.001, "MILLIMETERS"


def link(obj, coll):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def mesh_obj(name, bm, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def add_box(bm, x0, x1, y0, y1, z0, z1):
    bmesh.ops.create_cube(bm, size=1, matrix=(
        __import__("mathutils").Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        @ __import__("mathutils").Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1))))


def rounded_ring(cx, cy, w, l, r, seg=4):
    r = min(r, w / 2 - 1e-3, l / 2 - 1e-3)
    pts = []
    for qx, qy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (w / 2 - r), cy + qy * (l / 2 - r)
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def add_well_cutter(bm, cx, cy, w, l, r, z_floor, z_top):
    """Rounded-rect pocket from floor to z_top-CHAMFER, then 45-degree flare to z_top."""
    rings = [
        (rounded_ring(cx, cy, w, l, r), z_floor),
        (rounded_ring(cx, cy, w, l, r), z_top - CHAMFER),
        (rounded_ring(cx, cy, w + 2 * CHAMFER, l + 2 * CHAMFER, r + CHAMFER), z_top),
        (rounded_ring(cx, cy, w + 2 * CHAMFER + 0.2, l + 2 * CHAMFER + 0.2, r + CHAMFER + 0.1), z_top + 1.0),
    ]
    loops = [[bm.verts.new((x, y, z)) for x, y in ring] for ring, z in rings]
    n = len(loops[0])
    for a, b in zip(loops, loops[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(list(reversed(loops[0])))
    bm.faces.new(loops[-1])


def cassette(name, cols, rows, w, l, d, r, coll, pad=PAD):
    pitch_x, pitch_y = w + RIB, l + RIB
    field_w, field_l = cols * pitch_x + RIB, rows * pitch_y + RIB
    W, L, H = field_w + 2 * pad, field_l + 2 * pad, FLOOR + d
    bm = bmesh.new()
    add_box(bm, -W / 2, W / 2, -L / 2, L / 2, 0, H)
    slab = mesh_obj(name, bm, coll)
    bm = bmesh.new()
    for i in range(cols):
        for j in range(rows):
            add_well_cutter(bm, -field_w / 2 + RIB + w / 2 + i * pitch_x,
                            -field_l / 2 + RIB + l / 2 + j * pitch_y, w, l, r, FLOOR, H)
    cutter = mesh_obj(name + "_cutter", bm, coll)
    mod = slab.modifiers.new("wells", "BOOLEAN")
    mod.operation, mod.object, mod.solver = "DIFFERENCE", cutter, "EXACT"
    bpy.context.view_layer.objects.active = slab
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    slab["size_mm"] = (W, L, H)
    return slab, (W, L, H, field_w, field_l, pitch_x, pitch_y)


def carrier(cas_W, cas_L, coll):
    iw, il = cas_W + 2 * CLEARANCE, cas_L + 2 * CLEARANCE
    ow, ol = iw + 2 * WALL, il + WALL
    cas_top = BASE_T + FLOOR + WHEAT["d"]
    top = cas_top + RIM_H
    bm = bmesh.new()
    add_box(bm, -ow / 2, ow / 2, -il / 2, ol - il / 2, 0, BASE_T)                     # floor
    add_box(bm, -ow / 2, -iw / 2, -il / 2, ol - il / 2, 0, top)                        # left wall
    add_box(bm, iw / 2, ow / 2, -il / 2, ol - il / 2, 0, top)                          # right wall
    add_box(bm, -ow / 2, ow / 2, il / 2, ol - il / 2, 0, top)                          # back wall
    # apron: open front, floor flush with cassette crest, thinning to a rounded lip
    apron = bmesh.new()
    y0, y1 = -il / 2 - APRON, -il / 2
    v = [apron.verts.new(p) for p in (
        (-ow / 2, y1, 0), (ow / 2, y1, 0), (ow / 2, y1, cas_top), (-ow / 2, y1, cas_top),
        (-ow / 2, y0, 0), (ow / 2, y0, 0), (ow / 2, y0, LIP_T), (-ow / 2, y0, LIP_T))]
    for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)):
        apron.faces.new([v[i] for i in f])
    tmp = bpy.data.meshes.new("apron_tmp")
    apron.to_mesh(tmp)
    apron.free()
    bm.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)
    # side guides over the apron, tapering from wall height to the lip
    for sx in (-1, 1):
        x0, x1 = (sx * iw / 2, sx * ow / 2) if sx > 0 else (sx * ow / 2, sx * iw / 2)
        g = [bm.verts.new(p) for p in (
            (x0, y1, 0), (x1, y1, 0), (x1, y1, top), (x0, y1, top),
            (x0, y0, 0), (x1, y0, 0), (x1, y0, LIP_T + 1.5), (x0, y0, LIP_T + 1.5))]
        for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)):
            bm.faces.new([g[i] for i in f])
    # side retention ribs: 0.6 mm bumps at cassette crest height (snap-in by flex)
    for sx in (-1, 1):
        add_box(bm, sx * iw / 2 - (0.6 if sx > 0 else 0), sx * iw / 2 + (0.6 if sx < 0 else 0),
                -20, 20, cas_top - 0.4, cas_top + 0.6)
    # bm holds overlapping closed shells; union them exactly into one manifold solid
    shells = mesh_obj("Traeger_shells", bm, coll)
    bpy.context.view_layer.objects.active = shells
    bpy.ops.object.select_all(action="DESELECT")
    shells.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    pieces = list(bpy.context.selected_objects)
    o = pieces[0]
    o.name = "Traeger"
    for p in pieces[1:]:
        m = o.modifiers.new("u", "BOOLEAN")
        m.operation, m.object, m.solver = "UNION", p, "EXACT"
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.data.objects.remove(p)
    return o, (ow, ol + APRON, top, il)


def handle(carrier_back_y, top, coll):
    tilt = math.radians(HANDLE_DEG)
    bm = bmesh.new()
    add_box(bm, -HANDLE_W / 2, HANDLE_W / 2, -8, HANDLE_LEN, -HANDLE_T / 2, HANDLE_T / 2)
    for v in bm.verts:
        y, z = v.co.y, v.co.z
        v.co.y = y * math.cos(tilt) - z * math.sin(tilt) + carrier_back_y
        v.co.z = y * math.sin(tilt) + z * math.cos(tilt) + top * 0.55
    o = mesh_obj("Griff", bm, coll)
    b = o.modifiers.new("round", "BEVEL")
    b.width, b.segments = 6, 6
    return o


def material(name, rgb, rough=0.7):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    return m


def markers(W, L, z, coll):
    """Four distinguishable 4x4 bit patterns (stand-ins for ArUco 4x4 IDs 0-3)."""
    white, black = material("weiss", (0.95, 0.95, 0.95), 0.5), material("schwarz", (0.02, 0.02, 0.02))
    rnd = random.Random(3)
    s = PAD - 2.0
    for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        cx, cy = sx * (W - PAD) / 2, sy * (L - PAD) / 2
        bpy.ops.mesh.primitive_plane_add(size=s, location=(cx, cy, z + 0.02))
        link(bpy.context.active_object, coll).data.materials.append(black)
        cell = s / 6
        for i in range(4):
            for j in range(4):
                if rnd.random() < 0.5:
                    bpy.ops.mesh.primitive_plane_add(size=cell, location=(
                        cx + (i - 1.5) * cell, cy + (j - 1.5) * cell, z + 0.04))
                    link(bpy.context.active_object, coll).data.materials.append(white)


def fill_kernels(geo, z, coll, n_double=3, n_empty=4):
    W, L, H, field_w, field_l, px, py = geo
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1)
    proto = bpy.context.active_object
    proto.scale = (3.3 / 2, 6.8 / 2, 2.9 / 2)
    bpy.ops.object.transform_apply(scale=True)
    proto.data.materials.append(material("Weizen", (0.62, 0.38, 0.14), 0.5))
    rnd = random.Random(11)
    cells = [(i, j) for i in range(WHEAT["cols"]) for j in range(WHEAT["rows"])]
    empty = set(rnd.sample(cells, n_empty))
    double = set(rnd.sample([c for c in cells if c not in empty], n_double))
    for i, j in cells:
        if (i, j) in empty:
            continue
        cx = -field_w / 2 + RIB + WHEAT["w"] / 2 + i * px
        cy = -field_l / 2 + RIB + WHEAT["l"] / 2 + j * py
        s = rnd.uniform(0.9, 1.08)
        for extra in range(2 if (i, j) in double else 1):
            o = proto.copy()
            o.scale = (s, s, s)
            o.location = (cx + rnd.uniform(-0.3, 0.3) + extra * 0.8,
                          cy + rnd.uniform(-0.5, 0.5), z + 1.3 + extra * 2.2)
            o.rotation_euler = (0, rnd.uniform(-0.15, 0.15) + extra * 0.4, rnd.uniform(-0.08, 0.08))
            coll.objects.link(o)
    bpy.data.objects.remove(proto)


def render(name, cam, pos, at):
    cam.location = pos
    cam.rotation_euler = (Vector(at) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)


def export(obj, fn):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=str(OUT / fn), export_selected_objects=True, apply_modifiers=True)


def main():
    reset()
    OUT.mkdir(exist_ok=True)
    coll = bpy.data.collections.new("Tausendkorn_v1")
    bpy.context.scene.collection.children.link(coll)

    cas, geo = cassette("Kassette_Weizen_500", **WHEAT, coll=coll)
    W, L, H = geo[:3]
    car, (cw, cl, top, il) = carrier(W, L, coll)
    cas.location.z = BASE_T
    grip = handle(il / 2 + WALL - 2, top, coll)
    print(f"cassette {W:.1f} x {L:.1f} x {H:.1f} mm; carrier {cw:.1f} x {cl:.1f} x {top:.1f} mm")

    export(cas, "kassette_weizen_500.stl")
    export(car, "traeger.stl")
    export(grip, "griff.stl")

    # test coupons, laid out in a row for one print
    coup_coll = bpy.data.collections.new("Testcoupons")
    bpy.context.scene.collection.children.link(coup_coll)
    x = 0
    for w, d in COUPONS:
        c, g = cassette(f"Coupon_w{w}_d{d}", 5, 4, w, WHEAT["l"], d, WHEAT["r"], coup_coll, pad=4.0)
        export(c, f"coupon_w{w:.1f}_d{d:.1f}.stl")
        c.location = (x + 300, 0, 0)
        x += g[0] + 6
        print(f"coupon w{w} d{d}: {g[0]:.1f} x {g[1]:.1f} mm")

    dark = material("Mattanthrazit", (0.05, 0.05, 0.055), 0.85)
    for o in (cas, car, grip):
        o.data.materials.append(dark)
    for o in coup_coll.objects:
        o.data.materials.append(material("PLA_grau", (0.35, 0.36, 0.38), 0.6))
    markers(W, L, BASE_T + H, coll)
    if FILL:
        fill_kernels(geo, BASE_T + FLOOR, coll)

    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x, s.render.resolution_y = 1600, 1200
    s.world = bpy.data.worlds.new("w")
    s.world.use_nodes = True
    s.world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.88, 1)
    for loc in ((200, -250, 450), (-250, 100, 400)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        bpy.context.active_object.data.energy, bpy.context.active_object.data.size = 1.5e6, 300
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.data.clip_end = 5000
    s.camera = cam
    sfx = "_gefuellt" if FILL else ""
    render(f"v1_perspektive{sfx}", cam, (230, -420, 330), (0, 0, 10))
    render(f"v1_detail{sfx}", cam, (45, -95, 45), (15, -55, 3))
    render("v1_coupons", cam, (430, -260, 260), (430, 0, 0))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "pfanne_v1.blend"))


main()
