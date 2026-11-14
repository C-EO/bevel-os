"""Combine already-exported parts into one print plate (Elegoo Neptune 3 Pro, 225 x 225 bed).

Run after make_enclosure.py:
    /Applications/Blender.app/Contents/MacOS/Blender -b --python enclosure/make_plate.py

Outputs (+ a preview_<name>.png each):
  out/plate_lid_spares.stl - lid plus every small part: 2 USB-C clamp bars, ESP32 bridge,
                             VGA cover plate, VGA clamp block and cap (cap flipped, groove up)
  out/plate_holddowns.stl  - only the ESP32 bridge + 2 USB-C clamp bars
  out/plate_vga_coupler.stl - VGA gender-changer cage (frame + cap)
"""
import math
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
BED = 225.0
GAP = 8.0  # between parts

# Each plate: name -> [(file, rotation (x, y, z) in degrees, x, y of the part's min corner)]
row_y = 115 + GAP
PLATES = {
    # lid + every small part (lid front, small parts in a row behind it)
    "plate_lid_spares": [
        ("lid.stl", (0, 0, 0), 0, 0),
        ("vga_cover_plate.stl", (0, 0, 0), 0, row_y),
        ("vga_clamp_block.stl", (0, 0, 0), 49 + GAP, row_y),
        ("vga_clamp_cap.stl", (0, 180, 0), 49 + 22 + 2 * GAP, row_y),   # groove up
        ("clamp_bar.stl", (0, 0, 0), 49 + 44 + 3 * GAP, row_y),           # two bars stacked
        ("clamp_bar.stl", (0, 0, 0), 49 + 44 + 3 * GAP, row_y + 9 + GAP),
        ("esp_bridge.stl", (0, 0, 0), 49 + 44 + 24 + 4 * GAP, row_y),
    ],
    # VGA gender-changer cage: frame (pocket up) + cap
    "plate_vga_coupler": [
        ("vga_coupler_frame.stl", (0, 0, 0), 0, 0),
        ("vga_coupler_cap.stl", (0, 0, 0), 0, 24 + GAP),
    ],
    # only the hold-downs (if the lid plate is already printed)
    "plate_holddowns": [
        ("esp_bridge.stl", (0, 0, 0), 0, 0),
        ("clamp_bar.stl", (0, 0, 0), 0, 12 + GAP),
        ("clamp_bar.stl", (0, 0, 0), 24 + GAP, 12 + GAP),
    ],
}


def build(name, layout):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts = []
    for fname, rot, x, y in layout:
        bpy.ops.wm.stl_import(filepath=os.path.join(OUT, fname))
        ob = bpy.context.selected_objects[0]
        ob.rotation_euler = tuple(math.radians(a) for a in rot)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        vs = [v.co for v in ob.data.vertices]
        mn = [min(v[i] for v in vs) for i in range(3)]
        for v in ob.data.vertices:
            v.co.x += x - mn[0]
            v.co.y += y - mn[1]
            v.co.z -= mn[2]          # every part flat on the bed
        ob.data.update()
        parts.append(ob)

    # centre the whole group on the bed
    allv = [v.co for ob in parts for v in ob.data.vertices]
    mn = [min(v[i] for v in allv) for i in range(2)]
    mx = [max(v[i] for v in allv) for i in range(2)]
    size = (mx[0] - mn[0], mx[1] - mn[1])
    for ob in parts:
        for v in ob.data.vertices:
            v.co.x += BED / 2 - (mn[0] + mx[0]) / 2
            v.co.y += BED / 2 - (mn[1] + mx[1]) / 2
        ob.data.update()
    assert size[0] <= BED - 20 and size[1] <= BED - 20, f"{name} does not fit the bed"

    for o in bpy.context.selected_objects:
        o.select_set(False)
    for ob in parts:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    plate = bpy.context.view_layer.objects.active
    plate.name = name
    bpy.ops.wm.stl_export(filepath=os.path.join(OUT, name + ".stl"),
                          export_selected_objects=True, ascii_format=False)
    d = plate.dimensions
    print(f"{name}: {d.x:.1f} x {d.y:.1f} x {d.z:.1f} mm, {len(plate.data.polygons)} faces")
    render_preview(name)


def render_preview(name):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "SINGLE"
    scene.render.resolution_x, scene.render.resolution_y = 1200, 1000
    bpy.ops.mesh.primitive_plane_add(size=BED, location=(BED / 2, BED / 2, -0.01))
    bpy.ops.object.camera_add(location=(BED / 2, BED / 2 - 170, 260))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(33), 0, 0)
    cam.data.lens = 30
    scene.camera = cam
    scene.render.filepath = os.path.join(OUT, f"preview_{name}.png")
    bpy.ops.render.render(write_still=True)


for n, lay in PLATES.items():
    build(n, lay)
