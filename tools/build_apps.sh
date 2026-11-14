#!/bin/zsh
# Build every apps/<Name>.c into disk/Apps/<Name>.elf (a position-independent ELF for the loader).
# An app needs nothing but apps/bevel.h.
cd "$(dirname "$0")/.."
. ~/esp/esp-idf/export.sh >/dev/null 2>&1
CC=xtensa-esp32s3-elf-gcc
mkdir -p disk/Apps
for src in apps/*.c; do
  name=$(basename $src .c)
  [ "$name" = "crt" ] && continue
  out=disk/Apps/$name.elf
  $CC -Os -Wall -mlongcalls -fPIC -shared -nostartfiles -nostdlib -e bevel_entry \
      -fdata-sections -ffunction-sections -Wl,--gc-sections -fvisibility=hidden \
      -Wl,--strip-all -Wl,--strip-debug -Iapps apps/crt.c $src -lgcc -o $out || exit 1
  xtensa-esp32s3-elf-strip --strip-unneeded --remove-section=.comment --remove-section=.dynamic \
      --remove-section=.xt.lit --remove-section=.xt.prop --remove-section=.xtensa.info $out
  printf "%-14s %6d bytes\n" $name.elf $(stat -f %z $out)
done
