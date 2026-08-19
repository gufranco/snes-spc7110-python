"""The SPC7110 decompressor, all three of its modes.

    from spc7110 import describe

    chip = describe("4bpp").build(stream)
    chip.read(64)

One arithmetic decoder underneath, with a mode that decides how many bits a
symbol carries and what happens to it. The clock the same cartridge carries is a
separate part and lives in its own package.
"""

from . import decompressor, models, tables
from .decompressor import CONTEXTS, Context, Decompressor, Empty
from .models import MODES, Mode, UnknownMode, describe
from .version import VERSION

__version__ = VERSION

__all__ = [
    "CONTEXTS",
    "MODES",
    "Context",
    "Decompressor",
    "Empty",
    "Mode",
    "UnknownMode",
    "__version__",
    "decompressor",
    "describe",
    "models",
    "tables",
]
