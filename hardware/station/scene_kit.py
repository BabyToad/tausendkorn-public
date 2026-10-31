"""Shared scene helpers for the station renders: materials, kernels, phone, studio.

Imported by build_station.py inside Blender. Units: millimetres.
"""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    u = bpy.context.scene.unit_settings
    u.system, u.scale_length, u.length_unit = "METRIC", 0.001, "MILLIMETERS"


def material(name, rgb, rough=0.7, metal=0.0, emit=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        p.inputs["Emission Color"].default_value = (*emit[0], 1)
        p.inputs["Emission Strength"].default_value = emit[1]
    return m


def mesh_obj(name, bm, coll, mat=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    if mat:
        o.data.materials.append(mat)
    return o


def add_box(bm, x0, x1, y0, y1, z0, z1):
    bmesh.ops.create_cube(bm, size=1, matrix=(
        Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        @ Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1))))


def box(name, x0, x1, y0, y1, z0, z1, coll, mat=None, bevel=0.0):
    bm = bmesh.new()
    add_box(bm, x0, x1, y0, y1, z0, z1)
    o = mesh_obj(name, bm, coll, mat)
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width, b.segments = bevel, 3
        b.limit_method = "ANGLE"
    return o


def kernels(coll, n, region, z, seed=5, kind="wheat", min_gap=0.6):
    """Scatter n non-touching grains inside region (x0, x1, y0, y1) lying on z."""
    dims = {"wheat": (3.3, 6.6, 2.8, (0.62, 0.40, 0.17)),
            "barley": (3.6, 8.8, 2.6, (0.78, 0.62, 0.33))}[kind]
    w, l, h, rgb = dims
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1)
    proto = bpy.context.active_object
    for v in proto.data.vertices:  # slight egg shape + crease
        v.co.y *= 1.0 + 0.12 * v.co.y
        if v.co.z > 0 and abs(v.co.x) < 0.25:
            v.co.z *= 0.8
    proto.scale = (w / 2, l / 2, h / 2)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.shade_smooth()
    proto.data.materials.append(material("Korn_" + kind, rgb, 0.45))
    rnd = random.Random(seed)
    placed = []
    x0, x1, y0, y1 = region
    r = l / 2 + min_gap
    tries = 0
    while len(placed) < n and tries < n * 400:
        tries += 1
        p = (rnd.uniform(x0 + r, x1 - r), rnd.uniform(y0 + r, y1 - r))
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > (2 * r * 0.78) ** 2 for q in placed):
            placed.append(p)
    for x, y in placed:
        o = bpy.data.objects.new("Korn", proto.data)
        s = rnd.uniform(0.88, 1.1)
        o.scale = (s, s, s)
        o.location = (x, y, z + h / 2 * s * 0.92)
        o.rotation_euler = (rnd.uniform(-0.1, 0.1), rnd.uniform(-0.25, 0.25), rnd.uniform(0, math.tau))
        coll.objects.link(o)
    bpy.data.objects.remove(proto)
    return len(placed)


def phone(coll, w=71.5, l=147.6, t=8.3, cam_offset=(-24, 60)):
    """Generic slab phone lying screen-up; camera bump on the underside at cam_offset."""
    body = box("Phone", -w / 2, w / 2, -l / 2, l / 2, 0, t, coll,
               material("Phone_alu", (0.18, 0.19, 0.21), 0.35, 0.8), bevel=3.0)
    screen = box("Phone_screen", -w / 2 + 2.5, w / 2 - 2.5, -l / 2 + 2.5, l / 2 - 2.5, t, t + 0.2,
                 coll, material("Phone_glass", (0.01, 0.01, 0.015), 0.08, emit=((0.05, 0.25, 0.18), 0.6)))
    bump = box("Phone_cam", cam_offset[0] - 15, cam_offset[0] + 15, cam_offset[1] - 15,
               cam_offset[1] + 15, -1.8, 0, coll, material("Phone_alu", (0, 0, 0)), bevel=4.0)
    lens = []
    for dx, dy in ((-7, 7), (7, 7), (-7, -7)):
        bpy.ops.mesh.primitive_cylinder_add(radius=4.6, depth=0.6,
                                            location=(cam_offset[0] + dx, cam_offset[1] + dy, -2.0))
        c = bpy.context.active_object
        for u in c.users_collection:
            u.objects.unlink(c)
        coll.objects.link(c)
        c.data.materials.append(material("Lens", (0.0, 0.0, 0.02), 0.05, 0.3))
        lens.append(c)
    for o in [screen, bump, *lens]:
        o.parent = body
    return body


def studio(scene, bg=(0.93, 0.92, 0.89), floor_rgb=(0.80, 0.78, 0.74), res=(1920, 1280)):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.cycles.device = "CPU"
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (*bg, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    for loc, energy, size in (((380, -480, 700), 3.2e6, 500), ((-520, -120, 420), 1.1e6, 600),
                              ((0, 600, 500), 1.6e6, 400)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        lamp = bpy.context.active_object
        lamp.data.energy, lamp.data.size = energy, size
        lamp.rotation_euler = (-Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, -0.05))
    floor = bpy.context.active_object
    floor.name = "Boden"
    floor.data.materials.append(material("Boden", floor_rgb, 0.9))
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.data.clip_end = 8000
    cam.data.lens = 50
    scene.camera = cam
    return cam


def shoot(path, cam, pos, at, lens=50):
    cam.location = pos
    cam.data.lens = lens
    cam.rotation_euler = (Vector(at) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
