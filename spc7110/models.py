from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, override

from .decompressor import Decompressor
from .errors import UnknownMode, UnknownModelError

if TYPE_CHECKING:
    from .chip import Chip


class Mode:
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
    found = _BY_NUMBER.get(name) if isinstance(name, int) else _BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownMode(f"{name} is not a mode this chip has; it has {', '.join(sorted(MODES))}")
    return found


class Model:
    __slots__ = ("aliases", "modes", "name", "summary")

    def __init__(self, name: str, summary: str, aliases: Sequence[str] = ()) -> None:
        self.name = name
        self.summary = summary
        self.aliases = tuple(aliases)
        self.modes = tuple(sorted(MODES))

    def build(self, **options: Any) -> "Chip":
        from .chip import Chip

        return Chip(self.name, **options)

    @override
    def __repr__(self) -> str:
        return f"<Model {self.name}, {len(self.modes)} modes>"


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
