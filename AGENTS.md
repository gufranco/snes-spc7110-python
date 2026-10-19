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

| Call                                      | What it does                                                                |
| :---------------------------------------- | :-------------------------------------------------------------------------- |
| `decompress(source, mode, offset, index)` | Start a decompression, returning a `Decompressor`                           |
| `read(count)`                             | Take that many bytes off a started decompression                            |
| `reset()`                                 | Nothing, because nothing survives a decompression. Handed back for chaining |

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
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm run format:check
uvx yamllint==1.38.0 --strict .
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for file in $(find spc7110 conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$file"
done
"${cov[@]}" report
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
- No comments in source, and a docstring counts as one. A step that would need
  a comment is a step that should be a named function.
- Tests sit beside the module they cover as `<module>.test.py`. Arrange, act
  and assert, each block opened by its bare marker.
- 100% statement and branch coverage, enforced. `mypy` at strict, with every
  optional error class on.
- Everything a caller can catch is defined once, in `spc7110/errors.py`, and
  imported from there.
- A check nobody has seen fail is not known to work. Drive every new check
  against input that should fail it before keeping it.

The linter's ignores in [`pyproject.toml`](pyproject.toml) carry no comments, so
their reasons live here, beside those of the coverage exclusions:

- `N818`: three exceptions are control flow signals rather than failures, named
  the way CPython names `StopIteration`. Those that report a failure end in
  `Error`.
- `BLE001` and `T201` in `environment.py`: it reports what a machine is, so a
  check that throws becomes a line in the report rather than ending the run.
- `N999` in tests: a test file is named after the module it covers, with a dot,
  so a module and its tests are read together.
- `T201` in `conformance/`: these are command line tools and printing is their
  output. A logger would put a level and a timestamp in front of a report meant
  for a person.
- `BLE001` and `T201` in the doctor: it must survive whatever a check throws and
  report it, because a narrower catch would let a traceback take the rest of the
  report with it.
- Every optional `mypy` error class is on because the errors that matter in a
  model of hardware are a width, a mask or a `None` crossing a boundary.
- The `__main__` guard is excluded from coverage: it hands argv to a tested
  function, and importing the module to cover it would run the tool.
- The doctor's `sys.path` guard is excluded: a suite that imports the doctor has
  already put the repository on the path, so no test can take that branch.
- `if TYPE_CHECKING:` is excluded: it never runs, and Python 3.14 drops it before
  coverage sees it while earlier versions do not.
- A lone ellipsis and a signature ending in one are excluded: a protocol method
  has no body to run, and the same version split applies.
- `@unittest\.skipUnless\(CLOCKED,` in the coverage exclusions: this member is
  not a clocked part, so the family tests that drive a clock are skipped here
  and their bodies never run.
- `@unittest\.skipUnless\(QUOTED,` in the coverage exclusions: this record
  quotes no document, so the family tests that hold a quote checker to the
  pipeline are skipped here.
- `@unittest\.skipUnless\(SOLD_AS_A_COMPONENT,`, `^def machine_mentions\(` and
  `^def listing\(` in the coverage exclusions: this part only existed inside one
  machine, so the family sweep for machine names is skipped here.

The formatter's ignores in [`.prettierignore`](.prettierignore) carry no
comments either, so their reasons live here:

- `pnpm-lock.yaml` and `package-lock.json`: the package manager writes them, in
  its own layout, on every install.
- `node_modules/`, `.venv/`, `venv/`, `build/`, `dist/` and `*.egg-info/`:
  installed or built, never written by hand.
- `.coverage`, `coverage.json`, `htmlcov/` and the tool caches: the output of a
  run, never committed.
- `docs/`, `specs/`, `.work/` and `.claude/`: local working material, never
  committed.

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
  family_*.test.py  the family standard, held to this repository, one topic a file
  family_member.py  what this member answers to them
  family_shared.py  what more than one of them reads
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
