// The drive: a wear-levelled FAT filesystem in the internal flash, mounted at /disk.
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include "esp_vfs_fat.h"
#include "wear_levelling.h"
#include "esp_log.h"
#include "esp_heap_caps.h"
#include "esp_app_desc.h"
#include "os.h"

static wl_handle_t s_wl = WL_INVALID_HANDLE;
static bool s_mounted;

static bool s_new_firmware;   // this firmware has not written its bundled files to the drive yet

static void restore_file(const char *path, const char *data, size_t len, bool if_differs)
{
    struct stat st;
    if (stat(path, &st) == 0 && (!if_differs || ((size_t)st.st_size == len && !s_new_firmware))) return;
    FILE *f = fopen(path, "wb");
    if (f) { fwrite(data, 1, len, f); fclose(f); }
}

bool storage_init(void)
{
    const esp_vfs_fat_mount_config_t cfg = {
        .max_files = 8,
        .format_if_mount_failed = true,
        .allocation_unit_size = 4096,
    };
    esp_err_t err = esp_vfs_fat_spiflash_mount_rw_wl(DISK_ROOT, "storage", &cfg, &s_wl);
    s_mounted = err == ESP_OK;
    if (!s_mounted) ESP_LOGE("disk", "mount failed: %s", esp_err_to_name(err));
    else {
        // A blank drive (first boot, or reformatted after a power cut damaged it) gets its
        // folders and the welcome file back, so the OS always comes up usable.
        extern const char welcome_start[] asm("_binary_Welcome_txt_start");
        extern const char welcome_end[] asm("_binary_Welcome_txt_end");
        struct stat st;
        // Each firmware build stamps the drive; a different stamp means the bundled programs
        // on the drive may be older than the ones in this firmware.
        char stamp[65] = "", have[65] = "";
        esp_app_get_elf_sha256(stamp, sizeof(stamp));
        FILE *sf = fopen(DISK_ROOT "/System/firmware.id", "rb");
        if (sf) { size_t k = fread(have, 1, 64, sf); have[k] = 0; fclose(sf); }
        s_new_firmware = strcmp(stamp, have) != 0;
        // "blank" = the sample files of this firmware were never installed on this drive
        bool blank = stat(DISK_ROOT "/System/samples-1", &st) != 0;
        mkdir(DISK_ROOT "/Documents", 0777);
        if (blank) {
            restore_file(DISK_ROOT "/Documents/Welcome.txt", welcome_start, welcome_end - welcome_start, false);
        }
        mkdir(DISK_ROOT "/Pictures", 0777);
        mkdir(DISK_ROOT "/Apps", 0777);
        mkdir(DISK_ROOT "/System", 0777);
        // The bundled programs are kept in the firmware too and put back if missing or outdated.
        #define BUNDLED(sym, file) do { \
            extern const char sym##_start[] asm("_binary_" #sym "_elf_start"); \
            extern const char sym##_end[] asm("_binary_" #sym "_elf_end"); \
            restore_file(DISK_ROOT "/Apps/" file, sym##_start, sym##_end - sym##_start, true); } while (0)
        BUNDLED(Snake, "Snake.elf");
        BUNDLED(Hello, "Hello.elf");
        BUNDLED(CrashTest, "CrashTest.elf");
        BUNDLED(Doom, "Doom.elf");
        extern const char pic_start[] asm("_binary_Bevel_bmp_start");
        extern const char pic_end[] asm("_binary_Bevel_bmp_end");
        if (s_new_firmware) {
            sf = fopen(DISK_ROOT "/System/firmware.id", "wb");
            if (sf) { fwrite(stamp, 1, strlen(stamp), sf); fclose(sf); }
        }
        if (blank) {
            restore_file(DISK_ROOT "/Pictures/Bevel.bmp", pic_start, pic_end - pic_start, false);
            FILE *m = fopen(DISK_ROOT "/System/samples-1", "wb");
            if (m) fclose(m);
        }
    }
    return s_mounted;
}

bool storage_ok(void) { return s_mounted; }

bool storage_df(uint64_t *total, uint64_t *free_bytes)
{
    if (!s_mounted) return false;
    return esp_vfs_fat_info(DISK_ROOT, total, free_bytes) == ESP_OK;
}

void os_shutdown_prepare(void)
{
    extern bool settings_save(void);
    settings_save();
}

void storage_unmount(void)
{
    if (!s_mounted) return;
    esp_vfs_fat_spiflash_unmount_rw_wl(DISK_ROOT, s_wl);
    s_mounted = false;
}

void os_fmt_size(char *buf, int n, uint64_t bytes)
{
    if (bytes < 1024) snprintf(buf, n, "%u bytes", (unsigned)bytes);
    else if (bytes < 1024 * 1024) snprintf(buf, n, "%u.%u KB", (unsigned)(bytes / 1024), (unsigned)(bytes % 1024 * 10 / 1024));
    else snprintf(buf, n, "%u.%u MB", (unsigned)(bytes >> 20), (unsigned)((bytes & 0xFFFFF) * 10 >> 20));
}

void os_sd_summary(char *buf, int n)
{
    uint64_t t, f;
    if (!storage_df(&t, &f)) { snprintf(buf, n, "not mounted"); return; }
    char a[20], b[20];
    os_fmt_size(a, sizeof(a), f);
    os_fmt_size(b, sizeof(b), t);
    snprintf(buf, n, "%s free of %s (flash)", a, b);
}

void *os_grow(void *old, size_t old_bytes, size_t new_bytes)
{
    void *n = heap_caps_malloc(new_bytes, MALLOC_CAP_SPIRAM);
    if (!n) return NULL;
    if (old) {
        // copy in slices so this task can be preempted and the bus is shared fairly
        for (size_t off = 0; off < old_bytes; off += 16384) {
            size_t k = old_bytes - off < 16384 ? old_bytes - off : 16384;
            memcpy((char *)n + off, (char *)old + off, k);
        }
        free(old);
    }
    return n;
}
