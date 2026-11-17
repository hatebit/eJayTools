# `.PXD` samples — container and audio codec

The mix tooling needs the samples themselves, not just their names.  The
container and the audio codec are the same as the Dance eJay `.PXD` format.
The implementation here (`pxd.py`) is an independent Python implementation of
the algorithm published by the **ejay_pxd** project
(<https://github.com/Alys-Elica/ejay_pxd>, `pxd.cpp` / `pxd.h`); it does not
import the Dance decoder.  It was validated against every sample shipped for
this eJay release (see §4).

## 1. Container

Little-endian, mono, 44 100 Hz, 16 bit.

| offset | field |
|--------|-------|
| 0 | `byte[4]` magic `tPxD` |
| 4 | `uint8` `n` — length of the metadata block |
| 5 | `byte[n]` metadata: CRLF-separated text, NUL padded |
| … | padding of 7–32 bytes, variable |
| … | `byte` marker `0x54` |
| +0 | `uint24` decoded sample count |
| +3 | `byte[3]` skipped |
| +6 | coded audio stream to end of file |

The metadata is a sequence of CRLF lines.  A typical catalogue record is:

```
wood walk\r\n1\r\nRave eJay\r\n\r\nbass\r\n58800\x00\x00
```

i.e. one or two name lines, `Rave eJay`, an empty line, the category, and the
bar length in samples (`58800`).  `pxd.decode` splits on `\n`, strips the
`\r`, and exposes the lines as `PxdSample.strings`; the last line is
`58800\0\0` in every file that has metadata.  The header text is a second,
often split copy of the catalogue name — for example id 1800 is
`['trans', 'lunar', 'Rave eJay', '', 'voice', '58800']` — so the bank label
remains authoritative for identification.

The marker is searched for byte by byte, so the padding in front of it can vary
(observed: 7 to 32 bytes).

### The headerless file

`RAVE/BD/R1DA084.PXD` has **no** `tPxD` header.  It starts directly at the
`0x54` marker:

```
54 b0 e5 00 00 00 00 ...
```

`0x54` is the marker, `b0 e5 00` is the `uint24` count 58 800, then three
skipped bytes.  The decoder accepts this shape and reports `header_size = 7`,
an empty name and no metadata lines.  The file decodes to 58 799 samples
against a declared 58 800 (the usual one-sample-short stream; §4).

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
| `0xF4..0xFE` | `count = op - 0xF3` (1..11): read `count` bytes, store `table[byte]` into slots 0..count-1 of the table named by the next byte, write a sentinel at slot `count`, then replay that table |

Samples are the running sum of the deltas; the accumulator is not clamped, only
the stored sample is (to int16).  A table replay is therefore a burst of
consecutive samples — typically 5–11 — which is what makes the format compact
(~98 KB for 3.4 s of audio).

## 3. Decoding in Python

`pxd.decode(data)` → `PxdSample(name, strings, declared_count, samples,
header_size)`; `samples` is an `int16` NumPy array.  `pxd.decode(...,
truncate=False)` returns the raw stream length instead of stopping at the
declared count.  `pxd.decode_file(path)` and `pxd.write_wav(path, samples)` are
the helpers the player uses.

```
python libs/pxd disks/Rave_eJay/RAVE/BQ/R1BS001.PXD --stats
python libs/pxd disks/Rave_eJay/RAVE/BQ/R1BS001.PXD --wav out/wood.wav
```

## 4. Validation against all 1 149 catalogue samples

| check | result |
|-------|--------|
| files decoded without error | 1 149 / 1 149 |
| metadata parsed | 1 148 / 1 149 (one headerless file) |
| metadata ends with `58800` | 1 148 / 1 148 with metadata |
| duration a whole number of 58 800-sample bars | 1 145 / 1 149 |
| duration min / median / max | 1.292 s / 2.667 s / 26.667 s |
| peak level min / median / max | 0.023 / 0.188 / 0.500 |
| samples at full scale (clipping) | 0 (0.0000 %) |
| declared count vs decoded length | equal in 488 files, exactly one sample fewer in 661 |

The four non-whole declared lengths are the same exceptions as the catalogue's
nominal-bar field (`SAMPLES.md` §1):

| id | file | declared | bars |
|---:|------|---------:|-----:|
| 1059 | `BG/R1DF013.PXD` | 119 438 | 2.031 |
| 1097 | `BD/R1FX021.PXD` | 58 801 | 1.000 |
| 1345 | `BH/R1SF047.PXD` | 119 438 | 2.031 |
| 1800 | `BD/R1VX060.PXD` | 56 963 | 0.969 |

The duration quantisation is the strongest structural evidence: at 44.1 kHz
and 180 BPM a bar is exactly 58 800 samples, and the samples are 1, 2, 4, 8 …
bar loops (2.667 s = 2 bars, 117 600 samples; 26.667 s = 20 bars).

Two honest caveats:

* the declared count is **authoritative**: the opcode stream itself ends one
  sample short in 661 files (the encoder appears to count a final sample it does
  not encode).  Truncating at the declared count — what the reference decoder
  does too — yields 117 599 samples for a 2-bar file, which is inaudible;
* four samples are not exact whole-bar loops (one-shot/FX tails, §4 table),
  hence the 1 145/1 149.

Peaks stop at 0.500 (−6 dBFS) across the whole library: the samples are cut
with headroom so that eight layers can be mixed without clipping, which is why
the player applies an automatic gain instead of playing samples at unity.

## 5. Other sample files in `RAVE`

* `RAVE/EJAY/INTRO.PXD` — 1 025 436 bytes, metadata `Rave eJay Intro`,
  declared 1 234 800 samples = exactly 21 bars.  It is a sample, not a song.
* `RAVE/HYPER/R1HG0001 … R1HG0128.PXD` — 128 samples in eight categories
  (`HYPSOUND`: Vibes, Rave, Trash, Hardbass, Softbass, Space, Comic, Strikes).
  They decode cleanly; their declared lengths are 14 700 or 29 400 samples
  (1/4 or 1/2 bar), and their metadata category is `hyper`.  No id in
  `731..1879` references them, so they are not part of the song bank; see
  `SAMPLES.md` §5.
