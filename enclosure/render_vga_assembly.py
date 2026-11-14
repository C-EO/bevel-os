"""Explainer renders: how the VGA gender-changer cage mounts on the box and meets the cables.

Run after make_enclosure.py:
    /Applications/Blender.app/Contents/MacOS/Blender -b --python enclosure/render_vga_assembly.py

Writes out/vga_asm_<view>.png and out/vga_asm_labels.json (label anchor pixels for annotate).
Dimensions of the plugs and the changer are approximate; they are only for illustration.
"""
import json
import math
import os

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
W = 2.4                     # wall
VX, VZ = 130.0, 14.0        # VGA hole centre
WALL = -W                   # outer face of the wall (Y)

C_BOX = (0.93, 0.93, 0.9, 1)
C_CAGE = (0.95, 0.45, 0.1, 1)
C_BODY = (0.95, 0.85, 0.1, 1)
C_METAL = (0.7, 0.7, 0.74, 1)
C_PLUG = (0.1, 0.1, 0.11, 1)
C_SCREW = (0.45, 0.47, 0.52, 1)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection


def mk_box(name, x0, y0, z0, x1, y1, z1, color):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    ob = bpy.context.active_object
    ob.scale = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    bpy.ops.object.transform_apply(scale=True)
    ob.name, ob.color = name, color
    return ob


def mk_ycyl(name, x, z, y0, y1, d, color, seg=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=seg, radius=d / 2, depth=abs(y1 - y0),
                                        location=(x, (y0 + y1) / 2, z),
                                        rotation=(math.radians(90), 0, 0))
    ob = bpy.context.active_object
    bpy.ops.object.transform_apply(rotation=True)
    ob.name, ob.color = name, color
    return ob


def import_stl(fname, color):
    bpy.ops.wm.stl_import(filepath=os.path.join(OUT, fname))
    ob = bpy.context.selected_objects[0]
    ob.color = color
    return ob


def boolean(target, cutter, op):
    m = target.modifiers.new("b", "BOOLEAN")
    m.operation, m.object, m.solver = op, cutter, "EXACT"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)


# --- the box, cropped to the rear-right corner around the VGA hole ---------------------
box = import_stl("box.stl", C_BOX)
crop = mk_box("crop", 88, -3, -3, 170, 62, 48, C_BOX)
boolean(box, crop, "INTERSECT")
bpy.data.objects.remove(crop, do_unlink=True)

# --- parts, grouped so each group can be pulled apart for the exploded view -------------
groups = {}


def grp(name, *obs):
    groups.setdefault(name, []).extend(obs)


def place_part(fname, z0):
    """Cage parts are modelled with z out of the wall; turn them onto the box's -Y."""
    ob = import_stl(fname, C_CAGE)
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.location = (VX, WALL - z0, VZ)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=True, rotation=True)
    return ob


LIP, BT = 2.0, 6.6
y_body0, y_body1 = WALL - LIP, WALL - LIP - BT          # -4.4 .. -11.0
grp("frame", place_part("vga_coupler_frame.stl", 0.0))
grp("cap", place_part("vga_coupler_cap.stl", LIP + BT))

# gender changer: body, D shells and hex posts on both sides
ch = [mk_box("changer_body", VX - 16.6, y_body1, VZ - 6.4, VX + 16.6, y_body0, VZ + 6.4, C_BODY),
      mk_box("changer_shell_out", VX - 8.15, y_body1 - 6, VZ - 3.95, VX + 8.15, y_body1, VZ + 3.95, C_METAL),
      mk_box("changer_shell_in", VX - 8.15, y_body0, VZ - 3.95, VX + 8.15, y_body0 + 6, VZ + 3.95, C_METAL)]
for sx in (-1, 1):
    ch.append(mk_ycyl("post_out", VX + sx * 12.5, VZ, y_body1 - 5, y_body1, 5.5, C_METAL, seg=6))
    ch.append(mk_ycyl("post_in", VX + sx * 12.5, VZ, y_body0, y_body0 + 5, 5.5, C_METAL, seg=6))
grp("changer", *ch)

# screws (M3 x 20): head on the cap, shank into the pilot beside the hole
y_cap = WALL - LIP - BT - LIP
for sx in (-1, 1):
    grp("screws", mk_ycyl("screw_head", VX + sx * 21, VZ, y_cap - 2.0, y_cap, 5.5, C_SCREW),
        mk_ycyl("screw_shank", VX + sx * 21, VZ, y_cap, y_cap + 20, 3.0, C_SCREW))


