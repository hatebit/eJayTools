# `.PXD` samples — container and audio codec

The mix tooling needs the samples themselves, not just their names.  The
container and the audio codec were documented by the **ejay_pxd** project
(<https://github.com/Alys-Elica/ejay_pxd>, `pxd.cpp` / `pxd.h`); the
implementation here (`pxd.py`) is an independent Python port of that algorithm
for use by the player.  It was validated against every sample shipped in this
repository (see §4).

## 1. Container

Little-endian, mono, 44 100 Hz, 16 bit.

| offset | field |
|--------|-------|
| 0 | `byte[4]` magic `tPxD` |
| 4 | `uint8` `n` — length of the metadata block |
| 5 | `byte[n]` metadata: newline-separated text, NUL padded (normally the sample name) |
| … | padding of 7–32 bytes, variable |
| … | `byte` marker `0x54` |
| +0 | `uint24` decoded sample count |
| +3 | `byte[3]` skipped |
| +6 | coded audio stream to end of file |

The metadata block explains names that look truncated or padded in the dumps,
e.g. `Ray\x00\x00`, `GrabAgirl\x00\x00`, `Come on!\x00\x00`; `pxd.py` strips the
NULs only for display.

The marker is searched for byte by byte, so the padding in front of it can vary
(observed: 7 to 32 bytes).

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
consecutive samples — typically 5–11 — which is what makes the format compact
(~98 KB for 3.4 s of audio).

## 3. Decoding in Python

`pxd.decode(data)` → `PxdSample(name, strings, declared_count, samples,
header_size)`; `samples` is an `int16` NumPy array.  `pxd.decode(..., truncate=
False)` returns the raw stream length instead of stopping at the declared
count.  `pxd.decode_file(path)` and `pxd.write_wav(path, samples)` are the
helpers the player uses.

```
python libs/pxd disks/Dance_eJay/DANCE/BA/AAAF.PXD --stats
python libs/pxd disks/Dance_eJay/DANCE/BA/AAAF.PXD --wav out/ray.wav
```

## 4. Validation against all 1 352 shipped samples

| check | result |
|-------|--------|
| files decoded without error | 1 352 / 1 352 |
| header marker / metadata parse | all files, 0 exceptions |
| duration a near-whole number of bars (within 2 %) | 1 343 / 1 352 |
| duration min / median / max | 0.857 s / 3.429 s / 42.857 s |
| peak level min / median / max | 0.055 / 0.280 / 0.501 |
| samples at full scale (clipping) | 0 (0.0000 %) |
| declared count vs decoded length | equal in 603 files, exactly one sample fewer in 750 |
| dominant frequency examples | a pad at 79 Hz, a vocal phrase at 538 Hz, percussion at 1 817 Hz |

The duration quantisation is the strongest structural evidence: at 44.1 kHz and
140 BPM a bar is exactly 75 600 samples, and the samples are 1, 2, 4, 8 … bar
loops (3.429 s = 2 bars, 151 200 samples).

Two honest caveats:

* the declared count is **authoritative**: the opcode stream itself ends one
  sample short in 750 files (the encoder appears to count a final sample it does
  not encode).  Truncating at the declared count — what the reference decoder
  does too — yields 151 199 samples for such files, which is inaudible;
* nine samples are not whole-bar loops (one-shots, FX), hence the 1 343/1 352.

Peaks stop at 0.5 (−6 dBFS) across the whole library: the samples are cut with
headroom so that eight layers can be mixed without clipping, which is why the
player applies an automatic gain instead of playing samples at unity.
