# Sample ids, the sample banks and `.PXD` files

How a `uint16` in a Dance eJay 2 song becomes a sample record, and what this
copy of the data actually ships.

## 1. The base library: `PXD/DANCE20` + `DANCE20.INF`

`DANCE20` is **one 231 270 914-byte file** containing **1 957 concatenated
`tPxD` streams**.  `DANCE20.INF` is its index, a text file with a short header,
a `[SAMPLES]` line and then **twelve lines per record** (line endings are
plain CRLF, `\r\n`):

```
sample id     1 … 1957
bank          1 (all records)
file name     D5MA060, D5LY769R, …      (8.3 stem, no extension)
offset        byte offset into DANCE20
length        stream length in bytes
group         e.g. "humn.", "euro", "HR16"
name          e.g. "kick3", "9"
flag 1        small integer
flag 2        small integer
"" 0 ""       three fixed trailing lines
```

* **Records are ordered by file offset, not by id.**  The first record is id
  **1512** (`euro kick3`), the last is id **970**; every id `1 … 1957` occurs
  exactly once.
* Offsets are contiguous: record *n* starts where record *n−1* ends, the first
  starts at 0 and the last ends at 231 270 914, so the index covers the whole
  container without gaps or overlap.
* The label is `group + " " + name`, e.g. id 1930 → `humn. 9`; the pad name in
  the song is the unspaced form `humn.9`.
* Ids are therefore **looked up in the index**, not computed as `base + index`
  (unlike the eJay 1.x banks).  The id field is authoritative.

The pad records of the 13 songs use **81 distinct ids**, and all 130 pad
placements resolve to an index record.  `STEP.MIX` is a compact example: all ten
pads use id 1930 (`humn. 9`, `D5MG539`) at nine distinct pitches.

## 2. The add-on banks: `DANCESK4/5/6`

Three further concatenated containers are shipped next to `DANCE20`:

| container | bytes | records | ids | bank | covers box |
|-----------|------:|--------:|-----|-----:|------------|
| `DANCESK4` | 101 567 584 | 598 | 5100 … 5703 | 3 | Vol. 4 House (5100 … 5799) |
| `DANCESK5` | 107 149 698 | 677 | 5800 … 6476 | 4 | Vol. 5 Trance (5800 … 6499) |
| `DANCESK6` | 88 536 324 | 564 | 6500 … 7063 (+ one id 0) | 5 (563), 0 (1) | Vol. 6 Latin Dance (6500 … 7199) |

Each has its own `.INF` in the same twelve-line format, and each is contiguous
from offset 0 to its end.  Their ids fall inside the kit boxes of the song
format (`FORMAT.md` §5), which is how eJay knows which product to ask for.

The add-on banks are **indexed but not decoded** here: the record counts, ids,
banks and byte ranges above are measured, while their audio was not put through
the decoder.  Pattern-block references in the songs do include ids in these
ranges (for example `HOUSE` carries 5 359 and 5 427 = `DANCESK4`, and other
patterns carry 6 471 and 7 039), so the banks matter for playback.

The ranges `2 000 … 5 099` (box 1 “DanceMachine” and Vol. 1–3) have **no shipped
container**: those products are not part of this data set.

### The id-0 record in `DANCESK6`

`DANCESK6.INF` contains one record with **id 0**, bank 0, file `D8RP023`,
length 206 868, group `uno y dos y`, name `tres y quatro 2[6]`, at offset
43 318 902 —
i.e. a real stream in the middle of the container, not a placeholder.  The
other 563 records use ids 6 500 … 7 063 (7 062 is the one missing id).  The
record is kept and documented as-is; no correction is applied.

## 3. Standalone `tPxD` files

`D_ejay2/ejay` contains **118** single-sample PXD files in three folders:

| folder | files | header name |
|--------|------:|-------------|
| `Audio_d` | 46 | `Dance 2` / `Autodemo` |
| `Audio_e` | 37 | `demo01`, `demo02`, … |
| `Audio_f` | 35 | `demo01`, `demo02`, … |

Names are `DJ2DG003.PXD`, `MOUSE01.PXD` and similar.  Each file contains
exactly **one** `tPxD` stream; all 118 decode.  They are demo material with
their own metadata block, not slices of `DANCE20`.

`DINTRO.PXD` (one stream, header `Dance eJay 2.0` / `Intro Sound`) also decodes.
`METRO.PXD` is **not** a `tPxD` file: it starts `RIFF` and is a WAV metronome
click.

## 4. `PXD10` — a catalogue whose samples are missing

`D_ejay2/ejay/PXD10` is a text catalogue of **1 352** records, **six quoted
lines** per record:

```
"bm\asjo.pxd"
""            blank
"loop"        category
"2"           flag
"Grp. 1"      group
"Vers1[D]"    name
```

Categories: drum 300, sequence 229, rap 160, xtra 127, loop 126, layer 115,
bass 114, voice 100, effect 81.

The paths are 8.3 `.pxd` names in subdirectories such as `bm`, `bl`, `bc`, `bq`.
**None of the 1 352 paths exists** under `disks/Dance_2/D_ejay2` (there is no
`bm`/`bl`/`bc`/`bq` directory at all), and their names do not match the
`Audio_d/e/f` files.  So `PXD10` is not the index of the `Audio_*` samples; it
describes a sample library that this copy of the data does not include.  What
those sample files contained is unknown.

## 5. Resolution summary

* **130 pad placements, 81 distinct ids**: 100 % resolve to `DANCE20.INF`.
* The song pattern blocks (undecoded) additionally reference ids in the
  `DANCESK4/5/6` ranges; those containers are present, but their audio was not
  decoded in this work.
* Ids in the box ranges `2 000 … 5 099` have no shipped container.
* The 118 `Audio_*` files and `DINTRO.PXD` are independent `tPxD` samples;
  `METRO.PXD` is a WAV; `PXD10` lists 1 352 files that are absent.
