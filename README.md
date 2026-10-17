# SPC7110 Decompressor

The decompressor of the SPC7110 in Python, all three of its output modes, held byte for byte to the snes9x reference implementation.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-spc7110-python)](https://github.com/gufranco/snes-spc7110-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**3** modes, **200** generated streams over **102,400** bytes and **619** cartridge streams over **316,928** bytes compared against the reference, **0** disagreements, **616** tests, **100%** statement and branch coverage, no dependencies

```python
import spc7110

part = spc7110.Chip("spc7110")
started = part.decompress(bytes(range(256)), "4bpp")

print(started.read(8).hex(" "))
print(started.read(8).hex(" "))
print(started.mode, started.offset, started.held)
```

```
00 00 00 00 00 00 00 15
00 f2 00 1d 00 e2 00 19
2 12 16
```

The example hands the part the 256 byte values in order as a compressed stream and reads 16 bytes of 4bpp output, which is mode 2. Decoding them consumed 12 bytes of the stream. The part decodes ahead into a 64-byte buffer, and 16 decoded bytes are still waiting there.

## Install

| Requirement | Version |
|:--|:--|
| Python | 3.12 or newer |
| git | Any |
| A C++17 compiler, `g++` | Only to build the reference for the differential check |

```bash
git clone https://github.com/gufranco/snes-spc7110-python.git
cd snes-spc7110-python
python3 spc7110/doctor.py
```

The package imports nothing outside the standard library. The doctor checks the machine and the checkout and ends with one line. It runs as a file, so it still reports when the package itself will not import. A checkout where the reference has not been built still passes, and the doctor says the differential check will skip. Paste its whole output into any bug report.

```
  10 checks, nothing to report
```

It exits 0 when every check passed and 1 when any did not.

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/snes-spc7110-python/releases).

## The interface

`spc7110.Chip(model)` builds the part. `model` is required and there is no default. The name is matched without regard to case, hyphens, underscores or spaces, and the part keeps its canonical name on `model`.

| Model | Aliases | Modes |
|:--|:--|:--|
| `spc7110` | `spc-7110`, `epsonspc7110` | `1bpp`, `2bpp`, `4bpp` |

### Calls

| Call | Effect |
|:--|:--|
| `decompress(source, mode, offset=0, index=0)` | Starts a decompression of `source` in `mode` and returns a `Decompressor`. `mode` is a name, an alias or a mode number. `offset` is the byte of `source` to start at. `index` is how many decoded bytes to discard before the first read |
| `reset()` | Returns the part. Nothing survives a decompression, so there is nothing for it to clear |

A `Decompressor` is what `decompress` returns.

| Call or attribute | Meaning |
|:--|:--|
| `read(count)` | Returns the next `count` decoded bytes as `bytes` |
| `take_byte()` | Returns the next decoded byte as an `int` |
| `start(mode, offset, index)` | Restarts the same source in mode number `mode`, clearing every context. Returns the decompressor |
| `mode` | The mode number, or `None` before a start |
| `offset` | The index of the next source byte the decoder will take |
| `held` | Decoded bytes waiting in the 64-byte buffer |
| `contexts` | The 32 probability contexts, each a `Context` |
| `source` | The compressed stream, copied to `bytes` |

The decoder wraps its input. A read past the end of `source` continues from byte 0, because the reference does the same.

```python
import spc7110

part = spc7110.Chip("spc7110")
stream = bytes(range(256))

whole = part.decompress(stream, 1).read(16)
later = part.decompress(stream, 1, offset=0, index=8).read(8)
print(whole[8:] == later)

moved = part.decompress(stream, 1, offset=200).read(4)
wrapped = part.decompress(stream[200:] + stream[:200], 1).read(4)
print(moved == wrapped)

for source, mode in ((stream, "16bpp"), (b"", "2bpp")):
    try:
        part.decompress(source, mode)
    except (spc7110.UnknownMode, spc7110.Empty) as error:
        print(type(error).__name__, error)
```

```
True
True
UnknownMode 16bpp is not a mode this chip has; it has 1bpp, 2bpp, 4bpp
Empty a decompressor needs something to decompress
```

Discarding 8 bytes with `index` gives the same bytes as reading 16 and dropping the first 8. Starting at `offset=200` gives the same output as rotating the stream so byte 200 comes first.

### Errors

