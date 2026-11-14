# Bevel OS performance log

All numbers are measured on the board (ESP32-S3 N16R8, 240 MHz, octal PSRAM at 80 MHz) with the
`perf` serial command (`tools/bv.py cmd "perf all" 60`) while the display is running at
640×480@60. "Slack" is the worst-case time left before the DMA needed a bounce buffer during
that test (a 10-line buffer period is 318 µs; below 0 would be a visible glitch). "Late" counts
such glitches.

## Step 1: renderer core (2026-11-12, `-O2`, scan-out ISR and GUI on core 1)

### Scan-out

| What | Result | Notes |
|---|---|---|
| Bounce-buffer fill, 6400 bytes PSRAM → internal, `memcpy` | 17.8 µs avg | data is already in the cache: each fill preloads the next 10 lines (`Cache_Start_DCache_Preload`) |
| Same with PIE 128-bit copy | 12.1 µs avg, **only when the driver's bounce buffers are 16-byte aligned** | The aligned PIE store needs a 16-byte aligned destination. `esp_lcd` allocates the bounce buffers with 4-byte alignment, so depending on the build they are aligned or not; when they are not, the fill falls back to `memcpy` (18.0 µs). The shipped build currently measures 18.0 µs. |
| CPU share of one core spent feeding the display | 5.6 % (3.8 % in builds where PIE applies) | 3 000 fills/s |
| Worst fill while the CPU hammers PSRAM | 131 µs | slack stays ≥ 186 µs, 0 late fills in every test |
| Mouse pointer | 0 framebuffer bytes per move | overlaid in the bounce buffer during the fill (scan-out sprite), always 60 FPS |

### Memory bandwidth

| Operation | libc | PIE (`EE.VLD/VST.128`) | GDMA | Byte loop |
|---|---|---|---|---|
| Fill, internal RAM | 690 MB/s | **3 424 MB/s** | – | 110 MB/s |
| Copy, internal → internal | 349 MB/s | **1 171 MB/s** | – | 55 MB/s |
| Fill, PSRAM | 35.3 MB/s | 35.2 MB/s | – | – |
| Copy, internal → PSRAM | 35.0 MB/s | 35.3 MB/s | 25.4 MB/s | – |
| Copy, PSRAM → internal | 63.0 MB/s | 64.9 MB/s | 25.5 MB/s | – |

Decisions:

- **Render in internal RAM, write PSRAM exactly once.** Internal RAM is 20-100× faster than
  PSRAM, so the compositor paints each dirty strip into a 20 KB internal scratch buffer and
  copies the finished strip to the framebuffer.
- **PIE for everything in internal RAM** (fills 5×, copies 3.4× over libc). It does nothing for
  PSRAM, which is limited by the bus at ~35 MB/s write / ~63 MB/s read.
- **GDMA copies rejected**: slower than the CPU copy (25 vs 35 MB/s) and strips are small.

### Drawing (into internal RAM)

| Primitive | Rate |
|---|---|
| UI font text | 427 000 glyphs/s |
| UI font, bold | 341 000 glyphs/s |
| 8×16 mono text | 1 147 000 glyphs/s |
| 100×20 filled rectangle | 52 800 /s |
| 75×22 bevelled button | 39 500 /s |
| 32×32 icon with transparency | 30 800 /s |

### Compositing and tear-free flush

| Test | Result | Notes |
|---|---|---|
| Full-screen redraw, beam-raced | 60.6 FPS | locked to the refresh; 9.5 ms of each frame is waiting for the beam |
| Full-screen redraw, no beam race | 69.9 FPS | tears |
| PSRAM copy per full frame, no race | 6.9 ms | 300 KB at ~43 MB/s |
| PSRAM copy per full frame, beam-raced | **0.55 ms** | see below |
| 320×240 redraw, beam-raced | 157 FPS | |

Beam racing turned out to be faster, not slower: the flush follows right behind the scan-out,
which has just pulled those framebuffer rows into the data cache. The writes hit the cache
instead of waiting for PSRAM, and the write-back happens in the background. So tear-free
updates cost less CPU time than tearing ones, with a single framebuffer.

### Memory

| | |
|---|---|
| Free internal RAM at the desktop | 258 KB (largest block 208 KB) |
| Free PSRAM | 7.6 MB |
| Boot to first frame | 207 ms after reset (log timestamp) |

## Final run (2026-11-12, complete OS, `-O2`, PSRAM 80 MHz, scan-out ISR and GUI both on core 1)

Raw output: `tools/bv.py cmd "perf all" 60`. Zero late scan-out fills in every test.

### Targets

