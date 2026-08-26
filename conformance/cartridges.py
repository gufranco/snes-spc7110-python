"""Find the real streams in a cartridge, by reading the program that reaches them.

Everything this decompressor has been driven with was generated from a seed. That
is a fair test of an arithmetic decoder and it is not the data the part was built
for, and an earlier attempt to reach the real data failed in a way worth
recording: a pattern search turned up a run of plausible-looking directory
entries, every one of which decoded without complaint, and nothing separated them
from random offsets. This decompressor raises on nothing, so decoding without
complaint establishes nothing.

**What was missing was the program.** The part takes the directory base from
three registers the game writes, so the base is not something to search for. It
is a constant in the cartridge's own code, and reading it out settles where the
streams are without guessing.

Three cartridges carry this part and each writes the base differently:

| Cartridge | How its code names the base |
|:--|:--|
| Tengai Makyou Zero | three immediate loads |
| Momotarou Dentetsu Happy | three consecutive bytes of a table, read long-indexed |
| Super Power League 4 | two sixteen bit loads covering the same three bytes |

All three forms are read here. Nothing is executed.

**The oracle is calibrated rather than assumed.** A directory that decodes is not
a directory that is real. What tells them apart is what comes out: graphics carry
far less entropy than noise, and the streams a base names are compared against
streams at random offsets in the same image every time. The two figures are
recorded together, because a claim published without its noise floor is a claim
nobody can weigh.

**What is recorded.** How many streams, of which modes, where the directory sat,
and the entropy separation, with four digests of each cartridge. No compressed
byte and no decompressed byte, and no stream address: those are the game's
graphics in a different container.

Usage: python3 conformance/cartridges.py <directory of cartridges> <output directory>
"""

import collections
import hashlib
import json
import math
import random
import sys
import zlib
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from spc7110 import decompressor

ROOT = Path(__file__).resolve().parent

RECORDED = "cartridges.json"

PROGRAM_BYTES = 0x100000
"""Where the data ROM begins.

The part addresses two ROMs and a cartridge image holds them one after the other.
A megabyte is what all three carry, and it is checked rather than assumed: at any
other split the directory the program names decodes to nothing that ascends.
"""

BASE_REGISTER = 0x4801
"""The first of the three registers holding the directory base."""

STORE_ABSOLUTE = 0x8D

LOAD_IMMEDIATE = 0xA9

LOAD_LONG = 0xAF

LOAD_LONG_INDEXED = 0xBF

ENTRY_BYTES = 4

SAMPLE_BYTES = 512

TRIES = 150

DEFAULT_SEED = 0x7110

SUFFIXES = (".sfc", ".smc")


def digests_of(image: bytes) -> dict[str, str]:
    """The four a manifest publishes, so a reader can cross-check any of them."""
    return {
        "crc32": f"{zlib.crc32(image):08x}",
        "md5": hashlib.md5(image).hexdigest(),
        "sha1": hashlib.sha1(image).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }


def data_rom(image: bytes) -> bytes:
    """The half of the image the part decompresses out of."""
    return image[PROGRAM_BYTES:] if len(image) > PROGRAM_BYTES else b""


def directory(drom: bytes, base: int) -> tuple[list[tuple[int, int]], int]:
    """Every entry from that base, and where the run stopped.

    An entry is a mode and a twenty four bit address, and the run stops at the
    first entry that is not one: a mode the part does not have, an address past
    the end of the data ROM, or an address below the one before it. Real
    directories ascend, and requiring that is what keeps a run of ordinary bytes
    from reading as a long directory.
    """
    found: list[tuple[int, int]] = []
    at, last = base, -1
    while at + ENTRY_BYTES <= len(drom):
        mode = drom[at]
        address = drom[at + 1] << 16 | drom[at + 2] << 8 | drom[at + 3]
        if mode not in decompressor.MODES or address >= len(drom) or address < last:
            break
        found.append((mode, address))
        last = address
        at += ENTRY_BYTES
    return found, at


def bases(image: bytes) -> list[tuple[int, str]]:
    """Every directory base the cartridge's own code names, and how it named it.

    Three forms, because the three cartridges use three. An immediate load puts
    the byte in the instruction. A long load, indexed or not, names an address in
    the program ROM, and the three registers take three consecutive bytes from
    there, whether the game writes them with three eight bit loads or two sixteen
    bit ones.
    """
    found: list[tuple[int, str]] = []
    seen: set[int] = set()
    for at in range(4, len(image) - 2):
        if image[at] != STORE_ABSOLUTE:
            continue
        if image[at + 1] | image[at + 2] << 8 != BASE_REGISTER:
            continue

        if image[at - 2] == LOAD_IMMEDIATE:
            low = image[at - 1]
            rest = image[at + 3 :]
            if len(rest) < 10 or rest[0] != LOAD_IMMEDIATE or rest[5] != LOAD_IMMEDIATE:
                continue
            base = low | rest[1] << 8 | rest[6] << 16
            how = "three immediate loads"
        elif image[at - 4] in (LOAD_LONG, LOAD_LONG_INDEXED):
            where = image[at - 3] | image[at - 2] << 8
            if where + 3 > len(image):
                continue
            base = image[where] | image[where + 1] << 8 | image[where + 2] << 16
            how = f"a long load from {where:#08x}"
        else:
            continue

        if base not in seen:
            seen.add(base)
            found.append((base, how))
    return found


