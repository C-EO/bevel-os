#!/usr/bin/env python3
"""Power-cut test: reset the board (EN pulse, same effect on the flash drive as pulling the plug)
at random moments while a file is being written, then check that the OS boots and the drive
and its files are intact. Usage: powercut.py [rounds]"""
import sys, time, random, os, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bv
rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
ok = 0
for i in range(rounds):
    delay = random.uniform(0.0, 0.35)
    t = threading.Thread(target=lambda: bv.request("write /disk/Documents/cut.txt round%d-" % i, 3))
    t.start()
    time.sleep(delay)
    bv.request("~reset", 0.2)
    t.join()
    time.sleep(3.0)
    alive = b"pong" in bv.request("ping", 3)
    docs = bv.request("exists /disk/Documents", 3).decode(errors="replace")
    welcome = bv.request("exists /disk/Documents/Welcome.txt", 3).decode(errors="replace")
    snake = bv.request("exists /disk/Apps/Snake.elf", 3).decode(errors="replace")
    good = alive and "dir" in docs and "file" in welcome and "file" in snake
    ok += good
    print("round %2d: cut after %3d ms -> boots %s, drive %s, files %s" % (i + 1, delay * 1000, alive, "dir" in docs, "file" in welcome and "file" in snake), flush=True)
bv.request("rm /disk/Documents/cut.txt", 3)
print("%d of %d power cuts survived" % (ok, rounds))
sys.exit(0 if ok == rounds else 1)
