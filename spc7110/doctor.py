"""Look at this machine and say what is actually here, so a report can be believed.

What goes wrong with this package is rarely a defect in it. It is a Python too
old to run it, a reference driver that was never built so the differential check
quietly did nothing, or a disagreement about which commit of which reference the
numbers came from. All of those look the same from outside: the bytes disagree.

So this looks, and prints what it found in a form that can be pasted into an
issue as it stands.

Two rules shape it, and they are the whole point.

Nothing is hidden. A check that fails says what it saw, and a check that itself
throws is caught and reported as what it threw, named by its type. Swallowing
either would leave a report that says everything is fine on a machine where
something is not, which is worse than no report.

Nothing is inferred. Every line is something looked at on this machine just now,
including a stream actually decoded and the first bytes it produced.
"""

import hashlib
import json
import platform
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, override

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spc7110 import decompressor, errors, models  # noqa: E402
from spc7110.version import VERSION  # noqa: E402

PIN = ROOT / "conformance" / "pinned.json"

DRIVER = ROOT / "conformance" / "ref" / "driver"

OLDEST_PYTHON = (3, 12)

KNOWN = bytes(range(256))
"""A stream that is not anybody's data, so the answer can be printed without carrying anything."""

WITNESS = "4bpp"
"""The mode the decode is run in, being the one the cartridges that carry this part use most."""

SHOWN = 8
"""How many decoded bytes are printed, enough to tell two builds apart and too few to be data."""


class Finding:
    """One thing that was looked at, and what was there."""

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        """The one-line form, which is what a reader scans."""
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        """The same, with what to do about it when there is something to do."""
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
    return Finding("spc7110", True, f"version {VERSION}")


def _default_build(name: str, source: bytes | bytearray) -> Any:
    return models.mode_named(name).build(source)


def _mode(name: str, build: Callable[..., Any]) -> "Finding":
    """Whether that mode builds, saying exactly what stopped it if not."""
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


def _known(build: Callable[..., Any]) -> "Finding":
    """What a stream nobody owns decodes to here, printed so two builds can be compared.

    The bytes are the point. A report that says the numbers disagree is not
    actionable until both sides can see the same first few, and this stream is
    counted up from zero rather than taken from a cartridge, so printing what it
    produces carries nothing that belongs to anybody.
    """
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
    """That a decompressor with nothing to decompress is refused.

    A decoder that accepts an empty stream has to invent what it returns, and
    invented bytes are worse than an error because nothing downstream can tell
    them from real ones.
    """
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
    """Which implementation this is held to, and at which commit.

    Two people comparing against two commits of the same reference will disagree
    and both be right. The digest of the file that pins it is what ends that.
    """
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
    """Whether the reference is built, since its absence is silent otherwise.

    The differential check builds somebody else's implementation and decodes the
    same streams through both. That build is not needed to use this package, and
    a machine without it is the normal case rather than a broken one. It is
    reported so that nobody reads a run that skipped as a run that passed.
    """
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
) -> list["Finding"]:
    """Everything worth looking at on this machine, in the order a reader wants it."""
    found = [_python(), _package()]
    found.extend(_mode(name, build) for name in sorted(models.MODES))
    found.append(_known(build))
    found.append(_empty(start))
    found.append(_reference(pin))
    found.append(_driver(driver))
    return found


def report(found: list["Finding"]) -> list[str]:
    """The lines a person pastes into an issue."""
    unwell = [one for one in found if not one.ok]
    lines = [f"spc7110 {VERSION} on {platform.python_version()}, {platform.system()}", ""]
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
