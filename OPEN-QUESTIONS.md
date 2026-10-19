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

The register interface, added on 2026-10-19, rests on a different reference:
ares at commit `9408cb43d4948fc3ea6e152a307a34348df3fe04`, read beside snes9x's
older `spc7110emu.cpp` at commit `1bcc369e89f08243e0a462882fb1f3e42e51de3a`.
Both register files carry byuu's name, so they are one author's two readings of
the chip years apart rather than two investigations. Where they agree it is
recorded as their agreement; where they part, the package follows ares, the
later one, and the entry below says what each does.

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
reference names byuu and neviksti, and bsnes names neviksti as the original and
talarubi as the optimisation. ares carries the same decompressor as bsnes. All
of them descend from one reverse engineering. On 2026-10-19 ares's decompressor,
compiled unchanged and driven through the register interface, agreed with this
one on all 619 cartridge streams and on 231 register-driven cases: 375,040
bytes. That is a third program from the same research agreeing, not an
independent witness, and [`conformance/hardware.json`](conformance/hardware.json)
records it under `registerInterface` as exactly that.

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

### What a stream reads once it runs past the end of the data ROM.

**The document says.** Nothing.

**What changed.** This used to ask what the chip does with a malformed stream
that runs out. Through the registers no stream runs out: ares and snes9x both
feed the decoder through the data-ROM mapping, so every read lands somewhere.
The question that remains is which byte.

**What ares does.** Masks the address to the size `$4834` names, 1, 2, 4 or 8
megabytes, reads zero from the upper half below 8 megabytes, and mirrors what is
left onto the data ROM the way its bus mirrors any chip. **What snes9x does.**
Wraps by the data ROM's own size and ignores `$4834`.

**What this project does.** Follows ares through `Chip`. `Decompressor(source)`
over plain bytes still wraps at the end of `source`, as the snes9x decoder does.

**What would settle or reopen it.** A cartridge whose data ROM is not a power of
two, read past its end on hardware.

## Where a figure is a working size rather than a measured one

### The output buffer size.

**The document says.** Nothing.

**What this project follows.** The size the reference uses.

**Why.** It is a working size in an implementation rather than a property of the
silicon, and the record marks it as acknowledged rather than open, because
nothing about it is in doubt: it is simply not a hardware fact.

**What would settle or reopen it.** A die read, and it would not change any
output value.

## Where the register interface rests on ares, and snes9x disagrees

Each entry is also a divergence in
[`conformance/divergences.json`](conformance/divergences.json), with what each
implementation does word for word.

### When the decompression unit reads its directory, and how it seeks.

**What ares does.** Writing `$4804` reads the entry; writing `$4806` starts. A
seek of `$4805-$4806` rows happens only with bit 1 of `$480B` set, and bit 0
makes each row be followed by `$4807` skipped rows. `$4808` reads zero.
**What snes9x does.** Reads and starts on `$4806`, always skips
`($4805 | $4806 << 8) << mode` bytes, has no stride, and keeps `$4808`.

**What this project does.** Follows ares. Which order the three cartridges rely
on was not measured.

**What would settle or reopen it.** A bus capture of a game starting two streams
with one `$4804` write, or of a game using `$480B`.

### What bit 7 of `$480C` and `$482F` means, and whether a read clears it.

**What ares does.** `$480C` bit 7 is set when a start is ready; `$482F` bit 7 is
set while a multiply or divide runs. A read changes nothing. **What snes9x
does.** Both bits are set when the work is done, and a read clears them.

**What this project does.** Follows ares, which gives `$482F` the opposite
meaning to snes9x.

**What would settle or reopen it.** A bus capture of `$482F` read during and
after a divide.

### What writing `$482E` does to the arithmetic registers.

**What ares does.** Keeps bit 0, the sign, and nothing else. **What snes9x
does.** Clears `$4820` to `$482D` first.

**What this project does.** Follows ares.

**What would settle or reopen it.** A bus capture of the operands read back after
a write to `$482E`.

### How the data port steps.

