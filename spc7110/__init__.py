"""The SPC7110 decompressor, all three of its modes.

    from spc7110 import describe

    chip = describe("4bpp").build(stream)
    chip.read(64)

One arithmetic decoder underneath, with a mode that decides how many bits a
symbol carries and what happens to it. The clock the same cartridge carries is a
separate part and lives in its own package.
"""

from . import decompressor as decompressor
from . import models as models
from . import tables as tables
from .decompressor import CONTEXTS, Context, Decompressor
from .errors import Empty, UnknownMode, UnknownModelError
from .models import DEFAULT_MODEL, MODELS, MODES, Mode, Model, describe, describe_part
from .version import VERSION

__version__ = VERSION

from typing import Any


def Chip(model: str = DEFAULT_MODEL, **options: Any) -> models.Chip:  # noqa: N802
    """A chip of the named model, sharing one interface across the family.

    The model comes first because it is the thing a caller always knows. One
    model rather than several, and it still takes the argument, so a caller
    moving between members writes the same call and a typo is refused instead of
    silently building the default.

    The mode is not a model. Three modes exist and one chip does all three, so
    the mode is an argument to `decompress` rather than a name in this
    catalogue.
    """
    return describe_part(model).build(**options)


__all__ = [
    "CONTEXTS",
    "DEFAULT_MODEL",
    "MODELS",
    "MODES",
    "Chip",
    "Context",
    "Decompressor",
    "Empty",
    "Mode",
    "Model",
    "UnknownMode",
    "UnknownModelError",
    "__version__",
    "describe",
    "describe_part",
]
