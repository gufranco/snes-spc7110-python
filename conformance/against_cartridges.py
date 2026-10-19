import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import spc7110
from conformance import build, cartridges, differential

ROOT = Path(__file__).resolve().parent

RECORDED = "streams.json"

WINDOW_BYTES = 0x8000

WANTED_BYTES = 512

Ask = Callable[["differential.Case", Path | str], list[int]]


def case_for(drom: bytes, mode: int, address: int) -> "differential.Case":
    return differential.Case(
        seed=0,
        mode=mode,
        data=drom[address : address + WINDOW_BYTES],
        offset=0,
        index=0,
        wanted=WANTED_BYTES,
    )


def replay(case: "differential.Case") -> list[int]:
    return differential.replay(case)


def streams_of(image: bytes) -> list[tuple[int, int]]:
    reached = cartridges.found_in(image)
    return [] if reached is None else reached[0]


def compare(
    image: bytes,
    driver: Path | str = "",
    ask: Ask = differential.ask,
) -> dict[str, Any]:
    drom = spc7110.data_rom(image)
    found = streams_of(image)
    disagreed = 0
    first: dict[str, Any] | None = None
    for mode, address in found:
        case = case_for(drom, mode, address)
        differed = differential.disagreement(ask(case, driver), replay(case))
        if differed is None:
            continue
        disagreed += 1
        if first is None:
            index, theirs, ours = differed
            first = {"mode": mode, "byte": index, "reference": theirs, "model": ours}
    return {
        "streams": len(found),
        "bytes": len(found) * WANTED_BYTES,
        "disagreed": disagreed,
        "first": first,
    }


def recorded(where: Path | str | None = None) -> dict[str, Any]:
    path = Path(where) if where is not None else ROOT / RECORDED
    if not path.is_file():
        return {}
    found: dict[str, Any] = json.loads(path.read_text())
    return found


def main(
    argv: Sequence[str],
    say: Callable[[str], object] = print,
    ask: Ask = differential.ask,
) -> int:
    rest = list(argv)
    driver = Path(differential.DEFAULT_DRIVER)
    if "--driver" in rest:
        at = rest.index("--driver")
        if at + 1 >= len(rest):
            say("usage: against_cartridges.py <cartridges> <output> [--driver PATH]")
            return 2
        driver = Path(rest[at + 1])
        del rest[at : at + 2]

    if len(rest) < 2:
        say("usage: against_cartridges.py <cartridges> <output> [--driver PATH]")
        return 2

    source, out = Path(rest[0]), Path(rest[1])
    if not source.is_dir():
        say(f"  no such directory: {source}")
        return 2
    if not driver.exists():
        say(f"  no reference driver at {driver}; build it first")
        return 2

    rows = []
    for path in sorted(source.rglob("*")):
        if path.suffix.lower() not in cartridges.SUFFIXES or not path.is_file():
            continue
        image = path.read_bytes()
        if not streams_of(image):
            continue
        found = compare(image, driver, ask)
        rows.append({"name": path.name, **cartridges.digests_of(image), **found})
        say(
            f"  {path.name[:44]:44s} {found['streams']:4d} streams,"
            f" {found['bytes']:,} bytes, {found['disagreed']} disagreed"
        )

    if not rows:
        say(f"  no cartridge whose code names a directory base was found under {source}")
        return 2

    disagreed = sum(one["disagreed"] for one in rows)
    (out / RECORDED).write_text(
        json.dumps(
            {
                "note": (
                    "Both implementations driven with the streams the three cartridges "
                    "actually carry, found by reading each game's own code. Counts only: "
                    "no compressed byte, no decompressed byte and no stream address is "
                    "recorded here."
                ),
                "reference": build.reference(),
                "windowBytes": hex(WINDOW_BYTES),
                "wantedBytes": WANTED_BYTES,
                "readFrom": rows,
                "streams": sum(one["streams"] for one in rows),
                "bytes": sum(one["bytes"] for one in rows),
                "disagreed": disagreed,
            },
            indent=2,
        )
        + "\n"
    )
    say(
        f"  {sum(one['streams'] for one in rows)} real streams,"
        f" {sum(one['bytes'] for one in rows):,} bytes compared, {disagreed} disagreed"
    )
    return 1 if disagreed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
