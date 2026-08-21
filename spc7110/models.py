"""The three shapes the decompressor can produce, named the way people name them.

The chip does not have three decompressors. It has one, and a mode that decides
how many bits a symbol carries and what is done with them afterwards, so the
modes are worth naming by the depth they produce rather than by their number.

Mode zero produces one bit a pixel, mode one two, and mode two four. A cartridge
picks the mode per block, so the same stream decoded in the wrong mode produces
plausible bytes that are not the picture.
"""

from collections.abc import Sequence
from typing import Any, override

from .decompressor import Decompressor


class UnknownMode(Exception):
    pass


class Mode:
    """One mode: what it produces, and how to start a decompressor on it."""

    def __init__(
        self,
        number: int,
        name: str,
        depth: int,
        summary: str,
        aliases: Sequence[str] = (),
    ) -> None:
        self.number = number
        self.name = name
        self.depth = depth
        self.summary = summary
        self.aliases = tuple(aliases)

    def build(self, source: bytes | bytearray, offset: int = 0, index: int = 0) -> Any:
        return Decompressor(source).start(mode=self.number, offset=offset, index=index)

    @override
    def __repr__(self) -> str:
        return f"<Mode {self.number}, {self.name}>"


_CATALOGUE = (
    Mode(
        number=0,
        name="1bpp",
        depth=1,
        summary=(
            "One bit a pixel, packed eight to a byte. The context comes from the "
            "last few decisions rather than from any colour, because there are "
            "only two."
        ),
        aliases=("mode0", "1bit", "2-colour"),
    ),
    Mode(
        number=1,
        name="2bpp",
        depth=2,
        summary=(
            "Two bits a pixel, four colours, with a recency list so a colour used "
            "recently costs fewer bits than a new one. Two bytes a row."
        ),
        aliases=("mode1", "2bit", "4-colour"),
    ),
    Mode(
        number=2,
        name="4bpp",
        depth=4,
        summary=(
            "Four bits a pixel, sixteen colours, the same recency list over a "
            "longer one. A whole tile is buffered before it is handed back, "
            "because its planes do not come out in the order the console wants."
        ),
        aliases=("mode2", "4bit", "16-colour"),
    ),
)

MODES = {mode.name: mode for mode in _CATALOGUE}

_BY_NUMBER = {mode.number: mode for mode in _CATALOGUE}

_BY_ALIAS = {}
for _mode in _CATALOGUE:
    _BY_ALIAS[_mode.name] = _mode
    for _alias in _mode.aliases:
        _BY_ALIAS[_alias.replace("-", "")] = _mode


def _normalise(name: str | int) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "").replace(" ", "")


def describe(name: str | int) -> "Mode":
    """The mode of that name or number, however it happens to be written."""
    found = _BY_NUMBER.get(name) if isinstance(name, int) else _BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownMode(f"{name} is not a mode this chip has; it has {', '.join(sorted(MODES))}")
    return found
