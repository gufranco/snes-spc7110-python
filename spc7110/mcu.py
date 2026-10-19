from collections.abc import Sequence

PROGRAM_BYTES = 0x100000

BANK_BYTES = 0x100000

ADDRESS_MASK = 0xFFFFFF

TOP_BIT = 1 << 23

LARGEST_DATA_SIZE = 3

HIGH_HALF = 0x400000

PROGRAM_LOW = 0x100000

PROGRAM_HIGH = 0x200000

SECOND_PROGRAM_BANK = 0x04

RAM_ENABLE = 0x80

BANK_REGISTERS = (0x31, 0x32, 0x33)

REGISTER_MASKS = {0x30: 0x87, 0x31: 0x07, 0x32: 0x07, 0x33: 0x07, 0x34: 0x07}


def mirror(address: int, size: int) -> int:
    base, mask = 0, TOP_BIT
    while address >= size:
        while not address & mask:
            mask >>= 1
        address -= mask
        if size > mask:
            size -= mask
            base += mask
        mask >>= 1
    return base + address


class Mapper:
    __slots__ = ("data", "program", "ram", "registers")

    def __init__(
        self, program: bytes, data: bytes, ram: bytearray | None, registers: Sequence[int]
    ) -> None:
        self.program = program
        self.data = data
        self.ram = ram
        self.registers = {
            register: value & REGISTER_MASKS[register]
            for register, value in zip(sorted(REGISTER_MASKS), registers, strict=True)
        }

    def read_register(self, register: int) -> int:
        return self.registers[register]

    def write_register(self, register: int, value: int) -> None:
        self.registers[register] = value & REGISTER_MASKS[register]

    def data_read(self, address: int) -> int:
        address &= ADDRESS_MASK
        size = self.registers[0x34] & 3
        offset = address & ((BANK_BYTES << size) - 1)
        if size != LARGEST_DATA_SIZE and address & HIGH_HALF:
            return 0x00
        return self.data[mirror(offset, len(self.data))]

    def rom_read(self, reduced: int) -> int:
        within = reduced & (BANK_BYTES - 1)
        if reduced < PROGRAM_LOW:
            return self.program[mirror(within, len(self.program))]
        if reduced < PROGRAM_HIGH and self.registers[0x34] & SECOND_PROGRAM_BANK:
            return self.program[mirror(PROGRAM_LOW + within, len(self.program))]
        window = BANK_REGISTERS[reduced // BANK_BYTES - 1]
        return self.data_read(within | BANK_BYTES * (self.registers[window] & 7))

    def ram_read(self, reduced: int) -> int:
        held = self.ram
        if held is None or not self.registers[0x30] & RAM_ENABLE:
            return 0x00
        return held[mirror(reduced, len(held))]

    def ram_write(self, reduced: int, value: int) -> None:
        held = self.ram
        if held is not None and self.registers[0x30] & RAM_ENABLE:
            held[mirror(reduced, len(held))] = value & 0xFF
