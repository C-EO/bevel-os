"""Open the port (resets the board), then step through test modes, holding each one.
Usage: cycle_modes.py PORT HOLD_SECONDS MODES"""
import sys, time, re, serial
port, hold, modes = sys.argv[1], float(sys.argv[2]), sys.argv[3]
s = serial.Serial(port, 115200, timeout=0.2)
buf = b""; t0 = time.time()
while b"test pattern drawn" not in buf and time.time() - t0 < 10:
    buf += s.read(4096)
for m in modes:
    s.write(m.encode()); time.sleep(1.5)
    out = re.sub(rb"\x1b\[[0-9;]*m", b"", s.read(4096)).decode(errors="replace")
    lines = [l for l in out.splitlines() if "vga:" in l or "diag:" in l]
    print(time.strftime("%H:%M:%S"), f"bars={int(m)+1}", *lines, sep="\n  ", flush=True)
    time.sleep(max(0, hold - 1.5))
print("done", flush=True)
