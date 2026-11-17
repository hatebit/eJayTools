# `.PXD` samples — container and audio codec

The mix tooling needs the samples themselves, not just their names.  The
HipHop samples use the same container and codec as the Dance and Rave trees;
this copy (`pxd.py`) is independent of those trees.  The container and the
audio codec were documented by the **ejay_pxd** project
(<https://github.com/Alys-Elica/ejay_pxd>, `pxd.cpp` / `pxd.h`); this is an
independent Python port of that algorithm.  It was validated against every
sample shipped in this repository (see §4).

## 1. Container

Little-endian, mono, 44 100 Hz, 16 bit.

| offset | field |
|--------|-------|
| 0 | `byte[4]` magic `tPxD` |
| 4 | `uint8` `n` — length of the metadata block |
| 5 | `byte[n]` metadata: newline-separated text, NUL padded (normally the sample name) |
| … | padding of variable length |
| … | `byte` marker `0x54` |
| +0 | `uint24` decoded sample count |
| +3 | `byte[3]` skipped |
| +6 | coded audio stream to end of file |

The metadata block explains names that look truncated or padded in the dumps;
`pxd.py` strips the NULs only for display.

The marker is searched for byte by byte, so the padding in front of it can
vary: across the 1 341 HipHop samples the coded stream starts at byte 46 … 73
(203 files at 55, 145 at 56, 122 at 57, and a long tail down to 46 and up to
73).

## 2. Codec

A table-driven differential coder.  A 256-entry base table of signed deltas is
built deterministically:

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

Both truncations must wrap like a C `int16_t` cast — the ramp overflows 16 bits
around i ≈ 90, which is part of the scheme.

256 adaptive tables of 8 entries (+3 entries of overflow past the end of each
table) are initialised to five zero deltas and a `-1` sentinel.  Opcodes:

| opcode | meaning |
|--------|---------|
| `0x00..0xF3` | replay adaptive table `op` from its start until the sentinel |
| `0xFF` | one sample: add `table[next byte]` |
| `0xF4..0xFE` | `count = op - 0xF3` (1..11): read `count` bytes, store
`table[byte]` into slots 0..count-1 of the table named by the next byte, write a
sentinel at slot `count`, then replay that table |

Samples are the running sum of the deltas; the accumulator is not clamped, only
the stored sample is (to int16).  A table replay is therefore a burst of
consecutive samples — typically 5–11 — which is what makes the format compact.

## 3. Decoding in Python

`pxd.decode(data)` → `PxdSample(name, strings, declared_count, samples,
header_size)`; `samples` is an `int16` NumPy array.  `pxd.decode(..., truncate=
False)` returns the raw stream length instead of stopping at the declared
count.  `pxd.decode_file(path)` and `pxd.write_wav(path, samples)` are the
helpers the player uses.

```
python libs/pxd disks/Hiphop_eJay/HIPHOP/AA/H1BS001.PXD --stats
python libs/pxd disks/Hiphop_eJay/HIPHOP/AA/H1BS001.PXD --wav out/sample.wav
```

## 4. Validation against all 1 341 shipped samples

| check | result |
|-------|--------|
| files decoded without error | 1 341 / 1 341 |
| header marker / metadata parse | all files, 0 exceptions |
| duration a near-whole number of 110 250-sample bars (within 2 %) | 1 339 / 1 341 |
| decoded length min / median / max | 107 818 / 220 499 / 661 500 samples |
| declared lengths seen | 110 250 (647), 220 500 (649), 330 750 (13), 441 000 (27), 661 500 (2), plus 107 818, 220 612 and 227 391 once each |
| peak level min / median / max | 0.007 / 0.172 / 0.393 |
| samples at full scale (clipping) | 0 |
| declared count vs decoded length | equal in 766 files, exactly one sample fewer in 575 |

The bar quantisation is the strongest structural evidence for the tempo: at
44.1 kHz and 96 BPM a bar is exactly 110 250 samples, and the samples are 1, 2,
3, 4 or 6 bar loops (2.5 s = 110 250 samples, 5.0 s = 220 500, 7.5 s =
330 750, 10 s = 441 000, 15 s = 661 500).

Two honest caveats:

* the declared count is **authoritative**: the opcode stream itself ends one
  sample short in 575 files (the encoder appears to count a final sample it does
  not encode).  Truncating at the declared count — what the reference decoder
  does too — is inaudible;
* two samples are not whole-bar loops: `H1FX024.PXD` "swish" is 227 391
  samples (2.063 bars, 3.1 % long) and `H1DB301.PXD` "snreK" is 107 818
  samples (0.978 bars, 2.2 % short); hence the 1 339/1 341.  The 101
  `SPECIAL` WAVs are all exactly 220 500 frames (two bars).

Peaks stop at 0.393 (−8.1 dBFS) across the whole library: the samples are cut
with headroom so that eight layers can be mixed without clipping, which is why
the player applies an automatic gain instead of playing samples at unity.
