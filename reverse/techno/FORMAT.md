# Techno eJay 2 `*.MIX` format

Reversed from the 13 files in `disks/Techno_eJay/MIX`, cross-checked against
`disks/Techno_eJay/EJAY/PXD/RAVE20` + `RAVE20.INF` and the standalone
`EJAY/PXD/HYP1` … `HYP4` samples.  Nothing under `disks/` was executed.

Other documents: [`README.md`](README.md) (overview, tools),
[`SAMPLES.md`](SAMPLES.md) (sample ids and banks), [`PXD.md`](PXD.md)
(container and codec), [`MIXES.md`](MIXES.md) (per-song statistics),
[`METHOD.md`](METHOD.md) (evidence and unknowns).

Tooling (parser in `libs/mix/techno/`, adapter in
`apps/emp/src/format/techno/`):

```
python reverse/techno/mixdump.py --all                        # readable dump
python reverse/techno/mixdump.py --json reverse/techno/decoded --all
python reverse/techno/mixdump.py --verify --all               # re-encode, byte-compare
```

All fields are little-endian.  The layout is the same section sequence as Dance
eJay 2 (`reverse/dance2/FORMAT.md`); the signature, the strings, the id space
and the record contents differ.  The two trees share no code.

## 1. Overall layout

A song is a sequence of variable-length sections, not a fixed grid:

```
0x00  header                16 bytes
      author string
      identification string
      title record
      16 x track record     64 bytes
      six trailer words     12 bytes
      sample-set string
      uint16 marker
      kit boxes             7 x (8 + 2 + name), then 8 zero bytes
      pad prefix            28 bytes
      10 x pad record
      pattern block         variable
      event list            absent in this corpus
end   trailer               4 bytes
```

Files are **2 144 … 6 236 bytes** (52 369 bytes for the 13 songs).  There is no
fixed capacity: unused material is omitted instead of zero-filled.

## 2. Header (16 bytes)

| offset | type | field | values in this corpus |
|--------|------|-------|-----------------------|
| `0x00` | `uint16` | signature | **`0x0889`** in all 13 files |
| `0x02` | `uint16` | zero | 0 |
| `0x04` | `uint16` | `field_04` | 111, 129, 145, 149, 156, 217, 223, 236, 249, 250, 310, 391 |
| `0x06` | `uint16` | zero | 0 |
| `0x08` | `uint16` | tempo | **140** in all 13 files |
| `0x0A` | `uint16` | `field_0a` | 134, 135, 137, 140, 145, 146, 158 |
| `0x0C` | `uint16` | zero | 0 |
| `0x0E` | `uint16` | `field_0e` | 24, 28, 30 |

`field_04` is plausibly a song length in bars, but no field states that and the
pattern block carries no such value; it is documented as unknown.  `field_0a`
and `field_0e` have no established meaning.

Tempo matters for timing only: eJay cuts its samples at 140 BPM 4/4, so one
bar is `4 × 60/140 = 12/7 ≈ 1.714 s` = **75 600 samples** at 44.1 kHz.

## 3. Strings and the title record

Three different encodings appear in the same file:

```
author:      latin-1 characters, NUL
ident:       latin-1 characters, NUL
title:       0x01, uint16 length, characters, NUL, 0x01
```

`length` counts the characters plus the two trailing bytes.  Writers must keep
the three forms distinct: the author and identification strings have no flag
byte, the title has a leading `0x01` and a trailing NUL + `0x01`.

Values:

* author — `Daniel` (7 files), `mc magic` (4), `Le Teque` (1), `Jo` (1).
* ident — `#SKKENNUNG#:0000000` in all 13 files.
* title — verbatim, e.g. `here we go`, `Melodesk`, `sis is what se dj  does`
  (two spaces in the file).

## 4. Track table, trailer words and sample set

Immediately after the title come **16 track records**:

```
uint16 pan       0 = both, 1 = left, 2 = right   (reading inferred, see below)
uint16 volume    0 … 32767
```

The 259 pan words take 0 (109), 1 (46), 2 (52) and, once, 3 (`SOAP.MIX` track
16).  The reading of 0/1/2 is inferred: it is the Dance eJay 2 convention, the
range fits, and `…L`/`…R` sample pairs concentrate on the tracks read as left
and right (512 of the 890 left-track records are labelled `…L`, 503 of the 927
right-track records are labelled `…R`).  The single 3 is unexplained.

