from . import chip as chip
from . import decompressor as decompressor
from . import models as models
from . import tables as tables
from .decompressor import CONTEXTS, Context, Decompressor
from .errors import Empty, OutOfRange, UnknownMode, UnknownModelError
from .mcu import PROGRAM_BYTES
from .models import MODELS, MODES, Mode, Model, mode_named
from .streams import data_rom, directory
from .version import VERSION

__version__ = VERSION

from typing import Any


def Chip(model: str | None = None, **options: Any) -> chip.Chip:  # noqa: N802
    return models.lookup(model).build(**options)


__all__ = [
    "CONTEXTS",
    "MODELS",
    "MODES",
    "PROGRAM_BYTES",
    "Chip",
    "Context",
    "Decompressor",
    "Empty",
    "Mode",
    "Model",
    "OutOfRange",
    "UnknownMode",
    "UnknownModelError",
    "__version__",
    "data_rom",
    "directory",
    "mode_named",
]
