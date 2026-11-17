# How the Dance eJay 2 format was recovered (method, evidence, dead ends)

## 1. Constraints

* No program under `disks/` was executed; everything is static reading of data
  files.
* No file outside this project was read or written.
* Python 3 (3.14), standard library; `bash` (Git Bash on Windows).
* This tree is independent: nothing under `libs/mix/dance/` is imported.  The
  `.PXD` codec is duplicated on purpose.

## 2. Starting point: signature and sections

`Dance_2/MIX` holds 13 songs from 1 553 to 8 219 bytes — far too small for a
702 × 8 grid.  The first word is `0x0A19` in all of them; after it the files
walk as a sequence of length-prefixed sections, so the work was to identify
each section by reading it forward and confirming that the model re-encodes
every byte.

The sections were found in this order:

1. three strings (author, identification, title) — the title has a leading
   `0x01` and a `uint16` length, the other two are plain NUL-terminated;
2. 16 × (pan, volume) — values 0/1/2 for pan, matching the three speaker
   buttons in `Dance2_manual_uk.pdf`;
3. six words `0,0,0,0,0,16` — the last is the visible track count;
4. the sample-set string `Dance eJay 2.0`, a `uint16 9` marker;
5. seven kit boxes, each `lo, hi, length, name`, ended by eight zero bytes;
6. a pad prefix and ten pad records;
7. the pattern block;
8. an event list, then `A9 7A 8A 01`.

## 3. The bug that cost the first prototype

The first parser wrote eight zero bytes after the box terminator and then
skipped `8 + 12 + 12 + 4 = 36` bytes, assuming the terminator was followed by a
separate block of eight zeros.  It reported `pads=0` and rebuilt each file
**eight bytes short**, with the first difference at the pad prefix.

The actual layout is simpler: the eight zero bytes *are* the box terminator,
and the next bytes are already the first empty pad record.  The prefix is:

```
02 00 00 01 00 x 8      empty pad record     12 bytes
02 00 00 01 00 x 8      empty pad record     12 bytes
02 00 00 01             record tag            4 bytes
```

28 bytes, byte-identical in all 13 files.  Reading the two empty records and
the tag verbatim (instead of recomputing them) fixed both the pad count and the
missing eight bytes.  This is why the parser now stores `pad_prefix` as raw
bytes and `build()` emits it unchanged.

## 4. What each claim rests on

| claim | evidence |
|-------|----------|
| signature `0x0A19` | first word of all 13 files, no other value |
| 16 track records | the manual describes 16 audio tracks; exactly 16 (pan, volume) pairs follow the title; pans are only 0/1/2 |
| pan 0/1/2 = both/left/right | three values only, 208 records; eJay exposes exactly three per-track speaker states; the manual names them both/left/right.  Inferred, not stated by the file |
| extra track “0” = drum track | the manual separates one Drum Track from the 16 audio tracks; the file has ten pad records and a pattern block outside the 16-track table |
| 140 BPM | header word at `0x08` is 140 in all 13 files; eJay cuts samples at 140 BPM 4/4 (bar = 75 600 samples) |
| `field_04` 27 … 304 | header word at `0x04`; values look like bar counts (27 for the shortest song, 304 for the longest), but nothing in the file states it |
| seven kit boxes | all 13 files have the same seven ranges and names; the first name varies between `DanceMachine Samples` and `DanceMachine` |
| ten pads | every file has exactly ten records after the prefix; ids all resolve in `DANCE20.INF` |
| pad id = `DANCE20` id | id 1930 resolves to record 1930, name `humn.9`, label `humn. 9`; all 81 distinct ids resolve |
| five songs have no events | after the pattern block the bytes are the trailer `A9 7A 8A 01`; relaxing every event-field check still finds no chain |
| pattern section = track | section `n` of `OTHER` matches the track eJay shows for those samples: sections 13/14 hold exactly the two `bloose` records that eJay places at bars 5 and 9 |
| clip start bar | ground truth for `OTHER` bars 1-10: ids 270/271 at `block` 3 (`byte1` 255) fall on bar 5, ids 272/273 at `block` 5 on bar 9, id 711 at `block` 5 on bar 9; with this mapping all 187 non-empty sections are time-ordered, the opposite `byte1` reading breaks 59 |
| hit start bar | the twelve `heart beat` (id 502) records in `OTHER` sit at 0x8000 steps and eJay shows one in each of bars 1-12 |
| section 17 count = events | equals the length of the event list in all thirteen files, including the five with no events |
| event tail 27 bytes | kind 2 at offset 0 and channel `0x7F`/`0xFF` at offset 1 in all 449 events; re-encoding the whole list is exact |
| trailer constant | last four bytes of all 13 files |

