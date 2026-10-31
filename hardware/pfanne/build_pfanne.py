"""Tausendkorn-Pfanne: parametric scoop pan with a 1000-well kernel insert.

Run headless (Blender 5.0):
  blender --background --python-exit-code 1 --python hardware/pfanne/build_pfanne.py -- [--fill]

Writes pfanne.blend, pfanne_body.stl, einsatz_weizen.stl and renders into hardware/pfanne/out/.
Units: millimetres (scene unit scale 0.001).
"""

import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# --- parameters (wheat insert) -------------------------------------------------------
COLS, ROWS = 40, 25            # 1000 wells
WELL_W, WELL_L = 4.0, 7.5      # opening across / along the pour direction
WELL_D = 3.0                   # depth = rib height above insert floor
RIB = 1.2                      # rib width
INSERT_FLOOR = 1.6
WALL = 2.4                     # pan wall thickness
RIM_H = 22.0                   # rim height above insert top
LIP_LEN = 45.0                 # scoop lip in front of the well field
HANDLE_LEN, HANDLE_W, HANDLE_T = 130.0, 32.0, 14.0
PAD = 14.0                     # marker pad size at the field corners
BASE_T = 2.0                   # pan floor under the insert

OUT = Path(__file__).resolve().parent / "out"
FILL = "--fill" in sys.argv

field_w = COLS * WELL_W + (COLS + 1) * RIB          # x: across
field_l = ROWS * WELL_L + (ROWS + 1) * RIB          # y: along pour direction (front = -y)
insert_w = field_w + 2 * PAD
insert_l = field_l + 2 * PAD
insert_h = INSERT_FLOOR + WELL_D


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 0.001
    s.unit_settings.length_unit = "MILLIMETERS"


def box(name, size, loc, coll):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    for c in o.users_collection:
        c.objects.unlink(o)
    coll.objects.link(o)
    return o


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    return o


def union_all(obj):
    """Merge overlapping boxes into one manifold shell for printing."""
    m = obj.modifiers.new("remesh", "REMESH")
    m.mode = "SHARP"
    m.octree_depth = 10
    m.use_remove_disconnected = False


