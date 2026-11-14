# Session summary: hardware bring-up, enclosure and the OS brief (2026-11-10 to 2026-11-12)

This covers the first working session of the project, before the OS itself was built. In it the
AI agent (Claude, in Claude Code) took a hand-wired ESP32-S3 from nothing to a verified colour
picture on a remote-viewable screen. Along the way it debugged USB input, designed a 3D-printed
enclosure, and wrote the brief that a second agent then used to build the OS. The second session
is described in `docs/SESSION-SUMMARY.md`.

All human actions in this session are logged in `INTERVENTIONS.md`, rows 0-26. Hardware details
are in `docs/NOTES.md`.

## 1. Starting point

- **The brief:** `docs/HANDOFF.md` describes a graphical OS on an ESP32-S3 with VGA output,
  keyboard/mouse input and loadable apps, for a video testing whether an AI can build an OS for a
  microcontroller. The rules: log every human intervention, and ask before any rewiring.
- **The hardware:**
  - **Already wired by the human:** a 2-bit-per-channel resistor DAC (6 GPIOs → 64 colours), H/V
    sync wires, a cut VGA cable, a VGA-HDMI converter and a JetKVM for viewing.
  - **Board:** identified during the session as an N16R8, with 16 MB flash, 8 MB octal PSRAM and
    a CH343 USB-serial chip.
- **The user's instruction:** "Don't make the whole operating system yet. Let's first test the
  colors."

## 2. Milestone 1: colour bars (2026-11-10)

**Firmware (ESP-IDF 5.5.3):**
- **Video:** the RGB LCD peripheral drives an 8-bit bus, one byte per pixel (RGB222), with the
  framebuffer in PSRAM and bounce buffers in internal RAM.
- **Sync self-test:** a pulse-counter check that measures the board's own H-sync and V-sync
  frequency and duty cycle.
- **Serial commands:** framebuffer dump, test pattern, solid fills and mode switching.
- **Python tools:** `serlog.py`, `fbdump.py`, `serbridge.py`, `send.py` and `cycle_modes.py`.

**The "no signal" hunt, in order:**

1. **No capture card:** the HDMI capture card was not detected by macOS. The JetKVM became the
   viewer instead, after the human allowed Chrome on the local network.
2. **JetKVM, then a monitor:** the JetKVM showed "No HDMI signal". The converter got 5 V power,
   the HDMI went to an external monitor, and the sync wires were checked with a multimeter. The
   wiring was good, but there was still no signal.
3. **Pin 9 wire (approved rewiring):** the human added a 5 V wire to VGA pin 9. There was still
   no signal.
4. **Root cause 1, wrong converter direction:** the converter was HDMI→VGA, the wrong direction
   for this setup. The agent researched a replacement, but the human placed the order. The
   replacement was a VGA-source-to-HDMI adapter with USB power, plus a VGA female-female
   coupler and an HDMI cable.
5. **Testing on the Acer VGA monitor:** with the VGA cable plugged straight into the monitor, the
   agent cycled the sync variants while the human counted the white "mode bars" on screen.
   800×600 worked; standard 640×480 did not.
6. **Root cause 2, fractional clock divider:** the exact VGA pixel clock (25.175 MHz) needs the
   LCD peripheral's fractional clock divider, and the monitor rejects the uneven timing that
   produces. Every integer-divided clock worked. The new default is **640×480 at 26.67 MHz**
   (160 MHz ÷ 6), giving 31.45 kHz / 59.9 Hz, almost exactly standard.
7. **Colours confirmed:** a photo showed all 4 levels of red, green, blue and grey in the right
   order. Milestone 1 was done.

## 3. USB input bring-up (2026-11-10)

- **The breakout:** the board's native USB connector didn't fit next to the UART cable, so the
  human soldered a USB-C female breakout to GPIO19/20, GND and 5V. This is documented in
  `docs/HANDOFF-AMENDMENT-USB.md`.
- **Firmware:** the agent wrote a USB host test (`main/usb_input.c`), which logs descriptors and
  raw HID reports and reads the USB port's line state for debugging.
