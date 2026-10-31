"""Kornwaschpfanne prototypes A, B, C (Astra's spec, ASTRA_DESIGN.md): CAD, STL, GLB, renders.

Pan bodies are revolved from the profiles in designs.py (same geometry the simulation uses),
plus grip tabs, a railed pour lip and four ArUco markers (DICT_4X4_50, IDs 0-3) on the
flange. If out/sim/<design>_grains.json exists, the simulated grains are placed in the pan
(touching kernels optionally tinted red with --contacts).

  blender --background --python-exit-code 1 --python build_pfannen.py [-- --draft] [--contacts]

Units: millimetres. Outputs in out/.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "station"))
import designs as D  # noqa: E402
import scene_kit as k  # noqa: E402

OUT = HERE / "out"
DRAFT = "--draft" in sys.argv
CONTACTS = "--contacts" in sys.argv
PANS = ("A", "B", "C")
FLOOR_T, WALL_T = 3.0, 2.0
TAB = (50.0, 25.0, 3.0)                 # tangential x radial x thick, from r = 180
LIP_L, LIP_W0, LIP_W1, RAIL_H = 25.0, 40.0, 25.0, 3.0
MARKER, QUIET, MARKER_R = 18.0, 3.0, 167.5
ARUCO_4X4_50 = {
    0: ((1, 0, 1, 1), (0, 1, 0, 1), (0, 0, 1, 1), (0, 0, 1, 0)),
    1: ((0, 0, 0, 0), (1, 1, 1, 1), (1, 0, 0, 1), (1, 0, 1, 0)),
    2: ((0, 0, 1, 1), (0, 0, 1, 1), (0, 0, 1, 0), (1, 1, 0, 1)),
    3: ((1, 0, 0, 1), (1, 0, 0, 1), (0, 1, 0, 0), (0, 1, 1, 0)),
}
IVORY = (0.80, 0.76, 0.66)


def revolve(name, profile, thickness, coll, mat, seg=192):
    bm = bmesh.new()
    top, bot = [], []
    for i in range(seg):
        a = math.tau * i / seg
        c, s = math.cos(a), math.sin(a)
        top.append([bm.verts.new((r * c, r * s, z)) for r, z in profile[1:]])
        bot.append([bm.verts.new((r * c, r * s, z - thickness)) for r, z in profile[1:]])
    ct = bm.verts.new((0, 0, profile[0][1]))
    cb = bm.verts.new((0, 0, profile[0][1] - thickness))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((ct, top[i][0], top[j][0]))
        bm.faces.new((cb, bot[j][0], bot[i][0]))
        for q in range(len(profile) - 2):
            bm.faces.new((top[i][q], top[i][q + 1], top[j][q + 1], top[j][q]))
            bm.faces.new((bot[i][q], bot[j][q], bot[j][q + 1], bot[i][q + 1]))
        bm.faces.new((top[i][-1], bot[i][-1], bot[j][-1], top[j][-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = k.mesh_obj(name, bm, coll, mat)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    return o


def union(target, parts):
    for p in parts:
        m = target.modifiers.new("u", "BOOLEAN")
        m.operation, m.object, m.solver = "UNION", p, "EXACT"
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.data.objects.remove(p)
    return target


def appendages(coll, mat):
    """Grip tabs at 90/270 deg and the pour lip with side rails at 0 deg (+x)."""
    z1 = D.H_WALL
    parts = []
    for ang in (90, 270):
        t = k.box("tab", -TAB[0] / 2, TAB[0] / 2, D.R_RIM - 2, D.R_RIM + TAB[1], z1 - TAB[2], z1, coll, mat)
        t.rotation_euler.z = math.radians(ang - 90)
        bpy.context.view_layer.objects.active = t
        t.select_set(True)
        bpy.ops.object.transform_apply(rotation=True)
        parts.append(t)
    bm = bmesh.new()
    x0, x1 = D.R_RIM - 2, D.R_RIM + LIP_L
    quad = [(x0, -LIP_W0 / 2), (x1, -LIP_W1 / 2), (x1, LIP_W1 / 2), (x0, LIP_W0 / 2)]
    lo = [bm.verts.new((x, y, z1 - WALL_T)) for x, y in quad]
    hi = [bm.verts.new((x, y, z1)) for x, y in quad]
    bm.faces.new(lo[::-1])
    bm.faces.new(hi)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    lip = k.mesh_obj("lip", bm, coll, mat)
    taper = math.atan2((LIP_W0 - LIP_W1) / 2, LIP_L)
    rail_l = math.hypot(LIP_L, (LIP_W0 - LIP_W1) / 2)
    for sy in (-1, 1):  # side rails following the taper
        rail = k.box("rail", -rail_l / 2 - 1, rail_l / 2, -1.0, 1.0, z1 - 1.0, z1 + RAIL_H, coll, mat)
        rail.matrix_world = (Matrix.Translation(((x0 + x1) / 2, sy * ((LIP_W0 + LIP_W1) / 4 - 1.0), 0))
                             @ Matrix.Rotation(-sy * taper, 4, "Z"))
        bpy.context.view_layer.objects.active = rail
        bpy.ops.object.select_all(action="DESELECT")
        rail.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True)
        parts.append(rail)
    bpy.ops.object.select_all(action="DESELECT")
    lip.select_set(True)
    bpy.context.view_layer.objects.active = lip
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    parts.append(lip)
    return parts


def markers(coll, z):
    white = k.material("Marker_weiss", (0.9, 0.9, 0.9), 0.8)
    black = k.material("Marker_schwarz", (0.01, 0.01, 0.01), 0.8)
    out = []
    cell = MARKER / 6
    for mid, ang in zip(range(4), (135, 45, 315, 225)):  # clockwise from upper-left
        a = math.radians(ang)
        bm = bmesh.new()
        h = MARKER / 2 + QUIET
        k.add_box(bm, -h, h, -h, h, 0, 0.1)
        pad = k.mesh_obj(f"Marker_{mid}_Rand", bm, coll, white)
        bm = bmesh.new()
        k.add_box(bm, -MARKER / 2, MARKER / 2, -MARKER / 2, MARKER / 2, 0.1, 0.15)
        sq = k.mesh_obj(f"Marker_{mid}", bm, coll, black)
        bm = bmesh.new()
        for r, row in enumerate(ARUCO_4X4_50[mid]):
            for c, bit in enumerate(row):
                if bit:
                    x = -MARKER / 2 + (c + 1) * cell
                    y = MARKER / 2 - (r + 1) * cell
                    k.add_box(bm, x, x + cell, y - cell, y, 0.15, 0.2)
        bits = k.mesh_obj(f"Marker_{mid}_Bits", bm, coll, white)
        for o in (pad, sq, bits):
            o.matrix_world = (Matrix.Translation((MARKER_R * math.cos(a), MARKER_R * math.sin(a), z))
                              @ Matrix.Rotation(a - math.pi / 2, 4, "Z"))
            out.append(o)
    return out


def grains_from_sim(name, coll, root):
    f = OUT / "sim" / f"{name}_grains.json"
    if not f.exists():
        return 0
    poses = json.loads(f.read_text())
    protos = {}
    cols = {"korn": (0.62, 0.40, 0.17), "bruch": (0.78, 0.55, 0.26), "spreu": (0.86, 0.80, 0.56)}
    red = k.material("Korn_beruehrt", (0.85, 0.08, 0.05), 0.45)
    for kind in cols:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=8, radius=1)
        p = bpy.context.active_object
        if kind == "spreu":
            bpy.data.objects.remove(p)
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1)
            for v in bm.verts:
                v.co = Vector((v.co.x * 4.0, v.co.y * 6.5, v.co.z * 0.3))
            me = bpy.data.meshes.new("spreu")
            bm.to_mesh(me)
            bm.free()
        else:
            me = p.data
            for v in me.vertices:
                v.co.y *= 1.0 + 0.1 * v.co.y
                v.co = Vector((v.co.x * 1.65, v.co.y * 3.3, v.co.z * 1.4))
                if kind == "bruch" and v.co.y > 0.2:
                    v.co.y = 0.2
            bpy.data.objects.remove(p)
            for poly in me.polygons:
                poly.use_smooth = True
        me.materials.append(k.material("Korn_" + kind, cols[kind], 0.45))
        protos[kind] = me
    touching_me = {}
    n = 0
    for g in poses:
        me = protos[g["kind"]]
        if CONTACTS and g["touching"]:
            if g["kind"] not in touching_me:
                touching_me[g["kind"]] = me.copy()
                touching_me[g["kind"]].materials[0] = red
            me = touching_me[g["kind"]]
        o = bpy.data.objects.new("Korn", me)
        m = Matrix([row for row in g["m"]])
        loc, rot, _ = m.decompose()
        o.matrix_world = Matrix.Translation(loc * 10) @ rot.to_matrix().to_4x4()
        o.parent = root
        coll.objects.link(o)
        n += 1
    return n


def build_pan(name, coll):
    ivory = k.material("PP_elfenbein_matt", IVORY, 0.75)
    body = revolve(f"Pfanne_{name}", D.DESIGNS[name]["profile"], FLOOR_T, coll, ivory)
    union(body, appendages(coll, ivory))
    return body


def contact_views(sc, cam, roots):
    """Top-down of every simulated end state, touching kernels red: 13_kontakte_<sim>.png."""
    for o in bpy.data.objects:
        if o.type == "FONT":
            o.hide_render = True
    sims = sorted(p.stem[:-7] for p in (OUT / "sim").glob("*_grains.json"))
    sc.render.resolution_x = sc.render.resolution_y = 1400
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2 * D.R_RIM + 20
    cam.location, cam.rotation_euler = (0, 0, 900), (0, 0, 0)
    for sim in sims:
        coll = bpy.data.collections.new(f"Sim_{sim}")
        sc.collection.children.link(coll)
        root = bpy.data.objects.new(f"Sim_{sim}_Gruppe", None)
        coll.objects.link(root)
        if sim == "FLAT":
            k.box("A4", -105, 105, -148.5, 148.5, -0.3, 0, coll, k.material("Papier", (0.92, 0.92, 0.9), 0.9))
        else:
            body = revolve(f"Pfanne_{sim}", D.DESIGNS[sim]["profile"], FLOOR_T, coll,
                           k.material("PP_elfenbein_matt", IVORY, 0.75))
            body.parent = root
        grains_from_sim(sim, coll, root)
        for name in PANS:
            for o in [roots[name]] + roots[name].children_recursive:
                o.hide_render = True
        for other in bpy.data.collections:
            if other.name.startswith("Sim_"):
                other.hide_render = other is not coll
        sc.render.filepath = str(OUT / "sim" / f"13_kontakte_{sim}.png")
        bpy.ops.render.render(write_still=True)
        coll.hide_render = True
    cam.data.type = "PERSP"
    for name in PANS:
        for o in [roots[name]] + roots[name].children_recursive:
            o.hide_render = False


def main():
    k.reset()
    OUT.mkdir(exist_ok=True)
    (OUT / "stl").mkdir(exist_ok=True)
    sc = bpy.context.scene
    roots = {}
    for i, name in enumerate(PANS):
        coll = bpy.data.collections.new(f"Pfanne_{name}")
        sc.collection.children.link(coll)
        body = build_pan(name, coll)
        bpy.ops.object.select_all(action="DESELECT")
        body.select_set(True)
        if not CONTACTS:  # the contact run only renders; exports come from the clean run
            bpy.ops.wm.stl_export(filepath=str(OUT / "stl" / f"pfanne_{name}.stl"), export_selected_objects=True)
        root = bpy.data.objects.new(f"Pfanne_{name}_Gruppe", None)
        coll.objects.link(root)
        body.parent = root
        for o in markers(coll, D.H_WALL):
            o.parent = root
        n = grains_from_sim(name, coll, root)
        print(f"pan {name}: grains placed {n}")
        roots[name] = root

    cam = k.studio(sc, res=(1200, 800) if DRAFT else (2400, 1600))
    sc.cycles.samples = 24 if DRAFT else 96
    for o in bpy.data.objects:
        if o.name == "Boden":
            o.data.materials[0] = k.material("Boden", (0.30, 0.31, 0.32), 0.9)

    # lineup: three pans side by side, slightly overlapping fan
    spacing = 420
    for i, name in enumerate(PANS):
        roots[name].location = ((i - 1) * spacing, (abs(i - 1)) * 60, 0)
        roots[name].rotation_euler.z = math.radians(-90 + (i - 1) * 25)
    for i, name in enumerate(PANS):  # labels on the floor
        bpy.ops.object.text_add(location=((i - 1) * spacing, -250 + abs(i - 1) * 60, 0.2))
        t = bpy.context.active_object
        t.data.body, t.data.size, t.data.align_x = D.DESIGNS[name]["label"], 20, "CENTER"
        t.data.materials.append(k.material("Label", (0.92, 0.92, 0.9), 0.6))
    sfx = "_kontakte" if CONTACTS else ""
    k.shoot(OUT / f"10_pfannen_aufstellung{sfx}.png", cam, (0, -1250, 900), (0, 0, 0), lens=40)

    # top-down per pan (the phone's view), others hidden
    sc.render.resolution_x, sc.render.resolution_y = (800, 800) if DRAFT else (1800, 1800)
    for name in PANS:
        for other in PANS:
            for o in roots[other].children_recursive + [roots[other]]:
                o.hide_render = other != name
        roots[name].location = (0, 0, 0)
        roots[name].rotation_euler.z = 0
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 2 * (D.R_RIM + LIP_L) + 20
        cam.location, cam.rotation_euler = (0, 0, 900), (0, 0, 0)
        sc.render.filepath = str(OUT / f"11_pfanne_{name}_draufsicht{sfx}.png")
        bpy.ops.render.render(write_still=True)
    cam.data.type = "PERSP"
    for name in PANS:
        for o in roots[name].children_recursive + [roots[name]]:
            o.hide_render = False

    # hero close-up of pan A with grains
    sc.render.resolution_x, sc.render.resolution_y = (1200, 800) if DRAFT else (2400, 1600)
    for name in PANS:
        roots[name].location = (0, 0, 0) if name == "A" else (2000, 2000 * PANS.index(name), 0)
    for o in bpy.data.objects:
        if o.type == "FONT":
            o.hide_render = True
    k.shoot(OUT / f"12_pfanne_A_nah{sfx}.png", cam, (330, -420, 330), (20, 0, 0), lens=45)

    if CONTACTS:
        contact_views(sc, cam, roots)
        return

    bpy.ops.object.select_all(action="DESELECT")
    for name in PANS:
        roots[name].location = ((PANS.index(name) - 1) * spacing, 0, 0)
        for o in [roots[name]] + roots[name].children_recursive:
            if not o.name.startswith("Korn"):
                o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT / "pfannen.glb"), use_selection=True, export_apply=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "pfannen.blend"))


main()
