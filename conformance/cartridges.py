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

from spc7110 import PROGRAM_BYTES, data_rom, decompressor, directory

ROOT = Path(__file__).resolve().parent

RECORDED = "cartridges.json"

BASE_REGISTER = 0x4801

STORE_ABSOLUTE = 0x8D

LOAD_IMMEDIATE = 0xA9

LOAD_LONG = 0xAF

LOAD_LONG_INDEXED = 0xBF

SAMPLE_BYTES = 512

TRIES = 150

DEFAULT_SEED = 0x7110

SUFFIXES = (".sfc", ".smc")


def digests_of(image: bytes) -> dict[str, str]:
    return {
        "crc32": f"{zlib.crc32(image):08x}",
        "md5": hashlib.md5(image).hexdigest(),
        "sha1": hashlib.sha1(image).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }


def bases(image: bytes) -> list[tuple[int, str]]:
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
    path = Path(where) if where is not None else ROOT / RECORDED
    if not path.is_file():
        return {}
    found: dict[str, Any] = json.loads(path.read_text())
    return found


MINIMUM_ENTRIES = 8


def found_in(image: bytes) -> "tuple[list[tuple[int, int]], int, int, str] | None":
    drom = data_rom(image)
    if not drom:
        return None
    for base, how in bases(image):
        entries, end = directory(drom, base)
        if len(entries) >= MINIMUM_ENTRIES:
            return entries, base, end, how
    return None


def read_one(image: bytes) -> dict[str, Any] | None:
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
