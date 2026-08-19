"""The SPC7110's decompressor: an arithmetic decoder with three output shapes.

Underneath the three modes there is one decoder. It keeps a span and a value,
narrows the span by a probability drawn from a context, and decides a symbol by
where the value falls. When the span gets too small it renormalises, pulling bits
in from the compressed stream one at a time. That much is a textbook binary
arithmetic coder.

What the modes change is what a symbol means and what happens to it afterwards.

Mode zero decodes one bit at a time and packs eight of them into a byte, so its
context is chosen from the last few decisions and their inversions. Mode one
decodes two bits at a time, treats them as a pixel of a four colour tile, and
keeps a most-recently-used list of the four colours so a repeated colour costs
less than a new one. Mode two does the same with four bits and sixteen colours,
and buffers a whole tile before writing it, because the four planes it produces
do not come out in the order the console wants them.

Two things in here look like mistakes and are not.

The inversion flag lets a context decide that what it has been calling the likely
symbol is actually the unlikely one, and swap them. It is how the coder adapts
to a stream that starts one way and continues another.

And the pixel order lists are rotated, not sorted. The colour just decoded goes
to the front, then the three reference pixels are moved to the front in turn, so
the list ends up ordered by how recently each colour was useful rather than by
value. The number the coder produces is an index into that list, so the same
number means a different colour from one pixel to the next.

The buffer is a ring, and it refills half of itself at a time rather than one
byte, because the modes produce whole bytes or whole tiles and cannot stop
partway.
"""

from . import tables

MODES = (0, 1, 2)

BUFFER_BYTES = 64

CONTEXTS = 32

SPAN_FULL = 0xFF

RENORMALISE_BELOW = 0x7F

WORD_MASK = 0xFFFFFFFF

MODE1_COLOURS = 4

MODE2_COLOURS = 16

MODE2_TILE_BYTES = 16


class UnknownMode(Exception):
    pass


class Empty(Exception):
    pass


class Context:
    """One context: which row of the evolution table, and which symbol is likelier."""

    __slots__ = ("index", "invert")

    def __init__(self, index=0, invert=0):
        self.index = index
        self.invert = invert

    def __repr__(self):
        return f"<Context row {self.index} invert {self.invert}>"


class Decompressor:
    """One decompressor, reading a compressed stream and handing back bytes."""

    def __init__(self, source):
        if not source:
            raise Empty("a decompressor needs something to decompress")
        self.source = bytes(source)
        self.offset = 0
        self.mode = None
        self.contexts = [Context() for _ in range(CONTEXTS)]
        self.buffer = bytearray(BUFFER_BYTES)
        self.read_at = 0
        self.write_at = 0
        self.held = 0
        self._clear_working()

    def _clear_working(self):
        self.value = 0
        self.window = 0
        self.window_bits = 0
        self.span = SPAN_FULL
        self.out = 0
        self.out_high = 0
        self.inverts = 0
        self.lps = 0
        self.order = []
        self.tile = bytearray()

    def take(self):
        """One byte of the compressed stream, wrapping when it runs off the end."""
        self.offset %= len(self.source)
        value = self.source[self.offset]
        self.offset += 1
        return value

    def start(self, mode, offset, index):
        """Point the decoder at a stream and run it forward to an output position."""
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

    def _emit(self, value):
        self.buffer[self.write_at] = value & 0xFF
        self.write_at = (self.write_at + 1) & (BUFFER_BYTES - 1)
        self.held += 1

    def take_byte(self):
        """One decompressed byte, filling the buffer when it has run out."""
        if self.held == 0:
            if self.mode is None:
                return 0x00
            (self._mode0, self._mode1, self._mode2)[self.mode]()
        value = self.buffer[self.read_at]
        self.read_at = (self.read_at + 1) & (BUFFER_BYTES - 1)
        self.held -= 1
        return value

    def read(self, count):
        """That many decompressed bytes."""
        return bytes(self.take_byte() for _ in range(count))

    def _probability(self, context):
        return tables.EVOLUTION[self.contexts[context].index][tables.PROBABILITY]

    def _symbol(self, context):
        """One symbol, and how far the span had to be renormalised to get it."""
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

    def _advance(self, context, flag, shift):
        """Fold the symbol into the history and move the context along."""
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

    def _rotate(self, value):
        """Move a colour to the front of the recency list, keeping the rest in order."""
        self.order.remove(value)
        self.order.insert(0, value)

    def _mode0(self):
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

    def _mode1(self):
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

    def _mode2(self):
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

    def __repr__(self):
        return f"<Decompressor mode {self.mode} at {self.offset} holding {self.held}>"
