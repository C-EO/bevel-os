"""Send command characters to the board without resetting it. Usage: send.py PORT CHARS"""
import sys, time, serial
s = serial.Serial()
s.port = sys.argv[1]; s.baudrate = 115200; s.timeout = 0.3
s.dtr = False; s.rts = False  # set before open so the board is not reset
s.open()
s.write(sys.argv[2].encode()); time.sleep(0.5)
print(s.read(2000).decode(errors="replace"))
