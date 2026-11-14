"""Ask the board for its framebuffer over serial ('D') and save it as PNG.
Usage: fbdump.py PORT OUT.png"""
import sys, re, time, subprocess, serial
port, out = sys.argv[1], sys.argv[2]
s = serial.Serial(port, 115200, timeout=0.5)
s.dtr = False; s.rts = False
time.sleep(2.5); s.reset_input_buffer(); s.write(b"D")
buf = b""; t0 = time.time()
while b"@@FB" not in buf or b"\n" not in buf[buf.index(b"@@FB"):]:
    buf += s.read(256)
    if time.time() - t0 > 10: sys.exit("no header")
i = buf.index(b"@@FB"); j = buf.index(b"\n", i)
w, h, n = map(int, buf[i+4:j].split())
data = buf[j+1:]
while len(data) < n:
    data += s.read(n - len(data))
    if time.time() - t0 > 120: sys.exit("timeout")
data = data[:n]
pix = bytearray()
for k in range(0, n, 2):
    pix += bytes([data[k+1]]) * data[k]
assert len(pix) == w*h, len(pix)
lv = [0, 85, 170, 255]
rgb = bytearray()
for p in pix:
    rgb += bytes((lv[p & 3], lv[(p >> 2) & 3], lv[(p >> 4) & 3]))
ppm = out.rsplit(".", 1)[0] + ".ppm"
with open(ppm, "wb") as f:
    f.write(b"P6 %d %d 255\n" % (w, h)); f.write(rgb)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", ppm, out], check=True)
print("saved", out, w, h, "rle bytes", n)