| Error | Raised when |
|:--|:--|
| `spc7110.UnknownModelError` | `Chip` is given no model, or a name no part answers to. The message lists the names accepted |
| `spc7110.UnknownMode` | A mode name, alias or number is not one of the three. The message lists the three names |
| `spc7110.Empty` | The source is empty |

All three are defined once, in [`spc7110/errors.py`](spc7110/errors.py).

```python
import spc7110

for name, model in spc7110.MODELS.items():
    print(name, model.aliases, model.modes)

print(spc7110.Chip("SPC-7110").model, spc7110.Chip("epsonspc7110").model)
part = spc7110.Chip("spc7110")
print(part.reset() is part)

for named in (None, "spc7120"):
    try:
        spc7110.Chip(named)
    except spc7110.UnknownModelError as error:
        print(error)
```

```
spc7110 ('spc-7110', 'epsonspc7110') ('1bpp', '2bpp', '4bpp')
spc7110 spc7110
True
no model was named, and this package will not choose one for you. Name one of: spc7110
spc7120 is not a part this package covers; it has spc7110
```

### Module contents

| Name | Content |
|:--|:--|
| `spc7110.MODELS` | The one `Model` record, keyed by canonical name. A `Model` carries `name`, `aliases`, `modes`, `summary` and `build()` |
| `spc7110.MODES` | The three `Mode` records, keyed by name |
| `spc7110.Mode` | A mode record: `number`, `name`, `depth` in bits per pixel, `aliases`, `summary`, and `build(source, offset=0, index=0)`, which starts a `Decompressor` |
| `spc7110.mode_named(mode)` | The `Mode` for a number given as an `int`, or for a name or alias given as a string. A number written as a string, such as `"2"`, raises `UnknownMode` |
| `spc7110.Decompressor(source)` | The decoder itself, built straight from a stream. It produces nothing until `start` names a mode |
| `spc7110.Context` | One probability context: `index`, its row in the evolution table, and `invert`, which symbol it currently takes as the likely one |
| `spc7110.CONTEXTS` | 32, the number of contexts |
| `spc7110.tables` | `EVOLUTION`, 53 rows of probability, next row on each symbol and invert flag, and `MODE2_CONTEXT`, the 32 context transitions of mode 2 |
| `spc7110.__version__` | The installed version |

```python
import spc7110

for mode in spc7110.MODES.values():
    print(mode.number, mode.name, mode.depth, mode.aliases)

for named in (2, "2-Colour", "MODE1"):
    print(named, spc7110.mode_named(named).name)

started = spc7110.Chip("spc7110").decompress(bytes(range(256)), "1bpp")
started.read(64)
print(spc7110.CONTEXTS, len(started.contexts), started.contexts[0])
print(len(spc7110.tables.EVOLUTION), len(spc7110.tables.MODE2_CONTEXT))
```

```
0 1bpp 1 ('mode0', '1bit', '2-colour')
1 2bpp 2 ('mode1', '2bit', '4-colour')
2 4bpp 4 ('mode2', '4bit', '16-colour')
2 4bpp
2-Colour 1bpp
MODE1 2bpp
32 32 <Context row 48 invert 0>
53 32
```

After 64 bytes of 1bpp output, context 0 has moved from row 0 of the evolution table to row 48.

## The three modes

One arithmetic decoder sits under all three. The mode decides how many bits a symbol carries and what happens to it afterwards.

| Mode | Name | Produces | What is different |
|:--|:--|:--|:--|
| 0 | `1bpp` | One bit a pixel | The context comes from the last few decisions, since there are only two colours |
| 1 | `2bpp` | Two bits a pixel | A recency list of the four colours, so a colour used recently costs fewer bits |
| 2 | `4bpp` | Four bits a pixel | The same list over sixteen colours, and a whole 16-byte tile is buffered before it is handed back |

Two things in the decoder look like mistakes and are not.

**A context can swap which symbol it expects.** Each context carries an `invert` flag naming the symbol it takes as the likely one, and the 5 evolution table rows with a set flag toggle it on an unlikely symbol. That is how the coder follows a stream that starts one way and continues another.

**The colour lists are rotated, not sorted.** The colour just decoded goes to the front, then the three reference pixels are moved to the front in turn. The number the coder produces is an index into that list, so the same number means a different colour from one pixel to the next. A model that sorts the list, or keeps it in value order, decodes the first few pixels correctly and then drifts.

## Is it right

No manufacturer document for this part is known, and no recording taken off a real SPC7110 is on this machine. Both of those rungs of evidence, the manufacturer document and the hardware recording, are recorded as empty in [`conformance/hardware.json`](conformance/hardware.json). Every output value rests on agreement with the snes9x decompressor.