def vga_male(prefix, y_flange, direction, length=30, cable_len=30):
    """Male VGA plug whose flange sits on the changer's post tips at y_flange.
    direction = +1: body extends into the box (+Y); -1: out of the box."""
    d = direction
    obs = [mk_box(prefix + "_flange", VX - 15.4, y_flange, VZ - 6.25, VX + 15.4, y_flange + d * 0.8, VZ + 6.25, C_METAL),
           mk_box(prefix + "_shroud", VX - 8.6, y_flange, VZ - 4.4, VX + 8.6, y_flange - d * 4.5, VZ + 4.4, C_METAL),
           mk_box(prefix + "_body", VX - 17.1, y_flange + d * 0.8, VZ - 7.2, VX + 17.1, y_flange + d * (0.8 + length), VZ + 7.2, C_PLUG)]
    y_end = y_flange + d * (0.8 + length)
    obs.append(mk_ycyl(prefix + "_relief", VX, VZ, y_end, y_end + d * 8, 10, C_PLUG))
    obs.append(mk_ycyl(prefix + "_cable", VX, VZ, y_end + d * 8, y_end + d * (8 + cable_len), 7.9, C_PLUG))
    for sx in (-1, 1):   # knurled thumbscrew knobs on the sides of the moulding
        obs.append(mk_ycyl(prefix + "_knob", VX + sx * 12.5, VZ, y_flange + d * 3, y_flange + d * 12, 7.0, C_METAL, seg=18))
    return obs


grp("plug_in", *vga_male("in", y_body0 + 5, +1, length=28, cable_len=14))
grp("plug_out", *vga_male("out", y_body1 - 5, -1, length=30, cable_len=40))

# --- render setup -------------------------------------------------------------------
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light, sh.color_type = "STUDIO", "OBJECT"
sh.show_cavity, sh.show_shadows = True, True
sh.show_object_outline = True
scene.render.resolution_x, scene.render.resolution_y = 1500, 1050
world = bpy.data.worlds.new("w")
world.color = (0.16, 0.16, 0.18)
scene.world = world
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
col.objects.link(cam)
scene.camera = cam

labels = {}


def look(loc, target, lens):
    cam.location, cam_data.lens = loc, lens
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


def px(p):
    v = world_to_camera_view(scene, cam, Vector(p))
    return [round(v.x * scene.render.resolution_x), round((1 - v.y) * scene.render.resolution_y)]


def render(name, anchors):
    scene.render.filepath = os.path.join(OUT, f"vga_asm_{name}.png")
    bpy.ops.render.render(write_still=True)
    labels[name] = {k: px(p) for k, p in anchors.items()}


def shift(name, dy):
    for ob in groups[name]:
        ob.location.y += dy


# 1) exploded, seen from outside
EXP = {"frame": -16, "changer": -34, "cap": -54, "screws": -70, "plug_out": -100, "plug_in": 22}
for g, dy in EXP.items():
    shift(g, dy)
look((VX - 150, -205, VZ + 95), (VX - 4, -55, VZ - 2), 40)
render("exploded", {
    "box wall": (VX + 30, WALL, VZ + 22),
    "1  frame (back lip on the wall)": (VX - 24, WALL - 16 - 4, VZ + 10),
    "2  gender changer": (VX - 16, y_body1 - 34 + 2, VZ + 6),
    "3  cap": (VX - 24, y_cap - 54 + 1, VZ + 10),
    "4  2 x M3 x 20": (VX - 21, y_cap - 70 - 2, VZ),
    "VGA-to-HDMI adapter side": (VX - 17, y_body1 - 5 - 100 - 15, VZ + 7),
})
for g, dy in EXP.items():
    shift(g, -dy)

# 2) assembled, outside
look((VX - 110, -150, VZ + 70), (VX, -10, VZ), 40)
render("outside", {
    "cage clamps the changer": (VX - 24, y_cap, VZ + 10),
    "plug from the adapter": (VX - 17, y_body1 - 20, VZ + 7),
})
# 3) assembled, inside (lid off)
look((VX - 95, 95, VZ + 85), (VX, 8, VZ), 40)
render("inside", {
    "internal VGA cable (from the resistor DAC)": (VX, 50, VZ + 4),
    "plug + thumbscrews into the changer": (VX - 17, 6, VZ + 7),
    "box wall": (VX - 30, 0, VZ + 25),
})
# 4) section through the middle of the hole (keep x < VX), seen from the side
cutter = mk_box("cutter", VX, -300, -50, 400, 300, 100, C_BOX)
for ob in [o for o in scene.objects if o.type == "MESH" and o is not cutter]:
    boolean(ob, cutter, "DIFFERENCE")
bpy.data.objects.remove(cutter, do_unlink=True)
look((VX + 150, -12, VZ + 35), (VX, -8, VZ - 2), 45)
render("section", {
    "wall": (VX, -1.2, VZ + 20),
    "frame lip": (VX, WALL - 1, VZ + 9),
    "changer body (clamped)": (VX, (y_body0 + y_body1) / 2, VZ + 6.4),
    "cap lip": (VX, y_cap + 1, VZ + 9),
    "inside the box": (VX, 30, VZ + 7.2),
    "outside": (VX, -40, VZ + 7.2),
})

with open(os.path.join(OUT, "vga_asm_labels.json"), "w") as f:
    json.dump(labels, f, indent=1)
print("done")
