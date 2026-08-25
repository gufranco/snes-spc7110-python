"""Everything this package raises, in one place.

One module so a caller can see the whole set at once, and so `except` has
somewhere to import from. It imports nothing from the rest of the package, which
is what keeps it from ever closing a cycle: everything here raises, so everything
here imports this, and an import running the other way would make the order
modules happen to load in decide whether the package works at all.

`UnknownMode` was defined twice under one name, once beside the catalogue and
once beside the decoder, which is the trap the family standard names outright: an
`except UnknownMode` written against one of them sails straight through the
other. There is one definition now.
"""

from __future__ import annotations


class UnknownModelError(Exception):
    """No part goes by that name.

    The message names the parts that would have worked, because a refusal that
    does not costs the caller a search through the source. There is one.
    """


class UnknownMode(Exception):
    """The chip has no mode of that number or name.

    Three modes exist and a caller asking for a fourth is refused rather than
    quietly given the first, because a decompression that ran in the wrong mode
    produces bytes rather than an error.
    """


class Empty(Exception):
    """A decompressor was built with nothing to decompress.

    Refused at construction rather than at the first read, so a caller finds out
    where the mistake is rather than several calls later.
    """
