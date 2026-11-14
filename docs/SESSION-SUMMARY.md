# Session summary: an AI builds a desktop OS for an ESP32-S3

This is a factual account of one working session (2026-11-12) in which an AI coding agent
(Claude, running in Claude Code) built a graphical operating system for a microcontroller. It is
written as source material for a video script. Everything stated as measured was measured on the
real board; things that failed, or that the agent got wrong, are included on purpose.

Related files: `docs/OS-REPORT.md` (what the OS contains), `docs/PERF.md` (every benchmark),
`INTERVENTIONS.md` (every manual action by the human, rows 0-38), `docs/OS-BUILD-PROMPT.md` (the
brief the agent was given).

## 1. The premise

- **The question:** can an AI model build an operating system for a microcontroller, with the
  human acting only as its hands for physical things?
- **The hardware:** an ESP32-S3 board (two cores at 240 MHz, 16 MB flash, 8 MB PSRAM, about
  320 KB of fast internal RAM) in a 3D-printed box. Video is VGA at 640×480, 60 Hz, in 64 colours,
  produced by six resistors on six GPIO pins. Input is USB through the chip's single USB port.
- **Where the session started:** the hardware bring-up was already done in an earlier session
  (colour bars on screen, a USB keyboard logging raw reports). There was no OS: no windows, no
  mouse pointer, no files, no apps.
- **How the agent sees and touches the machine:** it cannot see the monitor. It built a serial
  command channel (2 Mbaud) that dumps the framebuffer as a pixel-exact PNG in 0.4 s and injects
  key presses and mouse clicks. It also viewed the real screen through a JetKVM (a network KVM)
  in a browser, and used the JetKVM's USB keyboard and mouse as real input devices.
- **The rules it was given:** log every human action, ask before any rewiring, verify on the
  real screen, back every performance decision with a measured number, and draw its own fonts
  and icons (inspired by the mid-90s look, but no Microsoft names, logos or copied artwork).

## 2. What exists at the end

The OS is called **Bevel OS**. In one session it went from a test pattern to:

- A desktop with icons, a taskbar with a menu button and a button per window, and a mouse
  pointer. Boots to the desktop in **0.7 seconds**.
- Overlapping windows that drag, resize, minimise, maximise and close; menus; dialogs; Alt+Tab.
- Its own toolkit: buttons, check boxes, radio buttons, text fields, sliders, lists, scrollbars.
- **Everything works from the keyboard alone** and from the mouse alone.
- Apps: Files, Text Editor, Picture Viewer, Terminal, Settings, System Information, Task list,
  Help, Benchmark, a Wi-Fi Network panel and a **Web Browser**.
- Programs loaded from the drive as separate binaries: **Snake**, a sample app, a deliberately
  crashing test app, and **Doom**.
- About 11 000 lines of C and a little assembly, written in the session. Firmware size 1.9 MB.

## 3. The story, in order

### Act 1: the renderer (the part nobody sees)

- The agent read the hand-off notes, committed the earlier work, and started a second AI agent in
  the background to draw the fonts, 33 icons and 7 mouse cursors as ASCII art while it wrote code.
- **Key design decision 1: the mouse pointer is never drawn into the framebuffer.** The display
  driver asks for 10 lines of pixels at a time; the agent's code fills them and paints the pointer
  on top at that moment, like a hardware sprite. Moving the mouse costs zero memory writes and is
  always 60 FPS, even when the rest of the system is busy.
- **Key design decision 2: "chase the beam".** Screen memory lives in slow external RAM (PSRAM,
  about 35 MB/s). The OS paints each changed area in a small buffer in fast internal RAM
  (20-100× faster), then copies it to the screen memory just *behind* the line the monitor is
  currently reading. That removes tearing without a second framebuffer.
- **A surprise the measurements produced:** the tear-free method turned out *cheaper* than the
  tearing one. The display had just pulled those lines into the CPU cache, so writing right
  behind it hits the cache instead of waiting for the slow RAM (0.55 ms instead of 6.9 ms for a
  full screen in the first test).
- First numbers: SIMD instructions fill internal RAM at 3.4 GB/s versus 0.69 GB/s for the
  standard library; DMA copies were slower than the CPU and were rejected.
- A small fix along the way: the picture was pushed against the left edge of the capture, so the
  agent re-centred it by changing the timing (no rewiring).

### Act 2: a desktop appears

- Window manager, menus, dialogs, taskbar, Alt+Tab and keyboard move/size compiled and ran on the
  first full build. The agent tested it by "typing" through the serial channel and looking at
  framebuffer dumps.
- Good screenshot moments: the first desktop, the menu opened by keyboard, the Alt+Tab switcher.

### Act 3: real input

- At first boot of this session the JetKVM's USB showed up unexpectedly as a keyboard, an
  absolute-position mouse and a relative mouse. The agent wrote a parser for USB HID report
  descriptors so all three kinds work.
