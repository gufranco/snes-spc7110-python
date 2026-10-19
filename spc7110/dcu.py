from collections.abc import Callable, Sequence

from .decompressor import Decompressor

ENTRY_BYTES = 4

ADDRESS_MASK = 0xFFFFFF

STREAM_MASK = 0x7FFFFF

INVALID_MODE = 3

READY = 0x80

SEEK_ENABLE = 0x02

STRIDE_ENABLE = 0x01

ROWS = 8

PLANE_PAIR_BYTES = 16

TILE_BYTES = 32

REGISTERS = (0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x09, 0x0A, 0x0B, 0x0C)

MASKS = {0x03: 0x7F, 0x0B: 0x03}


def entry(read: Callable[[int], int], table: int, index: int) -> tuple[int, int]:
    at = (table + index * ENTRY_BYTES) & ADDRESS_MASK
    mode = read(at) & 3
    address = read((at + 1) & ADDRESS_MASK) << 16
    address |= read((at + 2) & ADDRESS_MASK) << 8
    address |= read((at + 3) & ADDRESS_MASK)
    return mode, address & STREAM_MASK


class DecompressionUnit:
    __slots__ = (
        "address",
        "current",
        "decompressor",
        "mode",
        "offset",
        "pending",
        "read_data",
        "registers",
        "tile",
    )

    def __init__(self, read_data: Callable[[int], int], held: Sequence[int]) -> None:
        self.read_data = read_data
        self.registers = dict(zip(REGISTERS, held[: len(REGISTERS)], strict=True))
        rest = held[len(REGISTERS) :]
        self.pending = bool(rest[0] & 1)
        self.mode = rest[1] & 3
        self.address = (rest[2] << 16 | rest[3] << 8 | rest[4]) & STREAM_MASK
        self.offset = rest[5] & (TILE_BYTES - 1)
        self.tile = bytearray(rest[6 : 6 + TILE_BYTES])
        self.decompressor = Decompressor(fetch=read_data).start(
            rest[6 + TILE_BYTES] % 3, held[-1], 0
        )
        self.current = self.decompressor.row()

    def power(self) -> None:
        self.registers = dict.fromkeys(REGISTERS, 0x00)
        self.pending = False
        self.mode = 0
        self.address = 0

    def read(self, register: int) -> int | None:
        if register == 0x00:
            return self.take()
        if register == 0x08:
            return 0x00
        return self.registers.get(register)

    def write(self, register: int, value: int) -> None:
        if register not in self.registers or register == 0x0C:
            return
        self.registers[register] = value & MASKS.get(register, 0xFF)
        if register == 0x04:
            self.load_address()
        if register == 0x06:
            self.registers[0x0C] &= ~READY & 0xFF
            self.pending = True

    def load_address(self) -> None:
        table = self.registers[0x01] | self.registers[0x02] << 8 | self.registers[0x03] << 16
        self.mode, self.address = entry(self.read_data, table, self.registers[0x04])

    def begin(self) -> None:
        if self.mode == INVALID_MODE:
            return
        self.decompressor = Decompressor(fetch=self.read_data).start(self.mode, self.address, 0)
        self.current = self.decompressor.row()
        seek = 0
        if self.registers[0x0B] & SEEK_ENABLE:
            seek = self.registers[0x05] | self.registers[0x06] << 8
        self.advance(seek)
        self.registers[0x0C] |= READY
        self.offset = 0

    def advance(self, rows: int) -> None:
        for _ in range(rows):
            self.current = self.decompressor.row()

    def take(self) -> int:
        counter = (self.registers[0x09] | self.registers[0x0A] << 8) - 1
        self.registers[0x09] = counter & 0xFF
        self.registers[0x0A] = (counter >> 8) & 0xFF
        if not self.registers[0x0C] & READY:
            return 0x00
        if self.offset == 0:
            self.fill()
        value = self.tile[self.offset]
        depth = 1 << (self.decompressor.mode or 0)
        self.offset = (self.offset + 1) & (ROWS * depth - 1)
        return value

    def fill(self) -> None:
        stride = self.registers[0x07] if self.registers[0x0B] & STRIDE_ENABLE else 1
        for row in range(ROWS):
            self.place(row, self.current)
            self.advance(stride)

    def place(self, row: int, current: bytes) -> None:
        if len(current) == 1:
            self.tile[row] = current[0]
            return
        self.tile[row * 2 : row * 2 + 2] = current[:2]
        if len(current) == 4:
            at = row * 2 + PLANE_PAIR_BYTES
            self.tile[at : at + 2] = current[2:]
