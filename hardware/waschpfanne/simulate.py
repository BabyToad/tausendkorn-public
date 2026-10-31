"""Rigid-body panning simulation (Blender/Bullet) for the Kornwaschpfanne prototypes.

A mixed handful (whole kernels, broken halves, chaff flakes) is dropped into a pan, the pan
gyrates on a horizontal circle (hand panning), then everything settles. Reports how many
kernels touch, stack or leave the pan and where each material ends up radially.

  blender --background --python-exit-code 1 --python simulate.py -- --design P1 [--n 600]
          [--seconds 10] [--render] [--frames 0,120,600]

Internal units: 1 Blender unit = 1 cm (Bullet is unreliable below ~1 mm bodies). Designs in
designs.py use millimetres and are converted here. Results: out/sim/<design>.json (+ PNGs).
"""

import json
import math
import random
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import designs  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return type(default)(ARGS[ARGS.index(name) + 1]) if name in ARGS else default


DESIGN = arg("--design", "P1")
N = arg("--n", 600)
SECONDS = arg("--seconds", 10.0)
SEED = arg("--seed", 1)
RENDER = "--render" in ARGS
FPS = 60
OUT = HERE / "out" / "sim"
CM = 0.1  # mm -> cm

# sample mix and per-material physics (friction combines multiplicatively in Bullet)
MIX = {"korn": 0.90, "bruch": 0.06, "spreu": 0.04}
PHYS = {  # mass g, friction, restitution, linear/angular damping (damping stands in for air drag)
    "korn": dict(mass=0.045, friction=0.6, restitution=0.1, lin=0.05, ang=0.25),
    "bruch": dict(mass=0.02, friction=0.6, restitution=0.1, lin=0.05, ang=0.3),
    "spreu": dict(mass=0.002, friction=0.7, restitution=0.05, lin=0.9, ang=0.9),
}
PAN_FRICTION = 0.6


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system, s.unit_settings.scale_length = "METRIC", 0.01
    s.gravity = (0, 0, -981.0)  # cm/s^2
    s.render.fps = FPS
    s.frame_start, s.frame_end = 1, int(SECONDS * FPS)
    return s


def material(name, rgb, rough=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    return m


def revolve(name, profile_mm, thickness_mm, seg=160):
    """Solid of revolution: inner surface follows profile [(r, z)...] from r=0 outward; the
    underside is the same profile shifted down by thickness (closed, manifold)."""
    prof = [(r * CM, z * CM) for r, z in profile_mm]
    t = thickness_mm * CM
    bm = bmesh.new()
    top, bot = [], []
    for i in range(seg):
        a = math.tau * i / seg
        c, s = math.cos(a), math.sin(a)
        top.append([bm.verts.new((r * c, r * s, z)) for r, z in prof[1:]])
        bot.append([bm.verts.new((r * c, r * s, z - t)) for r, z in prof[1:]])
    ct = bm.verts.new((0, 0, prof[0][1]))
    cb = bm.verts.new((0, 0, prof[0][1] - t))
    m = len(prof) - 1
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((ct, top[i][0], top[j][0]))
        bm.faces.new((cb, bot[j][0], bot[i][0]))
        for kk in range(m - 1):
            bm.faces.new((top[i][kk], top[i][kk + 1], top[j][kk + 1], top[j][kk]))
            bm.faces.new((bot[i][kk], bot[j][kk], bot[j][kk + 1], bot[i][kk + 1]))
        bm.faces.new((top[i][-1], bot[i][-1], bot[j][-1], top[j][-1]))  # rim lip
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def grain_mesh(kind):
    """Low-poly convex shapes in cm: wheat kernel, broken half, chaff flake."""
    bm = bmesh.new()
    if kind == "spreu":
        bmesh.ops.create_cube(bm, size=1)
        for v in bm.verts:
            v.co = Vector((v.co.x * 0.40, v.co.y * 0.65, v.co.z * 0.03))
    else:
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=1)
        for v in bm.verts:
            v.co.y *= 1.0 + 0.1 * v.co.y
            v.co = Vector((v.co.x * 0.165, v.co.y * 0.33, v.co.z * 0.14))
        if kind == "bruch":
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                                   plane_co=(0, 0.02, 0), plane_no=(0, 1, 0), clear_outer=True)
            bmesh.ops.contextual_create(bm, geom=[e for e in bm.edges if e.is_boundary])
    me = bpy.data.meshes.new("grain_" + kind)
    bm.to_mesh(me)
    bm.free()
    return me


