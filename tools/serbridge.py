"""Hold the serial port open (opening it resets the board), log everything to a file,
and forward bytes written to a FIFO to the board. Usage: serbridge.py PORT FIFO LOG"""
import os, sys, threading, serial
port, fifo, log = sys.argv[1:4]
if not os.path.exists(fifo): os.mkfifo(fifo)
s = serial.Serial(port, 115200, timeout=0.1)
def reader():
    with open(log, "ab", buffering=0) as f:
        while True:
            d = s.read(4096)
            if d: f.write(d)
threading.Thread(target=reader, daemon=True).start()
while True:
    with open(fifo, "rb") as f:
        for chunk in iter(lambda: f.read(64), b""):
            s.write(chunk)
