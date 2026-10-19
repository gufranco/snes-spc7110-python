from collections.abc import Sequence

REGISTERS = tuple(range(0x20, 0x30))

BUSY = 0x80

MULTIPLY_FLAG = 0x01

SIGNED = 0x01

WORD_MASK = 0xFFFFFFFF


def signed(value: int, bits: int) -> int:
    top = 1 << (bits - 1)
    return value - (top << 1) if value & top else value


def truncated(dividend: int, divisor: int) -> tuple[int, int]:
    quotient = abs(dividend) // abs(divisor)
    if (dividend < 0) != (divisor < 0):
        quotient = -quotient
    return quotient, dividend - quotient * divisor


class ArithmeticUnit:
    __slots__ = ("divide_pending", "multiply_pending", "registers")

    def __init__(self, held: Sequence[int]) -> None:
        self.registers = dict(zip(REGISTERS, held[: len(REGISTERS)], strict=True))
        self.registers[0x2E] &= SIGNED
        self.multiply_pending = bool(held[len(REGISTERS)] & 1)
        self.divide_pending = bool(held[len(REGISTERS)] & 2)

    def power(self) -> None:
        self.registers = dict.fromkeys(REGISTERS, 0x00)
        self.multiply_pending = False
        self.divide_pending = False

    def read(self, register: int) -> int:
        return self.registers[register]

    def write(self, register: int, value: int) -> None:
        if register in (0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2F):
            return
        self.registers[register] = value & (SIGNED if register == 0x2E else 0xFF)
        if register == 0x25:
            self.registers[0x2F] |= BUSY | MULTIPLY_FLAG
            self.multiply_pending = True
        if register == 0x27:
            self.registers[0x2F] |= BUSY
            self.divide_pending = True

    def word(self, first: int, count: int) -> int:
        return sum(self.registers[first + at] << (8 * at) for at in range(count))

    def store(self, first: int, value: int, count: int) -> None:
        for at in range(count):
            self.registers[first + at] = (value >> (8 * at)) & 0xFF

    def multiply(self) -> None:
        multiplier, multiplicand = self.word(0x24, 2), self.word(0x20, 2)
        if self.registers[0x2E] & SIGNED:
            multiplier, multiplicand = signed(multiplier, 16), signed(multiplicand, 16)
        self.store(0x28, multiplier * multiplicand, 4)
        self.registers[0x2F] &= ~BUSY & 0xFF

    def divide(self) -> None:
        dividend, divisor = self.word(0x20, 4), self.word(0x26, 2)
        if self.registers[0x2E] & SIGNED:
            dividend, divisor = signed(dividend, 32), signed(divisor, 16)
        quotient, remainder = truncated(dividend, divisor) if divisor else (0, dividend)
        self.store(0x28, quotient, 4)
        self.store(0x2C, remainder, 2)
        self.registers[0x2F] &= ~BUSY & 0xFF