def spawn_handful(n, floor_z, rnd):
    """A loose heap above the pan centre, as if dropped from a hand."""
    meshes = {k: grain_mesh(k) for k in MIX}
    cols = {"korn": (0.62, 0.40, 0.17), "bruch": (0.80, 0.55, 0.25), "spreu": (0.85, 0.80, 0.55)}
    for k, me in meshes.items():
        me.materials.append(material("M_" + k, cols[k], 0.5))
    kinds = [k for k, f in MIX.items() for _ in range(round(n * f))]
    rnd.shuffle(kinds)
    objs = []
    for i, kind in enumerate(kinds):
        r, a = 2.6 * math.sqrt(rnd.random()), rnd.uniform(0, math.tau)
        o = bpy.data.objects.new(f"{kind}_{i:04d}", meshes[kind])
        o.location = (r * math.cos(a), r * math.sin(a), floor_z + 0.8 + 0.5 * (i % 40) + rnd.random() * 0.3)
        o.rotation_euler = [rnd.uniform(0, math.tau) for _ in range(3)]
        o["kind"] = kind
        bpy.context.scene.collection.objects.link(o)
        objs.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.rigidbody.objects_add(type="ACTIVE")
    for o in objs:
        p = PHYS[o["kind"]]
        rb = o.rigid_body
        rb.collision_shape = "CONVEX_HULL"
        rb.mass, rb.friction, rb.restitution = p["mass"], p["friction"], p["restitution"]
        rb.linear_damping, rb.angular_damping = p["lin"], p["ang"]
        rb.use_margin, rb.collision_margin = True, 0.004
    return objs


def animate_pan(pan, motion):
    """motion: list of phases dict(t=seconds, R=orbit mm, f=Hz, tilt=deg); gaps are rest."""
    t0 = 0.0
    phases = []
    for ph in motion:
        phases.append((t0, t0 + ph["t"], ph))
        t0 += ph["t"]
    phase_acc = 0.0
    last_t = 0.0
    for fr in range(1, int(SECONDS * FPS) + 1):
        t = (fr - 1) / FPS
        cur = next((ph for a, b, ph in phases if a <= t < b), None)
        R = (cur or {}).get("R", 0.0) * CM
        f = (cur or {}).get("f", 0.0)
        tilt = math.radians((cur or {}).get("tilt", 0.0))
        phase_acc += math.tau * f * (t - last_t)
        last_t = t
        # ramp the orbit in/out over 0.3 s so the pan does not jerk
        ramp = 1.0
        if cur:
            a, b, _ = next(p for p in phases if p[2] is cur)
            ramp = min(1.0, (t - a) / 0.3, (b - t) / cur.get("decay", 0.3))  # decay: slow fade-out
        pan.location = (R * ramp * math.cos(phase_acc), R * ramp * math.sin(phase_acc), 0)
        pan.rotation_euler = (tilt * ramp * math.sin(phase_acc), -tilt * ramp * math.cos(phase_acc), 0)
        pan.keyframe_insert("location", frame=fr)
        pan.keyframe_insert("rotation_euler", frame=fr)
    if pan.animation_data and pan.animation_data.action:
        try:
            for fc in pan.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        except AttributeError:  # Blender 5 layered actions: keys are dense, interpolation moot
            pass


