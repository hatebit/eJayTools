# Dance eJay 2 `*.MIX` format

Reversed from the 13 files in `disks/Dance_2/MIX`, cross-checked against
`disks/Dance_2/D_ejay2/PXD/DANCE20` + `DANCE20.INF`, the `DANCESK*` banks and
the standalone `Audio_*` samples.  Nothing under `disks/` was executed.

Other documents: [`README.md`](README.md) (overview, tools),
[`SAMPLES.md`](SAMPLES.md) (sample ids and banks), [`PXD.md`](PXD.md)
(container and codec), [`MIXES.md`](MIXES.md) (per-song statistics),
[`METHOD.md`](METHOD.md) (evidence and unknowns).

Tooling (parser in `libs/mix/dance2/`, adapter in
`apps/emp/src/format/dance2/`):

```
python reverse/dance2/mixdump.py --all                        # readable dump
python reverse/dance2/mixdump.py --json reverse/dance2/decoded --all
python reverse/dance2/mixdump.py --verify --all               # re-encode, byte-compare
```

All fields are little-endian.

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
      event list            variable (may be empty)
end   trailer               4 bytes
```

Files are 1 553 … 8 219 bytes (56 604 bytes for the 13 songs).  There is no
fixed capacity: unused material is omitted instead of zero-filled, which is why
two songs of the same release can differ by a factor of five.

## 2. Header (16 bytes)

| offset | type | field | values in this corpus |
|--------|------|-------|-----------------------|
| `0x00` | `uint16` | signature | `0x0A19` in all 13 files |
| `0x02` | `uint16` | zero | 0 |
| `0x04` | `uint16` | `field_04` | 27, 105, 134, 150, 153, 162, 185, 202, 209, 219, 246, 264, 304 |
| `0x06` | `uint16` | zero | 0 |
| `0x08` | `uint16` | tempo | **140** in all 13 files |
| `0x0A` | `uint16` | `field_0a` | 136, 140, 144, 148, 152 |
| `0x0C` | `uint16` | zero | 0 |
| `0x0E` | `uint16` | `field_0e` | 26, 29, 30 |

`field_04` is plausible as a song length in bars (it ranges from 27 for the
one-minute `STEP` to 304 for `TRANCE`), but no file states that and the pattern
block carries no bar field, so it is documented as unknown.  `field_0a` and
`field_0e` have no established meaning.

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

* author — `MC Magic` (10 files), `Yo!B` (`CAMRON`, `LIFEXL`), `DJ Andy`
  (`TRIBUTE`).
* ident — `#SKKENNUNG#:0000000` (10 files) and one each of `0000001`,
  `0000010`, `0000100`.  `SKKENNUNG` is German for “identifier”; the suffix
  varies but its meaning is unknown.
* title — verbatim, e.g. `Duck Dance`, `The Land of Camron`,
  `Don't Waste My Time Mix`.

## 4. Track table, trailer words and sample set

Immediately after the title come **16 track records**:

```
uint16 pan       0 = both, 1 = left, 2 = right   (reading inferred, see below)
uint16 volume    0 … 32767
```

All 208 words in the corpus take only 0, 1 and 2 for pan.  eJay's mixer has
exactly three speaker buttons per track (both, left, right) and the manual
describes them; that is the evidence for the reading, but the file does not
state it.  Volumes are `26699` (104 records), `26800` (64) and 40 further
records between 9 304 and 32 767 (31 distinct values).

The 16 tracked lanes exclude the drum track.  eJay's track list shows an
extra **track “0”**, which the manual identifies as the separate **Drum Track**;
its ten pads and its pattern are stored later in the file, not in this table
(§6, §7).

Then six words, constant `0, 0, 0, 0, 0, 16` in all 13 files.  The last word is
the visible track count; the five zeros are unexplained.

The sample-set string follows: `Dance eJay 2.0`, NUL, `0x01`, then a `uint16`
marker that is **9** in every file.  Its meaning is unknown.

## 5. Sample-kit boxes

A box declares an id range and the product that supplies it:

```
uint32 lo, uint32 hi, uint16 length, characters, NUL, 0x01
```

The list ends with eight zero bytes (`uint32 0, uint32 0`).  Every song has the
same **seven** boxes and ranges:

| ids | name |
|-----|------|
| 2 000 … 3 399 | `DanceMachine Samples` (9 files) / `DanceMachine` (4: `HAPPY`, `LIFEXL`, `OTHER`, `YOURTIME`) |
| 3 400 … 3 899 | `DanceMachine Samplekit Vol. 1 Raps & Voices` |
| 3 900 … 4 499 | `DanceMachine Samplekit Vol. 2 Drums & Synthies` |
| 4 500 … 5 099 | `DanceMachine Samplekit Vol. 3 Space Sounds` |
| 5 100 … 5 799 | `Dance eJay Samplekit Vol. 4 House` |
| 5 800 … 6 499 | `Dance eJay Samplekit Vol. 5 Trance` |
| 6 500 … 7 199 | `Dance eJay Samplekit Vol. 6 Latin Dance` |

