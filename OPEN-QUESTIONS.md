# Open questions

What this project does not know for certain, and what it would take to find out.

No manufacturer document for this part is known to exist. The algorithm was
reconstructed from the silicon or from its output, so the top two rungs of the
authority ladder are both empty here and a reference implementation is carrying
the whole package.
[`conformance/hardware.json`](conformance/hardware.json) says so rather than
promoting a rung.

What makes the comparison worth anything is how it is pinned. The reference is
fixed by commit and by three extracts of its source, so a check cannot start
comparing against a different implementation without the pin changing first and
somebody noticing.

Every entry is also in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## What would settle almost all of them

A document, which was searched for and not found, or a recording taken off a real
SPC7110.

## Where nothing but a second implementation stands behind it

### Every output value the decompressor produces.

**The document says.** Nothing. There is no document.

**What this project follows.** The reference decompressor, built from a pinned
commit, over 200 streams of random bytes across all three modes: 102,400 bytes
compared.

**Why.** It is the only source that produces output at all. Agreement between two
implementations is not a measurement of silicon, and saying so is the point of
this entry.

**What would settle or reopen it.** A capture of a real SPC7110 expanding a known
block.

### Whether the three modes are the only three.

**The document says.** Nothing.

**What this project follows.** Three, which is what the reference implements and
what every cartridge is consistent with.

**Why.** It establishes that no shipped cartridge uses a fourth. It does not
establish that the silicon has no fourth, and those are different claims.

**What would settle or reopen it.** A stream that selects a mode outside the
three, or a document.

### What the chip does with a malformed stream.

**The document says.** Nothing.

**What this project does.** Wraps its input rather than refusing when a read runs
off the end, which is what the reference does.

**Why.** Every implementation guesses here and none of the guesses can be
checked. This one follows the reference rather than inventing a third behaviour,
which at least keeps the two comparable.

**What would settle or reopen it.** A capture of the real part fed a truncated
block.

## Where a figure is a working size rather than a measured one

### The output buffer size.

**The document says.** Nothing.

**What this project follows.** The size the reference uses.

**Why.** It is a working size in an implementation rather than a property of the
silicon, and the record marks it as acknowledged rather than open, because
nothing about it is in doubt: it is simply not a hardware fact.

**What would settle or reopen it.** A die read, and it would not change any
output value.

## Where the question is a scope boundary, not an unknown

### Anything about timing.

**What this project does.** Models what a decode produces, and nothing about how
long it takes.

**Why it is not a gap.** How long a decode takes, and whether a console reading
the output can outrun it, would be a property of the board.

**What would settle or reopen it.** A bus capture.

### What a reset does.

**The document says.** Nothing.

**What this project does.** Nothing, because there is no state to clear: every
decompression is started from its own header and its own context table.

**Why.** The reset exists so a caller driving a board does not have to
special-case which parts hold state. It is deliberately not a claim about the
real part's reset pin, and the record says so.

**What would settle or reopen it.** A capture across a console reset mid-decode.

## What is not in question

So the boundary is visible rather than implied:

- **That all three modes agree with the reference.** 200 streams, 102,400 bytes,
  no disagreements.
- **That the comparison is against what it says it is.** The reference is pinned
  by commit and by three source extracts, so a silent substitution fails the pin
  rather than passing the check.
- **That random bytes are the right input.** Artwork walks the probability model
  along one path and leaves most of the state table unvisited.

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **The rest of the chip.** The SPC7110 also carries a real-time clock and a
  memory mapper, and both have homes:
  [snes-rtc-python](https://github.com/gufranco/snes-rtc-python) and
  [snes-mapper-python](https://github.com/gufranco/snes-mapper-python). The scope
  is in the name rather than implied.
- **Any cartridge data.** Nothing here is extracted from a retail image.
- **Anything with a clock.** A caller hands it a stream and reads bytes off what
  comes back.