def metrics(objs, pan_floor_z, rim_r_cm, design):
    grains = []
    for o in objs:
        mw = o.matrix_world
        verts = [mw @ v.co for v in o.data.vertices]
        c = sum(verts, Vector()) / len(verts)
        grains.append(dict(o=o, kind=o["kind"], c=c, verts=verts,
                           r=math.hypot(c.x, c.y), z=c.z))
    lost = [g for g in grains if g["r"] > rim_r_cm or g["z"] < pan_floor_z - 1.0]
    inside = [g for g in grains if g not in lost]
    counted = [g for g in inside if g["kind"] in ("korn", "bruch")]
    # 2D touching test on the photo plane: projected convex outlines closer than GAP
    hulls = {id(g): hull2d([(v.x, v.y) for v in g["verts"]]) for g in counted}
    touching = set()
    pairs = 0
    for i, a in enumerate(counted):
        for b in counted[i + 1:]:
            if (a["c"].x - b["c"].x) ** 2 + (a["c"].y - b["c"].y) ** 2 > 0.75 ** 2:
                continue
            if not separated(hulls[id(a)], hulls[id(b)], GAP):
                pairs += 1
                touching.add(id(a))
                touching.add(id(b))
    # stacked: centre clearly above the local monolayer (resting on another grain)
    stacked = [g for g in counted if g["z"] - local_floor(g, design) > 0.2]
    nn = []
    for a in counted:
        d = min((math.hypot(a["c"].x - b["c"].x, a["c"].y - b["c"].y) for b in counted if b is not a),
                default=0)
        nn.append(d * 10)
    radial = {}
    for kind in MIX:
        rs = sorted(g["r"] * 10 for g in inside if g["kind"] == kind)
        if rs:
            radial[kind] = dict(n=len(rs), median_mm=round(rs[len(rs) // 2], 1),
                                p10_mm=round(rs[len(rs) // 10], 1), p90_mm=round(rs[9 * len(rs) // 10], 1))
    poses = [dict(name=g["o"].name, kind=g["kind"], touching=id(g) in touching,
                  m=[list(row) for row in g["o"].matrix_world]) for g in grains]
    (OUT / f"{DESIGN}_grains.json").write_text(json.dumps(poses))
    return dict(
        design=DESIGN, n_total=len(grains), n_counted=len(counted), lost=len(lost),
        touching_frac=round(len(touching) / max(1, len(counted)), 3), touching_pairs=pairs,
        stacked_frac=round(len(stacked) / max(1, len(counted)), 3),
        nn_median_mm=round(sorted(nn)[len(nn) // 2], 2) if nn else None,
        radial=radial,
    )


GAP = 0.02  # cm: outlines closer than 0.2 mm count as touching in the photo


def hull2d(pts):
    pts = sorted(set((round(x, 5), round(y, 5)) for x, y in pts))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def separated(a, b, gap):
    """Separating-axis test for convex polygons with a minimum gap."""
    for poly in (a, b):
        for i in range(len(poly)):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % len(poly)]
            nx, ny = y1 - y0, x0 - x1
            ln = math.hypot(nx, ny) or 1.0
            nx, ny = nx / ln, ny / ln
            pa = [x * nx + y * ny for x, y in a]
            pb = [x * nx + y * ny for x, y in b]
            if max(pa) + gap < min(pb) or max(pb) + gap < min(pa):
                return True
    return False


def local_floor(g, design):
    return designs.floor_z_cm(design, g["r"])


def main():
    s = reset()
    d = designs.DESIGNS[DESIGN]
    pan = revolve("Pfanne", d["profile"], d.get("thickness", 3.0))
    pan.data.materials.append(material("Pfanne", d.get("rgb", (0.06, 0.07, 0.08)), 0.6))
    bpy.context.view_layer.objects.active = pan
    pan.select_set(True)
    bpy.ops.rigidbody.world_add()
    w = s.rigidbody_world
    w.substeps_per_frame, w.solver_iterations = arg("--substeps", 10), arg("--iters", 20)
    w.point_cache.frame_start, w.point_cache.frame_end = 1, int(SECONDS * FPS)
    bpy.ops.rigidbody.object_add(type="PASSIVE")
    pan.rigid_body.collision_shape = "MESH"
    pan.rigid_body.kinematic = True
    pan.rigid_body.friction = PAN_FRICTION
    pan.rigid_body.restitution = 0.1
    pan.rigid_body.collision_margin = 0.002
    animate_pan(pan, d["motion"])
    rnd = random.Random(SEED)
    objs = spawn_handful(N, designs.floor_z_cm(DESIGN, 0), rnd)
    t0 = time.time()
    frames = sorted({int(x) for x in arg("--frames", "").split(",") if x}) if RENDER else []
    OUT.mkdir(parents=True, exist_ok=True)
    if RENDER:
        setup_render(d)
    for fr in range(1, s.frame_end + 1):
        s.frame_set(fr)
        if fr % 60 == 0:
            print(f"PROGRESS {DESIGN} frame {fr}/{s.frame_end} after {time.time() - t0:.0f}s", flush=True)
        if fr in frames:
            s.render.filepath = str(OUT / f"{DESIGN}_f{fr:04d}.png")
            bpy.ops.render.render(write_still=True)
    sim_s = time.time() - t0
    rim_r = d["profile"][-1][0] * CM
    m = metrics(objs, designs.floor_z_cm(DESIGN, 0), rim_r, DESIGN)
    m.update(sim_seconds_wall=round(sim_s, 1), sim_seconds=SECONDS, motion=d["motion"])
    (OUT / f"{DESIGN}.json").write_text(json.dumps(m, indent=2))
    print("RESULT", json.dumps(m))
    if RENDER:
        s.render.filepath = str(OUT / f"{DESIGN}_final.png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f"{DESIGN}.blend"))


def setup_render(d):
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x = s.render.resolution_y = 1200
    s.view_settings.view_transform = "AgX"
    s.world = bpy.data.worlds.new("w")
    s.world.use_nodes = True
    s.world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.88, 1)
    s.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    bpy.ops.object.light_add(type="AREA", location=(0, 0, 80))
    bpy.context.active_object.data.energy = 2.0e5
    bpy.context.active_object.data.size = 60
    bpy.ops.object.camera_add(location=(0, 0, 90))
    cam = bpy.context.active_object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = d["profile"][-1][0] * CM * 2 + 2
    cam.data.clip_end = 500
    s.camera = cam


main()
