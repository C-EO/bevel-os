"""
ESP32-S3 VGA OS enclosure - parametric Blender script.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b --python enclosure/make_enclosure.py

Outputs (enclosure/out/):
  box.stl          - main box, print open side up, no supports
  lid.stl          - lid, already flipped for printing (top face on the bed)
  clamp_bar.stl    - USB-C breakout clamp bar with a stop tooth behind the receptacle, print 2
  esp_bridge.stl   - ESP32 far-end bridge: holds the board down + stops it sliding, print 1
  vga_cover_plate.stl - closes the VGA pass-through hole around the cable, print 1
  vga_clamp_cap.stl   - top half of the VGA cable clamp, print 1 (groove up)
  vga_clamp_block.stl - bottom half of the VGA cable clamp, print 1
  vga_fit_test.stl    - 3 VGA holes (0.2 / 0.4 / 0.6 mm clearance) to pick vga_clear quickly
  rear_panel.stl   - two-part option: the port wall + cradles, exported lying on its outer face
                     (print first, doubles as fit test)
  box_body.stl     - two-part option: the rest of the box, joined to rear_panel with 4 x M3
  preview_*.png    - renders for checking

Coordinates (box): X = length, Y = depth (0 = inner face of the rear "port" wall, +Y into
the box), Z = height (0 = top of the floor). All sizes in mm.

Every guessed dimension is in PARAMS. Measure your parts and edit them, then re-run.
"""
import math
import os
import bpy
import bmesh

# --------------------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------------------
P = dict(
    # Box
    inner_l=160.0, inner_d=110.0, inner_h=45.0,
    wall=2.4, floor=2.0, corner_r=6.0,
    # Lid
    lid_t=2.4, lip_h=5.0, lip_t=1.6, lip_clear=0.3,
    post_d=8.0, pilot_d=2.6, lid_hole_d=3.4,          # M3 self-tapping screws, 4 corners
    # ESP32-S3 dev board (MEASURE: board length / width)
    esp_len=58.0, esp_w=28.0, esp_x=10.0,            # PCB only (the WiFi module overhangs ~4 mm more)
    esp_com_dx=5.4,                                   # COM (UART) port centre, +X of board centre
    esp_expose_native=True,                           # also open the native USB port (keep it empty)
    esp_rail_h=4.0,                                   # board sits 4 mm up (wires soldered under it)
    # USB-C breakout (Robojax 4-pad) (MEASURE: board width, receptacle height)
    bo_w=13.0, bo_t=1.6, rec_h=3.3,
    bo_shelf_z=8.0,                                   # PCB underside height above floor
    bo_x=(66.0, 92.0),                                # centres of the two breakouts
    usb_plug_w=12.8, usb_plug_h=7.0,                  # outer recess for the plug's moulded body
    usb_rec_w=9.6, usb_rec_h=4.2,                     # inner USB-C shaped hole (socket is 8.94 x 3.26)
    usb_inner_skin=0.8,                               # wall left between pocket and inside
    # VGA: the internal cable's moulded plug (~34.2 x 14.4 mm face) goes all the way through
    # the wall; a cable clamp inside holds it, a slotted cover plate closes the hole after
    vga_x=130.0, vga_z=14.0,
    vga_plug_w=34.2, vga_plug_h=14.4,                 # measured moulded plug body
    vga_clear=0.2,                                    # per side; picked hole 1 of vga_fit_test (36x16 was too loose)
    vga_hole_r=2.5,
    vga_cable_d=7.9, vga_plate_dx=21.0,               # cover plate screws at +-21 mm
    # VGA mini gender changer (female-female), held in a cage on the outside of the VGA hole.
    # Read from ruler photos (MEASURE with calipers if it doesn't fit): metal body with the
    # yellow label, hex posts 5 mm long on both sides at the standard 25.0 mm spacing.
    cpl_body_w=33.2, cpl_body_h=12.8, cpl_body_t=6.6, cpl_clear=0.3,
    cpl_post_dx=12.5, cpl_post_d=6.2,                 # 4.8 mm hex posts, round clearance
    cpl_win_w=18.4, cpl_win_h=10.0,                   # passes the mating plug's metal shell
    cpl_lip=2.0,
    # Two-part box: rear panel + body joined by M3 screws through ribs on the side walls
    split_y=16.0, joint_z=(10.0, 32.0), rib_w=8.0, rib_len=10.0,
    # Perfboard M3 standoff grid
    grid_x=(60.0, 80.0, 100.0, 120.0, 140.0), grid_y=(62.0, 82.0, 102.0), grid_h=5.0,
    # Lid vents
    vent_w=2.5, vent_len=36.0, vent_pitch=6.0, vent_rows=8,
)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

