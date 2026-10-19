from collections.abc import Callable, Sequence

REGISTERS = (0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18)

MASKS = {0x13: 0x7F, 0x18: 0x7F}

WORD_MASK = 0xFFFFFFFF

ADDRESS_MASK = 0xFFFFFF

STRIDE_SELECT = 0x01

ADJUST_ENABLE = 0x02

STRIDE_SIGNED = 0x04

ADJUST_SIGNED = 0x08

ADJUST_TARGET = 0x10

TRIGGER_SHIFT = 5

TRIGGER_4814 = 1

TRIGGER_4815 = 2

TRIGGER_481A = 3


def signed16(value: int) -> int:
    return (value - 0x10000 if value & 0x8000 else value) & WORD_MASK


class DataPort:
    __slots__ = ("read_data", "registers")

    def __init__(self, read_data: Callable[[int], int], held: Sequence[int]) -> None:
        self.read_data = read_data
        self.registers = {
            register: value & MASKS.get(register, 0xFF)
            for register, value in zip(REGISTERS, held, strict=True)
        }

    def power(self) -> None:
        self.registers = dict.fromkeys(REGISTERS, 0x00)

    def offset(self) -> int:
        held = self.registers
        return held[0x11] | held[0x12] << 8 | held[0x13] << 16

    def adjust(self) -> int:
        return self.registers[0x14] | self.registers[0x15] << 8

    def stride(self) -> int:
        return self.registers[0x16] | self.registers[0x17] << 8

    def set_offset(self, address: int) -> None:
        self.registers[0x11] = address & 0xFF
        self.registers[0x12] = (address >> 8) & 0xFF
        self.registers[0x13] = (address >> 16) & 0x7F

    def set_adjust(self, value: int) -> None:
        self.registers[0x14] = value & 0xFF
        self.registers[0x15] = (value >> 8) & 0xFF

    def settings(self) -> int:
        return self.registers[0x18]

    def signed_adjust(self) -> int:
        held = self.adjust()
        return signed16(held) if self.settings() & ADJUST_SIGNED else held

    def fetch(self) -> None:
        adjust = self.signed_adjust() if self.settings() & ADJUST_ENABLE else 0
        self.registers[0x10] = self.read_data((self.offset() + adjust) & ADDRESS_MASK)

    def read(self, register: int) -> int | None:
        if register == 0x10:
            value = self.registers[0x10]
            self.step()
            return value
        if register == 0x1A:
            self.seek(TRIGGER_481A)
            return 0x00
        return self.registers.get(register)

    def write(self, register: int, value: int) -> None:
        if register not in self.registers or register == 0x10:
            return
        self.registers[register] = value & MASKS.get(register, 0xFF)
        if register in (0x13, 0x18):
            self.fetch()
        if register == 0x14:
            self.seek(TRIGGER_4814)
        if register == 0x15:
            if self.settings() & ADJUST_ENABLE:
                self.fetch()
            self.seek(TRIGGER_4815)

    def step(self) -> None:
        stride = self.stride() if self.settings() & STRIDE_SELECT else 1
        if self.settings() & STRIDE_SIGNED:
            stride = signed16(stride)
        if self.settings() & ADJUST_TARGET:
            self.set_adjust(self.signed_adjust() + stride)
        else:
            self.set_offset(self.offset() + stride)
        self.fetch()

    def seek(self, trigger: int) -> None:
        if self.settings() >> TRIGGER_SHIFT != trigger:
            return
        self.set_offset(self.offset() + self.signed_adjust())
        self.fetch()
