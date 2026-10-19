from .dcu import ENTRY_BYTES
from .decompressor import MODES
from .mcu import PROGRAM_BYTES


def data_rom(image: bytes | bytearray) -> bytes:
    return bytes(image[PROGRAM_BYTES:]) if len(image) > PROGRAM_BYTES else b""


def directory(drom: bytes | bytearray, base: int) -> tuple[list[tuple[int, int]], int]:
    found: list[tuple[int, int]] = []
    at, last = base, -1
    while at + ENTRY_BYTES <= len(drom):
        mode = drom[at]
        address = drom[at + 1] << 16 | drom[at + 2] << 8 | drom[at + 3]
        if mode not in MODES or address >= len(drom) or address < last:
            break
        found.append((mode, address))
        last = address
        at += ENTRY_BYTES
    return found, at
