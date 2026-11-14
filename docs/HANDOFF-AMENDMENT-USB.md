# Amendment: USB input wiring

This updates the original ESP32-S3 VGA OS handoff (docs/HANDOFF.md).

## What changed

The board's own native USB connector is **not used**, because its plug doesn't fit next to the UART cable. Instead, a **USB-C female breakout board** is wired directly to the ESP32's native USB pins. The JetKVM's USB cable plugs into this breakout, and the ESP32 acts as a USB host that sees the JetKVM as a keyboard + mouse.

The UART/COM port is still used for flashing, logs and power.

## Wiring (done, not yet tested)

| USB-C breakout pad | ESP32 pin |
|---|---|
| D− | GPIO 19 (USB D−) |
| D+ | GPIO 20 (USB D+) |
| G | GND |
| V | 5V pin (VBUS, fed from the computer via the UART cable) |

VBUS is supplied from the 5V pin, so no devkit OTG jumper or powered OTG adapter is needed. Nothing should be plugged into the board's own native USB connector, since it shares GPIO 19/20 with the breakout.

## Risks to check at the input milestone

- **USB-C CC roles:** simple 4-pad breakouts usually present as a *device* (Rd pull-downs), not a host. With a USB-C to USB-C cable, the JetKVM may not detect a host. If enumeration fails, the fallback is a USB-A female breakout plus a USB-C to USB-A cable, which has no CC negotiation. Ask the human to swap if needed.
- **Power budget:** the JetKVM may draw power from the V pad, and everything comes from one computer USB port. If the ESP32 browns out or the JetKVM reboots, the JetKVM needs its own power supply.
- Debug enumeration with ESP-IDF USB host logs over the UART console.
