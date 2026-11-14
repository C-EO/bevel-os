#!/usr/bin/env python3
"""Keyboard-only acceptance test for Bevel OS.

Drives the OS purely with injected key presses (no mouse events at all) through the serial
command channel and checks the outcome of every step: windows, focus and file contents.
Needs the serial daemon (tools/bv.py daemon). Usage: kbtest.py [--shots DIR]
"""
import sys, time, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bv

SHOTS = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else None
results = []

def cmd(line, t=15):
    out = bv.request(line, t).decode(errors="replace")
    return "\n".join(l for l in out.splitlines() if not l.startswith("@@OK") and not l.startswith("I ("))

def key(*keys):
    for k in keys: cmd("key " + k)

def typ(text): cmd("type " + text)

def state():
    out = cmd("wins")
    active = re.search(r"active: (.*?) \| shell focus: (\d) \| menu: (\d)", out)
    wins = re.findall(r'win "(.*?)" (-?\d+),(-?\d+) (\d+)x(\d+) flags ([0-9a-f]+) focus (\S+) "(.*?)"', out)
    return {"active": active.group(1) if active else "?", "shell": active and active.group(2) == "1",
            "menu": active and active.group(3) == "1", "wins": wins}

def win(title_part):
    for w in state()["wins"]:
        if title_part in w[0]: return w
    return None

def exists(path): return cmd("exists /disk" + path).strip().splitlines()[-1]

def cat(path):
    out = bv.request("cat /disk" + path, 10).decode(errors="replace")
    m = re.search(r"@@FILE (\d+)\n", out)
    if not m: return None
    return out[m.end():m.end() + int(m.group(1))]

def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else "   <- " + str(detail)), flush=True)
    if SHOTS:
        n = len(results)
        bv.dump(os.path.join(SHOTS, "kb%02d.png" % n))

def wait(cond, timeout=4.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cond(): return True
        time.sleep(0.15)
    return False

# ---- start from a clean boot
bv.request("reboot", 2)
time.sleep(3.0)
assert "pong" in cmd("ping"), "board does not answer"
cmd("rm /disk/KbTest")
cmd("rm /disk/System/snake.dat")
time.sleep(0.3)

s = state()
check("boots to the desktop with keyboard focus on the icons, no mouse needed", s["shell"] and not s["wins"], s)

key("ctrl+esc")
check("Ctrl+Esc opens the Bevel menu", state()["menu"])
key("esc")
s = state()
check("Esc closes it, focus stays on the taskbar", not s["menu"] and s["shell"], s)
key("tab")   # taskbar -> desktop icons
key("home", "enter")
check("Enter on the first desktop icon opens Files", wait(lambda: state()["active"].startswith("Files")), state())

key("ctrl+shift+n"); typ("KbTest"); key("enter")
check("Ctrl+Shift+N makes a folder", exists("/KbTest") == "dir", exists("/KbTest"))
key("enter")
check("Enter goes into the folder", state()["active"] == "Files - KbTest", state()["active"])

key("ctrl+n"); typ("note.txt"); key("enter")
check("Ctrl+N creates a text file", exists("/KbTest/note.txt") == "file")
key("enter")
check("Enter opens it in the editor", wait(lambda: state()["active"] == "note.txt - Editor"), state()["active"])

typ("First line typed with the keyboard.\\nSecond line."); key("ctrl+s")
time.sleep(0.3)
check("typing and Ctrl+S save the file", cat("/KbTest/note.txt") == "First line typed with the keyboard.\nSecond line.", repr(cat("/KbTest/note.txt")))
key("alt+f4")
check("Alt+F4 closes the editor, focus returns to Files", wait(lambda: state()["active"] == "Files - KbTest"), state()["active"])

key("f5", "enter")
check("the saved file opens again", wait(lambda: state()["active"] == "note.txt - Editor"))
key("ctrl+end"); typ("! Edited again."); key("shift+home", "ctrl+c", "end", "enter", "ctrl+v", "ctrl+s")
time.sleep(0.3)
want = "First line typed with the keyboard.\nSecond line.! Edited again.\nSecond line.! Edited again."
check("select, copy, paste and save in the editor", cat("/KbTest/note.txt") == want, repr(cat("/KbTest/note.txt")))
key("alt+f"); 
check("Alt+F opens the File menu", state()["menu"])
key("x")
check("the Exit menu item closes the editor", wait(lambda: state()["active"] == "Files - KbTest"), state()["active"])

key("f2"); typ("renamed.txt"); key("enter")
check("F2 renames", exists("/KbTest/renamed.txt") == "file" and exists("/KbTest/note.txt") == "none")
key("ctrl+c", "ctrl+v")
check("Ctrl+C / Ctrl+V copies a file", exists("/KbTest/Copy of renamed.txt") == "file")
key("del")
check("Delete asks first", state()["active"] == "Delete", state()["active"])
key("enter")
gone = [exists("/KbTest/renamed.txt"), exists("/KbTest/Copy of renamed.txt")]
check("...and deletes after Yes", gone.count("none") == 1, gone)
key("bksp")
check("Backspace goes to the parent folder", state()["active"] == "Files - Drive", state()["active"])

key("ctrl+esc", "p", "s", "enter")
check("the game starts from the menu (a separate program on the drive)", wait(lambda: state()["active"] == "Snake"), state()["active"])
key("down", "right", "up")
time.sleep(1.0)
check("the game keeps running while it is steered", win("Snake") is not None and state()["active"] == "Snake")

cmd("keydown alt"); cmd("key tab"); cmd("keyup alt")
check("Alt+Tab switches to the other window", state()["active"] == "Files - Drive", state()["active"])
cmd("keydown alt"); cmd("key tab"); cmd("keyup alt")
check("Alt+Tab switches back", state()["active"] == "Snake", state()["active"])

before = win("Snake")
key("alt+space", "m", "right", "right", "down", "enter")
after = win("Snake")
check("Alt+Space, Move, arrows, Enter moves the window", int(after[1]) == int(before[1]) + 16 and int(after[2]) == int(before[2]) + 8, (before, after))

cmd("keydown alt"); cmd("key tab"); cmd("keyup alt")
key("alt+space", "n")
s = state()
check("Alt+Space, Minimise hides the window", s["active"] == "Snake" and int(win("Files")[5], 16) & 0x10, s)
cmd("keydown alt"); cmd("key tab"); cmd("keyup alt")
check("Alt+Tab restores a minimised window", state()["active"] == "Files - Drive" and not int(win("Files")[5], 16) & 0x10, state())
key("alt+space", "x")
check("Alt+Space, Maximise", int(win("Files")[5], 16) & 0x20)
key("alt+space", "r")
check("Alt+Space, Restore", not int(win("Files")[5], 16) & 0x20)

key("f1")
check("F1 opens Help", state()["active"].startswith("Help"), state()["active"])
key("ctrl+alt+del")
check("Ctrl+Alt+Del opens the task list", state()["active"] == "Tasks", state()["active"])

for _ in range(6):
    if not state()["wins"]: break
    key("alt+f4"); time.sleep(0.4)
s = state()
check("Alt+F4 closes every window, focus lands on the desktop", not s["wins"] and s["shell"], s)
key("alt+f4")
check("Alt+F4 on the desktop offers to shut down", state()["active"].startswith("Shut Down"), state()["active"])
key("esc")
check("Esc cancels it", not state()["wins"])
check("clean up", cmd("rm /disk/KbTest").strip().endswith("deleted"))

bad = [n for n, ok in results if not ok]
print("\n%d of %d steps passed" % (len(results) - len(bad), len(results)))
sys.exit(1 if bad else 0)
