# `.PXD` samples — container, codec and the bundled index

The Dance eJay 2 samples use the `tPxD` container and codec documented by the
**ejay_pxd** project (<https://github.com/Alys-Elica/ejay_pxd>, `pxd.cpp` /
`pxd.h`); this is an independent Python implementation, shared with the other
four trees in `libs/pxd/`.  It was validated
against all 1 957 samples of the base container and all 119 standalone streams.

## 1. Container

Little-endian, mono, 44 100 Hz, 16 bit.

| offset | field |
|--------|-------|
| 0 | `byte[4]` magic `tPxD` |
| 4 | `uint8` `n` — length of the metadata block |
| 5 | `byte[n]` metadata: newline-separated text, NUL padded (sample name, product name) |
| … | variable padding |
| … | `byte` marker `0x54` |
| +0 | `uint24` decoded sample count |
| +3 | `byte[3]` skipped |
| +6 | coded audio stream to end of stream |

`pxd.decode()` searches for the `0x54` marker byte by byte, so padding length is
not assumed.  The metadata of the `Audio_d` demos is
`Dance 2\nAutodemo\nDance eJay 2.0\nUser Demo\nDemo`; `Audio_e/f` carry
`demoNN`; `DINTRO.PXD` carries `Dance eJay 2.0\nIntro Sound`.

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

256 adaptive tables of 8 entries start as five zero deltas and a `-1` sentinel.  Opcodes:

| opcode | meaning |
|--------|---------|
| `0x00..0xF3` | replay adaptive table `op` from slot 0 until the sentinel |
| `0xFF` | one sample: add `table[next byte]` |
| `0xF4..0xFE` | `count = op - 0xF3` (1..11): read `count` bytes, store them in slots 0..count-1 of the table named by the next byte, write a sentinel after them, then replay that table |

Samples are the running sum of the deltas; only the stored sample is clipped to
int16, not the accumulator.  The declared `uint24` count is not reliable: in the
base container it equals the decoded length in **213** of 1 957 samples, is one
shorter in **606**, and longer by up to 7 in most of the rest.  `pxd.decode()`
defaults to `truncate=True`, i.e. trims the stream to the declared count;
`truncate=False` returns everything the opcodes produce.

## 3. API and CLI

`pxd.decode(data)` → `PxdSample(name, strings, declared_count, samples,
header_size)` with `samples` an `int16` NumPy array.  `pxd.write_wav()` writes
16-bit mono 44.1 kHz.  `pxd.Bundle(data_path, inf_path)` reads a concatenated
container and its twelve-line index; `bundle.decode(record)` slices exactly
`offset … offset+length` and decodes that stream.

```
python libs/pxd disks/Dance_2/D_ejay2/ejay/DINTRO.PXD --stats
python libs/pxd disks/Dance_2/D_ejay2/PXD/DANCE20.INF --list
python libs/pxd disks/Dance_2/D_ejay2/PXD/DANCE20.INF --id 1930 --stats
python libs/pxd disks/Dance_2/D_ejay2/PXD/DANCE20.INF --id 1930 --wav out.wav
```

## 4. Validation — 1 957 base samples

| check | result |
|-------|--------|
| records decoded without error | **1 957 / 1 957** |
| bytes covered by the index | 231 270 914 / 231 270 914 (contiguous) |
| highest peak | **0.4854** (−6.3 dBFS) |
| length min / max | 9 424 / 604 797 samples (0.214 s / 13.714 s) |
| declared = decoded | 213 files |
| decoded one sample shorter | 606 files |
| decoded longer | up to +7 in the common cases |

The 0.4854 ceiling matches eJay's habit of cutting samples with headroom so
that layered tracks do not clip; the corpus never reaches full scale.

## 5. The bundled containers and their indexes

`DANCE20`, `DANCESK4`, `DANCESK5`, `DANCESK6` are plain concatenations of
`tPxD` streams; the `.INF` file gives each stream's `offset` and `length`.
Every index is contiguous from offset 0 to the end of its data file:

| container | bytes | records | ids | bank |
|-----------|------:|--------:|-----|-----:|
| `DANCE20` | 231 270 914 | 1 957 | 1 … 1957 | 1 |
| `DANCESK4` | 101 567 584 | 598 | 5100 … 5703 | 3 |
| `DANCESK5` | 107 149 698 | 677 | 5800 … 6476 | 4 |
| `DANCESK6` | 88 536 324 | 564 | 6500 … 7063, one id 0 | 5 and 0 |

Records are ordered by **offset**, not by id; look ids up through the index.
Only `DANCE20` was decoded end to end.  The add-on banks are indexed but their
audio was not decoded here.

## 6. Standalone files and `PXD10`

* `D_ejay2/ejay/Audio_d` (46), `Audio_e` (37), `Audio_f` (35): one `tPxD`
  stream each, 118 files, all decode.  Their metadata says `Dance 2` /
  `Autodemo` or `demoNN`.
* `DINTRO.PXD`: one stream, decodes.
* `METRO.PXD`: RIFF/WAVE, not `tPxD`.
* `PXD10`: 1 352 six-line catalogue entries with 8.3 paths such as
  `bm\asjo.pxd`; none of the paths exists in the shipped tree.  See
  [`SAMPLES.md`](SAMPLES.md) §4.
