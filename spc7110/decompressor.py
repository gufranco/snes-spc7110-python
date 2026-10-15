from typing import override

from . import tables
from .errors import Empty, UnknownMode

MODES = (0, 1, 2)

BUFFER_BYTES = 64

CONTEXTS = 32

SPAN_FULL = 0xFF

RENORMALISE_BELOW = 0x7F

WORD_MASK = 0xFFFFFFFF

MODE1_COLOURS = 4

MODE2_COLOURS = 16

MODE2_TILE_BYTES = 16


class Context:
    __slots__ = ("index", "invert")

    def __init__(self, index: int = 0, invert: int = 0) -> None:
        self.index = index
        self.invert = invert

    @override
    def __repr__(self) -> str:
        return f"<Context row {self.index} invert {self.invert}>"


class Decompressor:
    __slots__ = (
        "buffer",
        "contexts",
        "held",
        "inverts",
        "lps",
        "mode",
        "offset",
        "order",
        "out",
        "out_high",
        "read_at",
        "source",
        "span",
        "tile",
        "value",
        "window",
        "window_bits",
        "write_at",
    )

    def __init__(self, source: bytes | bytearray) -> None:
        if not source:
            raise Empty("a decompressor needs something to decompress")
        self.source = bytes(source)
        self.offset = 0
        self.mode: int | None = None
        self.contexts = [Context() for _ in range(CONTEXTS)]
        self.buffer = bytearray(BUFFER_BYTES)
        self.read_at = 0
        self.write_at = 0
        self.held = 0
        self._clear_working()

    def _clear_working(self) -> None:
        self.value = 0
        self.window = 0
        self.window_bits = 0
        self.span = SPAN_FULL
        self.out = 0
        self.out_high = 0
        self.inverts = 0
        self.lps = 0
        self.order: list[int] = []
        self.tile = bytearray()

    def take(self) -> int:
        self.offset %= len(self.source)
        value = self.source[self.offset]
        self.offset += 1
        return value

    def start(self, mode: int, offset: int, index: int) -> "Decompressor":
        if mode not in MODES:
            raise UnknownMode(f"{mode} is not a mode this chip has; it has {MODES}")
        self.mode = mode
        self.offset = offset
        self.read_at = 0
        self.write_at = 0
        self.held = 0
        for state in self.contexts:
            state.index = 0
            state.invert = 0
        self._clear_working()

        if mode == 1:
            self.order = list(range(MODE1_COLOURS))
        elif mode == 2:
            self.order = list(range(MODE2_COLOURS))
        self.value = self.take()
        self.window = self.take()
        self.window_bits = 8

        for _ in range(index):
            self.take_byte()
        return self

    def _emit(self, value: int) -> None:
        self.buffer[self.write_at] = value & 0xFF
        self.write_at = (self.write_at + 1) & (BUFFER_BYTES - 1)
        self.held += 1

    def take_byte(self) -> int:
        if self.held == 0:
            if self.mode is None:
                return 0x00
            (self._mode0, self._mode1, self._mode2)[self.mode]()
        value = self.buffer[self.read_at]
        self.read_at = (self.read_at + 1) & (BUFFER_BYTES - 1)
        self.held -= 1
        return value

    def read(self, count: int) -> bytes:
        return bytes(self.take_byte() for _ in range(count))

    def _probability(self, context: int) -> int:
        return tables.EVOLUTION[self.contexts[context].index][tables.PROBABILITY]

    def _symbol(self, context: int) -> tuple[int, int]:
        probability = self._probability(context)
        if self.value <= self.span - probability:
            self.span -= probability
            flag = 0
        else:
            self.value = (self.value - (self.span - (probability - 1))) & 0xFF
            self.span = probability - 1
            flag = 1

        shift = 0
        while self.span < RENORMALISE_BELOW:
            shift += 1
            self.span = ((self.span << 1) + 1) & 0xFF
            self.value = ((self.value << 1) + (self.window >> 7)) & 0xFF
            self.window = (self.window << 1) & 0xFF
            self.window_bits -= 1
            if self.window_bits == 0:
                self.window = self.take()
                self.window_bits = 8
        return flag, shift

    def _advance(self, context: int, flag: int, shift: int) -> int:
        state = self.contexts[context]
        invert = state.invert
        self.lps = (self.lps << 1) + flag
        self.inverts = (self.inverts << 1) + invert
        row = tables.EVOLUTION[state.index]
        if flag and row[tables.TOGGLE_INVERT]:
            state.invert ^= 1
        if flag:
            state.index = row[tables.NEXT_LPS]
        elif shift:
            state.index = row[tables.NEXT_MPS]
        return invert

    def _rotate(self, value: int) -> None:
        self.order.remove(value)
        self.order.insert(0, value)

    def _mode0(self) -> None:
        while self.held < BUFFER_BYTES // 2:
            for bit in range(8):
                mask = (1 << (bit & 3)) - 1
                context = mask + ((self.inverts & mask) ^ (self.lps & mask))
                if bit > 3:
                    context += 15

                mps = ((self.out >> 15) & 1) ^ self.contexts[context].invert
                flag, shift = self._symbol(context)
                self.out = ((self.out << 1) + (mps if not flag else 1 - mps)) & WORD_MASK
                self._advance(context, flag, shift)
            self._emit(self.out)

    def _mode1(self) -> None:
        while self.held < BUFFER_BYTES // 2:
            for _ in range(8):
                a = (self.out >> 2) & 3
                b = (self.out >> 14) & 3
                c = (self.out >> 16) & 3
                context = (b != c) if a == b else (2 if b == c else 4 - (a == c))

                self._rotate(a)
                real = list(self.order)
                for reference in (c, b, a):
                    real.remove(reference)
                    real.insert(0, reference)

                for _ in range(2):
                    flag, shift = self._symbol(context)
                    self._advance(context, flag, shift)
                    context = 5 + (context << 1) + ((self.lps ^ self.inverts) & 1)

                self.out = ((self.out << 2) + real[(self.lps ^ self.inverts) & 3]) & WORD_MASK

            data = tables.morton_2x8(self.out & 0xFFFF)
            self._emit(data >> 8)
            self._emit(data)

    def _mode2(self) -> None:
        while self.held < BUFFER_BYTES // 2:
            for _ in range(8):
                a = self.out & 15
                b = (self.out >> 28) & 15
                c = self.out_high & 15
                reference = (b != c) if a == b else (2 if b == c else 4 - (a == c))
                context = 0

                self._rotate(a)
                real = list(self.order)
                for pixel in (c, b, a):
                    real.remove(pixel)
                    real.insert(0, pixel)

                for _ in range(4):
                    flag, shift = self._symbol(context)
                    invert = self._advance(context, flag, shift)
                    context = tables.MODE2_CONTEXT[context][flag ^ invert] + (
                        reference if context == 1 else 0
                    )

                self.out_high = ((self.out_high << 4) + ((self.out >> 28) & 15)) & WORD_MASK
                self.out = ((self.out << 4) + real[(self.lps ^ self.inverts) & 0x0F]) & WORD_MASK

            data = tables.morton_4x8(self.out)
            self._emit(data >> 24)
            self._emit(data >> 16)
            self.tile.append((data >> 8) & 0xFF)
            self.tile.append(data & 0xFF)

            if len(self.tile) == MODE2_TILE_BYTES:
                for value in self.tile:
                    self._emit(value)
                self.tile = bytearray()

    @override
    def __repr__(self) -> str:
        return f"<Decompressor mode {self.mode} at {self.offset} holding {self.held}>"