| Target | Measured | |
|---|---|---|
| Mouse pointer at 60 FPS | 60 FPS always | the pointer is a scan-out sprite: it is drawn into the bounce buffer during the fill and moved from the USB task, so it stays smooth even while the GUI task is busy; 0 framebuffer bytes per move |
| Window drag ≥ 30 FPS, no tearing | **68 FPS** dragging a 488×357 window full of text (184 000 pixels repainted per step) | tear-free (beam-raced); 127 FPS with the beam race off |
| No scan-out glitches | 0 late fills, worst slack 186 µs of 318 µs | checked in every benchmark |
| Boot to desktop < 3 s | **0.7 s** from reset to the first desktop frame (0.9 s on the log clock with USB up) | PSRAM memory test skipped (saves ~1 s), drive mount 0.5 s |

### Whole-system numbers

| Test | Result |
|---|---|
| Full-screen redraw of the real desktop, tear-free | 76 FPS (render 1.1 ms + PSRAM copy 3.8 ms + beam wait) |
| Same, no beam race | 117 FPS |
| 320×240 redraw, tear-free | 297 FPS |
| 16×16 redraw (a button, a caret) | 99 900 updates/s |
| Window drag: render / PSRAM copy / wait per frame | 3.2 ms / 0.9 ms / 10.4 ms |
| UI text | 500 000 glyphs/s (bold 412 000, mono 8×16 378 000) |
| Free internal RAM at the desktop | 242 KB (largest block 196 KB) |
| Free PSRAM | 7.1 MB |
| Firmware size | 824 KB (`-O2`) |

### Experiments and what was kept

| Experiment | Result | Decision |
|---|---|---|
| Scan-out ISR on core 0, GUI on core 1 | drag 136 FPS, but worst scan-out slack fell from 186 µs to 55 µs (ISR max 262 µs) and the beam race stops working, because the two cores' cycle counters are not in step | **Rejected.** Same core: the ISR simply preempts the compositor, the two never fight over the PSRAM bus, and tear-free timing works. USB, drive, serial and loaded apps run on core 0. |
| `-Os` instead of `-O2` | firmware 779 KB instead of 824 KB (−5.5%); rendering 27% slower (drag render 4.1 ms vs 3.2 ms, UI text 379 000 vs 500 000 glyphs/s) | **`-O2` kept**; flash is not scarce (74% of the app partition is free). |
| PSRAM at 120 MHz (experimental in ESP-IDF) | write 56 MB/s (+59%), read 99 MB/s (+57%), drag 80 FPS, full redraw 85 FPS, slack 226 µs; ran stable on the bench | **Not enabled by default**: Espressif documents it as stable only at constant temperature, and the machine must survive being unplugged and replugged anywhere. To try it: `CONFIG_IDF_EXPERIMENTAL_FEATURES=y`, `CONFIG_SPIRAM_SPEED_120M=y`. |
| PIE (128-bit) kernels | internal fill 3.56 GB/s vs 0.70 (memset); internal copy 1.18 GB/s vs 0.35; scan-out fill 12.1 µs vs 18.0 when the bounce buffers are aligned (see step 1) | **Kept** for strips, fills, blits and the scan-out copy. No effect on PSRAM-bound copies. |
| GDMA (`esp_async_memcpy`) | 25 MB/s vs 36 MB/s for the CPU copy | **Rejected.** |
| Beam-raced flush vs immediate | tear-free costs waiting time, not work: the PSRAM copy is cheaper behind the beam (0.9 ms vs ~4 ms for a dragged window) because the scan-out has just loaded those rows into the cache | **Kept** (always on). |
| Dirty rectangles + strip rendering in internal RAM | a 16×16 change costs 10 µs; nothing is ever drawn directly into PSRAM | **Kept.** |
| Bypassing `esp_lcd` (raw LCD_CAM + GDMA) | not done: the driver's bounce-buffer callback already gives full control of the fill (own copy loop, sprite overlay, beam position) at 5.6% CPU. Owning the buffers would guarantee 16-byte alignment and save about 1.8% of one core; not worth replacing a proven driver | **Not needed.** |
| LVGL | not used: the whole toolkit, window manager and shell are about 3 000 lines and repaint only what changed | – |

### Robustness numbers

| Test | Result |
|---|---|
| `tools/kbtest.py` (keyboard only, no mouse events) | 34 of 34 steps pass |
| `tools/powercut.py` (reset at a random moment during a 64 KB file write) | 12 of 12: boots, drive mounts, files intact |
| App fault (write to address 4; division by zero) | error dialog, desktop keeps running |
| App hang (endless loop) | window marked "not responding" after 3 s, ended from the task list |

## Doom (2026-11-12)

| | |
|---|---|
| Frame rate in E1M1 | about 32 FPS (152 screen updates in 4.8 s; the engine's own limit is 35) |
| Per frame on the GUI core | 10 ms reading the 640×400 canvas from PSRAM and painting, 8 ms copying to the framebuffer |
| Scan-out while playing | worst slack 65-85 µs of 318 µs, worst fill 252 µs, 0 late fills |
| Memory while playing | PSRAM free 1.3 MB of 7.3 MB (4 MB engine heap, program image, canvas); internal RAM free 203 KB (32 KB task stack) |
| After closing | PSRAM free back to 6.9 MB |
| Program file / load time | 348 KB / about 0.4 s |