**What ares does.** Fetches at offset plus the adjust when bit 1 of `$4818` is
set, steps the offset or the adjust by one or by `$4816-$4817` on a read of
`$4810`, refetches on writes to `$4813` and `$4818`, and lets bits 5 and 6 choose
`$4814`, `$4815` or a read of `$481A` as the moment the adjust is added.
**What snes9x does.** Answers nothing until `$4811` to `$4813` have all been
written, latches `$4814` and `$4815` as a pair, adds one to the adjust on every
read with bit 1 set, and adds on `$481A` only with both bits 5 and 6 set.

**What this project does.** Follows ares.

**What would settle or reopen it.** A bus capture of a game reading text through
`$4810`, compared address by address.

### How long a decompression start, a multiply and a divide take.

**What ares does.** 20, 30 and 40 master clocks at 21,477,272 a second, each
after the one clock its loop spends noticing the request. **What snes9x does.**
All three at once.

**What this project does.** Follows ares through `tick()`: ready on the 21st,
31st and 41st clock after the write. The decode itself costs nothing in either
implementation once started.

**What would settle or reopen it.** A bus capture timing `$480C` after `$4806`
and `$482F` after `$4825` or `$4827`.

### What a signed divide of 0x80000000 by minus one gives.

**What ares does.** Computes it in C, where it is undefined behaviour, and so
does snes9x.

**What this project does.** Wraps the quotient to `0x80000000` and the remainder
to zero, and records that this is its own choice.

**What would settle or reopen it.** That divide on hardware.

### What a reset does.

**The document says.** Nothing.

**What this project does.** Sets what ares's `power()` sets: every decompression,
data port and arithmetic register to zero, `$4830` to `$4834` to 0, 0, 1, 2 and
0, and nothing waiting. snes9x's `reset()` sets the same values. The
decompressor's own state and the buffered tile survive, as in ares. Construction
scrambles every register from the seed and the constructor never calls
`reset()`.

**Why.** Neither implementation says whether the console's reset line reaches
the part. The record says this is an implementation's power on, not a claim
about the pin.

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
- **That the register interface reads what ares reads.** 619 cartridge streams
  and 231 register-driven cases, 375,040 bytes, no disagreements, measured once
  on 2026-10-19 with a harness that is not shipped.

### The real streams, which used to be generated.

**The document says.** Nothing.

**What was wrong with the first attempt.** It searched. A pattern search turned up
a run of 254 plausible directory entries in _Super Power League 4_, every one of
which decoded without complaint, which established nothing: this decompressor
raises on nothing, so a random offset decodes just as happily. The measurement
that killed it was entropy, 7.233 for the run against 7.144 for random offsets,
and a separation that small cannot tell a stream from a coincidence.

**What was missing was the program.** The part takes the directory base from
three registers the game writes, so the base was never something to search for.
It is a constant in the cartridge's own code, and the three games write it three
different ways:

| Cartridge                | How its code names the base                     | Streams |
| :----------------------- | :---------------------------------------------- | ------: |
| Tengai Makyou Zero       | three immediate loads                           |     196 |
| Momotarou Dentetsu Happy | three bytes of a table, read long-indexed       |     256 |
| Super Power League 4     | two sixteen bit loads over the same three bytes |     167 |

All three name `0x000008`, and in all three the directory ends at exactly the
address of the first stream, which is a structure holding across three
independently written games rather than a coincidence.

**What the oracle says now.** The separation that was missing is there:

| Cartridge                | Streams decode to | Random offsets decode to |
| :----------------------- | ----------------: | -----------------------: |
| Tengai Makyou Zero       |             2.685 |                    7.367 |
| Momotarou Dentetsu Happy |             3.654 |                    7.243 |
| Super Power League 4     |             3.603 |                    7.104 |

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

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **The real-time clock.** `$4840-$4842` belong to the clock beside the part,
  and [snes-rtc-python](https://github.com/gufranco/snes-rtc-python) models it.
  `Chip` refuses those addresses rather than answering for a part it is not.
- **The expansion ROM.** ares maps a further megabyte at `$40-$4F` on a board
  its own source labels as a fan translation's.
- **Any cartridge data.** Nothing here is extracted from a retail image.
