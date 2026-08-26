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

**A second reference is the obvious next rung and there is none to reach.**
Checked on 2026-08-25 by reading the headers rather than assuming: the pinned
reference names byuu and neviksti, and bsnes, which is the only other
implementation of this part, names neviksti as the original and talarubi as the
optimisation. Both descend from one reverse engineering. Building the second and
requiring the two to agree would be running one implementation twice and calling
the result corroboration, so it is not done.

The neighbouring `snes-sdd1` is in the same position for the same reason, and its
records say so too. What rescues that one is not a second implementation but a
second artefact: somebody expanded a cartridge, and the expanded image can be
compared against. No equivalent exists here.

**What would settle or reopen it.** A capture of a real SPC7110 expanding a known
block. Not a second implementation, because there is no independent one.

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

## Where the real streams were found after all

### Every stream this is driven with used to be generated.

**The document says.** Nothing.

**What was wrong with the first attempt.** It searched. A pattern search turned up
a run of 254 plausible directory entries in *Super Power League 4*, every one of
which decoded without complaint, which established nothing: this decompressor
raises on nothing, so a random offset decodes just as happily. The measurement
that killed it was entropy, 7.233 for the run against 7.144 for random offsets,
and a separation that small cannot tell a stream from a coincidence.

**What was missing was the program.** The part takes the directory base from
three registers the game writes, so the base was never something to search for.
It is a constant in the cartridge's own code, and the three games write it three
different ways:

| Cartridge | How its code names the base | Streams |
|:--|:--|--:|
| Tengai Makyou Zero | three immediate loads | 196 |
| Momotarou Dentetsu Happy | three bytes of a table, read long-indexed | 256 |
| Super Power League 4 | two sixteen bit loads over the same three bytes | 167 |

All three name `0x000008`, and in all three the directory ends at exactly the
address of the first stream, which is a structure holding across three
independently written games rather than a coincidence.

**What the oracle says now.** The separation that was missing is there:

| Cartridge | Streams decode to | Random offsets decode to |
|:--|--:|--:|
| Tengai Makyou Zero | 2.685 | 7.367 |
| Momotarou Dentetsu Happy | 3.654 | 7.243 |
| Super Power League 4 | 3.603 | 7.104 |

Entropy in bits per byte over 512 bytes. Graphics carry far less than noise, and
the gap is now four bits rather than a tenth of one.

**What is driven with them.** All 619 streams, through both implementations,
316,928 bytes compared, none disagreeing. The census is in
[`conformance/cartridges.json`](conformance/cartridges.json) and the run in
[`conformance/streams.json`](conformance/streams.json), both with the digests of
the three cartridges and no byte of any of them.

**What it does not establish.** That the algorithm is what the silicon does. Two
implementations agreeing on real data is still two implementations agreeing, and
these two descend from one reverse engineering. What it removes is the
possibility that they agreed only because generated streams never reach the paths
an encoder's output takes.

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