# --------------------------------------------------------------------------------------
# Mesh helpers
# --------------------------------------------------------------------------------------
def _obj_from_bmesh(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def prism(poly, z0, z1, name="prism"):
    """Extrude a CCW polygon [(x, y), ...] from z0 to z1."""
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in poly]
    top = [bm.verts.new((x, y, z1)) for x, y in poly]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    return _obj_from_bmesh(bm, name)


def box(x0, y0, z0, x1, y1, z1, name="box"):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, name)


def rrect(x0, y0, x1, y1, r, seg=10):
    pts = []
    corners = [(x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]
    for cx, cy, a0 in corners:
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def cyl(x, y, z0, z1, d, seg=32, name="cyl"):
    r = d / 2
    poly = [(x + r * math.cos(2 * math.pi * k / seg), y + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
    return prism(poly, z0, z1, name)


def ycyl(x, z, y0, y1, d, seg=32):
    """Cylinder along the Y axis, centred on (x, z), spanning y0..y1."""
    ob = cyl(0, 0, 0, y1 - y0, d, seg)
    rotate_x90(ob)                      # extruded along -Y from 0
    ob.location = (x, y1, z)
    apply_transform(ob)
    return ob


def rotate_x90(ob):
    """Rotate so the object's XY profile lies in the XZ plane (for cutting the Y=0 wall)."""
    ob.rotation_euler = (math.radians(90), 0, 0)
    apply_transform(ob)


def apply_transform(ob):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def boolean(target, tool, op):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = tool
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def add(target, tool):
    boolean(target, tool, "UNION")


def cut(target, tool):
    boolean(target, tool, "DIFFERENCE")


def text_mesh(body, size, depth, name="text"):
    """Flat text in the XY plane, centred on the origin, z from -depth to +depth."""
    bpy.ops.object.text_add()
    t = bpy.context.object
    t.data.body = body
    t.data.size = size
    t.data.extrude = depth
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.object
    ob.name = name
    # merge duplicates so the boolean gets clean geometry
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-4)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def wall_label(target, body, x, z, size=5.0, depth=0.5):
    """Deboss text into the outer face of the rear wall (y = -wall)."""
    t = text_mesh(body, size, depth)
    t.rotation_euler = (math.radians(90), 0, 0)
    t.location = (x, -P["wall"], z)
    apply_transform(t)
    cut(target, t)


def stadium(w, h, cx, zc, y0, y1):
    """Stadium (USB-C shaped) prism in the XZ plane, centred on (cx, zc), spanning y0..y1."""
    r, seg = h / 2, 16
    prof = []
    for cxs, a0 in ((w / 2 - r, -90), (-(w / 2 - r), 90)):   # right end, then left end
        for k in range(seg + 1):
            a = math.radians(a0 + 180 * k / seg)
            prof.append((cxs + r * math.cos(a), r * math.sin(a)))
    ob = prism(prof, 0, y1 - y0, "stadium")   # profile in XY, depth along Z
    rotate_x90(ob)                            # profile in XZ, depth along -Y
    ob.location = (cx, y1, zc)
    apply_transform(ob)
    return ob


def usb_c_cut(target, cx, zc, pitch=0.0, n=1):
    """USB-C opening(s) in the rear wall: a tight stadium hole per socket through the wall,
    plus one shallow outer recess (shared when there are several side-by-side sockets) for
    the plug's moulded body."""
    for i in range(n):
        x = cx + (i - (n - 1) / 2) * pitch
        cut(target, stadium(P["usb_rec_w"], P["usb_rec_h"], x, zc, -W - 1, 1))
    cut(target, stadium(P["usb_plug_w"] + (n - 1) * pitch, P["usb_plug_h"], cx, zc,
                        -W - 1, -P["usb_inner_skin"]))


def non_manifold_edges(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return n


def export_stl(ob, path):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, ascii_format=False)


# --------------------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)

L, D, H = P["inner_l"], P["inner_d"], P["inner_h"]
W, F, R = P["wall"], P["floor"], P["corner_r"]

# Shell
shell = prism(rrect(-W, -W, L + W, D + W, R + W), -F, H, "box")
cut(shell, prism(rrect(0, 0, L, D, R), 0, H + 1, "cavity"))

# Corner screw posts (merge into the walls), pilot holes for M3 self-tappers
post_c = [(P["post_d"] / 2 - 0.5, P["post_d"] / 2 - 0.5),
          (L - P["post_d"] / 2 + 0.5, P["post_d"] / 2 - 0.5),
          (P["post_d"] / 2 - 0.5, D - P["post_d"] / 2 + 0.5),
          (L - P["post_d"] / 2 + 0.5, D - P["post_d"] / 2 + 0.5)]
for (x, y) in post_c:
    add(shell, cyl(x, y, -0.1, H, P["post_d"]))
    # fill the gap between the round post and the rounded inner corner (stays inside the walls)
    wx = 0.5 if x < L / 2 else L - 0.5
    wy = 0.5 if y < D / 2 else D - 0.5
    add(shell, box(min(x, wx), min(y, wy), -0.1, max(x, wx), max(y, wy), H))
for (x, y) in post_c:
    cut(shell, cyl(x, y, H - 14, H + 1, P["pilot_d"]))

# --- ESP32 dev board: two rails, side guides, rear stop, USB window -------------------
ex0, ew, el, rh = P["esp_x"], P["esp_w"], P["esp_len"], P["esp_rail_h"]
ecx = ex0 + ew / 2
for (ya, yb) in [(16, 22), (el - 20, el - 14)]:
    add(shell, box(ex0 - 3.5, ya, -0.1, ex0 + ew + 3.5, yb, rh))
    add(shell, box(ex0 - 3.5, ya, -0.1, ex0 - 0.6, yb, rh + 3))           # side guides
    add(shell, box(ex0 + ew + 0.6, ya, -0.1, ex0 + ew + 3.5, yb, rh + 3))
# far-end M3 boss: acts as the end stop, and the printed clip tab screws onto it and
# presses down on the PCB edge (boss top 0.3 below the PCB top so the clip clamps)
# Two corner bosses just past the far end of the PCB: they stop the board sliding away
# from the wall, and a clip tab on each presses down on a PCB corner. Boss tops sit 0.3 mm
# below the PCB top so the tabs clamp, and below the WiFi module's overhang so it passes over.
esp_pcb_top = rh + P["bo_t"]
esp_boss_r = 3.25
esp_bosses = [(ecx + sx * (ew / 2 - 1.0), el + 0.6 + esp_boss_r) for sx in (-1, 1)]
for (bx, by) in esp_bosses:
    add(shell, cyl(bx, by, -0.1, esp_pcb_top - 0.3, 2 * esp_boss_r))
for (bx, by) in esp_bosses:
    cut(shell, cyl(bx, by, -1.0, esp_pcb_top + 1, P["pilot_d"]))
esp_usb_zc = rh + P["bo_t"] + 1.6                                         # receptacle centre
# Only the COM port gets an opening: the native USB port shares GPIO19/20 with the breakout.
win_cx = ecx + P["esp_com_dx"]
if P["esp_expose_native"]:
    usb_c_cut(shell, ecx, esp_usb_zc, pitch=2 * P["esp_com_dx"], n=2)
else:
    usb_c_cut(shell, win_cx, esp_usb_zc)

# --- USB-C breakout cradles + panel openings -------------------------------------------
pw = P["bo_w"] + 0.6                       # pocket width
shelf_z = P["bo_shelf_z"]
rec_zc = shelf_z + P["bo_t"] + P["rec_h"] / 2
cradle_top = shelf_z + P["bo_t"] + P["rec_h"] - 0.4    # 0.4 below receptacle top -> clamp bites
cradle_screw_y = 4.5
for cx in P["bo_x"]:
    add(shell, box(cx - pw / 2 - 4, -0.1, -0.1, cx - pw / 2, 14, cradle_top))   # side walls
    add(shell, box(cx + pw / 2, -0.1, -0.1, cx + pw / 2 + 4, 14, cradle_top))
    add(shell, box(cx - pw / 2 - 0.1, -0.1, -0.1, cx + pw / 2 + 0.1, 8, shelf_z))  # shelf
for cx in P["bo_x"]:
    for sx in (-1, 1):
        cut(shell, cyl(cx + sx * (pw / 2 + 2), cradle_screw_y, cradle_top - 9, cradle_top + 1, P["pilot_d"]))
    usb_c_cut(shell, cx, rec_zc)

# --- VGA pass-through ---------------------------------------------------------------------
vx, vz = P["vga_x"], P["vga_z"]
vw = P["vga_plug_w"] + 2 * P["vga_clear"]
vhh = P["vga_plug_h"] + 2 * P["vga_clear"]
# bosses behind the wall for the cover plate's two M3 screws
# (half-width 2.75 keeps them just outside the hole edge so they don't narrow the opening)
for sx in (-1, 1):
    bx = vx + sx * P["vga_plate_dx"]
    add(shell, box(bx - 2.75, -0.1, -0.1, bx + 2.75, 9, vz + 4.5))
# low floor pad for the removable cable clamp (stays below the plug's path through the hole)
clamp_pad_h = 4.0
add(shell, box(vx - 11, 4, -0.1, vx + 11, 14, clamp_pad_h))
# hole the whole plug fits through
hole = prism(rrect(-vw / 2, -vhh / 2, vw / 2, vhh / 2, P["vga_hole_r"]), 0, W + 2, "vga_hole")
rotate_x90(hole)
hole.location = (vx, 1, vz)
apply_transform(hole)
cut(shell, hole)
for sx in (-1, 1):
    cut(shell, ycyl(vx + sx * P["vga_plate_dx"], vz, -W - 1, 8.5, P["pilot_d"]))
for sx in (-1, 1):
    cut(shell, cyl(vx + sx * 7.5, 9, -1.0, clamp_pad_h + 1, P["pilot_d"]))

# --- Zip-tie anchors (perfboard, VGA strain relief, wire bundles) ----------------------
def anchor(x, y):
    add(shell, box(x - 6, y - 2, -0.1, x + 6, y + 2, 6))
    cut(shell, box(x - 2.5, y - 3, 0, x + 2.5, y + 3, 3.5))

anchor(ecx, el + 18)            # ESP32 wire bundle
anchor(vx, 55)                  # VGA cable strain relief (behind the ~38 mm inside plug)

# M3 standoff grid for the perfboard (drill the perfboard to match any 2-4 of them)
for x in P["grid_x"]:
    for y in P["grid_y"]:
        add(shell, cyl(x, y, -0.1, P["grid_h"], 7.0))
for x in P["grid_x"]:
    for y in P["grid_y"]:
        cut(shell, cyl(x, y, -1.0, P["grid_h"] + 1, P["pilot_d"]))

# --- Labels on the rear panel -----------------------------------------------------------
if P["esp_expose_native"]:   # AUX over the native USB port, COM over COM
    # (no letter T in labels: Blender's built-in font meshes it with a degenerate sliver)
    lz = esp_usb_zc + P["usb_plug_h"] / 2 + 4.2
    wall_label(shell, "AUX", ecx - P["esp_com_dx"] - 0.6, lz, size=4.0)
    wall_label(shell, "COM", win_cx + 0.6, lz, size=4.0)
else:
    wall_label(shell, "COM", win_cx, esp_usb_zc + P["usb_plug_h"] / 2 + 5)
wall_label(shell, "USB", P["bo_x"][0], rec_zc + P["usb_plug_h"] / 2 + 5)
wall_label(shell, "5V", P["bo_x"][1], rec_zc + P["usb_plug_h"] / 2 + 5)
wall_label(shell, "VGA", vx, vz + 12 + 4.5)     # above the cover plate

# --------------------------------------------------------------------------------------
# Lid (built top-up, exported flipped)
# --------------------------------------------------------------------------------------
lt = P["lid_t"]
lid = prism(rrect(-W, -W, L + W, D + W, R + W), H, H + lt, "lid")
cl, lipt, liph = P["lip_clear"], P["lip_t"], P["lip_h"]
m = 16.0  # keep lip segments clear of the corner posts
for (x0, y0, x1, y1) in [
    (m, cl, L - m, cl + lipt), (m, D - cl - lipt, L - m, D - cl),
    (cl, m, cl + lipt, D - m), (L - cl - lipt, m, L - cl, D - m)]:
    add(lid, box(x0, y0, H - liph, x1, y1, H + 0.1))
for (x, y) in post_c:
    cut(lid, cyl(x, y, H - 1, H + lt + 1, P["lid_hole_d"]))
    cut(lid, cyl(x, y, H + lt - 1.6, H + lt + 1, 6.4))          # counterbore for screw heads
# vents over the middle
vx0 = L / 2 - P["vent_len"] / 2
for k in range(P["vent_rows"]):
    y = D / 2 - (P["vent_rows"] - 1) * P["vent_pitch"] / 2 + k * P["vent_pitch"]
    for dx in (-P["vent_len"] / 2 - 6, P["vent_len"] / 2 + 6):
        cut(lid, box(L / 2 + dx - P["vent_len"] / 2, y - P["vent_w"] / 2, H - 1,
                     L / 2 + dx + P["vent_len"] / 2, y + P["vent_w"] / 2, H + lt + 1))
t = text_mesh("ESP32 S3 OS", 9.0, 0.5)
t.rotation_euler = (0, 0, math.radians(180))   # reads correctly from the front (ports at the back)
t.location = (L / 2, D - 14, H + lt)
apply_transform(t)
cut(lid, t)

# --------------------------------------------------------------------------------------
# Clamp bar for the USB-C breakouts
# --------------------------------------------------------------------------------------
def yslot(x, y, travel, d, z0, z1):
    """Screw slot along Y: hole of diameter d that can move +-travel."""
    s = cyl(x, y - travel, z0, z1, d)
    add(s, cyl(x, y + travel, z0, z1, d))
    add(s, box(x - d / 2, y - travel, z0, x + d / 2, y + travel, z1))
    return s


# Part coordinates: y=0 at the screw line, +Y into the box, z=0 on top of the cradle walls.
# A stop tooth hangs down behind the receptacle (in the bare strip between the receptacle and
# the V/D-/D+/G pads), so pushing a plug in can't shove the board into the box. The tooth
# ends 0.8 mm above the PCB so it clears the receptacle's rear solder legs and touches the
# metal shell. Slotted holes (+-1.5 mm): push the bar toward the wall until the tooth sits
# against the receptacle, then tighten.
bar_len = pw + 8 + 2
stop_y0 = 3.6                                          # tooth face, ~8.1 mm from the wall
stop_t, stop_w = 1.6, 9.4                              # receptacle shell is 8.94 wide
tooth_h = cradle_top - (shelf_z + P["bo_t"]) - 0.8
clamp = box(-bar_len / 2, -3.5, 0, bar_len / 2, stop_y0 + stop_t, 4.0, "clamp_bar")
add(clamp, box(-stop_w / 2, stop_y0, -tooth_h, stop_w / 2, stop_y0 + stop_t, 0.1))
for sx in (-1, 1):
    cut(clamp, yslot(sx * (pw / 2 + 2), 0, 1.5, P["lid_hole_d"], -1, 5))

# --------------------------------------------------------------------------------------
# ESP32 end bridge: screws onto both far-end bosses (replaces the two corner clips)
# --------------------------------------------------------------------------------------
# Part coordinates: x=0 board centre line, y=0 boss centre line (+Y away from the wall),
# z=0 boss top (0.3 mm below the PCB top, so the arms clamp the board down).
# - A notch lets the WiFi module's overhanging antenna end sit inside; the notch's back face
#   is the stopper the module end rests against, so the board can't slide away from the wall
#   when a USB plug goes in.
# - Two arms reach toward the wall over the PCB corners (outside the module) and press down.
# - Slotted holes (+-3 mm): push the bridge toward the wall until the stopper touches the
#   module end, then tighten (2 x M3 x 8).
br_x, br_t = 17.0, 3.0
mod_half = 9.75                                        # WROOM module is 18 mm wide
br_stop_y = 0.0                                        # nominal module end (PCB 58 + ~4 overhang)
br_arm_y = br_stop_y - 4.0 - 2.5                       # arms overlap the PCB end by 2.5 mm
esp_bridge = box(-br_x, br_arm_y, 0, br_x, 5.0, br_t, "esp_bridge")
cut(esp_bridge, box(-mod_half, br_arm_y - 1, -1, mod_half, br_stop_y, br_t + 1))
for sx in (-1, 1):
    cut(esp_bridge, yslot(sx * (ew / 2 - 1.0), 0, 3.0, P["lid_hole_d"], -1, br_t + 1))

# --------------------------------------------------------------------------------------
# Two-part version: rear panel (ports + cradles) and body, joined by 4 x M3.
# A rib on each side wall straddles the split; screws go in from the body side
# (counterbored) into pilot holes in the panel half of the rib.
# --------------------------------------------------------------------------------------
sy, rw, rl = P["split_y"], P["rib_w"], P["rib_len"]
rib_top = H - P["lip_h"] - 2                     # stays below the lid lip
split = shell.copy()
split.data = shell.data.copy()
bpy.context.collection.objects.link(split)
for (x0, x1) in [(-0.1, rw), (L - rw, L + 0.1)]:
    add(split, box(x0, sy - rl, -0.1, x1, sy + rl, rib_top))

rear_panel = split.copy()
rear_panel.data = split.data.copy()
bpy.context.collection.objects.link(rear_panel)
boolean(rear_panel, box(-W - 1, -W - 1, -F - 1, L + W + 1, sy, H + 1, "keep"), "INTERSECT")
rear_panel.name = "rear_panel"
body = split
boolean(body, box(-W - 1, sy, -F - 1, L + W + 1, D + W + 1, H + 1, "keep"), "INTERSECT")
body.name = "box_body"

joint_x = (rw / 2, L - rw / 2)
for jx in joint_x:
    for jz in P["joint_z"]:
        cut(body, ycyl(jx, jz, sy - 1, sy + rl + 1, P["lid_hole_d"]))     # clearance
        cut(body, ycyl(jx, jz, sy + 4, sy + rl + 1, 6.5))               # counterbore, 4 mm left
        cut(rear_panel, ycyl(jx, jz, sy - rl + 1, sy + 1, P["pilot_d"])) # pilot, 9 mm deep

# --------------------------------------------------------------------------------------
# VGA cover plate (fits over the cable after the plug is pushed out) and cable clamp cap
# --------------------------------------------------------------------------------------
pdx = P["vga_plate_dx"]
vga_plate = prism(rrect(-pdx - 3.5, -12, pdx + 3.5, 12, 2.5), 0, 2.5, "vga_plate")
cut(vga_plate, cyl(0, 0, -1, 4, P["vga_cable_d"] + 1.0))
cut(vga_plate, box(-(P["vga_cable_d"] + 0.6) / 2, -13, -1, (P["vga_cable_d"] + 0.6) / 2, 0, 4))
for sx in (-1, 1):
    cut(vga_plate, cyl(sx * pdx, 0, -1, 4, P["lid_hole_d"]))

# two-piece cable clamp, both removable: lower block sits on the floor pad, cap on top,
# 2 x M3 x 20 through both into the pad. Groove centre ends up at cable height (vga_z).
vga_cap = box(-11, -5, 0, 11, 5, 6, "vga_clamp_cap")
cut(vga_cap, ycyl(0, 0, -6, 6, P["vga_cable_d"] - 0.6))   # groove on the bottom face
for sx in (-1, 1):
    cut(vga_cap, cyl(sx * 7.5, 0, -1, 7, P["lid_hole_d"]))
blk_h = vz - clamp_pad_h
vga_block = box(-11, -5, 0, 11, 5, blk_h, "vga_clamp_block")
cut(vga_block, ycyl(0, blk_h, -6, 6, P["vga_cable_d"] - 0.6))  # groove on the top face
for sx in (-1, 1):
    cut(vga_block, cyl(sx * 7.5, 0, -1, blk_h + 1, P["lid_hole_d"]))

# --------------------------------------------------------------------------------------
# VGA gender-changer cage (outside the VGA hole, replaces the cover plate)
# --------------------------------------------------------------------------------------
# Part coordinates: x along the wall, y up, z out of the wall (z=0 on the wall's outer face).
# Two pieces share the two M3 screws at +-21 mm (existing pilots beside the VGA hole):
#   frame: back lip (2 mm, sits on the wall) + walls around the changer's body
#   cap:   front lip (2 mm) that closes the pocket
# The body is clamped between the two lips. The frame walls are 0.6 mm shorter than the body,
# so the cap always presses on the body, never on the walls. Both lips have a window for the
# D shell and the two hex posts; a plug's metal flange sits on the hex posts' tops (5 mm out),
# so it never reaches the lips and both plugs mate fully.
def cpl_window(z0, z1):
    w = prism(rrect(-P["cpl_win_w"] / 2, -P["cpl_win_h"] / 2, P["cpl_win_w"] / 2,
                    P["cpl_win_h"] / 2, 2.0), z0, z1, "cpl_win")
    for sx in (-1, 1):
        add(w, cyl(sx * P["cpl_post_dx"], 0, z0, z1, P["cpl_post_d"]))
    return w


cpl_outline = rrect(-pdx - 3.5, -12, pdx + 3.5, 12, 2.5)
cpl_pw = P["cpl_body_w"] + 2 * P["cpl_clear"]
cpl_ph = P["cpl_body_h"] + 2 * P["cpl_clear"]
cpl_wall_t = P["cpl_body_t"] - 0.6
lip = P["cpl_lip"]
cpl_frame = prism(cpl_outline, 0, lip + cpl_wall_t, "vga_coupler_frame")
cut(cpl_frame, box(-cpl_pw / 2, -cpl_ph / 2, lip, cpl_pw / 2, cpl_ph / 2, lip + cpl_wall_t + 1))
cut(cpl_frame, cpl_window(-1, lip + 0.5))
cpl_cap = prism(cpl_outline, 0, lip, "vga_coupler_cap")
cut(cpl_cap, cpl_window(-1, lip + 1))
for sx in (-1, 1):
    cut(cpl_frame, cyl(sx * pdx, 0, -1, lip + cpl_wall_t + 1, P["lid_hole_d"]))
    cut(cpl_cap, cyl(sx * pdx, 0, -1, lip + 1, P["lid_hole_d"]))

# --------------------------------------------------------------------------------------
# VGA fit-test strip: same wall thickness, three holes with 0.2 / 0.4 / 0.6 mm clearance
# per side, numbered 1-2-3 from left to right (seen from the numbered side).
# --------------------------------------------------------------------------------------
vga_test = prism(rrect(0, 0, 3 * 44 + 4, 30, 2.0), 0, W, "vga_fit_test")
for i, c in enumerate((0.2, 0.4, 0.6)):
    cxh = 4 + 22 + i * 44
    hw, hh = P["vga_plug_w"] + 2 * c, P["vga_plug_h"] + 2 * c
    cut(vga_test, prism(rrect(cxh - hw / 2, 13 - hh / 2, cxh + hw / 2, 13 + hh / 2, P["vga_hole_r"]),
                        -1, W + 1, "h"))
    tn = text_mesh(str(i + 1), 4.0, 0.4)
    tn.location = (cxh, 26.5, W)
    apply_transform(tn)
    cut(vga_test, tn)

# --------------------------------------------------------------------------------------
# Checks + export
# --------------------------------------------------------------------------------------
for ob in (shell, rear_panel, body, lid, clamp, esp_bridge, cpl_frame, cpl_cap, vga_plate, vga_cap, vga_block, vga_test):
    dims = ob.dimensions
    print(f"{ob.name}: {dims.x:.1f} x {dims.y:.1f} x {dims.z:.1f} mm, "
          f"{len(ob.data.polygons)} faces, non-manifold edges: {non_manifold_edges(ob)}")

export_stl(shell, os.path.join(OUT, "box.stl"))
# rear panel: export lying on its outer face (the -Y face goes down onto the bed)
rp_print = rear_panel.copy()
rp_print.data = rear_panel.data.copy()
bpy.context.collection.objects.link(rp_print)
rp_print.rotation_euler = (math.radians(90), 0, 0)
apply_transform(rp_print)
zmin = min(v.co.z for v in rp_print.data.vertices)
rp_print.location.z -= zmin
apply_transform(rp_print)
export_stl(rp_print, os.path.join(OUT, "rear_panel.stl"))
print(f"rear_panel (print orientation): {rp_print.dimensions.x:.1f} x {rp_print.dimensions.y:.1f} "
      f"x {rp_print.dimensions.z:.1f} mm")
bpy.data.objects.remove(rp_print, do_unlink=True)
export_stl(body, os.path.join(OUT, "box_body.stl"))
# small parts with features underneath: flip for printing (flat top on the bed)
def export_flipped(ob, path):
    c = ob.copy()
    c.data = ob.data.copy()
    bpy.context.collection.objects.link(c)
    c.rotation_euler = (math.radians(180), 0, 0)
    apply_transform(c)
    zmin = min(v.co.z for v in c.data.vertices)
    for v in c.data.vertices:
        v.co.z -= zmin
    export_stl(c, path)
    bpy.data.objects.remove(c, do_unlink=True)


export_flipped(clamp, os.path.join(OUT, "clamp_bar.stl"))      # stop tooth up
export_stl(esp_bridge, os.path.join(OUT, "esp_bridge.stl"))
export_stl(cpl_frame, os.path.join(OUT, "vga_coupler_frame.stl"))   # back lip on the bed
export_stl(cpl_cap, os.path.join(OUT, "vga_coupler_cap.stl"))
export_stl(vga_plate, os.path.join(OUT, "vga_cover_plate.stl"))
export_stl(vga_cap, os.path.join(OUT, "vga_clamp_cap.stl"))
export_stl(vga_block, os.path.join(OUT, "vga_clamp_block.stl"))
export_stl(vga_test, os.path.join(OUT, "vga_fit_test.stl"))
# lid: flip for printing (top face down)
lid_print = lid.copy()
lid_print.data = lid.data.copy()
bpy.context.collection.objects.link(lid_print)
lid_print.rotation_euler = (math.radians(180), 0, 0)
apply_transform(lid_print)
export_stl(lid_print, os.path.join(OUT, "lid.stl"))
bpy.data.objects.remove(lid_print, do_unlink=True)

# --------------------------------------------------------------------------------------
# Preview renders
# --------------------------------------------------------------------------------------
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.85, 0.55, 0.2)
scene.display.shading.show_cavity = True
scene.display.shading.show_shadows = True
scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
scene.render.film_transparent = False
world = bpy.data.worlds.new("w")
scene.world = world

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.collection.objects.link(cam)
scene.camera = cam


def look_at(ob, target):
    from mathutils import Vector
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render(name, loc, target, lens=35):
    cam.location = loc
    cam_data.lens = lens
    look_at(cam, target)
    scene.render.filepath = os.path.join(OUT, f"preview_{name}.png")
    bpy.ops.render.render(write_still=True)


# lid raised for an exploded view
lid.location.z += 40
clamp.location = (P["bo_x"][0], cradle_screw_y, cradle_top + 15)
clamp2 = clamp.copy()
bpy.context.collection.objects.link(clamp2)
clamp2.location = (P["bo_x"][1], cradle_screw_y, cradle_top + 15)

esp_bridge.location = (ecx, esp_bosses[0][1], esp_pcb_top - 0.3 + 15)
rear_panel.hide_render = body.hide_render = vga_plate.hide_render = vga_cap.hide_render = vga_block.hide_render = vga_test.hide_render = True
render("exploded", (L + 140, D + 150, 190), (L / 2, D / 2, 20))
lid.hide_render = True
render("inside", (L / 2 + 40, D + 120, 170), (L / 2, D / 2, 0))
clamp.hide_render = clamp2.hide_render = esp_bridge.hide_render = True
render("rear_panel", (L / 2, -230, 30), (L / 2, 0, 15), lens=50)
# two-part view: panel pulled back 25 mm from the body
for ob in list(scene.objects):
    if ob.type == "MESH":
        ob.hide_render = True
rear_panel.hide_render = body.hide_render = False
rear_panel.location.y -= 25
render("two_part", (L + 120, -170, 150), (L / 2, D / 3, 10))

# fit check: hold-downs installed on dummy boards (PCBs green-ish only by shape, not colour)
for ob in list(scene.objects):
    if ob.type == "MESH":
        ob.hide_render = True
rear_panel.location.y += 25
shell.hide_render = False
esp_bridge.hide_render = False
esp_bridge.location = (ecx, esp_bosses[0][1], esp_pcb_top - 0.3)
for c, cx in ((clamp, P["bo_x"][0]), (clamp2, P["bo_x"][1])):
    c.hide_render = False
    c.location = (cx, cradle_screw_y, cradle_top)
box(ex0, 0.3, rh, ex0 + ew, el, esp_pcb_top, "dummy_esp_pcb")
box(ecx - 9, el - 21.5, esp_pcb_top, ecx + 9, el + 4.0, esp_pcb_top + 0.8, "dummy_module")
box(ecx - 8, el - 21.5, esp_pcb_top + 0.8, ecx + 8, el - 4.0, esp_pcb_top + 3.2, "dummy_shield")
for cx in P["bo_x"]:
    box(cx - 6.4, 2.8, shelf_z, cx + 6.4, 13.3, shelf_z + P["bo_t"], "dummy_bo_pcb")
    box(cx - 4.47, 0.8, shelf_z + P["bo_t"], cx + 4.47, 8.15, shelf_z + P["bo_t"] + 3.26, "dummy_rec")
scene.display.shading.color_type = "OBJECT"
for ob in scene.objects:
    if ob.type == "MESH":
        ob.color = (0.85, 0.85, 0.82, 1)
for ob in scene.objects:
    if ob.name.startswith("dummy"):
        ob.color = (0.1, 0.35, 0.15, 1)
    if ob.name.startswith("dummy_rec") or ob.name.startswith("dummy_shield"):
        ob.color = (0.6, 0.6, 0.65, 1)
for ob in (esp_bridge, clamp, clamp2):
    ob.color = (0.95, 0.45, 0.1, 1)
for ob, z0 in ((cpl_frame, 0.0), (cpl_cap, lip + P["cpl_body_t"])):
    ob.rotation_euler = (math.radians(90), 0, 0)    # part z (out of wall) -> box -Y
    ob.location = (vx, -W - z0, vz)
    ob.hide_render = False
    ob.color = (0.95, 0.45, 0.1, 1)
bw, bh, bt = P["cpl_body_w"], P["cpl_body_h"], P["cpl_body_t"]
cb = box(vx - bw / 2, -W - lip - bt, vz - bh / 2, vx + bw / 2, -W - lip, vz + bh / 2, "dummy_cpl_body")
cb.color = (0.9, 0.85, 0.1, 1)
dsh = box(vx - 8.2, -W - lip - bt - 6, vz - 4, vx + 8.2, -W + 2.0, vz + 4, "dummy_cpl_shell")
dsh.color = (0.6, 0.6, 0.65, 1)
for sx in (-1, 1):
    hp = ycyl(vx + sx * 12.5, vz, -W - lip - bt - 5, -W - lip + 5, 4.8)
    hp.name = "dummy_cpl_post"
    hp.color = (0.6, 0.6, 0.65, 1)
render("fit_check_vga", (vx - 45, -75, vz + 35), (vx, -W - 6, vz), lens=50)
render("fit_check_esp", (ecx + 45, el + 45, 55), (ecx, el - 2, esp_pcb_top), lens=50)
render("fit_check_usb", (P["bo_x"][0] + 35, 45, 40), (P["bo_x"][0], 6, cradle_top - 2), lens=50)
print("done")
