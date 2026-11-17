# How the Techno eJay 2 format was recovered (method, evidence, unknowns)

## 1. Constraints

* No program under `disks/` was executed; everything is static reading of data
  files.
* No file outside this project was read or written.
* Python 3 (3.14), standard library; `bash` (Git Bash on Windows).
* This tree is independent: nothing under `libs/mix/dance2/` is imported.  The
  `.PXD` codec is duplicated on purpose.

## 2. Starting point

`Techno_eJay/MIX` holds 13 songs from 2 144 to 6 236 bytes, far too small for
the 702 × 8 grid of the eJay 1.x trees.  The first word is `0x0889` in all of
them and the next bytes walk as length-prefixed sections, which is the eJay 2
shape.  The parser was written forward from the bytes and checked by
re-encoding; the interpreted fields were then tested against the data:

1. three strings (author, identification, title) — the title has a leading
   `0x01` and a `uint16` length, the others are plain NUL-terminated;
2. 16 × (pan, volume);
3. six words `0,0,0,0,0,14` or `…,0,16`;
4. the sample-set string `Techno eJay 2 ` (or `Techno eJay `) and a `uint16 9`
   marker;
5. seven kit boxes, each `lo, hi, length, name`, ended by eight zero bytes;
6. a 28-byte pad prefix and ten pad records;
7. the pattern block;
8. no event list, then `A9 7A 8A 01`.

The section sequence is the one Dance eJay 2 uses.  That tree's spec was used
as a hypothesis, not as authority: every field was re-measured on the Techno
files, and the writer proves the byte layout.  Where the corpora differ, the
Techno docs say so (signature, sample set, pad ids, events, hit count).

## 3. What each claim rests on

| claim | evidence |
|-------|----------|
| signature `0x0889` | first word of all 13 files, no other value |
| 16 track records | exactly 16 (pan, volume) pairs follow the title and 16 sections follow the pattern headers |
| pan 0/1/2 = both/left/right | values are 0 (109), 1 (46), 2 (52) plus one 3; `…L` samples sit mostly on pan-1 tracks (512 of 890) and `…R` on pan-2 tracks (503 of 927).  Inferred, not stated by the file |
| 140 BPM | header word at `0x08` is 140 in all 13 files; every sampled loop is a multiple of 75 600 samples |
| sample-set variant | eleven files say `Techno eJay 2 ` with track count 16; `BUBBLE` and `STRAIGHT` say `Techno eJay ` with track count 14 |
| seven kit boxes | all 13 files have the same seven ranges; names vary in two complete sets |
| ten pads, id 0 | every file has exactly ten records after the prefix; every id is 0; the ten names are identical across the corpus |
| pattern section = track | 16 sections plus a zero-count section 17; L/R sample pairs concentrate on the correspondingly panned tracks; the 5 084 records are time-ordered per section with no exceptions |
| clip start bar | with `2·|block| − 1 + (255 − byte1)/128`, 4 430 clips land on a whole bar and all sections are ordered; the opposite `byte1` reading breaks most sections |
| hit start bar | `position / 32768 + 1`; 404 of 522 hits land on a whole bar and all sections stay ordered |
| preamble size word | the word at preamble offset 18 equals `len(pattern) − 18` in all 13 files |
| no events | section 17's count is 0 in all files and the pattern block runs straight into the trailer; the parser's event list is empty |
| trailer constant | last four bytes of all 13 files |

Two independent checks support the timing reading.  First, every section is
monotone in time under this mapping (0 violations in 5 084 records).  Second,
the clip sub-bar fractions use the same 1/128-bar grid as Dance eJay 2, and the
hit positions are mostly whole bars with a few 1/32768-bar offsets.

## 4. The sample containers

`RAVE20` is 429 261 617 bytes and `RAVE20.INF` has 4 015 twelve-line records.
Their `offset`/`length` pairs are contiguous from 0 to the end of the file and
their ids are exactly `13 000 … 17 014`, in offset order rather than id order.
All 362 ids used by the songs resolve.

`HYP1` … `HYP4` hold 504 standalone `tPxD` files with no index.  No arrangement
id references them; they decode cleanly but are not part of playback.

The ten pad records carry id 0 and names that do not occur in `RAVE20.INF`
(`eurokick5`, `elec.sn 2`, …).  A text search of the whole index finds none of
the ten names, so there is no id or name path from a pad to shipped audio.

## 5. Dead ends and open questions

* **The kit boxes as the id map**: rejected.  They declare `2 000 … 7 199`;
  zero arrangement records use that range.
* **Pads as arrangement samples**: rejected.  All ten have id 0, and the
  arrangement's 5 084 records already resolve through `RAVE20.INF`.
* **`field_04` as a byte length**: rejected — 111 for a 2 144-byte file and 391
  for a 5 469-byte file; it does not track size and is only roughly bar-like.
* **A fixed seven-byte record size**: rejected.  The sections mix 7-byte clips
  and 17-byte hits; the `0xFFFF` word at offset 3 is the discriminator and
  parsing them as one size does not end at the section boundary.
* **The 22-byte preamble as all unknown**: partly solved.  Its first 18 bytes
  are constant and its ninth word is the block length minus 18; the final word
  is always zero but unexplained.
* **Events**: none exist in this corpus, so the 27-byte event-tail code path is
  inherited from the shared layout but never exercised by a Techno song.
* Still unknown: the first 18 preamble bytes, a clip's `byte0` (only 0 seen), a
  hit's ten trailing bytes, `field_04`/`field_0a`/`field_0e`, the marker 9, pad
  words `word3`/`word4`, the single pan value 3, and whether eJay cuts a
  clip at the next record on its track as the player does.

## 6. Proof rather than plausibility

`python reverse/techno/mixdump.py --verify --all` parses each file, rebuilds it
from the structured model and compares the bytes: **13/13 identical**.  A wrong
prefix length, name encoding, pad tail, pattern record boundary or trailer
would break it immediately.

## 7. Reproducing the results

```
python reverse/techno/mixdump.py --verify --all                            # 13/13 byte-identical
python reverse/techno/mixdump.py --all                                     # readable dump
python reverse/techno/mixdump.py --pattern START.MIX | head
python reverse/techno/mixdump.py --json reverse/techno/decoded --all       # machine-readable dumps
python libs/pxd/ disks/Techno_eJay/EJAY/PXD/RAVE20.INF --id 13016 --stats
python libs/pxd/ disks/Techno_eJay/EJAY/PXD/HYP1/BASS001.PXD --stats
python apps/emp/src/mixplayer.py --format techno START.MIX --from 1 --bars 8 --wav out.wav
```
