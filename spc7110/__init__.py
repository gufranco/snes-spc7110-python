from . import decompressor as decompressor
from . import models as models
from . import tables as tables
from .decompressor import CONTEXTS, Context, Decompressor
from .errors import Empty, UnknownMode, UnknownModelError
from .models import MODELS, MODES, Mode, Model, mode_named
from .version import VERSION

__version__ = VERSION

from typing import Any


def Chip(model: str | None = None, **options: Any) -> models.Chip:  # noqa: N802
    return models.lookup(model).build(**options)


__all__ = [
    "CONTEXTS",
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
    "mode_named",
]