- The pointer was off to one side at first. The agent worked out that the capture device sees
  the picture narrower than standard, corrected the mapping, and then double-clicked an icon and
  dragged a window through the browser with the real mouse.

### Act 4: the human changes the plan (no SD card)

- The agent proposed SD card wiring and asked for approval, as required. The human answered:
  no SD card for this project.
- The agent switched to a 12 MB drive inside the board's own flash chip. Everything the SD card
  was meant for (files, settings, loadable programs) works on it.
- Built on top of it: Files (create, rename, copy, move, delete with confirmation), the Text
  Editor, the Picture Viewer with dithering to 64 colours, Settings and a Terminal.

### Act 5: apps, a game, and a crash test

- Programs are separate ELF files on the drive, loaded with Espressif's `elf_loader` and run in
  their own task. An app needs one header file with 24 functions.
- **Snake** is 4.8 KB.
- **CrashTest** breaks on purpose. Writing to an invalid address or dividing by zero gives an
  error dialog and the desktop keeps running. An endless loop gets the window marked "not
  responding" and can be ended from the task list (Ctrl+Alt+Del).
- Two requests from the human arrived mid-work: a fun retro game (Snake was already planned) and
  "I can't reach the reset button, so it must survive being unplugged". The agent made saves
  go through a temporary file, made the drive restore its bundled programs after a reformat, and
  made the shut-down screen restart on any key.

### Act 6: proving it

- **Keyboard-only test:** a script drives the OS with key presses only and checks 34 steps (make
  a folder, create, edit, save and reopen a file, rename, copy, delete, start Snake, switch,
  move, minimise, maximise and close windows). Result: **34 of 34**. The first run showed 33;
  the one failure was the test harness dropping a leading space, not the OS.
- **Power-cut test:** the board was reset at random moments while writing a file. **12 of 12**
  times it booted with the drive and files intact.
- **Performance targets:**

  | Target | Result |
  |---|---|
  | Boot to desktop in under 3 s | 0.7 s |
  | Mouse pointer at 60 FPS | 60 FPS, always |
  | Window drag at 30 FPS or more, no tearing | 68 FPS with full window contents |
  | No display glitches | 0 late fills in every benchmark |

- **Experiments that were measured and rejected:** compiling for size (5.5% smaller, 27% slower);
  running the display interrupt on the other core (faster, but the display's safety margin fell
  from 186 µs to 55 µs and tear-free timing broke); PSRAM at 120 MHz (58% faster and stable on
  the bench, but officially experimental, so left off).
- **The agent corrected itself:** it first logged the display fill as 12.1 µs, then noticed a
  later boot measured 18.0 µs. The fast path only works when a buffer happens to be aligned. It
  fixed the documentation rather than leaving the better number in.

### Act 7: Doom

- The human asked for "a community version of Doom". The agent asked permission before
  downloading anything, then fetched the open-source engine (doomgeneric, GPL-2) and the original
  shareware data file (checksum verified).
- Doom was built as a 348 KB loadable program, not baked into the OS. Obstacles on the way:
  - The program loader rejected the file because of one empty relocation entry. The agent
    instrumented the loader to find the failing check, then wrote a small tool to strip it.
  - The agent's own "self-healing drive" check then kept the old file, because it compared only
    sizes. It replaced the check with a firmware build stamp.
  - The 4.2 MB data file was sent to the drive over the serial cable in 114 seconds.
- Result: Doom runs in a window at about **32 FPS**, keyboard controlled. It renders 320×200 in
  256 colours; the agent's layer shows it at 640×400 and uses the four screen pixels of each game
  pixel as a dither pattern to fake more than 64 colours. Closing it returns all 5.5 MB of memory.
  There is no sound (the board has no audio output).

### Act 8: the USB saga (the part that did not work)

This is the honest low point and probably good material.

- **The unplug test:** the human pulled the power and plugged it back in. The OS came back, but
  the JetKVM keyboard and mouse were dead. The log showed the JetKVM connecting, dropping off
  60 ms later, and the board never retrying. The agent added a watchdog that revives the USB port.
- **Wrong guesses by the agent, in order:**
  1. "There is no 5 V on the port." The human: "But I have the 5 volt plugged in."
  2. "The USB-C plug is upside down." The human flipped it. No change.
  3. "A wire may have come loose in the box."
- **What it actually was:** the human tested a mouse alone (works), a keyboard alone (works), and
  both through the "splitter" from the JetKVM box (neither works). That splitter is a power/data
  Y-cable, not a USB hub, so two devices on it collide. The port and the firmware were fine.
