<div align="center">

<h1>SPC7110 Decompressor</h1>

<strong>All three modes of the SPC7110's decompressor, held to the chip's own reference implementation.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml)
[![Conformance](https://img.shields.io/badge/conformance-102%2C400%20bytes-brightgreen)](#how-this-is-checked)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#tests)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
  <a href="#quick-start">Quick start</a> &nbsp;|&nbsp;
  <a href="#the-three-modes">The modes</a> &nbsp;|&nbsp;
  <a href="#how-this-is-checked">How this is checked</a> &nbsp;|&nbsp;
  <a href="#why-random-bytes-are-a-real-test">Why random bytes</a> &nbsp;|&nbsp;
  <a href="https://github.com/gufranco/snes-spc7110-python/issues">Issues</a>
</p>

**3** modes · **200** streams compared against the reference · **102,400** bytes, **0** disagreements · **398** tests · **100%** statement and branch coverage · no dependencies

```python
from spc7110 import Chip

stream = bytes(range(64))

started = Chip().decompress(stream, "4bpp")
len(started.read(64))

# 64
```

## Install
```bash
pip install git+https://github.com/gufranco/snes-spc7110-python.git
```

Python 3.12 or newer. Nothing else.

## The interface
Everything a caller touches. Nothing else is public.

| Name | What it is |
|:--|:--|
| `Chip(model)` | A part of that model |
| `chip.decompress(source, mode, offset, index)` | Start a decompression in that mode |
| `Decompressor` | What that hands back: `read(count)` takes bytes off it |
| `describe(mode)`, `MODES`, `Mode` | The mode catalogue, by name or by number |
| `describe_part(model)`, `MODELS`, `Model` | The part catalogue |
| `Context`, `CONTEXTS` | The probability contexts, and how many there are |
| `UnknownModelError`, `UnknownMode`, `Empty` | Everything a caller can catch |

`Chip` takes the model first, which is the argument every member of the family
takes first. The mode is not a model: three modes exist and one chip does all
three, so the mode is an argument to `decompress` rather than a name in the part
catalogue.

The one part answers to more than one name, so a caller writing what a board
silkscreen calls it gets the part rather than a refusal:

| Name | Also answers to |
|:--|:--|
| `spc7110` | `spc-7110`, `epsonspc7110` |

```python
from spc7110 import Chip

chip = Chip("spc7110")
started = chip.decompress(bytes(64), "4bpp")

len(started.read(32))

# 32
```

A part name no chip answers to is refused rather than quietly building the only
one there is:

```python
from spc7110 import Chip, UnknownModelError

try:
    Chip("spc7120")
except UnknownModelError as refused:
    print(str(refused).split(";")[0])

# spc7120 is not a part this package covers
```

And so is a mode the chip does not have:

```python
from spc7110 import Chip, UnknownMode

try:
    Chip().decompress(bytes(64), "16bpp")
except UnknownMode as refused:
    print(type(refused).__name__)

# UnknownMode
```

## The three modes
There is one arithmetic decoder underneath. The mode decides how many bits a
symbol carries and what happens to it afterwards.

| Mode | Name | Produces | What is different |
|:-----|:-----|:---------|:------------------|
| 0 | `1bpp` | One bit a pixel | Context comes from the last few decisions, since there are only two colours |
| 1 | `2bpp` | Two bits a pixel | Keeps a recency list of the four colours, so a colour used recently costs fewer bits |
| 2 | `4bpp` | Four bits a pixel | The same over sixteen colours, and a whole tile is buffered before it is handed back |

```python
from spc7110 import describe

describe("2bpp").number  # 1
describe(2).name  # '4bpp'
```

Two things in the decoder look like mistakes and are not.

**A context can decide it had the symbols backwards.** Each one carries a flag
saying which of the two symbols it currently believes is the likely one, and some
rows of the table are allowed to flip it. That is how the coder follows a stream
that starts one way and continues another.

**The colour lists are rotated, not sorted.** The colour just decoded goes to the
front, then the three reference pixels are moved to the front in turn. The number
the coder produces is an index into that list, so the same number means a
different colour from one pixel to the next. A model that sorts, or that keeps
the list in value order, decodes the first few pixels correctly and then drifts.

## Is it right
Every mode is compared against the implementation every emulator already agrees
with, over streams generated from a seed.

| Measure | Value |
|:--------|:------|
| Streams | 200 |
| Bytes compared | 102,400 |
| Disagreements | 0 |
| Reference | [snes9x](https://github.com/snes9xgit/snes9x), pinned by commit |

```bash
python -m conformance.build
python -m conformance.differential
```

```
200 streams, 102,400 bytes compared, 0 disagreed
```

Each case names a mode, a place to start in the stream, and how much output to
discard before reading. Both sides get the same three.

The reference is not vendored. The build fetches it at a pinned commit and lifts
the decompressor out of the file it lives in, using markers that come from the
pin, so a file whose text has moved fails loudly rather than yielding something
else.

### Why random bytes are a real test

A decompressor needs something to decompress, and the streams this chip was made
for are cartridge graphics. Those are the protected work and they do not ship
here, so the streams are generated from a seed instead.

That is not the weaker choice it sounds like. An arithmetic decoder does not know
or care whether its input was ever compressed. It reads bits, narrows a span, and
produces symbols. Arbitrary bytes drive it through the same state machine real
data drives it through, and they drive it through parts real data never reaches,
because a stream nobody encoded has no reason to stay on the paths an encoder
would have used.

What a real stream would add is confidence that the output is a picture. What
these streams add is confidence that the decoder is the same decoder, byte for
byte, on inputs an encoder would never produce. The second is the one a model
needs.

If you own a cartridge, the same runner takes your own stream and compares it the
same way. That check stays on your machine, which is why the shipped one is built
this way.

**Open questions** are listed with the measurement that would close each one:
[`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md). Where two sources part, both are kept
in [`conformance/divergences.json`](conformance/divergences.json) with what would
settle it.

## Working on it
```bash
python -m coverage erase
for file in $(find spc7110 conformance -name '*.test.py' | sort); do
  python -m coverage run -a "$file"
done
python -m coverage report
```

`python3 spc7110/doctor.py` says what is actually on this machine. It is run as a file rather than with `-m` so that it still runs when the package itself will not import, which is the case it exists for.

[`AGENTS.md`](AGENTS.md) is the document for an agent working here. [`FAMILY.md`](FAMILY.md) is the standard this repository shares with the rest of the family, kept identical in every member.

### Layout

| File | Holds |
|:-----|:------|
| [`spc7110/decompressor.py`](spc7110/decompressor.py) | The arithmetic decoder and its three modes |
| [`spc7110/tables.py`](spc7110/tables.py) | The evolution table, the context table, and the plane shuffles |
| [`spc7110/models.py`](spc7110/models.py) | The mode named at construction |
| [`conformance/differential.py`](conformance/differential.py) | The runner that holds it to the reference |
| [`conformance/build.py`](conformance/build.py) | Fetches the pinned reference and lifts the chip out of it |

### For contributors and reviewers

### Running the tests

Each module has its test file beside it, named after it.

```bash
python -m coverage erase
for file in $(find spc7110 conformance -name '*.test.py' | sort); do
  python -m coverage run -a "$file"
done
python -m coverage report
```

Coverage is a gate, not a report: the build fails below 100% of statements and
branches.

### Reproducing a disagreement

Every case comes from a seed and the runner prints the seed of any that
disagreed, so it can be regenerated exactly:

```python
from conformance import differential

case = differential.cases(seeds=64)[63]
differential.replay(case)
```

### Project conventions

| Convention | Source |
|:-----------|:-------|
| Commit format | [Conventional Commits](https://www.conventionalcommits.org/) |
| Format and lint | [ruff](https://docs.astral.sh/ruff/), configured in [pyproject.toml](pyproject.toml) |
| Releases | [semantic-release](https://semantic-release.gitbook.io/), from the commit history |
| Test naming | A sentence stating the behaviour, not the function name |

### Non-obvious decisions

- The tables are shipped. They are coder parameters, saying how likely a symbol
  is and which row follows, which describes an algorithm rather than anything the
  cartridge draws.
- The decompressor takes its compressed stream as bytes rather than reading a
  cartridge. Where in a cartridge that stream sits is a mapping question, and a
  different one from how it decodes.
- The clock the same cartridge carries is not here. It is a separate part with a
  separate protocol and lives in its own package.
- The buffer refills half of itself at a time rather than a byte at a time,
  because the modes produce whole bytes or whole tiles and cannot stop partway.

### When something is wrong

```bash
python3 -m spc7110.doctor
```

It looks at this machine and prints what is actually there, and every line is
something it looked at just now rather than something that ought to be true. A
check that fails says what it saw. A check that itself throws is reported as what
it threw rather than taking the report down with it. Paste all of it into an
issue.

### Contributing

Measurements first. [CONTRIBUTING.md](CONTRIBUTING.md) has the gates a change is
expected to pass, [SECURITY.md](SECURITY.md) says what belongs in a private
report, and the [Code of Conduct](CODE_OF_CONDUCT.md) applies wherever this
project is discussed.

Never attach a copyrighted file, and never link to somewhere one can be
downloaded. A digest identifies a file without carrying it.

## References
This repository carries no documents and no cartridge data. Nobody published a
document for this part: the top rung of the authority ladder is empty here and
[`conformance/hardware.json`](conformance/hardware.json) says so rather than
promoting the rung below it.

| Source | Used for |
|:-------|:---------|
| The reference decompressor, pinned by commit and by extract in [`conformance/pinned.json`](conformance/pinned.json) | Every output value, which nothing else on this machine can produce |

The reference is pinned by extract as well as by commit, so a check cannot start
comparing against a different implementation without the pin changing first.

## Citing this
[CITATION.cff](CITATION.cff) is kept in step with the released version by the
same script that stamps the package, so the version it names is the version that
shipped.

## License
[MIT](LICENSE).

The reference implementation is a separate work under its own licence, fetched at
build time and never redistributed here.
