# HipHop eJay `*.MIX` format

Reversed from the 17 files in `disks/Hiphop_eJay/MIX`, cross-checked against
`disks/Hiphop_eJay/HIPHOP/EJAY/PXD`, `…/EJAY/SPECIAL` (the two sample catalogue
lists) and the `tPxD` headers of the samples.  Nothing under `disks/` was
executed; everything below comes from reading the data files.

Other documents: [`README.md`](README.md) (doc map, tools),
[`SAMPLES.md`](SAMPLES.md) (id → `.PXD`/WAV), [`MIXES.md`](MIXES.md)
(per-song statistics), [`PXD.md`](PXD.md) (container and codec),
[`METHOD.md`](METHOD.md) (evidence and unknowns).

Tooling (parser in `libs/mix/hiphop/`, adapter in
`apps/emp/src/format/hiphop/`):

```
python reverse/hiphop/mixdump.py --all                        # readable dump of every mix
python reverse/hiphop/mixdump.py --json reverse/hiphop/decoded --all
python reverse/hiphop/mixdump.py --verify --all               # re-encode, byte-compare
python apps/emr/src/format/hiphop/mixrender.py --out reverse/hiphop/images --all   # arrangement PNGs
```

## 1. Overall layout

All files are little-endian.

| offset   | size    | field |
|----------|---------|-------|
| `0x0000` | 2       | `uint16` signature, `0x0A08` in all 17 files |
| `0x0002` | 11232   | song grid: `702 * 8` `uint16` sample ids |
| `0x2BE2` | 1458    | sample-bank block (§4), present in every file |

`0x2BE2 = 2 + 702*8*2`.  Every file is exactly **12 692** bytes, so unlike
Dance eJay the bank block is not optional and its length does not vary: the
17 tails are byte-identical apart from the `head` word and `pan` words of §4.

Tempo is **not** stored: the samples are cut at **96 BPM, 4/4**, so one bar is
`4 * 60/96 = 2.5 s` = **110 250 samples** at 44.1 kHz and the maximum grid
(702 bars) is 29.25 minutes.  Evidence for the tempo is in §3 and
[`PXD.md`](PXD.md) §4: 1 339 of the 1 341 `.PXD` samples and all 101
`SPECIAL` WAVs are a whole number of 110 250-sample bars.

## 2. Song grid

The grid is **bar-major with the 8 tracks interleaved**:

```
slot(bar, track) = 0x0002 + (bar * 8 + track) * 2      bar = 0..701, track = 0..7
value            = sample id, 0 = empty slot
```

Evidence: the dense region ends exactly at the last occupied bar and the rest
of the grid is zero; over the corpus (5 963 bars) no bar holds more than 8
samples; and sample names on a fixed slot index read as one instrument lane
across a whole song (for example `START.MIX` T4 repeats `hard breath`).
`0 = empty` follows from the zero-filled tail.

* `song_length` = index of the last bar with any non-zero slot, plus 1.
* time of a bar = `bar * 2.5` seconds.
* The tracks are mono lanes with no pan value in the grid itself; pan is stored
  once per track in the bank block (§4).

## 3. Sample ids

A grid value is a **slot in eJay's sample bank**, not a line number in
`MAX`:

* `731 + n` is record `n` of `HIPHOP/EJAY/PXD` — **1 341** six-field records
  (path, empty, category, number, group, name), so ids **731 … 2071**.
* `1 + n` is record `n` of `HIPHOP/EJAY/SPECIAL` — **101** WAV records, so ids
  **1 … 101**, audio in `disks/Hiphop_eJay/SPECIAL/<stem>.WAV`.
* ids `102 … 730` are eJay's empty import slots; this corpus uses no add-on
  boxes and no id outside the two lists.

The browser label is `group + " " + name`.  `START.MIX` shows the mapping:

| id   | record | file            | label                |
|------|-------:|-----------------|----------------------|
| 1025 | 294    | `BH/H1EX021.PXD`| `help me`            |
| 1022 | 291    | `BF/H1EX018.PXD`| `hard breath`        |
| 1649 | 918    | `BH/H1RP056.PXD`| `hiphp jam`          |
| 2040 | 1309   | `BK/H1ZZ003.PXD`| `scrat rush`         |
| 8    | 7      | `SPECIAL/HXDRUM08.WAV` | `rattle snake` |

