# Prompt: build the retro OS for the ESP32-S3 VGA computer

You are taking over a working hardware bring-up and building a small, fast, graphical operating
system for it. The project lives in this repository (`esp32-op`). Read this whole prompt first,
then `docs/HANDOFF.md`, `docs/HANDOFF-AMENDMENT-USB.md`, `docs/NOTES.md` and `INTERVENTIONS.md`.

This is filmed for a video testing whether an AI model can build an OS for a microcontroller. The
human is your hands for anything physical and nothing else: you write, build, flash, test and debug
the software yourself.

## Goal

A complete little desktop OS on the ESP32-S3 with a **retro mid-90s desktop look**, made **as fast
and as lean as the hardware allows**, which covers the basic needs of an operating system:
browsing, opening, editing and saving files, and running apps.

## Hard rules

1. **Log every manual human action** (plugging, unplugging, pressing reset, rewiring, checking
   something, approving something) as a new row in `INTERVENTIONS.md`. The table already has
   rows 0-26; continue from 27. Be honest and specific: this log is reported at the end of the video.
2. **Ask before any rewiring.** Do not change the pin map below without the human's approval.
   Propose exact pins and wiring, wait for a yes, then log it.
3. **Verify on the real screen.** A feature is done only when you have seen it working on the
   display (see "Seeing the screen"), not when it compiles.
4. **Measure, don't guess.** Every performance decision is backed by a number (cycles, FPS,
   frame time, bytes of RAM) printed over serial. Keep a running table of these numbers in
   `docs/PERF.md`.
5. Commit at each working milestone, with a short message saying what works and what was measured.
   The current working tree has uncommitted milestone 1 work; commit that first.
6. The look is **inspired by** the 90s desktop style, but it is an original OS. Give it its own name.
   Do not use Microsoft names, logos, the Windows flag, its startup sound, or copied icons, fonts
   or bitmaps. Draw your own icons and your own bitmap font.

## Hardware (what is already proven to work)

- **Board:** ESP32-S3 N16R8 (rev v0.2): 2 cores at 240 MHz, 16 MB flash, 8 MB octal PSRAM.
  About 320 KB internal RAM free at boot. GPIO 33-37 are taken by the octal PSRAM.
- **Toolchain:** ESP-IDF v5.5.3. The Python env with pyserial is
  `~/.espressif/python_env/idf5.5_py3.12_env/bin/python`.
- **Serial / flashing:** the board's **COM** USB-C port (WCH CH343) appears on the Mac as
  `/dev/cu.usbmodem<serial>`. The AUX port is the ESP32's native USB, which the firmware uses for
  USB host. The Mac will not see the board through AUX. Opening the serial port can reset the
  board, so a tool that wants to talk to running firmware must hold the port open (see
  `tools/serbridge.py`). The console runs at 115200 baud; the CH343 can go much faster, so raising
  it (e.g. 2 Mbaud) is worth doing for framebuffer dumps.
- **Video:** the RGB LCD peripheral (`esp_lcd_new_rgb_panel`) drives a resistor DAC.
  - **Format:** 6-bit colour (RGB222), 64 colours, 8-bit data bus, one byte per pixel:
    `pixel = (B << 4) | (G << 2) | R`, each channel 0-3. The two top bits are unused.
  - **Pin map (do not change without asking):**

    | GPIO | Signal | GPIO | Signal |
    |---|---|---|---|
    | 5 | Red low bit | 4 | Red high bit |
    | 7 | Green low bit | 6 | Green high bit |
    | 16 | Blue low bit | 15 | Blue high bit |
    | 17 | H-sync | 18 | V-sync |
  - **Working mode:** 640×480 at 60 Hz, 26.67 MHz pixel clock (PLL160 ÷ 6), H total 848,
    negative sync. This is mode 1 in `main/vga.c`, and it shows on both the test monitor and the
    JetKVM.
  - **Avoid exactly 25.175 MHz:** that needs the LCD clock's fractional divider, and the monitor
    refuses the result. Only use integer-divided pixel clocks.
  - **Other modes that also work:** 24 MHz (PLL240 ÷ 10); 800×600 at 60 Hz, 40 MHz, positive
    sync; and positive sync at 640×480.
  - **Framebuffer:** 300 KB in PSRAM, scanned out through 10-line bounce buffers in internal RAM.
- **Display chain:** VGA → female-female gender changer in the box wall → VGA-to-HDMI adapter
  (needs its own USB power, otherwise "No HDMI signal") → HDMI → JetKVM.
