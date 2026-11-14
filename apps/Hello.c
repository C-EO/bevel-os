// Hello: the smallest useful Bevel OS app. A bouncing gem, a counter and key echo.
#include "bevel.h"

#define W 260
#define H 150

static void itoa10(int v, char *out)
{
    char tmp[12];
    int n = 0;
    if (v == 0) tmp[n++] = '0';
    while (v > 0) { tmp[n++] = '0' + v % 10; v /= 10; }
    while (n) *out++ = tmp[--n];
    *out = 0;
}

int app_main(const bevel_api_t *os, const char *arg)
{
    if (os->win_open("Hello", W, H) != 0) return 1;
    int x = 40, y = 30, dx = 2, dy = 1, frames = 0;
    char last[2] = "-";
    for (;;) {
        bv_event_t e;
        while (os->event(&e, 16)) {            // also our frame timer: about 60 per second
            if (e.type == BV_CLOSE) return 0;
            if (e.type == BV_KEY_DOWN) {
                if (e.key == BV_K_ESC) return 0;
                if (e.ch > ' ') last[0] = e.ch;
            }
            if (e.type == BV_MOUSE_DOWN) { x = e.x - 8; y = e.y - 8; }
        }
        x += dx; y += dy;
        if (x < 0 || x > W - 16) { dx = -dx; x += dx; }
        if (y < 20 || y > H - 16) { dy = -dy; y += dy; }
        os->clear(BV_RGB(0, 0, 1));
        os->fill(0, 0, W, 18, BV_RGB(2, 2, 2));
        os->text(6, 3, "Hello from a program loaded from the drive!", BV_FONT_UI, BV_RGB(0, 0, 0));
        // a little gem
        for (int i = 0; i < 8; i++) {
            os->fill(x + 8 - i - 1, y + i, 2 * i + 2, 1, BV_RGB(3, 3 - i / 3, 0));
            os->fill(x + 8 - i - 1, y + 15 - i, 2 * i + 2, 1, BV_RGB(2, 1, 0));
        }
        char num[40] = "Frame ";
        itoa10(++frames, num + 6);
        os->text(6, H - 30, num, BV_FONT_MONO, BV_RGB(3, 3, 3));
        os->text(150, H - 30, "Last key:", BV_FONT_MONO, BV_RGB(2, 2, 2));
        os->text(230, H - 30, last, BV_FONT_MONO, BV_RGB(3, 3, 0));
        os->text(6, H - 14, "Click to move the gem. Esc closes.", BV_FONT_UI, BV_RGB(2, 2, 2));
        os->flush();
    }
}