The id fields are not the format's only source of names: they are what eJay
uses to grey out or resolve add-on kits.  The shipped add-on containers cover
Vol. 4–6 (`DANCESK4/5/6`, §2 of [`SAMPLES.md`](SAMPLES.md)); the first four
boxes have no shipped audio, and the base `DANCE20` container uses ids
`1 … 1957`, below the first box.

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
uint16    sample id       DANCE20.INF id (1 … 1957)
uint16    length          characters + 2
byte[]    name, NUL, 0x01
int16     pitch           -12 … +12 in this corpus
uint16    word2           0 or 65535
uint16    word3           10 559 … 29 490 (26 578 in 90 of 130 pads)
uint16    word4           0 (95), 1 (17), 2 (18)
```

The ten pads are the Groove Generator drum pads of eJay's drum track.  The
sample ids resolve: across the corpus there are 130 pads and 81 distinct ids,
all found in `DANCE20.INF` (for example `STEP` uses id 1930 `humn.9` ten times
at nine distinct pitches, −10 … +4).  `pitch` is a signed semitone
transpose.  The three 16-bit words are not interpreted; `word4` taking only
0/1/2 suggests an enumeration (pan, mute or loop mode), but that is a guess
and is not relied on.

## 7. Pattern block — two record shapes, timing decoded

Between the last pad and the first event (or the trailer, when there are no
events) sits the song's **drum pattern**.  It is 149 … 3 474 bytes per song,
27 241 bytes over the corpus (48.1 % of all bytes).

The block opens with a **22-byte preamble** whose eleven words are not
interpreted and differ from song to song.  Then come seventeen section
headers, each

```
uint8   index      1 … 17
uint16  count      records in the section
uint16  0
```

Section `n` for `n` = 1 … 16 is track `n` — checked on `OTHER.MIX` against the
arrangement eJay shows, where the two-record sections 13 and 14 are exactly
the tracks holding those samples — and holds `count` records in time order.
Section 17 has no records: its `count` is the number of imported-sample
**events** (`93` in `CAMRON`, `16` in `STEP`, `0` in the five songs without
events) and equals the length of the event list in all thirteen files.  This
accounts for every byte of all thirteen blocks, and `decode_pattern` now
decodes all thirteen.

A section mixes two record shapes.  The word at offset 3 selects which:
`0xFFFF` marks a seven-byte **clip**, any other value a seventeen-byte **hit**.

```
clip  uint8   byte0      0 (2 559 clips) or 3 (1 095)
      uint8   byte1      sub-block offset, counted down
      int8    block      -1 … -88, the negated two-bar block index
      uint16  word       0xFFFF
      uint16  sample id  500 distinct, every one present in a shipped bank

hit   uint32  position   1/32 768 bar per unit
      uint8   0
      uint16  sample id
      byte[8] 0          in every hit seen
      uint16  unknown    AF EB, F0 FB, BF EF, 31 0C, 5E C9 … FF 3F
```

A **clip** starts at

```
start bar = 2 · |block| - 1 + (255 - byte1) / 128
```

so `block` indexes two-bar blocks (block 1 = bars 1-2, block 2 = bars 3-4, …)
and `byte1` counts *down* inside the block in units of 1/128 bar; 3 647 of the
3 654 clips land on a sixteenth of a bar (`(255 - byte1) / 8` whole).  A
**hit** starts at `position / 32 768 + 1` bars; all sixteen hits lie within
three units of a whole bar (bars 1-12 in `OTHER`, and 15, 19, 20, 21 in
`LATIN`).

The reading was checked against `OTHER.MIX`, whose first ten bars are known
from eJay: `summer time***** bloose 1L` (id 270) and `bloose 1R` (271) at
bar 5, `bloose 2L` (272) and `bloose 2R` (273) at bar 9, `grave beat 2`
(id 711) on track 3 at bar 9, and a one-bar `heart beat` (id 502) on track 8 in
every bar.  Sections 13 and 14 hold exactly those two `bloose` records each, at
`block` 3 and `block` 5 with `byte1` 255 — bars 5 and 9; section 3 begins with
id 711 at `block` 5 — bar 9; and section 8 holds twelve `heart beat` hits at
positions 0 … 0x58000 — bars 1 … 12.  The `bloose` samples are 302 399 frames,
four bars, so bars 5 and 9 are adjacent.

Two further properties hold across all thirteen files.  With this mapping every
one of the 187 non-empty track sections runs in non-decreasing time order; the
opposite reading of `byte1` breaks 59 of them.  And one-bar samples pair up on
consecutive bars, for example `OTHER` track 7, where ids 975 and 976 sit at
bars 23 and 24 (`byte1` 255 and 127) and ids 977 and 978 at bars 25 and 26.

Uninterpreted in this block: `byte0` of a clip (0 or 3), the ten bytes after a
hit's sample id, why only `LATIN` and `OTHER` use the hit form (16 records in
total), and the preamble.  A clip stores no length: the sample itself is 1, 2,
3, 4, 5 or 8 bars long (all within a few frames of a whole bar) and the next
record on the same track marks where the clip stops being needed.  How eJay
trims or loops a sample that is longer than that gap is not recorded in the
file, so `mixplayer.py` cuts the clip at the next record's start and never
loops or stretches it.

The block being the drum track follows from process of elimination: the pads are
the only other drum content, the manual describes one drum track separate from
the 16 audio tracks, and the block is the only region large enough to hold a
whole song's pattern.

## 8. Imported-sample events

Each event is a 27-byte tail followed by two length-prefixed strings:

```
byte[27]  tail
uint16    length 1, characters, NUL, 0x01      sample name
uint16    length 2, characters, NUL, 0x01      decimal number (may be empty)
```

Tail fields decoded in this corpus:

| offset | type | field | values |
|--------|------|-------|--------|
| 0 | `uint8` | kind | 2 in all 449 events |
| 1 | `uint8` | channel | `0x7F` (231) / `0xFF` (218) |
| 2 | `int24` | pitch | −71 … −1 |
| 5 | `uint16` | instance | 7200 … 7335 |
| 7 | 20 bytes | unknown | preserved verbatim |

The two strings are the imported sample's name and a decimal field (empty in
`STEP`, otherwise values `1 … 71`).  In most songs every event shares one name
(`Happy`, `B!Yo_1`, `Lifestyle`, …), which suggests a repeated imported sample
such as a vocal hook; `STEP` instead carries a sentence split at the file's
own word breaks: `You`, `can`, `even`, `create`, … `generat`, `or   if`,
`you`, `want`, `!!!!`, then one empty string.  The event list is absent
entirely in `HOUSE`, `LATIN`, `OTHER`, `TRANCE` and `TRIBUTE` (their pattern
block runs straight into the trailer).

## 9. Trailer

Four bytes `A9 7A 8A 01` (`uint32 0x018A7AA9`) in all 13 files.  The parser
checks it, the writer reproduces it.

## 10. Worked example — `STEP.MIX` (1 553 bytes)

```
0x0000  19 0A 00 00 1B 00 00 00 8C 00 8C 00 00 00 1E 00
        sig 0x0A19   f04=27    bpm=140  f0a=140    f0e=30