- **Input:**
  - **Wiring:** a USB-C breakout is wired to the native USB pins (D− GPIO19, D+ GPIO20) and the
    firmware runs ESP-IDF USB host with `espressif/usb_host_hid` (`main/usb_input.c`).
  - **What works:** a plain USB keyboard plugged into the box's "USB" port works (raw HID reports
    logged), as long as a USB charger is plugged into the box's "5V" port. The board's own 5Vin pin
    gives no 5 V to the breakout.
  - **Not working yet:** the JetKVM's own keyboard/mouse (its USB shows "Disconnected"). The
    JetKVM's USB-C is also its power input, and the breakout has no CC resistors. Expect to ask
    the human to sort out power and cabling here (see `docs/HANDOFF-AMENDMENT-USB.md`). The
    JetKVM mouse most likely reports **absolute** coordinates, so parse the HID report descriptor;
    don't assume boot protocol.
- **SD card: not wired yet.**
  - **Pins:** pick pins for 4-bit SDMMC (the S3 routes SDMMC through the GPIO matrix) from the free
    ones: roughly 1, 2, 8-14, 21, 38-42, 47, 48. Check whether the board's onboard RGB LED uses 38
    or 48, and avoid the strapping pins 0, 3, 45 and 46.
  - **Fallback:** if 4-bit wiring is impractical, use SPI mode.
  - **Approval:** propose the exact wiring and an SD module or breakout to the human and wait for
    approval before using it.
- **Free pins otherwise:** everything not listed above, except 0, 3, 45, 46 (strapping),
  19 and 20 (USB), 43 and 44 (console), and 26-37 (flash and PSRAM).

## Seeing the screen

- **JetKVM:** browser UI at `http://<jetkvm-ip>`, one viewer session at a time. If you have
  browser automation, open it and take screenshots. Chrome sometimes shows "Autoplay permissions
  required"; click "Manually start stream".
- **Serial fallback:** the firmware has a `D` command that dumps the framebuffer, and
  `tools/fbdump.py` turns it into a PNG. Keep that command in the OS: it is the pixel-exact check
  for rendering bugs.
- **Serial commands to keep for testing:** keep a serial command channel in the OS. Use it to
  inject key presses and mouse moves/clicks and to run self-tests, so you can test the GUI without
  the human at the keyboard. This does not replace testing with real USB input.

## Performance: go as low-level as it pays

The user wants this as efficient as possible. Go down to registers, DMA and assembly wherever that
buys measurable speed or memory. Keep ESP-IDF and FreeRTOS as the base for the boot chain, flash,
PSRAM, USB host, SD/FAT and the scheduler, unless you measure a concrete gain from replacing a
piece. Rewriting a USB stack is not a good trade.

Known constraints:

- **The bottleneck is PSRAM bandwidth.** Scan-out alone reads about 27 MB/s from PSRAM (26.67 MHz
  × 1 byte, 640×480 visible at 60 Hz), and the CPU shares that bus. Every byte the renderer writes
  to PSRAM competes with the display. Underruns show up as jitter or garbage lines, so check for
  them in every perf test.
- **Internal RAM is small:** about 320 KB, part of it already taken by bounce buffers, USB and
  FreeRTOS. A full 640×480 frame (300 KB) does not fit; a 320×240 frame (75 KB) would.

Techniques to evaluate (measure each, keep what wins, record the numbers in `docs/PERF.md`):

- **No full-screen redraws.** Use dirty-rectangle tracking and repaint only damaged regions.
  Draw the cursor as a small save-under sprite, so moving the mouse touches about 256 bytes
  instead of redrawing windows.
- **Tear-free updates** without doubling PSRAM traffic. For example, batch the dirty-rectangle
  flushes into the vertical blanking interval using the panel's VSYNC/bounce-buffer callbacks.
  Double buffering is an alternative only if the measurements show you can afford it.
- **Fast primitives in internal RAM:** fills, blits, glyph drawing and bevel drawing as
  `IRAM_ATTR` code. Write 32-bit or 128-bit words instead of bytes. Use the S3's PIE SIMD
  instructions (`EE.VLD.128`, `EE.VST.128` and friends, 16 bytes per op) in inline assembly or `.S`
  files for the hot loops, and compare each against the plain C version.
- **DMA copies:** use GDMA (`esp_async_memcpy`) for large copies PSRAM↔internal RAM while the CPU
  does other work.