Volumes span 10 214 … 32 767 and are not applied by the player.

Then six words: `0, 0, 0, 0, 0, N` where `N` is **14** in `BUBBLE.MIX` and
`STRAIGHT.MIX`, **16** in the other eleven files.  The last word is the visible
track count; the five zeros are unexplained.

The sample-set string follows.  It is `Techno eJay 2 ` (14 chars) in eleven
files and `Techno eJay ` in the two 14-track songs; then `0x01`, then a `uint16`
marker that is **9** in every file.  Its meaning is unknown.

## 5. Sample-kit boxes

A box declares an id range and the product that supplies it:

```
uint32 lo, uint32 hi, uint16 length, characters, NUL, 0x01
```

The list ends with eight zero bytes (`uint32 0, uint32 0`).  Every song has the
same **seven** boxes and ranges:

| ids | name (11 songs) | name (2 songs) |
|-----|-----------------|----------------|
| 2 000 … 3 399 | `DanceMachine` | `Dance eJay 1.0` |
| 3 400 … 3 899 | `DanceMachine Samplekit Vol. 1 Raps & Voices` | same |
| 3 900 … 4 499 | `DanceMachine Samplekit Vol. 2 Drums & Synthies` | `Dance eJay Samplekit Vol. 2 Drums & Synthés` |
| 4 500 … 5 099 | `DanceMachine Samplekit Vol. 3 Space Sounds` | `Dance eJay Samplekit Vol. 3 Space Sounds` |
| 5 100 … 5 799 | `Dance eJay Samplekit Vol. 4 House` | same |
| 5 800 … 6 499 | `Dance eJay Samplekit Vol. 5 Trance` | same |
| 6 500 … 7 199 | `Dance eJay Samplekit Vol. 6 Latin Dance` | same |

The ranges are **not** the id space the arrangements use: no record in the 13
songs has an id in `2 000 … 7 199`.  The boxes are inherited product
declarations; the player ignores them and looks all ids up in `RAVE20.INF`
(§8 of [`SAMPLES.md`](SAMPLES.md)).

## 6. Pad prefix and the ten drum pads

After the box terminator comes a **28-byte prefix** that is byte-identical in
all 13 files:

```
02 00 00 01  00 x 8        empty pad record
02 00 00 01  00 x 8        empty pad record
02 00 00 01                record tag
```

Then exactly **10 pad records**, each:

```
uint8[4]  02 00 00 01
uint16    sample id       0 in all 130 records
uint16    length          characters + 2
byte[]    name, NUL, 0x01
int16     pitch           -7 … 0 in this corpus
uint16    word2           0 in every record
uint16    word3           17 840 … 26 578
uint16    word4           0 (…), 1, 2
```

The ten names are identical in every file, in this order: `eurokick5`,
`elec.sn 2`, `808cl.hat2`, `808op.hat`, `crash2`, `clap8`, `darabuka2`,
`egg2`, `hit5`, `humn.13`.  They are old Dance eJay drum-machine names and are
**not** present in `RAVE20.INF`; with sample id 0 there is nothing to resolve,
so these pads are metadata and do not contribute to playback.

## 7. Pattern block — two record shapes, timing decoded

Between the last pad and the trailer sits the song's entire arrangement.  It is
1 354 … 5 465 bytes per song, **42 199 bytes over the corpus (80.6 % of all
bytes)**.

The block opens with a **22-byte preamble**:

```
00 00 ff 7f 9e 3f 00 00 5f 20 7f 3e 00 00 3e 3f 7e 3e   constant, 18 bytes
uint16  pattern length - 18                               e.g. 4428 for 4446 bytes
uint16  0
```

The first 18 bytes are identical in all thirteen files, and the next word is
exactly `len(pattern) - 18` in every file.  The meaning of the first 18 bytes is
unknown; the final word is always 0.

Then come seventeen section headers, each

```
uint8   index      1 … 17
uint16  count      records in the section
uint16  0
```

Section `n` for `n` = 1 … 16 holds `count` records of **track `n`** in time
order.  Section 17 has no records: its `count` is the imported-event count and
is **0** in all thirteen files, matching the absent event list.

A section mixes two record shapes.  The word at offset 3 selects which:
`0xFFFF` marks a seven-byte **clip**, any other value a seventeen-byte **hit**.