The strongest numbering check is the ceiling: the highest id used anywhere is
**2071**, which is `731 + 1 340`, the last `PXD` record.  Ids 731…2071 and
1…101 all resolve (5 161 and 327 placements respectively, 5 488 in total); no
placement in the corpus is unresolved.

`MAX` (1 381 lines) and `MIN` (743 lines) are installation manifests in
folder order (`MAX` = 1 341 `.pxd` + 40 `SCRATCH` `.wav`), not the id order;
see [`SAMPLES.md`](SAMPLES.md) §2.

## 4. Bank block (always appended, 1 458 bytes)

The block starts with the same shape Dance eJay's `0x0A08` block uses, then
continues with HipHop-specific content.  Offsets are relative to `0x2BE2`:

```
0x0000  uint16  tag            0x0A08
0x0002  uint16  nlists         1
0x0004  uint16  len            18
0x0006  byte[len]  version     "HipHop eJay 1.01" + NUL + 0x01
0x0018  1408       tables      two 704-byte tables (§4a)
0x0598  uint16 x 4 head        [1, X, 0, 0] in every file (§4b)
0x05A0  uint16  track_count    8
0x05A2  uint16 x 8 pan         one word per track (§4c)
0x05B2  end                   1 458 bytes total
```

The version string is stored the `0x0A08` way: characters, a NUL, then a `0x01`
flag byte, and `len` counts all 18 bytes.  Every file in the corpus has
`nlists = 1`, version `HipHop eJay 1.01`, and version flag `1`.

### (a) The two 704-byte tables — layout known, meaning unknown

`tables` is **identical in all 17 files**.  It is two 704-byte halves and each
half is:

```
uint16 350
byte   702 x 0x00
```

350 = `0x015E`.  No file varies a single byte here, so this corpus cannot
show what the two tables are for: a candidate reading is a fixed-capacity slot
table (2 + 702 bytes is also `2 + BARS`), but that is a reading, not evidence.
The writer keeps the 1 408 bytes verbatim; they are documented as unresolved.

### (b) `head` — one varying word, unknown meaning

Four words, `[1, X, 0, 0]`.  The first word is 1, the last two are 0 in every
file.  `X` takes six values:

| `X`    | files | note |
|-------:|-------|------|
| 11 025 | 12    | `44100/4`; the common value (`BCAUSE`, `FEEDHIP`, `GOODMOOD`, `HIPHOP`, `HIPHOUSE`, `JUNGLE`, `MYSELF`, `SLOWUP`, `START`, `SUMMER`, `SWEET`, `XDAYS`) |
| 11 944 | 1     | `SHYGIRL` |
| 13 322 | 1     | `DUTCH` |
| 16 538 | 1     | `UPDOWN` |
| 19 753 | 1     | `RAGE` |
| 22 050 | 1     | `VIBE`; `44100/2` |

Two of the values are simple fractions of the sample rate, the other four are
not; `X` does not correlate with song length, placement count, sample choice,
pan or the version string, so its meaning is unknown.

### (c) `pan` — inferred, not proved

`track_count` is 8 and is followed by eight words, one per track.  Only the
values 0, 1 and 2 occur:

| word | meaning (inferred) |
|-----:|--------------------|
| 0 | centre |
| 1 | hard left |
| 2 | hard right |

The evidence is threefold: the words take exactly these three values; 11 of
the 17 files use the constant default `C C C C C C L R`, i.e. T7 left, T8
right; and the song that pans more tracks keeps the values in opposite pairs
(`GOODMOOD` = `C C C C L R R L`).  This also matches the independent Dance
eJay corpus, whose identical trailing 18-byte structure carries
`8, 0×6, 1, 2` in all 16 files while Dance's documentation derives T7 hard
left / T8 hard right from its sample labels.  It is still an inference: the
grid itself stores no pan, and no file in this corpus states the meaning.

Observed pans:

