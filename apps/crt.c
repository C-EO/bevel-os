// Entry shim: the loader calls the ELF entry as entry(argc, argv); we pass the OS table in argv.
#include "bevel.h"
int bevel_entry(int magic, char **argv)
{
    if (magic != 0x42564C31) return -1;
    return app_main((const bevel_api_t *)argv[0], argv[1]);
}