```bash
python3 -m conformance.build
python3 -m conformance.differential
```

```
200 streams, 102,400 bytes compared, 0 disagreed
```

The reference is not vendored. `conformance.build` fetches snes9x at the commit pinned in [`conformance/pinned.json`](conformance/pinned.json), cuts the decompressor out of its source between two marker lines the pin names, and compiles it with `g++` against [`conformance/ref/driver.cpp`](conformance/ref/driver.cpp). A source whose markers have moved stops the build. It exits 0 when built, 1 when the compiler fails, and 2 on a bad argument or a fetch that failed.

| Tool | Arguments | Exit codes |
|:--|:--|:--|
| `python3 -m conformance.build` | `--sources DIR`, `--output PATH`, `--pinned PATH`, `--driver-source PATH` | 0 built, 1 compile failed, 2 usage or fetch |
| `python3 -m conformance.differential` | `--seeds N`, default 200, and `--driver PATH` | 0 all agreed, 1 any disagreed, 2 no driver or usage |
| `python3 -m conformance.cartridges` | A directory of cartridges and an output directory | 0 recorded, 2 nothing found or usage |
| `python3 -m conformance.against_cartridges` | A directory of cartridges, an output directory, and `--driver PATH` | 0 all agreed, 1 any disagreed, 2 nothing found, no driver or usage |
| `python3 -m conformance.speed` | None | 0 at or above 10,000 decoded bytes a second, 1 below |

Each generated case is 8,192 bytes from a seeded generator, a mode chosen by the seed, a random start offset, and on odd seeds up to 63 discarded bytes. Both sides decode 512 bytes from the same three settings. The runner prints the first 5 cases that disagree.

### Streams from cartridges

Random bytes drive the decoder through states an encoder never produces. Real streams drive it through the ones an encoder does. Both are checked.

`conformance.cartridges` finds the stream directory in each cartridge by reading the base address the game's own code writes to the chip, not by searching for a pattern. Three cartridges carry 619 streams between them, all three modes reached. [`conformance/cartridges.json`](conformance/cartridges.json) records the counts, the modes, and the entropy of each set of streams against random offsets in the same data. `conformance.against_cartridges` drives every one of those streams through both implementations, and [`conformance/streams.json`](conformance/streams.json) records the result: 619 streams, 316,928 bytes, 0 disagreed. Both records carry the four digests of each cartridge and no byte of any of them. Two implementations agreeing on real data is still two implementations agreeing, and both descend from one reverse engineering.

### Reproducing a disagreement

Every generated case comes from its seed, so a case the runner names can be rebuilt exactly and decoded by the model alone.

```python
from conformance import differential

case = differential.cases(seeds=64)[63]
print(case)
print(bytes(differential.replay(case)[:8]).hex(" "))
```

```
<Case seed 63 mode 0 offset 3448 skip 35>
41 2f 61 31 d1 3d 7e 90
```

The 7 open questions, each with the measurement that would close it, are in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md). Where two sources part, both are kept in [`conformance/divergences.json`](conformance/divergences.json) with what would settle it.

## Working on it

| Need | Where |
|:--|:--|
| Every gate and the order to run them | [CONTRIBUTING.md](CONTRIBUTING.md) |
| The same material for a coding agent | [AGENTS.md](AGENTS.md) |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md) |
| Bug reports | [GitHub Issues](https://github.com/gufranco/snes-spc7110-python/issues) |
| Security reports | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
python3 -m coverage erase
for file in $(find spc7110 conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
python3 -m conformance.speed
```

Each module has a test file beside it, named after it, and each runs on its own. Coverage is a hard gate at 100% statement and branch. The throughput floor runs outside the coverage step, so it measures the decoder and not the tracer.

The tables ship in [`spc7110/tables.py`](spc7110/tables.py). They are coder parameters: how likely a symbol is and which row follows. The decompressor takes its stream as bytes. Where a stream sits in a cartridge is a mapping question, and the chip's mapper and real-time clock are separate packages.

## References

This repository carries no document and no cartridge data.

- snes9x, `spc7110dec.cpp` and `spc7110dec.h` at commit `2971061cf07fdc6fc7d18883edf4e648eb16a6d2`, https://github.com/snes9xgit/snes9x, for every output value. It is fetched and compiled at build time and never redistributed here.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE). The reference implementation is a separate work under its own licence.