def material(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def build_insert(coll):
    parts = [box("insert_floor", (insert_w, insert_l, INSERT_FLOOR),
                 (0, 0, INSERT_FLOOR / 2), coll)]
    z = INSERT_FLOOR + WELL_D / 2
    x0, y0 = -field_w / 2, -field_l / 2
    for i in range(COLS + 1):     # ribs along y
        parts.append(box(f"rx{i}", (RIB, field_l, WELL_D),
                         (x0 + RIB / 2 + i * (WELL_W + RIB), 0, z), coll))
    for j in range(ROWS + 1):     # ribs along x
        parts.append(box(f"ry{j}", (field_w, RIB, WELL_D),
                         (0, y0 + RIB / 2 + j * (WELL_L + RIB), z), coll))
    for sx in (-1, 1):            # flush marker pads at the four corners
        for sy in (-1, 1):
            parts.append(box(f"pad{sx}{sy}", (PAD, PAD, WELL_D),
                             (sx * (insert_w - PAD) / 2, sy * (insert_l - PAD) / 2, z), coll))
    # solid border between field and pads
    for sx in (-1, 1):
        parts.append(box(f"bx{sx}", (PAD, insert_l, WELL_D), (sx * (insert_w - PAD) / 2, 0, z), coll))
    for sy in (-1, 1):
        parts.append(box(f"by{sy}", (insert_w, PAD, WELL_D), (0, sy * (insert_l - PAD) / 2, z), coll))
    ins = join(parts, "Einsatz_Weizen")
    ins.location.z = BASE_T
    return ins


def build_body(coll):
    w, l = insert_w + 2 * WALL, insert_l + 2 * WALL
    top = BASE_T + insert_h + RIM_H
    parts = [box("base", (w, l + LIP_LEN, BASE_T), (0, -LIP_LEN / 2, BASE_T / 2), coll)]
    for sx in (-1, 1):
        # full-height wall along the well field
        parts.append(box(f"side{sx}", (WALL, l, top), (sx * (w - WALL) / 2, 0, top / 2), coll))
        # wedge over the scoop lip, sloping from full height down to the lip edge
        wedge = box(f"lipwall{sx}", (WALL, LIP_LEN, top), (sx * (w - WALL) / 2, -l / 2 - LIP_LEN / 2, top / 2), coll)
        for v in wedge.data.vertices:
            if v.co.z > 0 and v.co.y < -l / 2 - LIP_LEN / 2:
                v.co.z = -top / 2 + BASE_T + 3.0
        parts.append(wedge)
    parts.append(box("back", (w, WALL, top), (0, (l - WALL) / 2, top / 2), coll))
    # front stop so the insert cannot slide out, low enough to pour over
    parts.append(box("insert_stop", (w, WALL, BASE_T + insert_h + 1.0),
                     (0, -(l - WALL) / 2, (BASE_T + insert_h + 1.0) / 2), coll))
    body = join(parts, "Pfanne")
    # handle: rounded bar leaving the back wall at mid height, rising 15 degrees
    tilt = math.radians(15)
    # box spanning y in [0, HANDLE_LEN] from a hinge on the back wall, then tilted up
    h = box("Griff", (HANDLE_W, HANDLE_LEN + 6, HANDLE_T), (0, (HANDLE_LEN + 6) / 2 - 6, 0), coll)
    for v in h.data.vertices:
        y, z = v.co.y, v.co.z
        v.co.y = y * math.cos(tilt) - z * math.sin(tilt) + l / 2
        v.co.z = y * math.sin(tilt) + z * math.cos(tilt) + top * 0.6
    bev = h.modifiers.new("bevel", "BEVEL")
    bev.width, bev.segments = 5, 6
    bpy.context.view_layer.update()
    ys = [v.co.y for v in h.data.vertices]
    print(f"handle y {min(ys):.0f}..{max(ys):.0f}, back wall at {l / 2:.0f}")
    for c in h.users_collection:
        c.objects.unlink(h)
    coll.objects.link(h)
    return body, h


def add_kernels(coll, insert):
    """Scatter wheat kernels into the wells for presentation renders."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1)
    k = bpy.context.active_object
    k.name = "korn_proto"
    k.scale = (3.2 / 2, 6.6 / 2, 2.8 / 2)
    bpy.ops.object.transform_apply(scale=True)
    k.data.materials.append(material("Korn", (0.62, 0.38, 0.14), 0.5))
    rnd = random.Random(7)
    x0, y0 = -field_w / 2 + RIB + WELL_W / 2, -field_l / 2 + RIB + WELL_L / 2
    z = BASE_T + INSERT_FLOOR + 1.4
    for i in range(COLS):
        for j in range(ROWS):
            if rnd.random() < 0.006:   # a few empty wells, like a real fill
                continue
            o = k.copy()
            o.location = (x0 + i * (WELL_W + RIB) + rnd.uniform(-0.25, 0.25),
                          y0 + j * (WELL_L + RIB) + rnd.uniform(-0.4, 0.4), z)
            o.rotation_euler = (0, rnd.uniform(-0.2, 0.2), rnd.uniform(-0.06, 0.06))
            coll.objects.link(o)
    bpy.data.objects.remove(k)


def scene_setup(target):
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x, s.render.resolution_y = 1600, 1200
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.92, 0.9, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    s.world = world
    bpy.ops.object.light_add(type="AREA", location=(150, -250, 500))
    sun = bpy.context.active_object
    sun.data.energy = 3e6
    sun.data.size = 400
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.data.lens = 50
    cam.data.clip_end = 10000
    s.camera = cam
    return cam


def look(cam, pos, at=(0, -20, 10)):
    cam.location = pos
    d = Vector(at) - Vector(pos)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def main():
    reset()
    OUT.mkdir(exist_ok=True)
    coll = bpy.data.collections.new("Tausendkorn")
    bpy.context.scene.collection.children.link(coll)
    ins = build_insert(coll)
    body, handle = build_body(coll)
    black = material("Mattschwarz", (0.03, 0.03, 0.035), 0.8)
    for o in (ins, body, handle):
        o.data.materials.append(black)
    marker = material("Marker", (0.95, 0.95, 0.95), 0.4)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bpy.ops.mesh.primitive_plane_add(size=PAD - 3, location=(
                sx * (insert_w - PAD) / 2, sy * (insert_l - PAD) / 2, BASE_T + insert_h + 0.05))
            bpy.context.active_object.data.materials.append(marker)

    print(f"field {field_w:.1f} x {field_l:.1f} mm, insert {insert_w:.1f} x {insert_l:.1f} mm, "
          f"wells {COLS * ROWS}")

    bpy.ops.object.select_all(action="DESELECT")
    for o, fn in ((ins, "einsatz_weizen.stl"), (body, "pfanne_body.stl"), (handle, "griff.stl")):
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.wm.stl_export(filepath=str(OUT / fn), export_selected_objects=True,
                              global_scale=1.0, apply_modifiers=True)
        o.select_set(False)

    if FILL:
        add_kernels(coll, ins)
    cam = scene_setup(ins)
    shots = {"perspektive": (260, -560, 380), "draufsicht": (0, -30, 900),
             "detail": (60, -190, 90)}
    for name, pos in shots.items():
        look(cam, pos, at=(40, -120, 5) if name == "detail" else (0, -20, 10))
        if name == "draufsicht":
            cam.rotation_euler = (0, 0, 0)
        bpy.context.scene.render.filepath = str(OUT / f"{name}{'_gefuellt' if FILL else ''}.png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "pfanne.blend"))


main()
