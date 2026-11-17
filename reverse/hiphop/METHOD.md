# How the format was recovered (method, evidence, dead ends)

## 1. Constraints

* No program from the repository was executed — everything is static reading
  of data files.
* No file outside this project was read or written.
* Python 3 only (`python`, 3.14), standard library; `bash` (Git Bash on
  Windows) for running the scripts.
* This tree is independent: nothing under `libs/mix/dance/` or `libs/mix/rave/`
  is imported.  The shared algorithm of the `.PXD` codec is duplicated on
  purpose.

## 2. Starting point: the size

Every HipHop `*.MIX` is exactly **12 692** bytes, and all 17 files agree.  The
same arithmetic that worked for Dance identifies the song part:

```
11234 = 2 + 11232 = 2 + 702 * 8 * 2
12692 - 11234 = 1458
```

i.e. a 2-byte signature plus `702 bars × 8 tracks × uint16`, then a 1 458-byte
block.  The 702-bar grid is ≈ 29 minutes at the measured tempo, and every
grid slot after the last occupied bar is zero.

## 3. What each claim rests on

| claim | evidence |
|-------|----------|
| signature `0x0A08` | first word of all 17 files, no other value |
| 702 × 8 grid of `uint16` | file size arithmetic; 17 files agree on the 11 234-byte split; the tail of the grid is zero |
| bar-major, tracks interleaved | sample ids recur at a period of 8 words and never exceed 8 per bar over 5 963 bars; a fixed slot index reads as one instrument lane across a song (`MIXES.md` §4) |
| no bar holds > 8 samples | maximum over the whole corpus is exactly 8 |
| 0 = empty | the zero-filled tail and the sparse lane pattern |
| song length from the last non-empty bar | the dense region ends exactly 2 bytes past the last occupied slot; derived times are musically plausible (2 min to 20 min) |
| 96 BPM not stored | no tempo field anywhere in the 12 692 bytes; 1 339 of 1 341 `.PXD` declared lengths are a whole number of 110 250-sample bars, and all 101 `SPECIAL` WAVs are 220 500 frames = two such bars |
| id = `731` + `PXD` record | 1 341 records ⇒ ids 731…2071; the corpus reaches exactly 2071, the last record; `START.MIX` first bars show exactly the records this predicts (`SAMPLES.md` §1) |
| ids 1…101 = `SPECIAL` records | 101 records, 101 WAVs on disk, all present; ids 1, 4, 8 … used in the grids |
| no add-on boxes | largest id 2071 < 3 400; every one of the 5 488 placements resolves |
| bank block 1 458 bytes | all 17 tails are the same length; the only byte differences are at tail offsets 1 434/1 435 and 1 446…1 456 |
| 18-byte "version + NUL + flag" header | same shape as Dance's `0x0A08` block; `len` counts the flag byte, and re-encoding reproduces it |
| two 704-byte constant tables | identical in all 17 files, each `uint16 350` + 702 zero bytes |
| per-track `pan` words | 8 words after the track count; values only 0/1/2; 11 files use the constant default `C C C C C C L R`; `GOODMOOD` pairs them `L R R L` |

## 4. Cross-validation of the sample numbering

1. The `PXD` list has 1 341 six-field records (path, empty, category, number,
   group, name); `id = 731 + index`, label = `group + " " + name`.
2. The highest id in the corpus is exactly the last record's id, 2071 — a
   coincidence that would not survive a wrong base or width.
3. The names make musical sense in the dumps: `START.MIX` opens with
   `help me`, `hard breath` and `hiphp jam` on T3/T4/T7, and the drum lane T4
   repeats `hard breath`.
4. The `MAX` guess was again wrong: `MAX` is a folder-ordered manifest
   (1 341 `.pxd` + 40 scratch `.wav` = 1 381), and `MIN` is a 743-line subset
   of it.  Neither is the id order.

## 5. The bank block

The first 24 bytes of the tail match the Dance `0x0A08` shape exactly:
`tag 0x0A08`, `nlists = 1`, `len = 18`, `"HipHop eJay 1.01"`, NUL, `0x01`.
Beyond that the HipHop writer appends 1 408 bytes of tables, four `head` words,
the track count and eight pan words.

The tables were found by comparing all 17 tails byte by byte: they are
identical everywhere, and only offsets 1 434/1 435 and 1 446…1 456 differ.  The
constant part is `5e 01` followed by 702 zero bytes, twice.  Reading it as two
fixed 704-byte tables (rather than one 1 408-byte blob) follows the repeated
`350` word exactly 704 bytes apart; what the tables mean is not determined by
this corpus.

The varying 26 bytes at the end decode as four `head` words, a track-count
word `8`, then eight words whose values are 0, 1 or 2.  The pan reading is the
one that explains the constant default `T7 = 1, T8 = 2` together with the
Dance corpus, where the same trailing 18-byte structure is constant
`8, 0×6, 1, 2` and the documentation derives T7 hard left / T8 hard right
from the sample labels.  It remains an inference: the grid has no pan field,
and no HipHop file states the unit.

The `head` word `X` was checked against song length, placement count, distinct
ids, maximum id, pan and the version string — no correlation.  Two values are
`44100/4` and `44100/2`, but the other four are not related to the sample rate,
so `X` is documented as unknown rather than guessed.

## 6. Dead ends

* **Public documentation**: web searches turned up nothing for this format;
  no specification was available.
* **`MAX`/`MIN` as id order**: both are installation manifests; the ids come
  from `PXD`, proved by the 2071 ceiling and the names.
* **`HIPHOP/EJAY/PXD` as a directory**: it is a *file* (the catalogue list);
  the `.PXD` audio lives in `HIPHOP/AA…BR`.
* **`HIPHOP/SCRATCH`**: 40 WAVs listed in `MAX`/`MIN` but in no catalogue and
  referenced by no grid id; they are eJay's recorded scratch takes, not a
  mix sample bank.
* **The two 704-byte tables**: constant in this corpus, so no field boundary
  or purpose is distinguishable; they are preserved verbatim.
* **`head` word `X`**: six values, no correlation found.

## 7. Proof rather than plausibility

The strongest evidence for the whole model is the round trip: parse a file,
rebuild it from the structured model (signature, 702 × 8 grid, bank block) and
compare.  `python reverse/hiphop/mixdump.py --verify --all` reports
**17/17 byte-identical**.  A wrong bar/track order, id width, table length or
field offset would break it immediately.

## 8. What is still unknown

* the purpose of the two 704-byte tables (24 072 bytes of the corpus
  including the `head` words, 11.2 %),
* the meaning of the varying `head` word `X`,
* whether the pan words really are pan (strong inference, not proof),
* why every HipHop block declares exactly one list and the same version string,
* the `.PXD` audio payload internals beyond the validated decoder.

A byte-level breakdown is in [`FORMAT.md`](FORMAT.md) §8: 24 072 of 215 764
bytes have unknown meaning, 340 more are identified in position but read by
inference, and everything else is identified.

## 9. Reproducing the results

```
python reverse/hiphop/mixdump.py --verify --all                            # 17/17 byte-identical
python reverse/hiphop/mixdump.py --all                                     # readable dump, with sample names
python reverse/hiphop/mixdump.py --json reverse/hiphop/decoded --all       # machine-readable grids
python apps/emr/src/format/hiphop/mixrender.py --out reverse/hiphop/images --all # arrangement PNGs
python libs/pxd/ disks/Hiphop_eJay/HIPHOP/AA/H1BS001.PXD --stats
```
