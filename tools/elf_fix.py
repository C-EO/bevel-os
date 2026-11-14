#!/usr/bin/env python3
"""Drop R_XTENSA_NONE relocations from a shared ELF. The linker leaves one behind (from libgcc's
unwind data) with no target address, and the ELF loader's validator rejects any relocation that
does not point into a loaded section. Usage: elf_fix.py file.elf"""
import struct, sys
path = sys.argv[1]
d = bytearray(open(path, "rb").read())
shoff, = struct.unpack_from("<I", d, 32)
shentsize, shnum = struct.unpack_from("<HH", d, 46)
removed = 0
for i in range(shnum):
    base = shoff + i * shentsize
    name, typ, flags, addr, off, size, link, info, align, entsize = struct.unpack_from("<10I", d, base)
    if typ != 4: continue   # SHT_RELA
    ents = [bytes(d[off + k:off + k + 12]) for k in range(0, size, 12)]
    keep = [e for e in ents if (struct.unpack("<III", e)[1] & 0xff) != 0]
    if len(keep) == len(ents): continue
    removed += len(ents) - len(keep)
    d[off:off + size] = b"".join(keep) + b"\0" * (12 * (len(ents) - len(keep)))
    struct.pack_into("<I", d, base + 20, len(keep) * 12)
open(path, "wb").write(d)
print("%s: removed %d empty relocation(s)" % (path, removed))
