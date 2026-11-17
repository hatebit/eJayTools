# Rave eJay `*.MIX` format

Reversed from the 15 files in `disks/Rave_eJay/MIX`, cross-checked against
`disks/Rave_eJay/RAVE/EJAY/PXD` (sample catalogue) and the `tPxD` headers of the
sample files.  No binary from the repository was executed; everything below
comes from reading the data files.

Other documents: [`README.md`](README.md) (doc map, tools),
[`SAMPLES.md`](SAMPLES.md) (id → `.PXD`, low ids, HYPER),
[`MIXES.md`](MIXES.md) (per-song statistics), [`METHOD.md`](METHOD.md)
(evidence and unknowns), [`PXD.md`](PXD.md) (container and codec).

Tooling (parser in `libs/mix/rave/`, adapter in
`apps/emp/src/format/rave/`):

```
python reverse/rave/mixdump.py --all                        # readable dump of every mix
python reverse/rave/mixdump.py --json reverse/rave/decoded --all
python reverse/rave/mixdump.py --verify --all               # re-encode, byte-compare
python apps/emr/src/format/rave/mixrender.py --out reverse/rave/images --all   # arrangement PNGs
```

## 1. Overall layout

All files are little-endian.

| offset   | size    | field |
|----------|---------|-------|
| `0x0000` | 2       | `uint16` signature, `0x0A07` in all 15 files |
| `0x0002` | 11 232  | song grid: `702 * 8` `uint16` sample ids |
| `0x2BE2` | variable| sample-bank block (§4); every file has one |

`0x2BE2 = 2 + 702*8*2`.  The grid is allocated for the maximum song length;
the tail of the grid is zero-filled, so the real song length is derived from
the data (§2).  The 15 files are 11 276 bytes (14 files, 42-byte bank block)
and 11 326 bytes (`NODRUGS.MIX`, 92-byte block); the corpus is 169 190 bytes.

Tempo is **not** stored: the samples are cut at **180 BPM, 4/4**, so one bar is
`4 * 60/180 = 4/3 ≈ 1.333 s` and 58 800 samples at 44.1 kHz.  The maximum grid
(702 bars) is ≈ 936 s ≈ 15.6 minutes.

## 2. Song grid

The grid is **bar-major with the 8 tracks interleaved**:

```
slot(bar, track) = 0x0002 + (bar * 8 + track) * 2      bar = 0..701, track = 0..7
value            = sample id, 0 = empty slot
```

Evidence: the file size is exactly `2 + 702*8*2` plus the bank block; sample
ids recur at a period of 8 words and never repeat inside a bar; every slot
index (mod 8) behaves as one continuous instrumental lane across a whole song
(`MIXES.md` §4 shows `START.MIX` lane by lane); and the corpus reaches exactly
8 occupied slots in a bar (50 bars), the ceiling for 8 tracks.

* `track` is the position in the eJay track list (0-based; the GUI shows
  T1..T8).  The tracks are mono lanes and the grid stores no pan value.
  Unlike Dance eJay, this corpus does **not** put every `… L` sample on T7 and
  every `… R` sample on T8: of 871 placements whose label ends in `L` or `R`,
  308 are on T7 and 309 on T8, but 127 are on T6, 62 on T5, 28 on T3, 23 on T2,
  11 on T4 and 3 on T1, sometimes with both halves on one track.  The player
  therefore mixes all tracks centred rather than inventing a pan rule.
* `song_length` = index of the last bar with any non-zero slot, plus 1.  It
  includes unresolved low ids (`1..15`), so the grid can be much longer than
  the audible content: `VIENI` reaches bar 526, but its last shipped sample
  ends at bar 221.  `mixplayer.py` plays to the end of the grid and further
  only if the last placed sample with shipped audio rings out beyond it.
* time of a bar = `bar * 4/3` seconds.

## 3. Sample ids

A grid value is a **slot in eJay's sample bank**, not a line number in
`MAX`: `731 + n` is record `n` of `RAVE/EJAY/PXD` (1 149 records of six quoted
fields — path, empty, category, nominal bars, group, name).  The browser label
is `group + " " + name`, which is what `START.MIX` shows in its first bars:

| id   | record | file            | label |
|------|-------:|-----------------|-------|
| 1094 | 363    | `AB/R1FX018.PXD`| `thumb` |
| 1075 | 344    | `BN/R1FX001L.PXD`| `scream L` |
| 1076 | 345    | `BJ/R1FX001R.PXD`| `scream R` |
| 1846 | 1115   | `BR/R1VX102.PXD`| `this is  MC magic` |
| 1018 | 287    | `BN/R1DC037.PXD`| `hihat distorted 1` |
| 1400 | 669    | `AE/R1SF096.PXD`| `distorted motion 1` |
| 1850 | 1119   | `BQ/R1VX106.PXD`| `life in space` |
| 1755 | 1024   | `BR/R1VX016.PXD`| `eJay 5` |

The catalogue's numeric field is the **nominal loop length in bars**: it equals
`declared_count / 58 800` exactly for 1 145 of the 1 149 records.  The four
exceptions are listed in [`SAMPLES.md`](SAMPLES.md) §1; all are within 3.2 % of
the nominal value.

`MAX` (3 145 entries) and `MIN` (860) are installation manifests in
folder-sorted order: useful to know which files exist, but not the id order.
The Rave file names (`R1BS001`, `R1VX102`, …) are not a base-26 index.

Ids `731..1879` exist on disk (the 1 149 samples in folders `AA…AK` / `BA…BS`,
exactly the `PXD` records); ids `1..15` are used but have no shipped audio,
`16..730` are empty, and this corpus uses no add-on box ids.
`RAVE/EJAY/INTRO.PXD` is a `tPxD` sample, not a song; `RAVE/HYPER` is a
separate 128-sample bank.  See `SAMPLES.md`.

Special values seen in the grid:

* `0` – empty slot.
* `1..15` – used in nine songs (174 placements), no shipped sample; eJay's
  mapping for these slots is unknown.
* `16..730` – not used by any shipped song (empty import slots).
* `731..1879` – the `RAVE/EJAY/PXD` catalogue (`id = 731 + record index`).

## 4. Bank block (appended)

Every one of the 15 files carries a block.  It uses the same v8 shape as the
Dance eJay `0x0A08` block — tag, list count, version string with NUL and flag,
then one or more box lists — but Rave writes **one empty list and no boxes**,
followed by a trailer that is kept verbatim:

```
uint16  tag         0x0A08
uint16  nlists      1
uint16  len         16
byte    version[16] "Rave eJay 1.01" + NUL + 0x01
uint16  count       0                  (one empty box list)
byte    trailer[18 or 68]
```

The trailer is the only part that differs between files:

| file(s) | trailer | bytes |
|---------|---------|------:|
| 12 files (`EARTH`, `GALACTIC`, `MAGIC`, `OHEJAY`, `PSYCOA`, `START`, `TRANCE`, `VIENI`, `WARP`, `WOOF`, `XENON`, `XWING`) | `08 00` + 12 × `00` + `01 00 02 00` | 18 |
| `LAJALI`, `SCOOL` | `08 00` + 8 × `00` + `01 00 02 00` + `01 00 02 00` | 18 |
| `NODRUGS` | the 18-byte standard trailer + 50 extra bytes | 68 |

The first word of the trailer is **8**, the number of tracks the grid is
divided into; that is the only field in it with a supported reading.  The
50 extra bytes of `NODRUGS` look like a trailing fragment of a serialised
sample reference: `"ool"`, then a length-prefixed `"004"`, a length-prefixed
path `c:\raveejay\hypersav\scool004.wav`, and a length-prefixed `"hyper"`.
They are preserved byte for byte and not interpreted further.

Names and version strings are raw bytes in the program's code page (read as
latin-1).  The block is written back from the parsed fields, including the
verbatim trailer, which is why every file re-encodes exactly.

## 5. Worked example — `START.MIX`