- **Two dongles, two different failures:**
  - Dongle 1: never detected at all, either way up. Likely needs a full USB-C port; the box's
    socket has only four wires.
  - Dongle 2 (a QGeeM USB-C multiport adapter with HDMI and card reader): detected electrically,
    but fails at the very first USB request every time. The human asked for a driver; the agent
    explained that a driver cannot help because the failure happens before the device has even
    identified itself.
- **Questions the human asked along the way, and the answers:** the AUX port cannot take a second
  device (it is the same two wires as the USB port); the COM port cannot either (it is a serial
  adapter, not a USB host).
- **Where it stands:** single devices and combined keyboard-and-mouse receivers work. Hub support
  is switched on but has never been seen working, because no plain USB hub was available.

### Act 9: "it has Wi-Fi, can we add a browser?"

- The agent set expectations first: a 1990s-style text browser is realistic; modern JavaScript
  sites are not.
- It built a Wi-Fi manager, a Network panel (scan, pick, type the password as asterisks) and the
  browser: HTTP and HTTPS, headings, lists, links, preformatted text, simple search boxes,
  history, bookmarks, keyboard link navigation.
- The human joined their Wi-Fi by typing the password on the board itself, then tried Google. It
  came back as an error page. That is Google's behaviour: it now requires JavaScript. Typing
  search words into the address bar uses FrogFind instead, which works.
- Pages confirmed working on the board: FrogFind search results, NPR's text edition, Wikipedia
  articles (over HTTPS).
- **A bug the agent caught by its own instrumentation:** loading a Wikipedia article caused 29
  late display fills, the first glitches of the whole project. The cause was growing large memory
  buffers with `realloc`, which copies with interrupts switched off. After replacing it, the same
  page and a larger one load with 0 late fills.

## 4. Numbers worth quoting

| | |
|---|---|
| Boot to desktop | 0.7 s |
| Window drag, tear-free | 68 FPS |
| Full-screen redraw, tear-free | 76 FPS |
| Mouse pointer | 60 FPS, zero framebuffer writes |
| Doom | about 32 FPS |
| Internal RAM fill with SIMD | 3.5 GB/s (5× the standard library) |
| PSRAM write speed (the bottleneck) | 35 MB/s |
| Keyboard-only test | 34 of 34 |
| Power-cut test | 12 of 12 |
| Code written | about 11 000 lines |
| Firmware size | 1.9 MB |
| Snake | 4.8 KB |
| Git commits in the session | 12 |

## 5. How much the human had to do

`INTERVENTIONS.md` has rows 0-38. Rows 0-26 are the hardware bring-up from before this session.
This session added rows 27-38:

- **Decisions and approvals (3):** no SD card; approving the Doom downloads; typing the Wi-Fi
  password and trying the browser.
- **Requested check (1):** the unplug/replug power test.
- **USB experiments the human chose to try (7):** the splitter, single devices, two dongles, two
  plug flips, a photo of the dongle.
- **Found already done (1):** the JetKVM USB cabling was in place when the session started; what
  exactly was done there was never confirmed.

During the main build (renderer through Snake, tests and benchmarks) the human pressed no reset
button, did no rewiring and plugged nothing in. The physical work in this session was all in the
USB experiments.

## 6. What does not work or was not verified

- **Two USB devices at once** through any adapter tried so far.
- **JetKVM control after a power cycle:** broke in the unplug test; a watchdog was added but the
  JetKVM was never reconnected to confirm the fix.
- **A real cold power cut** was tested once by the human (the OS came back); the 12-of-12 figure
  is from resets, not from pulling the plug.
- **Doom's data file** cannot repair itself if the drive is reformatted (too big to keep a copy
  in the firmware). Saved games were not tested.
- **The browser** shows text only: no images, no JavaScript, no style sheets, no form POSTs.
  Wikipedia pages begin with a lot of menu clutter. example.com fails from this network.
- **The Wi-Fi password** is stored on the drive in plain text.
- **Doom and the browser together** were not tested; with Wi-Fi on, free internal RAM drops from
  about 240 KB to about 125 KB.
- **Tearing** was verified by counters, not by eye (the JetKVM stream is recompressed video).
- **Loadable apps** cannot create their own buttons or lists, and an app that crashes inside an
  OS call still restarts the whole system.
- **The SD card** from the original brief was dropped by the human's decision.

## 7. Moments that may work well on camera

- The first desktop appearing from a framebuffer dump, minutes after the renderer benchmarks.
- The agent double-clicking a desktop icon through the JetKVM with the real mouse.
- The keyboard-only test scrolling 34 PASS lines.
- CrashTest: a program crashes, a polite dialog appears, the desktop carries on.
- "But I have the 5 volt plugged in" and the eventual answer that the splitter is not a hub.
- Doom running in a window on a chip that costs a few dollars, next to a 4.8 KB Snake.
- The Google search that fails, followed by a search that works.
- The agent finding and fixing display glitches that no human had noticed, from its own counters.
