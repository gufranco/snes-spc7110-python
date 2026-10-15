import random
import struct
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spc7110 import decompressor

USAGE = "usage: differential.py [--seeds N] [--driver PATH]"

DEFAULT_DRIVER = str(Path(__file__).resolve().parent / "ref" / "driver")

DRIVER_TIMEOUT = 300

SEEDS = 200

MODES = decompressor.MODES

STREAM_BYTES = 8192

WANTED_BYTES = 512

MAX_SKIPPED = 64

REPORT_LIMIT = 5


class Usage(Exception):
    pass


class Options:
    def __init__(self, seeds: int = SEEDS, driver: Path | str = DEFAULT_DRIVER) -> None:
        self.seeds = seeds
        self.driver = driver


class Case:
    def __init__(
        self,
        seed: int,
        mode: int,
        data: bytes,
        offset: int,
        index: int,
        wanted: int,
    ) -> None:
        self.seed = seed
        self.mode = mode
        self.data = data
        self.offset = offset
        self.index = index
        self.wanted = wanted

    @override
    def __repr__(self) -> str:
        return f"<Case seed {self.seed} mode {self.mode} offset {self.offset} skip {self.index}>"


def cases(seeds: int = SEEDS) -> list["Case"]:
    found = []
    for seed in range(seeds):
        source = random.Random(seed)
        data = bytes(source.randrange(256) for _ in range(STREAM_BYTES))
        found.append(
            Case(
                seed=seed,
                mode=MODES[seed % len(MODES)],
                data=data,
                offset=source.randrange(len(data)),
                index=source.randrange(MAX_SKIPPED) if seed % 2 else 0,
                wanted=WANTED_BYTES,
            )
        )
    return found


def replay(case: "Case") -> list[int]:
    chip = decompressor.Decompressor(case.data)
    chip.start(mode=case.mode, offset=case.offset, index=case.index)
    return list(chip.read(case.wanted))


def ask(case: "Case", driver: Path | str) -> list[int]:
    done = subprocess.run(
        [driver, str(case.mode), str(case.offset), str(case.index)],
        input=struct.pack("<I", case.wanted) + case.data,
        capture_output=True,
        check=False,
        timeout=DRIVER_TIMEOUT,
    )
    if done.returncode:
        raise Usage(f"the reference driver failed: {done.stderr.decode(errors='replace').strip()}")
    return [int(line, 16) for line in done.stdout.split()]


def disagreement(
    expected: Sequence[int], actual: Sequence[int]
) -> tuple[int, int | None, int | None] | None:
    for index in range(max(len(expected), len(actual))):
        theirs = expected[index] if index < len(expected) else None
        ours = actual[index] if index < len(actual) else None
        if theirs != ours:
            return index, theirs, ours
    return None


def options(argv: Sequence[str]) -> "Options":
    chosen = Options()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item not in ("--seeds", "--driver"):
            raise Usage(USAGE)
        if not rest:
            raise Usage(USAGE)
        value = rest.pop(0)
        if item == "--seeds":
            chosen.seeds = int(value)
        else:
            chosen.driver = value
    return chosen


def run(argv: Sequence[str]) -> int:
    chosen = options(argv)
    if not Path(chosen.driver).exists():
        print(f"no reference driver at {chosen.driver}; build it first")
        return 2

    checked = 0
    failed = 0
    for case in cases(chosen.seeds):
        found = disagreement(ask(case, chosen.driver), replay(case))
        checked += case.wanted
        if found is None:
            continue
        failed += 1
        index, theirs, ours = found
        if failed <= REPORT_LIMIT:
            print(f"FAIL {case} at byte {index}: reference {theirs}, model {ours}")

    print(f"{chosen.seeds} streams, {checked:,} bytes compared, {failed} disagreed")
    return 1 if failed else 0


def main(argv: Sequence[str]) -> int:
    try:
        return run(argv)
    except Usage as error:
        print(error)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
