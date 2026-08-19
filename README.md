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

**3** modes · **200** streams compared against the reference · **102,400** bytes, **0** disagreements · **107** tests · **100%** statement and branch coverage

```python
from spc7110 import describe

chip = describe("4bpp").build(stream)
chip.read(64)
```

## Quick start

### Prerequisites

| Tool | Version | Install |
|:-----|:--------|:--------|
| Python | 3.12 or newer | [python.org](https://www.python.org/downloads/) |
| A C++ compiler | any recent | only for running the conformance comparison |

### Install

```bash
pip install git+https://github.com/gufranco/snes-spc7110-python.git
```

### Decompress something

```python
from spc7110 import Decompressor

chip = Decompressor(stream)
chip.start(mode=2, offset=0, index=0)
tile = chip.read(32)
```

`offset` is where in the compressed stream to begin. `index` is how many output
bytes to throw away first, which is how the cartridge reaches the middle of a
block without decompressing it into memory.

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

## How this is checked

Every mode is compared against the implementation every emulator already agrees
with, over streams generated from a seed.

| Measure | Value |
|:--------|:------|
| Streams | 200 |
| Bytes compared | 102,400 |
| Disagreements | 0 |
| Reference | [snes9x](https://github.com/snes9xgit/snes9x), pinned by commit |

```bash
python conformance/build.py
python conformance/differential.py
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

## Why random bytes are a real test

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

## Layout

| File | Holds |
|:-----|:------|
| [`spc7110/decompressor.py`](spc7110/decompressor.py) | The arithmetic decoder and its three modes |
| [`spc7110/tables.py`](spc7110/tables.py) | The evolution table, the context table, and the plane shuffles |
| [`spc7110/models.py`](spc7110/models.py) | The mode named at construction |
| [`conformance/differential.py`](conformance/differential.py) | The runner that holds it to the reference |
| [`conformance/build.py`](conformance/build.py) | Fetches the pinned reference and lifts the chip out of it |

## For contributors and reviewers

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
import differential

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

## Licence

[MIT](LICENSE).

The reference implementation is a separate work under its own licence, fetched at
build time and never redistributed here.