def entropy(held: bytes) -> float:
    """How many bits a byte of this carries, which is what tells graphics from noise."""
    if not held:
        return 0.0
    counted = collections.Counter(held)
    return -sum((n / len(held)) * math.log2(n / len(held)) for n in counted.values())


def separation(
    drom: bytes,
    entries: "Sequence[tuple[int, int]]",
    tries: int = TRIES,
    seed: int = DEFAULT_SEED,
) -> dict[str, float]:
    """What the directory's streams decode to, against what random offsets do.

    The second number is the point of the first. A directory that decodes is not
    a directory that is real, and this decompressor decodes anything.
    """
    chance = random.Random(seed)
    real = [
        entropy(bytes(decompressor.Decompressor(drom).start(mode, address, 0).read(SAMPLE_BYTES)))
        for mode, address in list(entries)[:tries]
    ]
    noise = [
        entropy(
            bytes(
                decompressor.Decompressor(drom)
                .start(
                    chance.choice(decompressor.MODES),
                    chance.randrange(max(1, len(drom) - 0x1000)),
                    0,
                )
                .read(SAMPLE_BYTES)
            )
        )
        for _ in range(min(tries, len(real) or tries))
    ]
    return {
        "real": round(sum(real) / len(real), 3) if real else 0.0,
        "noise": round(sum(noise) / len(noise), 3) if noise else 0.0,
        "tried": len(real),
    }


def census(entries: "Sequence[tuple[int, int]]", base: int, end: int) -> dict[str, Any]:
    """What was found, carrying no stream address and no byte of any stream."""
    modes: collections.Counter[str] = collections.Counter()
    for mode, _address in entries:
        modes[str(mode)] += 1
    return {
        "streams": len(entries),
        "modes": dict(sorted(modes.items())),
        "directory": [hex(base), hex(end)],
        "adjacent": bool(entries) and entries[0][1] == end,
    }


def recorded(where: Path | str | None = None) -> dict[str, Any]:
    """The reading this repository carries, or nothing if it is not there."""
    path = Path(where) if where is not None else ROOT / RECORDED
    if not path.is_file():
        return {}
    found: dict[str, Any] = json.loads(path.read_text())
    return found


MINIMUM_ENTRIES = 8
"""How many ascending entries a base has to yield before it is believed.

A run of ordinary bytes can produce two or three by accident. Eight ascending
entries with valid modes does not happen by accident, and every real directory
found here runs to hundreds.
"""


def found_in(image: bytes) -> "tuple[list[tuple[int, int]], int, int, str] | None":
    """The streams one cartridge holds, where its directory sat, and how it was named."""
    drom = data_rom(image)
    if not drom:
        return None
    for base, how in bases(image):
        entries, end = directory(drom, base)
        if len(entries) >= MINIMUM_ENTRIES:
            return entries, base, end, how
    return None


def read_one(image: bytes) -> dict[str, Any] | None:
    """Everything one cartridge yields, or nothing if its code names no base."""
    reached = found_in(image)
    if reached is None:
        return None
    entries, base, end, how = reached
    found = census(entries, base, end)
    found["baseFrom"] = how
    found["separation"] = separation(data_rom(image), entries)
    return found


def main(argv: Sequence[str], say: Callable[[str], object] = print) -> int:
    if len(argv) < 2:
        say("usage: cartridges.py <directory of cartridges> <output directory>")
        return 2

    source, out = Path(argv[0]), Path(argv[1])
    if not source.is_dir():
        say(f"  no such directory: {source}")
        return 2

    rows = []
    for path in sorted(source.rglob("*")):
        if path.suffix.lower() not in SUFFIXES or not path.is_file():
            continue
        image = path.read_bytes()
        found = read_one(image)
        if found is None:
            continue
        found = {"name": path.name, "bytes": len(image), **digests_of(image), **found}
        rows.append(found)
        say(
            f"  {path.name[:44]:44s} {found['streams']:4d} streams,"
            f" modes {found['modes']}, entropy {found['separation']['real']}"
            f" against {found['separation']['noise']}"
        )

    if not rows:
        say(f"  no cartridge whose code names a directory base was found under {source}")
        return 2

    (out / RECORDED).write_text(
        json.dumps(
            {
                "note": (
                    "The real streams in the cartridges that carry this part, found by "
                    "reading the directory base out of each program rather than by "
                    "searching for a pattern. Counts, modes and entropy only: no stream "
                    "address, no compressed byte and no decompressed byte is recorded "
                    "here, and none can be recovered from this."
                ),
                "producedBy": "conformance/cartridges.py",
                "programBytes": hex(PROGRAM_BYTES),
                "readFrom": rows,
                "streams": sum(one["streams"] for one in rows),
            },
            indent=2,
        )
        + "\n"
    )
    say(f"  {sum(one['streams'] for one in rows)} streams across {len(rows)} cartridges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
