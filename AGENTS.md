# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this
family carries, byte for byte, and it decides most questions before they are
asked. What follows is only what is true of this member. [README.md](README.md)
is the document written for a person.

## What this project is, in one paragraph

The SPC7110's decompressor, all three of its modes. A caller hands it a stream
and reads bytes off what comes back. No manufacturer document for this part is
known to exist, so the top two rungs of the authority ladder are both empty and a
reference implementation is carrying the package: 200 streams of random bytes
across three modes, 102,400 bytes compared, with the reference pinned by commit
and by three extracts of its source so a check cannot start comparing against
something else without the pin changing first.

## The interface a caller drives

The part answers a request. There is no clock, no instruction to step through and
no cycle count to hand back, so none of the family's clocked interface appears
here.

`Chip(model)` builds one.

| Call | What it does |
|:--|:--|
| `decompress(source, mode, offset, index)` | Start a decompression, returning a `Decompressor` |
| `read(count)` | Take that many bytes off a started decompression |
| `reset()` | Nothing, because nothing survives a decompression. Handed back for chaining |

The mode is not a model. Three modes exist and one chip does all three, so the
mode is an argument to `decompress` rather than a name in the part catalogue.
`describe` answers about modes and `describe_part` answers about parts, kept
apart because one function that guessed which was meant would answer the wrong
one for a caller who wrote a mode number.

## The authority ladder

1. **A manufacturer document**, of which there is none.
2. **A recording taken off a real SPC7110**, of which there is none on this
   machine.
3. **The reference implementation**, which is where all of this comes from.

The record names both empty rungs rather than promoting the third.

## What is settled and what is not

**Not settled: 7 things**, each in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with the measurement that would close it.
The honest summary is that every output value rests on agreement between two
implementations.

Settled: that all three modes agree with the reference over 102,400 bytes, and
that the comparison is against what it says it is, because the pin covers the
source and not only the commit.

## The pin is the point

[`conformance/pinned.json`](conformance/pinned.json) fixes the reference by
commit and by three extracts of its source. A change that updates the commit
without re-reading the extracts has removed the only thing that makes the
comparison trustworthy.

## Every gate, in the order to run them

```bash
ruff format --check .
ruff check .
mypy
pnpm run format:check
python3 -m coverage erase
for file in $(find spc7110 conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

Then the throughput floor, which runs outside the coverage step because a tracer
costs about ten times what the model does:

```bash
python3 -m conformance.speed
```

The differential run needs the reference, which is built rather than vendored and
needs a C++ compiler:

```bash
python3 -m conformance.build
python3 -m conformance.differential
```

And the doctor, which reports what it could not check rather than passing
quietly:

```bash
python3 spc7110/doctor.py
```

Everything under `conformance/` runs as a module. Run as a script, its own
directory goes on the import path and a file there shadows any standard library
module of the same name. `doctor.py` is the exception and runs as a file on
purpose, so that it still runs when the package itself will not import, which is
the case it exists for.

## Conventions that are not negotiable

- Python only, standard library only, no dependencies.
- No comments in source. Reasoning goes in docstrings, and a step that would need
  a comment is a step that should be a named function.
- Tests sit beside the module they cover as `<module>.test.py`. Arrange, blank
  line, one act, blank line, assert, with no section labels.
- 100% statement and branch coverage, enforced. `mypy` at strict, with every
  optional error class on.
- Everything a caller can catch is defined once, in `spc7110/errors.py`, and
  imported from there.
- A check nobody has seen fail is not known to work. Drive every new check
  against input that should fail it before keeping it.

## Layout

```text
spc7110/
  __init__.py       the package, and the part chosen at construction
  decompressor.py   the arithmetic decoder and its context table
  models.py         the three modes, and the one part
  tables.py         the evolution table the contexts move through
  errors.py         everything this package raises, in one place
  doctor.py         what is actually on this machine, printed for a bug report
  version.py        rewritten by the release job and by nothing else
conformance/
  family.test.py    the family standard, held to this repository
  pinned.json       the reference, by commit and by source extract
  build.py          building the reference from that pin
  differential.py   200 streams across three modes, compared byte for byte
  ref/driver.cpp    the harness this repository owns, around the pinned source
  hardware.json     what this package asserts, and where each assertion comes from
  divergences.json  where sources part, and what would settle each
  speed.py          the throughput floor
```

## Things that will bite you

- **`UnknownMode` used to be defined twice**, once beside the catalogue and once
  beside the decoder. An `except` written against one sailed straight through the
  other. There is one definition now, in `errors.py`, and adding a second is the
  failure the family standard exists to prevent.
- **The decoder wraps its input.** A read that runs off the end starts again at
  the beginning rather than refusing, because that is what the reference does.
  Nobody knows what the silicon does.
- **`describe` and `describe_part` answer different questions.** One takes a mode
  by name or number, the other takes a part by name.
- **The reference is not vendored.** It is built from a pinned commit, and a
  machine without a C++ compiler skips that step and says so.

## Before calling anything finished

Every gate above, green, with output shown. A claim without a run behind it is
not evidence. If a check was skipped because a file is not on this machine, say
which check and why rather than reporting a pass.

## What a change is expected to leave behind

A test that fails without the change and passes with it. An entry in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) if it turned a settled thing into an open
one, or removed one.
