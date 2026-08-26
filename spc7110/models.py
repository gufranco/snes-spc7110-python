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
from .errors import UnknownMode, UnknownModelError


class Mode:
    """One mode: what it produces, and how to start a decompressor on it."""

    __slots__ = (
        "aliases",
        "depth",
        "name",
        "number",
        "summary",
    )

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


def mode_named(name: str | int) -> "Mode":
    """The mode of that name or number, however it happens to be written.

    Named for what it hands back. A mode is not a part and is not built by the
    constructor, so it keeps a resolver of its own; MODES is the catalogue and
    this is what turns the names and numbers people write into one of its
    entries.
    """
    found = _BY_NUMBER.get(name) if isinstance(name, int) else _BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownMode(f"{name} is not a mode this chip has; it has {', '.join(sorted(MODES))}")
    return found


class Model:
    """One part: what it is, and what a caller can ask it to do.

    A part rather than a mode. The three modes are how a caller asks for one
    decompression, not three chips: one SPC7110 was made and it does all three.
    The family's catalogue is a catalogue of parts, so it holds one entry, and
    the mode is an argument to the call rather than a name in the catalogue.
    """

    __slots__ = ("aliases", "modes", "name", "summary")

    def __init__(self, name: str, summary: str, aliases: Sequence[str] = ()) -> None:
        self.name = name
        self.summary = summary
        self.aliases = tuple(aliases)
        self.modes = tuple(sorted(MODES))

    def build(self, **options: Any) -> "Chip":
        return Chip(self.name, **options)

    @override
    def __repr__(self) -> str:
        return f"<Model {self.name}, {len(self.modes)} modes>"


class Chip:
    """The chip as a thing a caller holds, rather than a function they call."""

    __slots__ = ("model",)

    def __init__(self, model: str) -> None:
        self.model = model

    def decompress(
        self,
        source: bytes | bytearray,
        mode: str | int,
        offset: int = 0,
        index: int = 0,
    ) -> Decompressor:
        """Start a decompression of that stream in that mode.

        The mode comes second because it is the thing that changes per call. It
        is looked up through the same catalogue a caller would use, so a mode
        this chip does not have is refused here rather than several bytes into a
        decode.
        """
        started: Decompressor = mode_named(mode).build(source, offset=offset, index=index)
        return started

    def reset(self) -> "Chip":
        """The console's reset line, which this part carries no state across.

        Every decompression is started from its own header and its own context
        table, and nothing survives from one to the next. So this changes
        nothing, and it exists because a caller driving a board resets every
        part on it and should not have to special-case which ones hold state.
        """
        return self

    @override
    def __repr__(self) -> str:
        return f"<Chip {self.model}>"


_PARTS = (
    Model(
        name="spc7110",
        summary=(
            "The SPC7110's decompressor, one of three things the chip does. The other "
            "two, a real-time clock and a memory mapper, have homes of their own."
        ),
        aliases=("spc-7110", "epsonspc7110"),
    ),
)

MODELS = {part.name: part for part in _PARTS}

_PART_BY_ALIAS = {}
for _part in _PARTS:
    _PART_BY_ALIAS[_part.name] = _part
    for _name in _part.aliases:
        _PART_BY_ALIAS[_name.replace("-", "")] = _part

DEFAULT_MODEL = "spc7110"


def lookup(name: str | None) -> Model:
    """The part of that name, however it happens to be written.

    Naming nothing is refused rather than filled in. A default would be the one
    implicit thing in the call that builds a part, and it is worst where it looks
    most harmless: a caller who learns to leave the model out against a member
    covering one part writes the same call against a member covering sixteen.

    Kept apart from the mode resolver because the two catalogues answer different
    questions, and one function that guessed which was meant would answer the
    wrong one for a caller who wrote a mode number.

    Not exported from the package. What a caller wants is the part, and the part
    carries its own model.
    """
    if name is None:
        raise UnknownModelError(
            "no model was named, and this package will not choose one for you."
            f" Name one of: {', '.join(sorted(MODELS))}"
        )
    found = _PART_BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownModelError(
            f"{name} is not a part this package covers; it has {', '.join(sorted(MODELS))}"
        )
    return found