```
clip  uint8   byte0      0 in all 4 562 clips
      uint8   byte1      sub-block offset, counted down
      int8    block      -1 … -100, the negated two-bar block index
      uint16  word       0xFFFF
      uint16  sample id  362 distinct, every one present in RAVE20.INF

hit   uint32  position   1/32 768 bar per unit
      uint8   0
      uint16  sample id
      byte[8] 0          in every hit seen
      uint16  unknown    varies
```

A **clip** starts at

```
start bar = 2 · |block| - 1 + (255 - byte1) / 128
```

so `block` indexes two-bar blocks (block 1 = bars 1-2, block 2 = bars 3-4, …)
and `byte1` counts *down* inside the block in units of 1/128 bar; 4 430 of the
4 562 clips land on a whole bar, the rest on fractions such as 1/2 or 1/8.
A **hit** starts at `position / 32 768 + 1` bars; 404 of the 522 hits land on a
whole bar and the rest on fractions (for example 30.9375).  Clip starts span
bars 1 … 199 and hit starts bars 1 … 217.

All **5 084** records run in non-decreasing time order inside their track, and
every record's start bar lies in bars 1 … 217.

Uninterpreted in this block: a clip's `byte0` (only 0 is seen), the ten bytes
after a hit's sample id, and the first 18 preamble bytes.  A clip stores no
length: the sample itself is 1, 2, 3, 4, 6, 7, 8, 10 or 16 whole bars (one
record is 76 040 samples, slightly over one bar).  The next record on the same
track marks where the clip stops being needed.  How eJay trims or loops a
sample longer than that gap is not recorded in the file, so `mixplayer.py` cuts
the clip at the next record's start and never loops or stretches it.

## 8. Imported-sample events

None.  In all 13 files the pattern block runs straight into the trailer.
Section 17's count is 0, so the parser's event list is empty by construction.

## 9. Trailer

Four bytes `A9 7A 8A 01` (`uint32 0x018A7AA9`) in all 13 files.  The parser
checks it, the writer reproduces it.

## 10. Worked example — `START.MIX` (5 225 bytes)

```
0x0000  89 08 00 00 EC 00 00 00 8C 00 92 00 00 00 1E 00
        sig 0x0889   f04=236  bpm=140  f0a=146        f0e=30
0x0010  "mc magic" 00
0x0019  "#SKKENNUNG#:0000000" 00
0x002D  01 0C 00 "here we go" 00 01
0x003C  16 x (pan, volume)                          64 bytes
0x007C  00 00 x5, 10 00                              track count 16
0x0088  "Techno eJay 2 " 00 01
0x0098  09 00                                       marker
0x009A  D0 07 00 00 | 47 0D 00 00 | 16 00 | "DanceMachine" 00 01
        lo=2000      hi=3399      len=22
...     7 boxes, then 00 x 8
...     28-byte pad prefix, then 10 pads (all id 0)
0x0307  pattern block                              4 446 bytes
        00 00 ff 7f 9e 3f 00 00 5f 20 7f 3e 00 00 3e 3f 7e 3e
        4C 11 00 00                                4 428 = 4 446 - 18
        01 04 00 00 00                             section 1, 4 records
        00 FF EB FF FF FA 35                       clip: block 21, bar 41, id 13818
        ...                                        5 084 records are not; 467 here
0x1465  A9 7A 8A 01                                trailer
```

`START.MIX` places 467 records (360 clips, 107 hits) on 16 tracks over 134
bars.  Six tracks carry pan 0; the other ten are split five left
(T7/T9/T11/T13/T15) and five right (T8/T10/T12/T14/T16).

## 11. Verification and byte accounting

`mixdump.py --verify --all` reports **13/13 byte-identical**.

Across 52 369 bytes:

| region | bytes | status |
|--------|------:|--------|
| headers, strings, track table, trailer words, sample set, marker | 1 873 | identified except three header words (`field_04`, `field_0a`, `field_0e`) and the constant marker 9 |
| seven kit boxes + terminator | 4 605 | identified |
| pad prefix | 364 | positions identified; dead records |
| 130 pad records | 3 276 | name, pitch identified; sample id 0, `word3`/`word4` unknown |
| pattern block | **42 199** | preamble size word, 17 headers and 5 084 records with start bars; clip `byte0`, hit tails and 18 preamble bytes unknown |
| event list | 0 | absent |
| trailer | 52 | constant |

Every byte is located and reproduced exactly.
