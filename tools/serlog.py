"""Reset the board via RTS and print the serial log for N seconds."""
import sys, time, serial
port = sys.argv[1]; secs = float(sys.argv[2]) if len(sys.argv) > 2 else 5
s = serial.Serial(port, 115200, timeout=0.1)
s.dtr = False; s.rts = True; time.sleep(0.1); s.rts = False  # EN pulse
end = time.time() + secs
while time.time() < end:
    d = s.read(4096)
    if d: sys.stdout.write(d.decode(errors="replace")); sys.stdout.flush()