## 5. The sample containers

`DANCE20` is 231 270 914 bytes.  `DANCE20.INF` has 1 957 records of twelve
lines; their `offset`/`length` pairs are contiguous from 0 to the end, and every
record decodes as a `tPxD` stream.  Ids run `1 … 1957` but the records are
ordered by file offset (first id 1512, last 970), so the index must be searched
by id rather than indexed by it.

`DANCESK4/5/6` are the same shape with 598, 677 and 564 records; their ids sit
inside the Vol. 4–6 box ranges (except one id-0 record in `DANCESK6`), which is
how eJay maps a song id to an add-on product.  `DANCESK6` contains one record with id 0 at a normal mid-file
offset — a quirk of the shipped index, kept as-is.

The `Audio_d/e/f` folders hold 118 single-stream `tPxD` files.  `METRO.PXD`
turned out to be RIFF/WAVE.  `PXD10` lists 1 352 `.pxd` paths in `bm`/`bl`/…
directories that do not exist in this data, and its names do not match the
`Audio_*` files, so it is a catalogue of a missing sample library, not their
index.

## 6. Dead ends and open questions

* **`PXD10` as the `Audio_*` index**: rejected — zero of 1 352 paths exist, and
  the directory names (`bm`, `bl`, `bc`, `bq`) are absent.
* **Pads as a fixed table**: rejected — all ten are real records with names and
  ids; the empty records before them are a prefix, not unused pad slots.
* **`field_04` as a byte length**: rejected — 27 for a 1 553-byte file and 304
  for a 4 271-byte file; it does not track size.
* **A fixed seven-byte record size**: rejected.  `LATIN`'s section 6 body is
  206 bytes for 28 records, which is 27 × 7 + 17; solving the header chain with
  both sizes shows the two shapes interleave inside one section instead of
  splitting by file.  `sign(pitch) < 0` and `word at 3 == 0xFFFF` both parsed
  all thirteen files, which is what identified the `0xFFFF` word as the
  discriminator rather than a per-song switch.
* **`byte1` as a single flag**: too coarse.  The high bit alone orders only
  162 sections; treating `255 - byte1` as 1/128-bar steps inside the block
  orders all of them, and the 1 085 clips that share a block with another clip
  land on distinct sub-bar positions.
* **`pitch` as a transposition**: rejected.  The value is always negative and
  strictly decreasing along every section, which is time, not pitch: it matches
  eJay's placement of the `bloose` records on bars 5 and 9.
* **Event tail**: only the first 7 bytes of 27 are understood (kind, channel,
  int24 pitch, `uint16` instance).  The remaining 20 bytes may hold position
  and length, but the pattern block would have to be decoded first to test that.
* **`field_0a`, `field_0e`, marker 9, pad words 2/3/4**: no correlation found
  with song length, pad count, event count or sample choice.
* **Why five songs have no events**: unknown; their arrangements live entirely
  in the pattern block.

## 7. Proof rather than plausibility

`python reverse/dance2/mixdump.py --verify --all` parses each file, rebuilds it
from the structured model and compares the bytes: **13/13 identical**.  A wrong
prefix length, name encoding, pad tail, event tail or trailer would break it
immediately.

## 8. What is still unknown

* the 22-byte pattern preamble, a clip's `byte0` and a hit's ten trailing
  bytes (4 100 bytes);
* how eJay trims or loops a clip that is shorter or longer than the gap to
  the next record on its track (the playback rule, not a stored field; the
  player cuts at the next record and never loops);
* 20 of the 27 bytes of each event tail (8 980 bytes over 449 events);
* pad words 2/3/4 (780 bytes), header words `field_04`/`field_0a`/`field_0e`
  (78 bytes), the marker 9 and its role;
* the meaning of `field_04` as a bar count;
* what `PXD10`'s missing sample paths referred to;
* whether pan 0/1/2 really means both/left/right (strong inference).

## 9. Reproducing the results

```
python reverse/dance2/mixdump.py --verify --all                           # 13/13 byte-identical
python reverse/dance2/mixdump.py --all                                    # readable dump
python reverse/dance2/mixdump.py --pattern disks/Dance_2/MIX/OTHER.MIX | head
python reverse/dance2/mixdump.py --json reverse/dance2/decoded --all       # machine-readable dumps
python libs/pxd/ disks/Dance_2/D_ejay2/PXD/DANCE20.INF --id 1930 --stats
python libs/pxd/ disks/Dance_2/D_ejay2/ejay/DINTRO.PXD --stats
```