| pan | files |
|-----|-------|
| `C C C C C C L R` | `BCAUSE`, `HIPHOUSE`, `JUNGLE`, `RAGE`, `SHYGIRL`, `SLOWUP`, `START`, `SUMMER`, `SWEET`, `UPDOWN`, `VIBE` |
| `C C C C C C R L` | `DUTCH`, `FEEDHIP` |
| `C C C C C C C C` | `MYSELF`, `XDAYS` |
| `C C C C L R R L` | `GOODMOOD` |
| `C C R C C L C C` | `HIPHOP` |

`mixplayer.py` uses these words (0 centre, 1 left, 2 right), so the playback
pan follows each song instead of a hard-coded T7/T8 rule.

## 5. Worked example — `START.MIX`

```
0x0000: 08 0A            signature
0x0002: 01 04            slot(bar 0, track 1) = 1025 -> BH/H1EX021.PXD  "help me"
0x0004: FE 03            slot(bar 0, track 2) = 1022 -> BF/H1EX018.PXD  "hard breath"
0x0006: 71 06            slot(bar 0, track 3) = 1649 -> BH/H1RP056.PXD  "hiphp jam"
...
0x2BE2: 08 0A 01 00 12 00 "HipHop eJay 1.01" 00 01
0x2BFA: 5E 01 00 00 ...   (1 408-byte tables)
0x317A: 01 00 11 2B 00 00 00 00    head [1, 11025, 0, 0]
0x3182: 08 00                     track count
0x3184: 00 00 00 00 00 00 01 00 00 00 00 00 00 00 02 00
         pan  C  C  C  C  C  C  L  R
```

`START.MIX`: 429 bars, 277 placed samples, 65 distinct samples, 1 072.5 s.

## 6. Visualising an arrangement

`mixrender.py` draws one PNG per mix: x = bar, y = track (T1 on top), one
coloured cell per placed sample, ruler every 4 bars (labelled every 8).  The
colour is derived from the sample id alone (`hue = id * 0.618 mod 1`), so a
repeated sample is always the same colour and loops/fills stand out.

```
python apps/emr/src/format/hiphop/mixrender.py --out reverse/hiphop/images --all
python apps/emr/src/format/hiphop/mixrender.py --out reverse/hiphop/images --cell-w 8 --cell-h 22 disks/Hiphop_eJay/MIX/START.MIX
```

PNG is written with `zlib` + `struct` only (no Pillow), 8-bit RGB.  The cell
width defaults to `900 / song_length` clamped to 4..10 px per bar, and the
track rows are `--cell-h` tall.

For listening rather than looking, `mixplayer.py` decodes the `.PXD` samples
([`PXD.md`](PXD.md)) and streams the mix through `sounddevice`; one bar is
exactly 110 250 samples at 96 BPM / 44.1 kHz, so onsets need no resampling.

## 7. Verification

`mixdump.py --verify` parses every file and re-encodes it from the decoded
model (signature, 702×8 grid, bank block): **17/17 files reproduce
byte-identically**.

## 8. Byte accounting

Across the 17 files (215 764 bytes in total):

| region | bytes | status |
|--------|------:|--------|
| signature (`0x0A08`) | 34 | constant; family tag, exact meaning inferred |
| song grid | 190 944 | fully identified |
| block header (tag, `nlists`, length, version + NUL + flag) | 408 | identified |
| the two 704-byte tables | 23 936 | layout identified (350 then 702 zero bytes per half), meaning unknown |
| `head` (4 words) | 136 | positions identified; word 1 unknown, other three constant |
| track-count word | 34 | value 8; identified as the track count by inference |
| `pan` words | 272 | values 0/1/2; meaning inferred (§4c) |
| **total** | **215 764** | |

So **24 072 bytes (11.2 %)** have no established meaning (the tables and the
`head` words), and **340 bytes** (signature 34, track count 34, pan 272) are
identified in position but read by inference.  Every byte of every file is
located, and the writer reproduces all 215 764 of them exactly.

Data-level gaps: none — every one of the 5 488 placements resolves to a shipped
sample file, and both catalogue lists are complete on disk.