0x0010  "MC Magic" 00
0x0019  "#SKKENNUNG#:0000000" 00
0x002D  01 0C 00 "Duck Dance" 00 01
0x003C  16 x (pan, volume)                          64 bytes
0x007C  00 00 x5, 10 00                              track count 16
0x0088  "Dance eJay 2.0" 00 01
0x0098  09 00                                       marker
0x009A  D0 07 00 00 | 47 0D 00 00 | 16 00 | "DanceMachine S…"
        lo=2000      hi=3399      len=22
...
0x01EF  00 x 8                                      box terminator
0x01F7  02 00 00 01 00 x8  02 00 00 01 00 x8  02 00 00 01
0x0213  02 00 00 01 | 8A 07 | 08 00 | "humn.9" 00 01 | F6 FF
        00 00 | D2 67 | 00 00
        pad 1: id 1930, pitch -10, word2 0, word3 26578, word4 0
0x0303  149-byte pattern block                     (0x0303 … 0x0397)
0x0398  02 FF FF FF FF 98 1C 01 00 04 41 00 … 00
        kind 2, channel 0xFF, pitch -1, instance 7320, 20 unknown bytes
0x03B3  05 00 "You" 00 01   02 00 00 01
        name record (len 5 = 3 + 2), empty number record (len 2 = 0 + 2)
0x03BE  second event, 16 events in total …
0x060D  A9 7A 8A 01                              trailer
```

The first box is `2000 … 3399` in every file; the pattern is the 149 bytes
`0x0303 … 0x0397`; the 16 events fill `0x0398 … 0x060C`.  The second event's
tail starts `02 7F FF FF FF 99 1C …` (channel 0x7F, pitch −1, instance 7321), so
both channel values and consecutive instance numbers occur inside one file.

## 11. Verification and byte accounting

`mixdump.py --verify --all` reports **13/13 byte-identical**.

Across 56 604 bytes:

| region | bytes | status |
|--------|------:|--------|
| headers, strings, track table, trailer words, sample set, marker | 2 080 | identified except three header words (`field_04`, `field_0a`, `field_0e`) and the constant marker 9 |
| seven kit boxes + terminator | 4 505 | identified |
| pad prefix | 364 | positions identified; dead records |
| 130 pad records | 3 285 | id, name, pitch identified; `word2/word3/word4` unknown |
| pattern block | **27 241** | 22-byte preamble, 17 section headers, 3 654 clips and 16 hits with start bars; clip `byte0`, hit tails and preamble unknown |
| 449 event tails | 12 123 | 7 of 27 bytes decoded; 20 unknown |
| event names/numbers | 6 954 | identified |
| trailer | 52 | constant |

What has no established meaning is the 22-byte preamble of each block (286
bytes), the leading byte of each clip (3 654 bytes), the ten trailing bytes of
the sixteen hits (160 bytes), 8 980 bytes of event-tail payload (20 × 449),
780 bytes of pad-tail words and 78 bytes of header words: **13 938 bytes
(24.6 %)**.  Every byte is nevertheless located and reproduced exactly.
