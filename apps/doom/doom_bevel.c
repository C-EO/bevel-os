// Doom on Bevel OS: the platform layer for doomgeneric (https://github.com/ozkl/doomgeneric, GPL-2).
// The engine renders 320x200 in 256 colours. We show it at 640x400 in the 64-colour RGB222
// palette, using the four screen pixels of every game pixel for a 2x2 ordered dither, which
// gives five shades between each pair of real colour levels at no loss of resolution.
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "../bevel.h"
#include "doomgeneric.h"
#include "doomkeys.h"

struct color { uint32_t b:8; uint32_t g:8; uint32_t r:8; uint32_t a:8; };
extern struct color colors[256];
extern int palette_changed;   // boolean in the engine

static const bevel_api_t *os;
static uint8_t *s_canvas;
static int s_cw, s_ch;
static uint16_t s_lut_top[256], s_lut_bot[256];   // two dithered screen pixels per game pixel, per row

#define KQ 64
static struct { uint8_t pressed, key; } s_keys[KQ];
static int s_kr, s_kw;

void bevel_exit(void);

static uint8_t quant(int r, int g, int b, int pos)
{
    static const int off[4] = {-32, 11, 32, -11};   // 2x2 Bayer thresholds, in units of 1/255
    int c[3] = {r, g, b};
    uint8_t p = 0;
    for (int k = 0; k < 3; k++) {
        int v = c[k] + off[pos];
        int q = (v + 42) / 85;
        if (v < 0) q = 0;
        if (q > 3) q = 3;
        p |= q << (k * 2);
    }
    return p;
}

static void build_lut(void)
{
    for (int i = 0; i < 256; i++) {
        int r = colors[i].r, g = colors[i].g, b = colors[i].b;
        s_lut_top[i] = quant(r, g, b, 0) | quant(r, g, b, 1) << 8;
        s_lut_bot[i] = quant(r, g, b, 2) | quant(r, g, b, 3) << 8;
    }
}

void DG_Init(void)
{
    if (os->win_open("Doom", 640, 400) != 0) bevel_exit();
    s_canvas = os->canvas(&s_cw, &s_ch);
    if (!s_canvas || s_cw < 640 || s_ch < 400) bevel_exit();
}

void DG_DrawFrame(void)
{
    if (palette_changed) { build_lut(); palette_changed = 0; }
    const uint8_t *src = (const uint8_t *)DG_ScreenBuffer;
    uint16_t top[320], bot[320];
    for (int y = 0; y < 200; y++, src += 320) {
        for (int x = 0; x < 320; x++) { uint8_t i = src[x]; top[x] = s_lut_top[i]; bot[x] = s_lut_bot[i]; }
        memcpy(s_canvas + (y * 2) * s_cw, top, 640);
        memcpy(s_canvas + (y * 2 + 1) * s_cw, bot, 640);
    }
    os->flush();
}

void DG_SleepMs(uint32_t ms) { os->sleep_ms(ms); }
uint32_t DG_GetTicksMs(void) { return os->ticks_ms(); }
void DG_SetWindowTitle(const char *title) { (void)title; }

static uint8_t map_key(const bv_event_t *e)
{
    switch (e->key) {
    case 0x4F: return KEY_RIGHTARROW;
    case 0x50: return KEY_LEFTARROW;
    case 0x52: return KEY_UPARROW;
    case 0x51: return KEY_DOWNARROW;
    case 0xE0: case 0xE4: return KEY_FIRE;      // Ctrl
    case 0x2C: return KEY_USE;                  // Space
    case 0xE1: case 0xE5: return KEY_RSHIFT;    // Shift = run
    case 0x28: case 0x58: return KEY_ENTER;
    case 0x29: return KEY_ESCAPE;
    case 0x2B: return KEY_TAB;                  // map
    case 0x2A: return KEY_BACKSPACE;
    case 0x36: return KEY_STRAFE_L;             // ,
    case 0x37: return KEY_STRAFE_R;             // .
    case 0x2E: return KEY_EQUALS;
    case 0x2D: return KEY_MINUS;
    case 0x3B: return KEY_F2; case 0x3C: return KEY_F3; case 0x3E: return KEY_F5; case 0x3F: return KEY_F6;
    case 0x40: return KEY_F7; case 0x41: return KEY_F8; case 0x42: return KEY_F9; case 0x44: return KEY_F11;
    }
    if (e->key >= 0x04 && e->key <= 0x1D) return 'a' + (e->key - 0x04);
    if (e->key >= 0x1E && e->key <= 0x26) return '1' + (e->key - 0x1E);
    if (e->key == 0x27) return '0';
    return 0;
}

static void pump(void)
{
    bv_event_t e;
    while (os->event(&e, 0)) {
        if (e.type == BV_CLOSE) bevel_exit();
        if (e.type != BV_KEY_DOWN && e.type != BV_KEY_UP) continue;
        if (e.repeat) continue;
        uint8_t k = map_key(&e);
        if (!k) continue;
        int next = (s_kw + 1) % KQ;
        if (next == s_kr) continue;
        s_keys[s_kw].pressed = e.type == BV_KEY_DOWN;
        s_keys[s_kw].key = k;
        s_kw = next;
    }
}

int DG_GetKey(int *pressed, unsigned char *key)
{
    pump();
    if (s_kr == s_kw) return 0;
    *pressed = s_keys[s_kr].pressed;
    *key = s_keys[s_kr].key;
    s_kr = (s_kr + 1) % KQ;
    return 1;
}

void bevel_exit(void) { exit(0); }

int app_main(const bevel_api_t *api, const char *arg)
{
    os = api;
    static char *argv[] = {"doom", "-iwad", "/disk/Apps/doom1.wad", "-mb", "4", NULL};
    FILE *f = fopen(argv[2], "rb");
    if (!f) {
        os->msgbox("Doom", "The game data file doom1.wad is missing from the Apps folder.", BV_MB_OK);
        return 1;
    }
    fclose(f);
    doomgeneric_Create(5, argv);
    for (;;) doomgeneric_Tick();
}
