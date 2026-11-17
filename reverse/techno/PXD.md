# `.PXD` samples — container, codec and the index

The Techno eJay 2 samples use the `tPxD` container and codec documented by the
**ejay_pxd** project (<https://github.com/Alys-Elica/ejay_pxd>, `pxd.cpp` /
`pxd.h`); this is an independent Python implementation, shared with the other
four trees in `libs/pxd/`.  It was validated
against the 362 `RAVE20` records the songs use and all 504 standalone `HYP`
files.

## 1. Container

Little-endian, mono, 44 100 Hz, 16 bit.

| offset | field |
|--------|-------|
| 0 | `byte[4]` magic `tPxD` |
| 4 | `uint8` `n` — length of the metadata block |
| 5 | `byte[n]` metadata: newline-separated text (sample name, product name) |
| … | variable padding |
| … | `byte` marker `0x54` |
| +0 | `uint24` decoded sample count |
| +3 | `byte[3]` skipped |
| +6 | coded audio stream to end of stream |

`pxd.decode()` searches for the `0x54` marker byte by byte, so the padding
length is not assumed.  The `HYP` files carry short metadata such as
`4\n5\nHyper2\n\n2\n`; the `RAVE20` records carry eJay's own sample names.

## 2. Codec

A table-driven differential coder.

```
step = 2.2 ; multiplier = 1.0565
table[128] = 0
for i in 1..127:
    increment = 1 if i < 6 else int(step - 0.52)
    table[128+i] = int16(table[127+i] + increment)
    step *= multiplier ; multiplier -= 0.00022
table[0] = 0
for i in 1..127: table[128-i] = -table[128+i]
for all: table[i] = int16(table[i] << 1)
```

Both `int16` truncations must wrap like a C cast; the ramp overflows around
i ≈ 90 and that is part of the scheme.

256 adaptive tables of 8 entries start as five zero deltas and a `-1` sentinel.
Opcodes:

| opcode | meaning |
|--------|---------|
| `0x00..0xF3` | replay adaptive table `op` from slot 0 until the sentinel |
| `0xFF` | one sample: add `table[next byte]` |
| `0xF4..0xFE` | `count = op - 0xF3` (1..11): read `count` bytes, store them in slots 0..count-1 of the table named by the next byte, write a sentinel after them, then replay that table |

Samples are the running sum of the deltas; only the stored sample is clipped to
int16, not the accumulator.  `pxd.decode()` defaults to `truncate=True`, i.e.
trims the stream to the declared count; `truncate=False` returns everything the
opcodes produce.

In this corpus the raw stream of every referenced `RAVE20` record produces **4
or 5 samples past** the declared count (242 and 120 records respectively).
Trimming to the declared count makes all 362 exact whole bars, and that is what
the player does.  Of the 504 standalone `HYP` files, 362 decode one sample
shorter than declared and 142 are exact.

## 3. API and CLI

`pxd.decode(data)` → `PxdSample(name, strings, declared_count, samples,
header_size)` with `samples` an `int16` NumPy array.  `pxd.write_wav()` writes
16-bit mono 44.1 kHz.  `pxd.Bundle(data_path, inf_path)` reads a concatenated
container and its twelve-line index; `bundle.decode(record)` slices exactly
`offset … offset+length` and decodes that stream.

```
python libs/pxd disks/Techno_eJay/EJAY/PXD/RAVE20.INF --list
python libs/pxd disks/Techno_eJay/EJAY/PXD/RAVE20.INF --id 13016 --stats
python libs/pxd disks/Techno_eJay/EJAY/PXD/RAVE20.INF --id 13016 --wav out.wav
python libs/pxd disks/Techno_eJay/EJAY/PXD/HYP1/BASS001.PXD --stats
```

## 4. Validation

`RAVE20`, referenced ids only:

| check | result |
|-------|--------|
| records decoded without error | **362 / 362** |
| declared = decoded (trimmed) | 362 / 362 |
| highest peak | **0.4509** (−6.9 dBFS) |
| length min / max | 75 600 / 1 209 600 samples (1.714 s / 27.429 s) |
| whole-bar lengths | 361; id 16 862 is 76 040 samples |

All 504 standalone `HYP` files:

| check | result |
|-------|--------|
| records decoded without error | **504 / 504** |
| highest peak | **0.4987** (−6.0 dBFS) |
| lengths | mostly 1/8, 1/4, 1/2 or 1 bar; a few longer |

The ~0.50 ceiling matches eJay's habit of cutting samples with headroom so
that layered tracks do not clip.  The `RAVE20` container was **not** decoded end
to end; only the ids the arrangements reference were, which is what the player
and the docs claim.

## 5. The bundled container and its index

`RAVE20` is a plain concatenation of `tPxD` streams; `RAVE20.INF` gives each
stream's `offset` and `length`.

| container | bytes | records | ids | bank |
|-----------|------:|--------:|-----|-----:|
| `RAVE20` | 429 261 617 | 4 015 | 13 000 … 17 014 | 6 |

Records are ordered by **offset**, not by id; look ids up through the index.
See [`SAMPLES.md`](SAMPLES.md) for the id list and the standalone `HYP` kits.