- **The problems, as they were found:**
  - Plugging the JetKVM's USB-C into the breakout knocked out both the JetKVM and the board. The
    JetKVM's USB-C is also its power input.
  - A keyboard, then a mouse: neither was detected, and the mouse LED stayed off.
  - **Root cause:** the human measured 0.7 V on the board's 5Vin pin. That pin is input-only (it
    sits behind a diode), so nothing plugged into the breakout got power. The breakout also has no
    CC resistors, so a Mac won't talk to it directly.
- **Fix (approved rewiring):** the second Robojax breakout became a 5 V power input, fed by a USB
  charger. The human typed "hello" and the keyboard reports arrived. USB host input works.

## 4. The enclosure (2026-11-10 to 2026-11-12)

The human asked for a box for everything: two USB-C breakouts, the resistor perfboard, the
ESP32 and the VGA cable. The agent wrote a parametric Blender script that produces print-ready
STLs for an Elegoo Neptune 3 Pro, then set up Cura with the print settings and opened each file
in it. Everything is in `enclosure/`; see `enclosure/README.md` for the part list, screws and
assembly.

How the design evolved, mostly from the human's photos of real prints:

- **First design:**
  - A 160×110×45 mm inner space and a rear panel with labelled cut-outs (AUX/COM, USB, 5V, VGA).
  - M3 screws throughout, "ESP32 S3 OS" on the lid.
  - The rear panel can be split off and screwed to the body, so a bad port fit only means
    reprinting the panel.
- **The COM cut-out** was reshaped to expose just the USB-C ports, then widened to expose both
  of the board's ports "just in case".
- **The VGA hole** was made big enough for the whole plug body to pass through. The first print
  was too loose, so a fit-test strip with 3 clearances was printed and the tightest one chosen.
  The whole box was then printed in one piece.
- **Combined print:** the lid and all remaining small parts were laid out on one print plate
  (`plate_lid_spares.stl`).
- **Hold-downs (from photos of the fitted boards):**
  - An ESP32 bridge that screws over the board's far end. Its notch catches the module's
    overhang, so plugging in a cable can't push the board back.
  - USB-C clamp bars with a stop tooth that drops into the strip behind the receptacle.
  - A separate plate with just these parts (`plate_holddowns.stl`).
- **VGA gender changer:**
  - The printed hole came out too tight for the plug, so the human put a VGA female-female gender
    changer in the hole instead. That was loose.
  - The agent designed a two-piece cage (frame + cap, 2 × M3 × 20) that clamps the changer's body
    on the outside of the wall.
  - It also rendered a labelled assembly guide showing the stacking order, the outside and inside
    views, and a cross-section (`enclosure/out/vga_assembly_guide.png`).
- **Not acted on:** a message about unrelated purchases was meant for another project. The user
  withdrew it, and nothing was done with it.

## 5. First remote picture through the JetKVM (2026-11-12)

With the box assembled and the new adapter in place, the human wired up the JetKVM.

1. **"No HDMI signal detected":** the Mac didn't see the board either. The USB cable was in the
   AUX port, which is the ESP32's own USB and is taken over by the USB-host firmware. Moved to COM,
   the board appeared.
2. **The board was fine:** clean boot, video running, and the sync self-test reported correct
   frequencies in all 4 integer-clock modes. The agent cycled the modes while watching the JetKVM:
   still no signal in any of them, so the fault had to be after the VGA socket.
3. **Root cause 3, adapter power:** the adapter has no 5 V. The pin 9 wire carries nothing,
   because the board's 5V pin is input-only. With the adapter's USB power plugged in, the JetKVM
   showed the test pattern. This was the **first time the agent could see the screen itself**,
   without the human describing the monitor.

**Working chain:** ESP32 VGA → gender changer in the box wall → VGA-to-HDMI adapter (USB-powered)
→ HDMI → JetKVM (viewed in Chrome; sometimes the stream has to be started manually).

## 6. The OS brief (2026-11-12)

The user asked for a prompt to hand to another agent to build the full OS: as efficient and
low-level as possible, with all the basic OS needs (viewing and saving files, apps), and a
Windows-95-style retro look. The agent wrote `docs/OS-BUILD-PROMPT.md`, which contains:

- **Rules:** keep logging interventions; ask before rewiring; a feature counts only when seen on
  the real screen; every performance decision backed by a measured number in `docs/PERF.md`; an
  original OS with its own name and artwork (no Microsoft names, logos or copied graphics).
- **Proven hardware facts:** pin map, the 26.67 MHz mode, why 25.175 MHz fails, the display
  chain, serial-port quirks, and the USB power situation.
- **Performance strategy:**
  - The real bottleneck is PSRAM bandwidth shared with scan-out.
  - Dirty rectangles, a save-under cursor sprite and vblank-synced flushes.
  - Hot loops in internal RAM using the S3's SIMD instructions, and DMA copies.
  - Direct LCD_CAM/GDMA programming only if measured gains justify it.
  - A core split, and concrete targets (60 FPS cursor, 30+ FPS window drags, boot under 3 s).
- **Look:** grey bevelled panels, navy title bars, a teal desktop, a taskbar with a menu button,
  hand-drawn pixel fonts and icons, and its own toolkit instead of LVGL. The 64-colour palette
  happens to fit this style.
- **Features:** desktop, windows, file management, text editor, viewers, loadable ELF apps with
  an app API, a game, system info, a task list, settings and robustness.
- **Keyboard-only navigation (added at the user's request):**
  - Every feature must also work without a mouse, because the user will test it keyboard-only
    after the demo.
  - Visible focus at all times, global shortcuts (taskbar menu, window switching, closing, moving
    and sizing windows, task list) and Tab/arrow/Enter/Esc navigation in every window.
  - File browser and editor shortcuts, a playable game, an F1 shortcut list, and a scripted
    keyboard-only test run at every milestone.

**Later changes, from the other agent's session:**
- **No SD card:** the brief proposed SD-card wiring, but the user then decided against an SD
  card. Storage became a FAT drive in the internal flash (`/disk`).
- **The result:** an OS called **Bevel OS**, covered in `docs/SESSION-SUMMARY.md`,
  `docs/OS-REPORT.md` and `docs/PERF.md`.

## 7. Root causes found in this session (useful for the video)

| Symptom | Cause | Fix |
|---|---|---|
| "No signal" everywhere at first | Converter was HDMI→VGA, the wrong direction | Bought a VGA-source-to-HDMI adapter + female-female coupler |
| Monitor shows 800×600 but not 640×480 | 25.175 MHz needs the fractional clock divider; the monitor rejects the jitter | Integer clock 26.67 MHz (160 ÷ 6) |
| USB keyboard/mouse dead on the breakout | Board's 5Vin pin is input-only (0.7 V), so the breakout had no power | Second breakout as a 5 V input from a charger |
| JetKVM USB-C on the breakout killed both devices | JetKVM's USB-C is also its power input | Left for the OS session |
| Mac doesn't see the board | Cable was in AUX (native USB, used by the USB-host firmware) | Use the COM port |
| JetKVM "No HDMI signal" with the new adapter | Adapter unpowered; VGA pin 9 carries no 5 V | Plug in the adapter's USB power |
| VGA plug didn't fit the printed hole; the gender changer was loose in it | Print tolerance | Printed cage that clamps the gender changer outside the wall |

## 8. Human involvement

The human made 27 logged interventions in this session (rows 0-26 of `INTERVENTIONS.md`):

| Kind of action | Rows |
|---|---|
| Plugging and unplugging cables | 1, 3, 5, 6, 9, 10, 15, 16, 17, 24, 25, 26 |
| Approved rewiring (pin 9 5 V wire, USB-C breakout, 5 V input breakout) | 8, 14, 19 |
| Measuring or checking with a multimeter | 7, 18 |
| Watching the monitor and reporting what it showed, before the agent could see the screen | 11, 12, 13 |
| A macOS privacy permission | 4 |
| Typing on the keyboard for a test | 20 |
| 3D printing and fitting the enclosure | 21, 22, 23 |
| Wiring done before the session started | 0 |
| The capture card that macOS never detected | 2 |

All purchases were made by the human.
