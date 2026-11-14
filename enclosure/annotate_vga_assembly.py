"""Combine the vga_asm_*.png renders into one labelled sheet: out/vga_assembly_guide.png"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
anchors = json.load(open(os.path.join(OUT, "vga_asm_labels.json")))

S = 0.6                       # panel scale (1500 x 1050 -> 900 x 630)
PW, PH = int(1500 * S), int(1050 * S)
TITLE_H, LEG_LINE, LEG_N = 56, 32, 6
font_t = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
font_n = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
ORANGE, WHITE, GREY = (242, 115, 26), (240, 240, 240), (170, 170, 175)

PANELS = [
    ("exploded", "1. Order, from the wall outwards", [
        ("box wall", "Box rear wall with the VGA hole"),
        ("1  frame (back lip on the wall)", "Frame: flat side on the wall, pocket facing out"),
        ("2  gender changer", "Gender changer: body sits in the frame's pocket"),
        ("3  cap", "Cap: closes the pocket"),
        ("4  2 x M3 x 20", "2 x M3 x 20 through cap + frame into the wall"),
        ("VGA-to-HDMI adapter side", "Plug from the VGA-to-HDMI adapter (outside)"),
    ]),
    ("outside", "2. Assembled, from outside", [
        ("cage clamps the changer", "Changer body clamped between the two lips"),
        ("plug from the adapter", "Adapter plug screws onto the changer's posts"),
    ]),
    ("inside", "3. Inside the box (lid off)", [
        ("internal VGA cable (from the resistor DAC)", "Internal VGA cable from the resistor DAC"),
        ("plug + thumbscrews into the changer", "Its plug mates through the hole; tighten thumbscrews"),
        ("box wall", "Rear wall (inside face)"),
    ]),
    ("section", "4. Cut through the middle", [
        ("outside", "Outside: adapter plug"),
        ("cap lip", "Cap lip (2 mm)"),
        ("changer body (clamped)", "Changer body, clamped"),
        ("frame lip", "Frame lip (2 mm) against the wall"),
        ("wall", "Box wall"),
        ("inside the box", "Inside: internal cable plug"),
    ]),
]

cell_h = TITLE_H + PH + 16 + LEG_N * LEG_LINE + 16
sheet = Image.new("RGB", (2 * PW + 3 * 20, 2 * cell_h + 3 * 20), (30, 30, 34))
d = ImageDraw.Draw(sheet)
for i, (view, title, items) in enumerate(PANELS):
    ox, oy = 20 + (i % 2) * (PW + 20), 20 + (i // 2) * (cell_h + 20)
    img = Image.open(os.path.join(OUT, f"vga_asm_{view}.png")).convert("RGB").resize((PW, PH), Image.LANCZOS)
    sheet.paste(img, (ox, oy + TITLE_H))
    d.text((ox, oy + 10), title, font=font_t, fill=WHITE)
    for n, (key, text) in enumerate(items, 1):
        ax, ay = anchors[view][key]
        cx, cy = ox + ax * S, oy + TITLE_H + ay * S
        r = 15
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ORANGE, outline=WHITE, width=2)
        d.text((cx, cy), str(n), font=font_n, fill=WHITE, anchor="mm")
        ly = oy + TITLE_H + PH + 16 + (n - 1) * LEG_LINE
        d.ellipse((ox, ly, ox + 24, ly + 24), fill=ORANGE)
        d.text((ox + 12, ly + 12), str(n), font=font_n, fill=WHITE, anchor="mm")
        d.text((ox + 36, ly + 1), text, font=font, fill=GREY)

path = os.path.join(OUT, "vga_assembly_guide.png")
sheet.save(path)
print(path, sheet.size)
