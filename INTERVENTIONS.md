# Manual interventions log

Every physical or manual action the human takes, for honest reporting in the video.
Times are local (2026-11-10).

| # | When | What the human did | Why |
|---|------|--------------------|-----|
| 0 | before start | Wired the resistor DAC, VGA cable, converter (done before handoff) | Hardware prep, per handoff |
| 1 | session start | Plugged the ESP32-S3 UART/COM USB port into the computer | No serial port was detected; needed for flashing |
| 2 | session start | Plugged in the HDMI capture card (not yet detected by macOS) | To let the AI see the VGA output |
| 3 | after flashing | Connected the JetKVM: HDMI from the converter, USB-C for power, network; gave its IP | Capture card not detected; JetKVM used to view the screen |
| 4 | after flashing | Allowed Chrome in macOS Local Network privacy settings so the JetKVM page opens | Chrome was blocked from reaching the JetKVM on the LAN |
| 5 | after flashing | Connected 5 V USB power to the VGA→HDMI converter | Converter showed no HDMI signal; it needs external power since the ESP32 does not supply VGA pin 9 +5 V |
| 6 | debugging no-signal | Moved the converter HDMI output from the JetKVM to an external monitor, and reports what the monitor shows | JetKVM showed no signal; isolating converter vs JetKVM |
| 7 | debugging no-signal | Checked continuity with a multimeter: GPIO17→VGA13, GPIO18→VGA14, GND→VGA5/10 all good | Monitor showed no signal from converter |
| 8 | debugging no-signal | Added a wire from devkit 5V to VGA pin 9 (approved wiring change), reconnected converter HDMI to the JetKVM | Converter likely needs +5 V on pin 9 to detect a source |
| 9 | debugging no-signal | Identified the converter as HDMI→VGA (female VGA, male HDMI): the wrong direction. Disconnected it | Explains "no signal" on both JetKVM and monitor |
| 10 | debugging no-signal | Plugged the ESP32's VGA cable directly into a monitor with VGA input; reports what it shows | No working VGA→HDMI converter yet, so the human is the only one who can see the screen |
| 11 | debugging no-signal | Watched the monitor during an automatic cycle of 7 sync variants; reported that variant 6 (800x600@60, positive sync) shows a picture | Find a mode the monitor accepts |
| 12 | colour test | Sent a photo of the monitor showing the 800x600 test pattern; confirmed the converter is HDMI→VGA (wrong direction) | Visual check of colours; converter diagnosis |
| 13 | colour test | Watched a second mode cycle on the monitor: integer-clock 640x480 (26.67 MHz, 24 MHz, +/- sync) and 800x600 work; fractional 25.175 MHz fails | Identify why 640x480 did not display |
| 14 | before input milestone | Wired a USB-C female breakout to GPIO19 (D−), GPIO20 (D+), GND and 5V, for the JetKVM keyboard/mouse (documented in docs/HANDOFF-AMENDMENT-USB.md) | Board native USB connector does not fit next to the UART cable |
| 15 | input milestone | Moved the JetKVM USB-C cable from its charger to the USB-C breakout. Afterwards the ESP32 vanished from the Mac USB bus and the JetKVM stopped answering on the network | Start USB host test |
| 16 | input milestone | Plugged a USB keyboard into the USB-C breakout (USB-C to Mac gave no result: breakout has no CC resistors) | Test the GPIO19/20 soldering in USB host mode |
| 17 | input milestone | Swapped in a USB mouse for the keyboard; briefly moved the UART cable to the native USB port, then back | Debugging: no USB device detected on the breakout |
| 18 | input milestone | Sent photos of the board; measured 0.7 V on the 5Vin pin with the board running from the UART cable | Diagnosing why the USB mouse/keyboard got no power |
| 19 | input milestone | Wired the second Robojax USB-C breakout as a power input (V → 5Vin node, G → GND) and plugged in a USB-A charger (approved wiring change) | Board 5Vin pin is input-only, so the device breakout had no 5 V |
| 20 | input milestone | Typed "hello" on the USB keyboard connected to the breakout | Verify keyboard reports reach the ESP32 |
| 21 | enclosure | 3D-printed the rear panel and a VGA hole fit-test strip, reported fits (VGA hole too loose; picked the 0.2 mm clearance hole) | Box for the hardware, side task |
| 22 | enclosure | Printed the one-piece box, fitted the ESP32 and the USB-C breakouts, sent photos; asked for hold-downs that stop the boards sliding when plugging in | Box for the hardware, side task |
| 23 | enclosure | VGA plug did not fit the printed hole; fitted a female-female gender changer in the hole instead, sent a video + ruler photos of it | Box for the hardware, side task |
| 24 | display | Wired the JetKVM to the boxed ESP32 (VGA out → VGA-to-HDMI adapter → JetKVM HDMI in); asked for a check of the screen. JetKVM page showed "No HDMI signal detected", USB "Disconnected"; ESP32 not visible on the Mac serial | View the OS screen remotely |
| 25 | display | Connected the ESP32 to the Mac for diagnosis; Mac saw no device at first; moved the cable to the COM port after asking which port to use. Board then booted fine, video sync measured OK in modes 1-4, JetKVM still "No HDMI signal" in all of them | Diagnose the JetKVM "no signal" |
| 26 | display | Plugged in the VGA-to-HDMI adapter's USB power cable | Adapter gives no HDMI output without its own 5 V (VGA pin 9 has none). JetKVM then showed the test pattern |
| 27 | before the OS session (2026-11-12) | Connected the JetKVM's USB to the box's "USB" port with its own power arrangement; at the first boot of this session the JetKVM enumerated as a USB keyboard + mouse (details of the cabling to be confirmed by the human) | JetKVM keyboard/mouse input for the OS |
| 28 | SD card step | Decided not to use an SD card for the project (answered the wiring proposal with "skip that part"); no wiring done | Storage moved to a FAT drive in the internal flash instead |
| 29 | Doom request | Approved downloading the open-source Doom engine (doomgeneric) and the shareware DOOM1.WAD | Needed before fetching third-party code and game data |
| 30 | power-cycle test | Unplugged the board and plugged it back in; reported that the OS loads but the JetKVM keyboard/mouse no longer control it | Requested check that the OS survives losing power |
| 31 | USB splitter test | Disconnected the JetKVM, connected the VGA output to a monitor, plugged a keyboard and a mouse into the USB port through a splitter; reported that it does not work | Try keyboard + mouse as two devices |
| 32 | USB splitter test | Confirmed the 5 V charger is plugged in; turned the USB-C plug over at the box's USB port. Still no device seen | Diagnosing why no USB device is detected after the power-cycle test |
| 33 | USB splitter test | Tested a mouse alone (works), a keyboard alone (works), and both through the splitter from the JetKVM box (neither works) | Narrowing down the USB problem |
| 34 | USB hub test | Plugged a USB dongle (hub) into the box's USB port with the keyboard and mouse on it | Second attempt at two USB devices at once |
| 35 | USB hub test | Turned the dongle's plug over and plugged it in again; still no device seen | Checking whether plug orientation was the reason the dongle is not detected |
| 36 | browser test | Joined the Wi-Fi network in the Network panel (typed the password on the board's keyboard) and tried a Google search in the browser | Needed before the browser can load real pages |
| 37 | USB hub test | Plugged in a second, different dongle | It is detected electrically but does not answer the first USB request; not working yet |
| 38 | USB hub test | Sent a photo of the second dongle (a QGeeM USB-C multiport adapter with HDMI and card reader) and asked for a driver | Identify the device; a driver cannot help because it fails before identifying itself |

