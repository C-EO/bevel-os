#!/bin/zsh
# Build Doom (third_party/doomgeneric + apps/doom/doom_bevel.c) into disk/Apps/Doom.elf.
cd "$(dirname "$0")/.."
. ~/esp/esp-idf/export.sh >/dev/null 2>&1
CC=xtensa-esp32s3-elf-gcc
SRC=third_party/doomgeneric/doomgeneric
OBJ=build/doom
mkdir -p $OBJ disk/Apps
FILES=(dummy am_map doomdef doomstat dstrings d_event d_items d_iwad d_loop d_main d_mode d_net f_finale f_wipe g_game
 hu_lib hu_stuff info i_cdmus i_endoom i_joystick i_scale i_sound i_system i_timer memio m_argv m_bbox m_cheat m_config
 m_controls m_fixed m_menu m_misc m_random p_ceilng p_doors p_enemy p_floor p_inter p_lights p_map p_maputl p_mobj
 p_plats p_pspr p_saveg p_setup p_sight p_spec p_switch p_telept p_tick p_user r_bsp r_data r_draw r_main r_plane
 r_segs r_sky r_things sha1 sounds statdump st_lib st_stuff s_sound tables v_video wi_stuff w_checksum w_file w_main
 w_wad z_zone w_file_stdc i_input i_video doomgeneric)
CFLAGS=(-O2 -w -mlongcalls -fPIC -fdata-sections -ffunction-sections -fvisibility=hidden -fno-jump-tables
 -DCMAP256 -DDOOMGENERIC_RESX=320 -DDOOMGENERIC_RESY=200 -DNORMALUNIX -D_DEFAULT_SOURCE -I$SRC -Iapps)
objs=()
for f in $FILES; do
  o=$OBJ/$f.o
  if [ ! -f $o ] || [ $SRC/$f.c -nt $o ]; then $CC $CFLAGS -c $SRC/$f.c -o $o || exit 1; fi
  objs+=($o)
done
$CC $CFLAGS -Wall -c apps/doom/doom_bevel.c -o $OBJ/doom_bevel.o || exit 1
$CC $CFLAGS -c apps/crt.c -o $OBJ/crt.o || exit 1
$CC -shared -fPIC -nostartfiles -nostdlib -e bevel_entry -Wl,--gc-sections -Wl,--strip-all -Wl,--strip-debug \
    $OBJ/crt.o $OBJ/doom_bevel.o $objs -lgcc -o disk/Apps/Doom.elf || exit 1
xtensa-esp32s3-elf-strip --strip-unneeded --remove-section=.comment --remove-section=.xt.lit --remove-section=.xt.prop \
    --remove-section=.xtensa.info disk/Apps/Doom.elf
python3 tools/elf_fix.py disk/Apps/Doom.elf
printf "Doom.elf %d bytes\n" $(stat -f %z disk/Apps/Doom.elf)
