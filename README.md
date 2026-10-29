# SPC7110 Decompressor

The SPC7110 in Python: its decompressor in all three output modes, held byte for byte to snes9x, and the registers a console reaches it through, held to ares.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![ci](https://img.shields.io/github/actions/workflow/status/gufranco/snes-spc7110-python/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/gufranco/snes-spc7110-python?style=flat-square&label=release)](https://github.com/gufranco/snes-spc7110-python/releases/latest)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml)
[![openssf scorecard](https://img.shields.io/ossf-scorecard/github.com/gufranco/snes-spc7110-python?style=flat-square&label=openssf%20scorecard)](https://scorecard.dev/viewer/?uri=github.com/gufranco/snes-spc7110-python)
[![license](https://img.shields.io/github/license/gufranco/snes-spc7110-python?style=flat-square&label=license)](LICENSE)

**3** modes, **200** generated streams over **102,400** bytes and **619** cartridge streams over **316,928** bytes compared against the reference, **619** cartridge streams and **231** register-driven cases read through the registers against ares, **0** disagreements, **833** tests, **100%** statement and branch coverage, no dependencies

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

| Requirement             | Version                                                |
| :---------------------- | :----------------------------------------------------- |
| Python                  | 3.12 or newer                                          |
| git                     | Any                                                    |
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

`spc7110.Chip(model, rom=None, ram=None, seed=7110)` builds the part. `model` is required and there is no default. The name is matched without regard to case, hyphens, underscores or spaces, and the part keeps its canonical name on `model`. `rom` is the whole cartridge image: the first 1 MiB is the program ROM and the rest is the data ROM. Without one the part builds a 2 MiB image of its own, scrambled from `seed`. `ram` is the save RAM as a `bytearray`, kept as handed; without one the part answers nothing at `$6000-$7FFF`. Every register comes up scrambled from `seed`, and none holds a defined value until `reset()`.

| Model     | Aliases                    | Modes                  |
| :-------- | :------------------------- | :--------------------- |
| `spc7110` | `spc-7110`, `epsonspc7110` | `1bpp`, `2bpp`, `4bpp` |

### Calls

| Call                                          | Effect                                                                                                                                                                                                                                   |
| :-------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `decompress(source, mode, offset=0, index=0)` | Starts a decompression of `source` in `mode` and returns a `Decompressor`. `mode` is a name, an alias or a mode number. `offset` is the byte of `source` to start at. `index` is how many decoded bytes to discard before the first read |
| `reset()`                                     | Sets the registers ares sets at power on and drops any operation waiting. Returns the part                                                                                                                                               |
| `read(address)`                               | Reads the 24-bit CPU address. Returns an `int`, or `None` for a register inside `$4800-$483F` that the part does not drive                                                                                                               |
| `write(address, value)`                       | Writes the low 8 bits of `value` to the 24-bit CPU address. A write to ROM changes nothing                                                                                                                                               |
| `tick(clocks=1)`                              | Advances the part `clocks` master clocks, at 21,477,272 a second. A decompression start, a multiply and a divide finish on a later clock. Returns the part                                                                               |

| Attribute | Meaning                                                    |
| :-------- | :--------------------------------------------------------- |
| `rom`     | The cartridge image, as handed or as built                 |
| `program` | The program ROM, the first 1 MiB of `rom`, as `bytes`      |
| `data`    | The data ROM, everything after the first 1 MiB, as `bytes` |
| `ram`     | The save RAM it was handed, or `None`                      |
| `model`   | The canonical model name                                   |

A `Decompressor` is what `decompress` returns.

| Call or attribute            | Meaning                                                                                          |
| :--------------------------- | :----------------------------------------------------------------------------------------------- |
| `read(count)`                | Returns the next `count` decoded bytes as `bytes`                                                |
| `take_byte()`                | Returns the next decoded byte as an `int`                                                        |
| `row()`                      | Decodes one row of eight pixels and returns its 1, 2 or 4 bytes, bypassing the buffer            |
| `start(mode, offset, index)` | Restarts the same source in mode number `mode`, clearing every context. Returns the decompressor |
| `mode`                       | The mode number, or `None` before a start                                                        |
| `offset`                     | The index of the next source byte the decoder will take                                          |
| `held`                       | Decoded bytes waiting in the 64-byte buffer                                                      |
| `contexts`                   | The 32 probability contexts, each a `Context`                                                    |
| `source`                     | The compressed stream, copied to `bytes`, or `b""` when built over a `fetch`                     |
| `fetch`                      | The function it reads each source byte through, given the offset, or `None`                      |

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

| Error                       | Raised when                                                                                                              |
| :-------------------------- | :----------------------------------------------------------------------------------------------------------------------- |
| `spc7110.UnknownModelError` | `Chip` is given no model, or a name no part answers to. The message lists the names accepted                             |
| `spc7110.UnknownMode`       | A mode name, alias or number is not one of the three. The message lists the three names                                  |
| `spc7110.Empty`             | The source is empty, or a cartridge image holds no data ROM after its first 1 MiB, or the save RAM handed holds no bytes |
| `spc7110.OutOfRange`        | `read` or `write` is given an address the part does not decode, or one outside 24 bits                                   |

All four are defined once, in [`spc7110/errors.py`](spc7110/errors.py).

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

| Name                            | Content                                                                                                                                                                                                               |
| :------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `spc7110.MODELS`                | The one `Model` record, keyed by canonical name. A `Model` carries `name`, `aliases`, `modes`, `summary` and `build()`                                                                                                |
| `spc7110.MODES`                 | The three `Mode` records, keyed by name                                                                                                                                                                               |
| `spc7110.Mode`                  | A mode record: `number`, `name`, `depth` in bits per pixel, `aliases`, `summary`, and `build(source, offset=0, index=0)`, which starts a `Decompressor`                                                               |
| `spc7110.mode_named(mode)`      | The `Mode` for a number given as an `int`, or for a name or alias given as a string. A number written as a string, such as `"2"`, raises `UnknownMode`                                                                |
| `spc7110.Decompressor(source)`  | The decoder itself, built straight from a stream. It produces nothing until `start` names a mode. `Decompressor(fetch=f)` reads through `f(offset)` instead, which is how the part reads its data ROM                 |
| `spc7110.PROGRAM_BYTES`         | 1,048,576, the size of the program ROM at the front of a cartridge image                                                                                                                                              |
| `spc7110.data_rom(image)`       | The data ROM of a cartridge image, everything after `PROGRAM_BYTES`, or `b""` when there is nothing after it                                                                                                          |
| `spc7110.directory(drom, base)` | The stream directory at `base`: a list of `(mode, address)` entries read four bytes at a time until a mode the part lacks, an address past the end or an address lower than the last, and the offset where it stopped |
| `spc7110.chip`                  | The constants behind the timing: `MASTER_CLOCK_HZ`, `DECOMPRESSION_CLOCKS`, `MULTIPLY_CLOCKS`, `DIVIDE_CLOCKS` and `UNSET_SEED`                                                                                       |
| `spc7110.Context`               | One probability context: `index`, its row in the evolution table, and `invert`, which symbol it currently takes as the likely one                                                                                     |
| `spc7110.CONTEXTS`              | 32, the number of contexts                                                                                                                                                                                            |
| `spc7110.tables`                | `EVOLUTION`, 53 rows of probability, next row on each symbol and invert flag, and `MODE2_CONTEXT`, the 32 context transitions of mode 2                                                                               |
| `spc7110.__version__`           | The installed version                                                                                                                                                                                                 |

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

| Mode | Name   | Produces          | What is different                                                                                 |
| :--- | :----- | :---------------- | :------------------------------------------------------------------------------------------------ |
| 0    | `1bpp` | One bit a pixel   | The context comes from the last few decisions, since there are only two colours                   |
| 1    | `2bpp` | Two bits a pixel  | A recency list of the four colours, so a colour used recently costs fewer bits                    |
| 2    | `4bpp` | Four bits a pixel | The same list over sixteen colours, and a whole 16-byte tile is buffered before it is handed back |

Two things in the decoder look like mistakes and are not.

**A context can swap which symbol it expects.** Each context carries an `invert` flag naming the symbol it takes as the likely one, and the 5 evolution table rows with a set flag toggle it on an unlikely symbol. That is how the coder follows a stream that starts one way and continues another.

**The colour lists are rotated, not sorted.** The colour just decoded goes to the front, then the three reference pixels are moved to the front in turn. The number the coder produces is an index into that list, so the same number means a different colour from one pixel to the next. A model that sorts the list, or keeps it in value order, decodes the first few pixels correctly and then drifts.

## Driving it through its registers

A game never hands the part a stream. It writes the directory base to `$4801-$4803`, an index to `$4804`, starts with `$4806`, waits for bit 7 of `$480C`, and reads `$4800`. The part reads the directory entry and the stream through its own data-ROM mapping, so a stream never runs off the end of anything.

```python
import random

import spc7110

data = bytearray(random.Random(1).randbytes(0x10000))
data[8:12] = bytes((1, 0x00, 0x20, 0x00))
chip = spc7110.Chip("spc7110", rom=bytes(spc7110.PROGRAM_BYTES) + data).reset()

for register, value in ((0x4801, 0x08), (0x4802, 0x00), (0x4803, 0x00), (0x4804, 0x00)):
    chip.write(register, value)
chip.write(0x4806, 0x00)

print(hex(chip.tick(20).read(0x480C)), hex(chip.tick(1).read(0x480C)))
print(bytes(chip.read(0x4800) for _ in range(16)).hex(" "))
print(chip.read(0xD00000) == data[0], chip.read(0x581234))
```

```
0x0 0x80
46 a0 43 65 12 74 46 a1 97 b9 73 99 33 92 1b 32
True 0
```

The directory entry at `$000008` names mode 1 at `$002000`. The start is ready on the 21st master clock: one to notice it and the 20 ares charges. Bank `$D0` reads the data ROM's first megabyte, because `$4831` is 0 after reset, and bank `$58` answers as `$4808`, which reads 0.

| Registers     | Unit           | What they do                                                                                                                                  |
| :------------ | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- |
| `$4800-$480C` | Decompression  | Directory base, index, seek, stride, length counter, control and status; `$4800` hands out the decoded bytes a tile at a time                 |
| `$4810-$481A` | Data port      | Reads the data ROM at an offset plus an optional adjust, stepping by one or by a stride, signed or not                                        |
| `$4820-$482F` | Arithmetic     | 16 by 16 multiply and 32 by 16 divide, signed or not; 30 and 40 master clocks, with bit 7 of `$482F` busy until the result lands              |
| `$4830-$4834` | Memory control | Save RAM enable in bit 7 of `$4830`, the data-ROM megabyte banks `$D0`, `$E0` and `$F0` show, the data ROM's size and the second program bank |

```python
import spc7110

chip = spc7110.Chip("spc7110").reset()
for register, value in ((0x4820, 0x34), (0x4821, 0x12), (0x4824, 0x78), (0x4825, 0x56)):
    chip.write(register, value)

print(hex(chip.read(0x482F)), hex(chip.tick(31).read(0x482F)))
print(bytes(chip.read(0x4828 + at) for at in range(4))[::-1].hex())

for address in (0x7E0000, 0x004840):
    try:
        chip.read(address)
    except spc7110.OutOfRange as error:
        print(error)
```

```
0x81 0x1
06260060
0x7e0000 is not an address the SPC7110 answers
0x004840 is not an address the SPC7110 answers
```

The multiply reads its operands when it finishes, so a write to `$4820` during the 30 clocks changes the product. `$4840-$4842` is the real-time clock beside the part, which [snes-rtc-python](https://github.com/gufranco/snes-rtc-python) models, so it is refused here. Where ares and snes9x disagree about a register, the part follows ares and [`conformance/divergences.json`](conformance/divergences.json) carries both.

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

| Tool                                        | Arguments                                                                 | Exit codes                                                         |
| :------------------------------------------ | :------------------------------------------------------------------------ | :----------------------------------------------------------------- |
| `python3 -m conformance.build`              | `--sources DIR`, `--output PATH`, `--pinned PATH`, `--driver-source PATH` | 0 built, 1 compile failed, 2 usage or fetch                        |
| `python3 -m conformance.differential`       | `--seeds N`, default 200, and `--driver PATH`                             | 0 all agreed, 1 any disagreed, 2 no driver or usage                |
| `python3 -m conformance.cartridges`         | A directory of cartridges and an output directory                         | 0 recorded, 2 nothing found or usage                               |
| `python3 -m conformance.against_cartridges` | A directory of cartridges, an output directory, and `--driver PATH`       | 0 all agreed, 1 any disagreed, 2 nothing found, no driver or usage |
| `python3 -m conformance.speed`              | None                                                                      | 0 at or above 10,000 decoded bytes a second, 1 below               |

Each generated case is 8,192 bytes from a seeded generator, a mode chosen by the seed, a random start offset, and on odd seeds up to 63 discarded bytes. Both sides decode 512 bytes from the same three settings. The runner prints the first 5 cases that disagree.

### Through the registers, against ares

The register interface is held to ares at commit `9408cb43d4948fc3ea6e152a307a34348df3fe04`. Its decompressor, compiled unchanged inside a harness that repeats its tile logic, was driven beside `spc7110.Chip` through the registers over 619 cartridge streams and 231 register-driven cases with random seeks and strides: 375,040 bytes, 0 disagreed. [`conformance/hardware.json`](conformance/hardware.json) records the run under `registerInterface`. The harness is not shipped, so this is a dated measurement rather than a check the pipeline repeats, and ares, bsnes and snes9x all descend from one reverse engineering.

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

The 11 open questions, each with the measurement that would close it, are in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md). Where two sources part, both are kept in [`conformance/divergences.json`](conformance/divergences.json) with what would settle it.

## Working on it

| Need                                                            | Where                                                                   |
| :-------------------------------------------------------------- | :---------------------------------------------------------------------- |
| Every gate and the order to run them                            | [CONTRIBUTING.md](CONTRIBUTING.md)                                      |
| The same material for a coding agent                            | [AGENTS.md](AGENTS.md)                                                  |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md)                                                  |
| Bug reports                                                     | [GitHub Issues](https://github.com/gufranco/snes-spc7110-python/issues) |
| Security reports                                                | [SECURITY.md](SECURITY.md)                                              |

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

The tables ship in [`spc7110/tables.py`](spc7110/tables.py). They are coder parameters: how likely a symbol is and which row follows. The part reads streams through the data-ROM mapping its own registers set. The real-time clock beside it is a separate package.

## References

This repository carries no document and no cartridge data.

- snes9x, `spc7110dec.cpp` and `spc7110dec.h` at commit `2971061cf07fdc6fc7d18883edf4e648eb16a6d2`, https://github.com/snes9xgit/snes9x, for every output value. It is fetched and compiled at build time and never redistributed here.
- ares, `ares/sfc/coprocessor/spc7110` at commit `9408cb43d4948fc3ea6e152a307a34348df3fe04`, https://github.com/ares-emulator/ares, for the register interface, its timing and the bank mapping. Facts only; no code is taken.
- snes9x, `spc7110emu.cpp` and `spc7110.cpp` at commit `1bcc369e89f08243e0a462882fb1f3e42e51de3a`, read as the second witness for the register interface.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE). The reference implementation is a separate work under its own licence.
