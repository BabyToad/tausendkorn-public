"""Render the v1 pan from several viewpoints for the pitch.

  blender --background out_v1/pfanne_v1.blend --python-exit-code 1 --python render_views.py

Writes out_v1/views/*.png. Does not change the .blend.
"""

import math
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(bpy.data.filepath).parent / "views"
OUT.mkdir(exist_ok=True)
s = bpy.context.scene
s.render.engine = "BLENDER_EEVEE"
s.render.resolution_x, s.render.resolution_y = 1920, 1280
s.view_settings.view_transform = "AgX"

# hide the coupon row so the pan fills the frame
for o in bpy.data.collections["Testcoupons"].objects:
    o.hide_render = True

# soft studio: key, fill, rim
for o in [o for o in s.objects if o.type == "LIGHT"]:
    bpy.data.objects.remove(o)
for loc, energy, size in (((260, -320, 420), 2.2e6, 350), ((-300, -80, 260), 0.9e6, 400),
                          ((0, 380, 300), 1.2e6, 250)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    lamp = bpy.context.active_object
    lamp.data.energy, lamp.data.size = energy, size
    lamp.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

# ground plane catching shadows
bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, -0.05))
floor = bpy.context.active_object
floor.name = "Boden"
mat = bpy.data.materials.new("Boden")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.78, 0.76, 0.72, 1)
mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
floor.data.materials.append(mat)

cam = s.camera
cam.data.lens = 50

cassette = bpy.data.objects["Kassette_Weizen_500"]
kernels = [o for o in s.objects if o.type == "MESH" and o.data.materials
           and o.data.materials[0].name.startswith("Weizen")]
markers = [o for o in s.objects if o.type == "MESH" and o.name.startswith("Plane")]


def shot(name, pos, at, lens=50, ortho=None):
    cam.data.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        cam.data.ortho_scale = ortho
    cam.data.lens = lens
    cam.location = pos
    cam.rotation_euler = (Vector(at) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    s.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)


shot("01_draufsicht_fotoperspektive", (0, -10, 600), (0, -10, 0), ortho=270)
shot("02_dreiviertel_vorne", (260, -430, 300), (0, -10, 8))
shot("03_dreiviertel_hinten_griff", (-300, 420, 260), (0, 20, 10))
shot("04_seitenprofil", (520, 10, 25), (0, 10, 12), lens=70)
shot("05_schoepflippe_tief", (60, -330, 28), (0, -110, 4), lens=40)
shot("06_mulden_detail", (35, -80, 30), (10, -50, 2), lens=85)

# exploded view: lift cassette, kernels and markers above the carrier
lift = 45.0
for o in [cassette, *kernels, *markers]:
    o.location.z += lift
shot("07_explosionsansicht", (300, -380, 260), (0, 0, 25))
