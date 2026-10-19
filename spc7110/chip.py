import random
from collections.abc import Generator
from typing import override

from .alu import ArithmeticUnit
from .dataport import DataPort
from .dcu import DecompressionUnit
from .decompressor import Decompressor
from .errors import Empty, OutOfRange
from .mcu import PROGRAM_BYTES, REGISTER_MASKS, Mapper
from .models import mode_named

MASTER_CLOCK_HZ = 21_477_272

DECOMPRESSION_CLOCKS = 20

MULTIPLY_CLOCKS = 30

DIVIDE_CLOCKS = 40

UNSET_SEED = 7110

BUILT_ROM_BYTES = 2 * PROGRAM_BYTES

ADDRESS_LIMIT = 0x1000000

REGISTER_FIRST = 0x4800

REGISTER_LAST = 0x483F

RAM_FIRST = 0x6000

ROM_FIRST = 0x8000

LOW_BANKS = 0x40

DATA_BANKS = 0xC0

ALIASES = {0x50: 0x00, 0x58: 0x08}

POWER_BANKS = (0x00, 0x00, 0x01, 0x02, 0x00)

SCRAMBLED_UNIT_BYTES = 64

REGISTER = "register"

ROM = "rom"

RAM = "ram"


def reduce_ram(address: int) -> int:
    return ((address >> 3) & ~0x1FFF) | (address & 0x1FFF)


class Chip:
    __slots__ = ("alu", "decompression", "mapper", "model", "port", "rom", "thread")

    def __init__(
        self,
        model: str,
        rom: bytes | bytearray | None = None,
        ram: bytearray | None = None,
        seed: int = UNSET_SEED,
    ) -> None:
        scrambled = random.Random(seed)
        held = scrambled.randbytes(BUILT_ROM_BYTES) if rom is None else rom
        if len(held) <= PROGRAM_BYTES:
            raise Empty("an SPC7110 cartridge needs a data ROM after its first 1 MiB")
        if ram is not None and not ram:
            raise Empty("save RAM handed to the part has to hold at least one byte")
        self.model = model
        self.rom = held
        program, data = bytes(held[:PROGRAM_BYTES]), bytes(held[PROGRAM_BYTES:])
        banks = [scrambled.randrange(256) for _ in REGISTER_MASKS]
        self.mapper = Mapper(program, data, ram, banks)
        unit = [*scrambled.randbytes(SCRAMBLED_UNIT_BYTES), scrambled.randrange(1 << 24)]
        self.decompression = DecompressionUnit(self.mapper.data_read, unit)
        self.port = DataPort(self.mapper.data_read, list(scrambled.randbytes(9)))
        self.alu = ArithmeticUnit(list(scrambled.randbytes(17)))
        self.thread = self.run()

    @property
    def program(self) -> bytes:
        return self.mapper.program

    @property
    def data(self) -> bytes:
        return self.mapper.data

    @property
    def ram(self) -> bytearray | None:
        return self.mapper.ram

    def reset(self) -> "Chip":
        for register, value in zip(sorted(REGISTER_MASKS), POWER_BANKS, strict=True):
            self.mapper.write_register(register, value)
        self.decompression.power()
        self.port.power()
        self.alu.power()
        self.thread = self.run()
        return self

    def tick(self, clocks: int = 1) -> "Chip":
        for _ in range(clocks):
            next(self.thread)
        return self

    def run(self) -> Generator[None, None, None]:
        while True:
            if self.decompression.pending:
                self.decompression.pending = False
                yield from self.wait(DECOMPRESSION_CLOCKS)
                self.decompression.begin()
            if self.alu.multiply_pending:
                self.alu.multiply_pending = False
                yield from self.wait(MULTIPLY_CLOCKS)
                self.alu.multiply()
            if self.alu.divide_pending:
                self.alu.divide_pending = False
                yield from self.wait(DIVIDE_CLOCKS)
                self.alu.divide()
            yield

    def wait(self, clocks: int) -> Generator[None, None, None]:
        for _ in range(clocks):
            yield

    def read(self, address: int) -> int | None:
        kind, where = self.decode(address)
        if kind == REGISTER:
            return self.read_register(where)
        if kind == ROM:
            return self.mapper.rom_read(where)
        return self.mapper.ram_read(where)

    def write(self, address: int, value: int) -> None:
        kind, where = self.decode(address)
        if kind == REGISTER:
            self.write_register(where, value & 0xFF)
        if kind == RAM:
            self.mapper.ram_write(where, value)

    def decode(self, address: int) -> tuple[str, int]:
        if not 0 <= address < ADDRESS_LIMIT:
            raise OutOfRange(f"{address:#x} is not a 24-bit address")
        bank, low = address >> 16, address & 0xFFFF
        if bank in ALIASES:
            return REGISTER, ALIASES[bank]
        if bank >= DATA_BANKS:
            return ROM, address & 0x3FFFFF
        if bank & LOW_BANKS:
            raise OutOfRange(f"{address:#08x} is not an address the SPC7110 answers")
        return self.decode_low(address, low)

    def decode_low(self, address: int, low: int) -> tuple[str, int]:
        if REGISTER_FIRST <= low <= REGISTER_LAST:
            return REGISTER, low & 0x3F
        if low >= ROM_FIRST:
            return ROM, address & 0x7FFFFF
        if low >= RAM_FIRST and self.mapper.ram is not None:
            return RAM, reduce_ram(address)
        raise OutOfRange(f"{address:#08x} is not an address the SPC7110 answers")

    def read_register(self, register: int) -> int | None:
        if register < 0x10:
            return self.decompression.read(register)
        if register < 0x20:
            return self.port.read(register)
        if register < 0x30:
            return self.alu.read(register)
        if register in REGISTER_MASKS:
            return self.mapper.read_register(register)
        return None

    def write_register(self, register: int, value: int) -> None:
        if register < 0x10:
            self.decompression.write(register, value)
        elif register < 0x20:
            self.port.write(register, value)
        elif register < 0x30:
            self.alu.write(register, value)
        elif register in REGISTER_MASKS:
            self.mapper.write_register(register, value)

    def decompress(
        self,
        source: bytes | bytearray,
        mode: str | int,
        offset: int = 0,
        index: int = 0,
    ) -> Decompressor:
        started: Decompressor = mode_named(mode).build(source, offset=offset, index=index)
        return started

    @override
    def __repr__(self) -> str:
        return f"<Chip {self.model}>"
