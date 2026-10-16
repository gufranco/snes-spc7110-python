import hashlib
import json
import platform
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, override

ROOT = Path(__file__).resolve().parent.parent


def _reachable(root: Path = ROOT, path: list[str] | None = None) -> bool:
    where = sys.path if path is None else path
    if str(root) in where:
        return False
    where.insert(0, str(root))
    return True


_reachable()

from spc7110 import decompressor, environment, errors, models  # noqa: E402
from spc7110.version import VERSION  # noqa: E402

PIN = ROOT / "conformance" / "pinned.json"

DRIVER = ROOT / "conformance" / "ref" / "driver"

OLDEST_PYTHON = (3, 12)

KNOWN = bytes(range(256))

WITNESS = "4bpp"

SHOWN = 8


class Finding:
    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _python() -> "Finding":
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _package() -> "Finding":
    return Finding("snes-spc7110-python", True, f"version {VERSION}")


def _default_build(name: str, source: bytes | bytearray) -> Any:
    return models.mode_named(name).build(source)


def _mode(name: str, build: Callable[..., Any]) -> "Finding":
    try:
        build(name, KNOWN)
    except Exception as trouble:
        return Finding(
            name,
            False,
            f"{type(trouble).__name__}: {trouble}",
            "this is the decoder failing to start rather than anything to do with"
            " a reference; the line above is what it said",
        )
    described = models.mode_named(name)
    return Finding(name, True, f"mode {described.number}, {described.depth} bits per pixel")


def _chip(name: str, build: Callable[[str], Any]) -> "Finding":
    try:
        chip = build(name)
        chip.reset()
    except Exception as trouble:
        return Finding(
            name,
            False,
            f"{type(trouble).__name__}: {trouble}",
            "this is the part failing rather than anything to do with a reference;"
            " the line above is what it said",
        )
    return Finding(name, True, f"model {chip.model}, resets and carries nothing across it")


def _default_chip(name: str) -> Any:
    return models.lookup(name).build()


def _known(build: Callable[..., Any]) -> "Finding":
    try:
        chip = build(WITNESS, KNOWN)
        produced = bytes(chip.take_byte() for _ in range(SHOWN))
    except Exception as trouble:
        return Finding(
            "known stream",
            False,
            f"{type(trouble).__name__}: {trouble}",
            "decoding a stream that is here failed, which is itself the finding",
        )
    return Finding(
        "known stream",
        True,
        f"{WITNESS} of 0..255 begins {' '.join(f'{one:02x}' for one in produced)}",
    )


def _empty(build: Callable[..., Any]) -> "Finding":
    try:
        build(b"")
    except errors.Empty:
        return Finding("empty stream", True, "refused")
    except Exception as trouble:
        return Finding(
            "empty stream",
            False,
            f"{type(trouble).__name__}: {trouble}",
            "an empty source should raise Empty; this raised something else",
        )
    return Finding(
        "empty stream",
        False,
        "accepted, and whatever it returns came from nowhere",
        "bytes that came from nowhere cannot be told from real ones",
    )


def _reference(where: Path | str) -> "Finding":
    try:
        raw = Path(where).read_bytes()
    except OSError as trouble:
        return Finding(
            "reference",
            False,
            f"could not be read: {trouble}",
            "the file that pins which implementation this is held to is missing from conformance/",
        )
    digest = hashlib.sha256(raw).hexdigest()
    try:
        held = json.loads(raw)
    except ValueError as trouble:
        return Finding(
            "reference",
            False,
            f"is not readable as JSON: {trouble}, sha256 {digest}",
            "the file is here and damaged, which is worse than absent",
        )
    named = held.get("reference") or {}
    if not named:
        return Finding(
            "reference",
            False,
            f"names no implementation, sha256 {digest}",
            "a pin that names nothing pins nothing",
        )
    return Finding(
        "reference",
        True,
        f"{named.get('name', 'not stated')} at {named.get('commit', 'no commit')}, sha256 {digest}",
    )


def _driver(where: Path | str) -> "Finding":
    found = Path(where).exists()
    return Finding(
        "reference driver",
        True,
        "built and here"
        if found
        else "not built, so the differential check will skip rather than run",
    )


def examine(
    build: Callable[..., Any] = _default_build,
    pin: Path | str = PIN,
    driver: Path | str = DRIVER,
    start: Callable[..., Any] = decompressor.Decompressor,
    chip: Callable[[str], Any] = _default_chip,
) -> list["Finding"]:
    found = [_python(), _package()]
    found.extend(_chip(name, chip) for name in sorted(models.MODELS))
    found.extend(_mode(name, build) for name in sorted(models.MODES))
    found.append(_known(build))
    found.append(_empty(start))
    found.append(_reference(pin))
    found.append(_driver(driver))
    return found


def report(found: list["Finding"]) -> list[str]:
    unwell = [one for one in found if not one.ok]
    lines = [f"spc7110 {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., list["Finding"]] = examine,
    say: Callable[[str], None] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