- **Lower-level scan-out, if needed.** Consider programming the LCD_CAM peripheral and GDMA
  descriptors directly (bypassing `esp_lcd`) if that lets you do something better, for example a
  bounce-buffer fill that composes a cached desktop plus windows on the fly. Only do it if
  measured gains justify it, and keep a fallback to the working driver.
- **Core split:** pin video and compositing to one core and USB, SD and apps to the other, with
  lock-free queues between them.
- **Memory placement:** put hot data (glyph tables, dirty lists, the window list) in internal
  RAM, and bitmaps, file buffers and app heaps in PSRAM.
- **PSRAM settings:** test whether the octal PSRAM runs stably at 120 MHz on this board, and
  tune the data cache size and line size.
- **Build flags:** `-O2` or `-Os` per component (measure both), turn off asserts and logging in
  hot paths, and ship release builds with the log level lowered. The USB debug logging in
  `main/usb_input.c` is currently verbose; turn it down.
- **Benchmarks:** add a `perf` serial command and a built-in benchmark app (fill rate, blit rate,
  text rate, window-drag FPS, free RAM) so the numbers can be shown in the video.

**Targets:** dragging a window and moving the cursor should feel smooth (aim for 60 FPS on the
cursor and 30 FPS or more on window drags) with no tearing or scan-out glitches. Boot to the
desktop in under 3 seconds.

## Look and feel: 90s retro desktop (original design)

- **Style:** the classic mid-90s desktop. Flat light-grey panels with 3D bevels (white top-left
  edge, dark-grey bottom-right edge, 1-2 px), a solid-colour desktop, and windows with a
  dark-blue gradient-free title bar, white title text and close/minimise buttons.
- **Taskbar:** at the bottom, with a menu button on the left, a button per open window and a
  clock or uptime on the right.
- **Desktop:** desktop icons with labels, a menu that pops up from the taskbar button, and
  dialog boxes with OK/Cancel.
- **Palette:** the 64-colour RGB222 palette maps naturally onto this style. Grey (2,2,2), white
  (3,3,3), dark grey (1,1,1), black, navy (0,0,2) title bars and a teal (0,2,2) desktop.
  Define the palette once as named constants.
- **Bitmap fonts:** draw your own crisp fonts, e.g. an 8×16 for text and a small proportional
  UI font. Store them as packed bitmaps in flash or IRAM. Keep them pixel-perfect; no
  anti-aliasing is possible with 64 colours anyway.
- **Icons:** draw your own pixel-art icons at 16×16 and 32×32 (folder, file, text file, app,
  drive, game, settings). They can be stored as C arrays or loaded from the SD card.
- **UI toolkit:** write your own small toolkit (windows, buttons, menus, lists, scrollbars, text
  fields, message boxes) on top of the renderer. That is better here than LVGL: you control
  every byte and every redraw, and the bevel style is simple to draw directly. If you choose
  LVGL anyway, justify it with numbers.

## Full mouse AND keyboard-only control (required)

Everything in the OS must work with the mouse, and **everything must also work with the
keyboard alone, with no mouse plugged in**. After the demo the user will test the OS
keyboard-only. Build this from the start into the window manager and toolkit, not as an
afterthought. If something can only be done with the mouse, that is a bug.

- **Visible focus everywhere.** Exactly one window is active, and inside it exactly one control
  has focus. Show the focus with a clear dotted focus rectangle or a highlight, in the retro style.
  The focus must never get lost or be invisible, including after closing a window or dialog.
- **Global keys (work from anywhere):**

  | Key | Action |
  |---|---|
  | Ctrl+Esc (and the Windows/GUI key) | Opens the taskbar menu |
  | Alt+Tab / Alt+Shift+Tab | Cycle windows, including minimised ones; show a small switcher while Alt is held |
  | Alt+F4 | Closes the active window; on the desktop, opens a shut-down/restart dialog |
  | Alt+Space | Opens the window menu: Restore, Move, Size, Minimise, Maximise, Close. In Move/Size mode the arrow keys move or resize the window, Enter confirms, Esc cancels |
  | Ctrl+Alt+Del | Opens the task list, so a hung app can be closed |
  | A key to show the desktop, or a desktop focus mode | Selects the desktop icons |

- **Inside windows and dialogs:**

  | Key | Action |
  |---|---|
  | Tab / Shift+Tab | Move between controls in a sensible order |
  | Arrow keys | Move within lists, menus, grids and icon views |
  | Enter | Activates the default button or opens the selection |
  | Space | Presses the focused button or toggles a checkbox |
  | Esc | Cancels or closes the dialog |
  | Alt or F10 | Focuses the menu bar |
  | Alt + underlined letter | Menu and button mnemonics |
  | Home/End, PgUp/PgDn | Long lists and text |

