"""The two tables the decoder is steered by, and the bit shuffles it ends with.

The evolution table is the state machine of an arithmetic coder. Each row is a
probability and where to go next: one way when the less likely symbol arrives,
another when the more likely one does, plus a flag saying whether the row is
allowed to swap which symbol is which. Fifty three rows, and a context is a
cursor into them.

These are coder parameters rather than content. They say how likely a symbol is
and which row follows, which describes an algorithm rather than anything the
cartridge draws. Nothing here is a picture, a sound, or a byte of a game.

The Morton tables are a de-interleave. The decoder produces pixels with their
bits woven together and the console wants them separated into planes, so the last
thing each mode does is unweave them. Doing that a bit at a time would be eight
shifts and eight masks per byte; doing it through a table built once is a lookup,
which is what the reference does and why the tables are here rather than the
arithmetic that would replace them.
"""

from collections.abc import Sequence

EVOLUTION = (
    (0x5A, 1, 1, 1),
    (0x25, 6, 2, 0),
    (0x11, 8, 3, 0),
    (0x08, 10, 4, 0),
    (0x03, 12, 5, 0),
    (0x01, 15, 5, 0),
    (0x5A, 7, 7, 1),
    (0x3F, 19, 8, 0),
    (0x2C, 21, 9, 0),
    (0x20, 22, 10, 0),
    (0x17, 23, 11, 0),
    (0x11, 25, 12, 0),
    (0x0C, 26, 13, 0),
    (0x09, 28, 14, 0),
    (0x07, 29, 15, 0),
    (0x05, 31, 16, 0),
    (0x04, 32, 17, 0),
    (0x03, 34, 18, 0),
    (0x02, 35, 5, 0),
    (0x5A, 20, 20, 1),
    (0x48, 39, 21, 0),
    (0x3A, 40, 22, 0),
    (0x2E, 42, 23, 0),
    (0x26, 44, 24, 0),
    (0x1F, 45, 25, 0),
    (0x19, 46, 26, 0),
    (0x15, 25, 27, 0),
    (0x11, 26, 28, 0),
    (0x0E, 26, 29, 0),
    (0x0B, 27, 30, 0),
    (0x09, 28, 31, 0),
    (0x08, 29, 32, 0),
    (0x07, 30, 33, 0),
    (0x05, 31, 34, 0),
    (0x04, 33, 35, 0),
    (0x04, 33, 36, 0),
    (0x03, 34, 37, 0),
    (0x02, 35, 38, 0),
    (0x02, 36, 5, 0),
    (0x58, 39, 40, 1),
    (0x4D, 47, 41, 0),
    (0x43, 48, 42, 0),
    (0x3B, 49, 43, 0),
    (0x34, 50, 44, 0),
    (0x2E, 51, 45, 0),
    (0x29, 44, 46, 0),
    (0x25, 45, 24, 0),
    (0x56, 47, 48, 1),
    (0x4F, 47, 49, 0),
    (0x47, 48, 50, 0),
    (0x41, 49, 51, 0),
    (0x3C, 50, 52, 0),
    (0x37, 51, 43, 0),
)

PROBABILITY = 0

NEXT_LPS = 1

NEXT_MPS = 2

TOGGLE_INVERT = 3

MODE2_CONTEXT = (
    (1, 2),
    (3, 8),
    (13, 14),
    (15, 16),
    (17, 18),
    (19, 20),
    (21, 22),
    (23, 24),
    (25, 26),
    (25, 26),
    (25, 26),
    (25, 26),
    (25, 26),
    (27, 28),
    (29, 30),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
    (31, 31),
)

_TWO_PLANE = (
    ((7, 11), (6, 3), (5, 10), (4, 2), (3, 9), (2, 1), (1, 8), (0, 0)),
    ((7, 15), (6, 7), (5, 14), (4, 6), (3, 13), (2, 5), (1, 12), (0, 4)),
)

_FOUR_PLANE = (
    ((7, 25), (6, 17), (5, 9), (4, 1), (3, 24), (2, 16), (1, 8), (0, 0)),
    ((7, 27), (6, 19), (5, 11), (4, 3), (3, 26), (2, 18), (1, 10), (0, 2)),
    ((7, 29), (6, 21), (5, 13), (4, 5), (3, 28), (2, 20), (1, 12), (0, 4)),
    ((7, 31), (6, 23), (5, 15), (4, 7), (3, 30), (2, 22), (1, 14), (0, 6)),
)


def _built(patterns: Sequence[Sequence[tuple[int, int]]]) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(
            sum(((value >> source) & 1) << target for source, target in pattern)
            for value in range(256)
        )
        for pattern in patterns
    )


MORTON16 = _built(_TWO_PLANE)

MORTON32 = _built(_FOUR_PLANE)


def morton_2x8(data: int) -> int:
    """Two eight bit values woven together, taken apart again."""
    return MORTON16[0][data & 0xFF] + MORTON16[1][(data >> 8) & 0xFF]


def morton_4x8(data: int) -> int:
    """Four eight bit values woven together, taken apart again."""
    return (
        MORTON32[0][data & 0xFF]
        + MORTON32[1][(data >> 8) & 0xFF]
        + MORTON32[2][(data >> 16) & 0xFF]
        + MORTON32[3][(data >> 24) & 0xFF]
    )
