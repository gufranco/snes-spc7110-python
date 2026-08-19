#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>

typedef uint8_t uint8;
typedef uint16_t uint16;
typedef uint32_t uint32;
typedef int8_t int8;
typedef int16_t int16;
typedef int32_t int32;

#define SPC7110_DECOMP_BUFFER_SIZE 64

static std::vector<uint8> cartridge_rom;

#define memory_cartrom_size()   ((unsigned)cartridge_rom.size())
#define memory_cartrom_read(a)  (cartridge_rom[(a)])

#include "spc7110dec.h"
#include "spc7110_bodies.inc"

static const unsigned WINDOW_BASE = 0x100000;

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: driver <mode> <offset> <index>\n");
        return 2;
    }

    unsigned mode = (unsigned)strtoul(argv[1], NULL, 0);
    unsigned offset = (unsigned)strtoul(argv[2], NULL, 0);
    unsigned index = (unsigned)strtoul(argv[3], NULL, 0);

    unsigned wanted = 0;
    if (fread(&wanted, sizeof(wanted), 1, stdin) != 1) return 1;

    std::vector<uint8> window;
    int byte;
    while ((byte = fgetc(stdin)) != EOF) window.push_back((uint8)byte);
    if (window.empty()) return 1;

    cartridge_rom.assign(WINDOW_BASE, 0x00);
    cartridge_rom.insert(cartridge_rom.end(), window.begin(), window.end());

    SPC7110Decomp chip;
    chip.init(mode, offset, index);

    for (unsigned at = 0; at < wanted; at++) {
        printf("%02X\n", chip.read());
    }
    return 0;
}
