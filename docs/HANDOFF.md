# ESP32-S3 VGA OS — Project Handoff

## Goal

Build a small graphical "operating system" for an ESP32-S3 that outputs VGA video, takes keyboard and mouse input, and can load apps from an SD card. This is for a video testing whether an AI model can build an OS for a microcontroller, so keep a log of every manual intervention the human makes (wiring changes, pressing reset, etc.) so it can be reported honestly at the end.

The human has finished the hardware wiring. Your job starts with software. The human is your hands for anything physical; ask them to plug, unplug, reset or check things when needed.

## Success checklist (the bar for "it's an OS")

1. Boots to a desktop with a mouse cursor
2. Windows that can be dragged
3. File browser reading from an SD card
4. Text editor that can type and save a file
5. Launches a separate app binary from the SD card (ideally a small game)

## Hardware

- **MCU:** ESP32-S3 dev board. Flash/PSRAM size not yet confirmed. Check with `esptool.py flash_id` and the boot log. If it's an N16R8 (octal PSRAM), GPIO 33–37 are used internally for PSRAM.
- **Video path:** ESP32-S3 GPIOs → resistor DAC on perfboard → cut VGA cable → active VGA-to-HDMI converter → HDMI → JetKVM (browser view) or a USB3 HDMI capture card (shows up as a webcam on the computer).
- **Power / flashing:** ESP32 is connected to the computer through its **UART/COM USB port**. The native USB port (GPIO 19/20) is reserved for USB host input later.

## Pin map (already wired, do not change without asking)

| ESP32 GPIO | Signal | Resistor | VGA pin |
|---|---|---|---|
| 4 | Red, bright bit (MSB) | 2× 220 Ω in series (440 Ω) | 1 |
| 5 | Red, dim bit (LSB) | 1 kΩ | 1 |
| 6 | Green, bright bit | 440 Ω | 2 |
| 7 | Green, dim bit | 1 kΩ | 2 |
| 15 | Blue, bright bit | 440 Ω | 3 |
| 16 | Blue, dim bit | 1 kΩ | 3 |
| 17 | H-sync | none (direct) | 13 |
| 18 | V-sync | none (direct) | 14 |
| GND | Ground | — | 5, 10, cable braid |

Each color uses two GPIOs joined after their resistors, forming a 2-bit DAC into the monitor's 75 Ω load. Approximate output levels: 0 V, 0.2 V, 0.45 V, 0.65 V. Total: 6 color bits = 64 colors (RGB222).

**Reserved / avoid:** GPIO 19, 20 (native USB, needed for input later), 0, 3, 45, 46 (strapping), 43, 44 (UART0 console), 26–37 (flash/PSRAM on most modules).

## Video target

- Mode: **640×480 @ 60 Hz**, the most standard VGA mode; cheap converters lock onto it reliably.
- Standard timing: pixel clock 25.175 MHz.
  - Horizontal: 640 visible, 16 front porch, 96 sync, 48 back porch (800 total)
  - Vertical: 480 visible, 10 front porch, 2 sync, 33 back porch (525 total)
  - Both sync pulses are **negative** (active low).
- The S3 probably can't hit 25.175 MHz exactly. Something near 25 MHz with adjusted porches should still be accepted by the converter; verify with the capture card.

## Suggested implementation approach

- Use ESP-IDF with the **RGB LCD peripheral** (`esp_lcd_new_rgb_panel`) to generate pixels plus H-sync/V-sync in hardware. Verify the current ESP-IDF API details (data width, whether unused data/PCLK/DE pins can be set to -1, sync polarity flags, bounce buffers) against the docs for the installed IDF version rather than from memory.
- Suggested 8-bit data bus mapping, so one byte = one pixel:
  - D0 = GPIO 5 (R lo), D1 = GPIO 4 (R hi)
  - D2 = GPIO 7 (G lo), D3 = GPIO 6 (G hi)
  - D4 = GPIO 16 (B lo), D5 = GPIO 15 (B hi)
  - D6, D7 = unused
  - Pixel byte = `(B << 4) | (G << 2) | R`, each 0–3
- Framebuffer: 640×480×1 byte = 300 KB, which must live in **PSRAM**. Use the RGB driver's bounce-buffer mode so the panel streams from internal RAM; PSRAM bandwidth is the main limit. If 640×480 is unstable, try 8-bit color at a lower pixel clock, or render 320×240 and double pixels.
- Prior art worth checking: bitluni's ESP32-S3 VGA work, and FabGL (original ESP32 only, but useful for ideas).

## Milestones

1. **Color bars.** Output a 640×480 test pattern showing all 4 brightness levels of each channel plus a white border. Confirms timing, sync polarity, and that each color bit is wired right. If the converter shows "no signal," check sync timing/polarity first.
2. **Framebuffer + text.** Draw text and shapes from software; check for flicker or tearing.
3. **GUI.** Add LVGL with a mouse cursor and draggable windows.
4. **Input.** USB host HID on the native USB port. The JetKVM will appear as a USB keyboard + mouse (its mouse likely reports **absolute** coordinates, so parse the HID report descriptor rather than assuming boot protocol). Before this works physically: the ESP32 must supply 5 V VBUS on its USB port (devkit OTG jumper or powered OTG adapter), and the JetKVM needs its own power. Ask the human to set this up when you get here.
5. **Storage.** SD card with FAT.
6. **Apps.** Load separate app binaries from SD using Espressif's ELF loader component.
7. **Desktop apps.** File browser, text editor, a small game.

## Seeing the screen

The model can't see the display directly. Options, best first:
- **HDMI capture card:** appears as a webcam on the computer; grab a frame with ffmpeg and inspect it.
- **JetKVM:** shows the screen in a browser tab.
- **Debug fallback:** have the firmware dump the framebuffer over serial as an image.

## Working notes

- Flash and read logs via the UART/COM port.
- Ask the human before any change that involves rewiring.
- Keep a running log of manual interventions for the video.
