// Wi-Fi and HTTP(S) fetching.
#pragma once
#include <stdint.h>
#include <stdbool.h>

enum { NET_OFF = 0, NET_IDLE, NET_CONNECTING, NET_CONNECTED, NET_FAILED };
typedef struct { int state; char ssid[33]; char ip[16]; int rssi; } net_status_t;
typedef struct { char ssid[33]; int8_t rssi; bool secure; } net_ap_t;

void net_boot(void);                                   // connects in the background if a network is saved
bool net_start(void);                                  // bring the radio up (idempotent)
void net_status(net_status_t *out);
int  net_scan(net_ap_t *out, int max);                 // blocks about 2 s; call from a worker task
void net_connect(const char *ssid, const char *password, bool save);
void net_disconnect(bool forget);

// GET a URL into a PSRAM buffer (NUL-terminated; caller frees). Follows redirects. Returns the HTTP
// status, or a negative value: -1 no network, -2 connection failed, -3 too large, -4 cancelled, -5 no memory.
int net_fetch(const char *url, char **body, int *len, char *ctype, int ctype_n, char *final_url, int final_n,
              int max_bytes, volatile bool *cancel, volatile int *progress);
const char *net_error_text(int code);