- **The desktop and the taskbar** must be reachable by keyboard too: arrow keys between icons,
  Enter to open, and a way to focus the taskbar and pick a window from it.
- **File browser:**

  | Key | Action |
  |---|---|
  | Arrows | Move the selection |
  | Enter | Opens |
  | Backspace | Goes to the parent folder |
  | Delete | Deletes, with a confirmation dialog |
  | F2 | Renames |
  | Ctrl+C / Ctrl+X / Ctrl+V | Copy / cut / paste |
  | Ctrl+N | New folder or file |
  | Typing letters | Jumps to the next matching name |

- **Text editor:** the usual keys (arrows, Shift+arrows to select, Ctrl+A/C/X/V, Ctrl+S, Ctrl+O,
  Ctrl+N, Ctrl+F for find) and key repeat.
- **Apps and the game** get keyboard input through the app API, and the game must be playable
  with the keyboard. Apps built on the toolkit get keyboard navigation automatically.
- **Mouse still works fully** (click, double-click, drag, right-click menus where they make sense).
  Mixing both must not confuse the focus: clicking moves the keyboard focus to what was clicked.
- **Shortcut reference:** a Help window (F1) listing every shortcut.
- **Testing:**
  - **Scripted test:** add a keyboard-only test using the serial key injection, with the mouse
    disabled or unplugged. It walks through every checklist item below: open the file browser,
    make a folder, create, edit and save a text file, reopen it, launch the game, switch windows,
    move a window, close everything. Run it at each milestone and show the result on the JetKVM.
  - **Mouse-free boot:** the OS must boot and be fully usable with no mouse attached.

## OS features (the bar for "done")

From the original handoff's success checklist (these five come first):

1. Boots straight to a desktop with a mouse cursor.
2. Windows can be dragged, focused (click brings to front), minimised to the taskbar and closed.
3. A file browser that reads the SD card.
4. A text editor that can type and save a file.
5. Launches a separate app binary from the SD card, ideally a small game.
6. All of 1-5 can be done with the keyboard alone and with the mouse alone (see the section above).

Then, for "all the basic needs of an operating system":

- **File management:** list folders, navigate, open by file type, create a folder or file,
  rename, copy, move and delete (with confirmation), and show file sizes. Also show free and
  total space on the card.
- **Editor:** open, edit, save, save-as and new file, with a cursor, selection, scrolling and
  the usual keys (arrows, Home/End, PgUp/PgDn, Backspace/Delete, Ctrl+S). Handle files larger
  than the screen.
- **Viewers:** an image viewer (BMP, converted to the 64-colour palette with dithering) and a
  plain text viewer.
- **Apps:** apps are separate ELF files on the SD card, loaded with Espressif's `elf_loader`
  component. Define a small, stable app API (a function table or syscall table for windows,
  drawing, input events, files and timers), so an app needs only a header to build. Include a
  build script plus at least one sample app and one game.
- **System:** an about/system-info window (CPU, RAM, PSRAM, SD, uptime, FPS); a task list
  showing running apps and their memory, which can close them; and a settings panel (desktop
  colour, mouse speed, key repeat) saved to the SD card.
- **Terminal (optional):** a terminal window with a few commands (ls, cd, cat, rm, mkdir, mem).
- **Robustness:** a crashed or misbehaving app should not take the desktop down where that can
  be prevented: check the app API calls, and catch app faults and show an error dialog where
  possible. The OS must survive the SD card being removed and reinserted.

## Suggested order

1. Commit the current state. Then build the renderer core: primitives, fonts, dirty rectangles,
   a vblank-synced flush and the cursor sprite. Put a benchmark on screen, check for
   tearing and flicker on the JetKVM, and start `docs/PERF.md`.
2. Window manager and toolkit, with the retro theme, using serial-injected input. Build the
   focus system and keyboard navigation here, together with the mouse handling.
3. Real input: USB HID keyboard and mouse (absolute and relative), with key repeat and a
   US layout. Ask the human for the power and cabling setup at this point.
4. SD card. Propose the wiring and wait for approval, then FAT, the file browser and file
   operations.
5. Text editor, viewers, settings.
6. App API and ELF loading, a sample app, then a game.
7. Polish: boot screen, performance pass and the final `docs/PERF.md`. Write an
   `docs/OS-REPORT.md` summary of what was built, what was measured and the full intervention
   count.

At the start of each step, tell the human in one or two lines what you are about to do and
whether you will need them for anything physical.