```
0x0000: 07 0A            signature
0x0008: 46 04            slot(bar 0, track 4)  = 1094 -> AB/R1FX018.PXD  "thumb"
0x000E: 33 04            slot(bar 0, track 7)  = 1075 -> BN/R1FX001L.PXD "scream L"
0x0010: 34 04            slot(bar 0, track 8)  = 1076 -> BJ/R1FX001R.PXD "scream R"
0x0012: 36 07            slot(bar 1, track 1)  = 1846 -> BR/R1VX102.PXD  "this is  MC magic"
0x0026: FA 03            slot(bar 2, track 3)  = 1018 -> BN/R1DC037.PXD  "hihat distorted 1"
0x002A: 78 05            slot(bar 2, track 5)  = 1400 -> AE/R1SF096.PXD  "distorted motion 1"
0x0032: 3A 07            slot(bar 3, track 1)  = 1850 -> BQ/R1VX106.PXD  "life in space"
0x0046: FA 03            slot(bar 4, track 3)  = 1018 -> BN/R1DC037.PXD  "hihat distorted 1"
0x004C: DB 06            slot(bar 4, track 6)  = 1755 -> BR/R1VX016.PXD  "eJay 5"
```

`START.MIX`: grid 115 bars, 221 placed samples, 63 distinct samples, 153.3 s;
the last placed sample ends at bar 117.  It has no low-id placements, so its
grid is exactly the audible arrangement.  Songs whose tails are padded with
unresolved low ids are noted in `MIXES.md` §3.

## 6. Visualising an arrangement

`mixrender.py` draws one PNG per mix: x = bar, y = track (T1 on top), one
coloured cell per placed sample, ruler every 4 bars (labelled every 8).  The
colour is derived from the sample id alone (`hue = id * 0.618 mod 1`), so a
repeated sample is always the same colour and loops/fills stand out.  The
canvas runs to the last ringing tail of a sample with shipped audio, as the
player does, so it can be wider than the grid.

```
python apps/emr/src/format/rave/mixrender.py --out reverse/rave/images --all
python apps/emr/src/format/rave/mixrender.py --out reverse/rave/images --cell-w 8 --cell-h 22 disks/Rave_eJay/MIX/START.MIX
```

PNG is written with `zlib` + `struct` only (no Pillow), 8-bit RGB.  The cell
width defaults to `900 / bars` clamped to 4..10 px per bar (override with
`--cell-w`), and the track rows are `--cell-h` tall.

For listening rather than looking, `mixplayer.py` decodes the `.PXD` samples
(`PXD.md`) and streams the mix through `sounddevice`; one bar is exactly
58 800 samples at 180 BPM / 44.1 kHz, so onsets need no resampling.

## 7. Verification

`mixdump.py --verify` parses every file and re-encodes it from the decoded
model (signature, 702×8 grid, bank block): **15/15 files reproduce
byte-identically**, including both trailer variants and the 50 extra bytes of
`NODRUGS.MIX`.

## 8. Byte accounting — what is still unknown

Across the 15 files (169 190 bytes in total):

| region | bytes | status |
|--------|------:|--------|
| signature (`0x0A07`) | 30 | value constant; format tag, exact meaning inferred |
| song grid | 168 480 | fully identified |
| bank-block tag, `nlists`, version length | 90 | fully identified |
| version string + NUL + flag | 240 | text identified; the trailing `0x01` flag (15 bytes) unknown |
| empty-list count (`00 00`) | 30 | identified as an empty box list |
| bank trailer | 320 | first word `8` = track count (inferred); 290 bytes unknown |
| **total** | **169 190** | |

So **290 trailer bytes + 15 version-flag bytes = 305 bytes (0.18 %)** have no
confirmed meaning, and the 30 signature bytes are constant but read as a format
tag rather than a decoded field.  Every byte of every file is located, and the
writer reproduces all 169 190 of them exactly.

Data-level gaps (the bytes are understood, the samples are not):

* 174 placements use ids `1..15`; no file for those ids is shipped, so the
  sample identity is unknown (`SAMPLES.md` §5);
* the 128 `RAVE/HYPER` samples are not referenced by any id in `731..1879`,
  and are not assumed to fill the low slots;
* the 50 extra `NODRUGS` trailer bytes name a `hypersav\scool004.wav`, which is
  a lead to how that song was built but not a grid-id mapping.
