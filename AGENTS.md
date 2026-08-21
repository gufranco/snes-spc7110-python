# Working in this repository

This file is for a coding agent. A person reading it will not be harmed, but
[README.md](README.md) is the document written for them.

## What this project is, in one paragraph

The SPC7110's decompressor, all three of its modes. It takes a compressed stream
and gives back the bytes the chip would have produced. It does not read
cartridges, drive a bus, or model time.

## The authority ladder, and the fact that both upper rungs are empty

1. **A manufacturer document.** None. No datasheet for the SPC7110 was published.
2. **A recording taken off a real SPC7110.** None on this machine.
3. **The reference implementation**, which is where all of this comes from.

Every constant in `conformance/hardware.json` carries `verified: false` for that
reason and not because anybody doubts the value. `conformance/hardware.test.py`
asserts that none of them claims otherwise.

## What the differential does and does not establish

`conformance/build.py` builds snes9x's decompressor from pinned source and
`conformance/differential.py` drives both with the same generated streams,
comparing byte for byte.

A disagreement is real and worth acting on. **An agreement means two programs
agree.** Where the reference is wrong this is wrong with it, and nothing here
could tell. That is the first entry in `conformance/divergences.json` and it is
the honest description of what this package's green run means.

## One coincidence, written down before anybody cites it

The output ring buffer is sixty four bytes. An eight bit per dot character is
also sixty four bytes. **They are unrelated.** This is an internal buffer whose
size is tied to no character format.

It is recorded because the coincidence is inviting, and inviting is how a guess
becomes a citation. A citation for something nobody documented is worse than no
citation at all.

## Every gate, in the order to run them

```bash
ruff format --check .                     # formatting
ruff check .                              # lint, zero warnings
mypy                                      # types, strict
pnpm run format:check                     # every JSON file
for f in spc7110/*.test.py conformance/*.test.py; do python3 "$f"; done
python3 -m coverage report                # fails below 100%

python3 conformance/build.py              # builds the reference from pinned source
python3 conformance/differential.py       # drives both and compares
python3 -m spc7110.doctor                 # what is missing on this machine
```

`conformance/hardware.test.py` needs no compiler and is the part of the gate that
runs anywhere.

## Things that will bite you

**A stream wraps rather than running out.** Reading past the end continues from
the beginning. A chip asked for more than the stream holds has to do something,
and stopping is not what this one does.

**Starting at an index runs the decoder forward.** It is not a seek: the coder's
state depends on everything before that point, so starting at an index must
produce what decoding from the beginning and discarding would.

**The coder renormalises below half the interval**, and the two constants are
related that way rather than independently chosen.

## Conventions

| Thing | Rule |
|:------|:-----|
| Language | Python only |
| Comments | None in source. Docstrings carry the reasoning, and say why rather than what |
| Test layout | `<module>.test.py` beside the module it covers |
| Test structure | Arrange, blank line, one act, blank line, assert. No section labels |
| Package manager for tooling | pnpm, never npm |
| Commits | Conventional Commits |
| Promoting a constant to verified | Needs a datasheet or a recording off a real part, never another implementation that agrees |
