# Catalogue of the 13 songs

Measured with `mixdump.py` and the player's placement rule; every number is
computed from the files.  `f04` is the header word at `0x04`; it is plausibly a
song length in bars, but that is not proved.  `last start` is the latest record
start bar; `render bars` includes samples ringing out past that point.  `left` /
`right` list the tracks whose pan word is 1 or 2; all other tracks are 0 (both).

## 1. Files

| file | bytes | f04 | f0a | f0e | recs | clips | hits | ids | last start | render bars | left | right | title |
|------|------:|----:|----:|----:|-----:|------:|-----:|----:|-----------:|------------:|------|-------|-------|
| `BUBBLE.MIX`   | 3 251 | 149 | 135 | 28 | 339 | 339 |   0 | 28 |  89.00 |  90 | 15 | 14, 16 | 2nd Attempt |
| `CLOUDS.MIX`   | 6 181 | 310 | 134 | 30 | 577 | 452 | 125 | 51 | 186.00 | 189 | 8, 11, 13, 15 | 9, 12, 14, 16 | no ground no way |
| `EDGE.MIX`     | 3 175 | 156 | 135 | 28 | 302 | 285 |  17 | 34 |  94.12 |  95 | 11, 13, 15 | 12, 14, 16 | straight edge mix |
| `E_FUNK.MIX`   | 3 101 | 217 | 158 | 28 | 298 | 285 |  13 | 20 | 109.00 | 112 | 3, 8, 9 | 4, 10, 13, 16 | 1st Attempt |
| `FAR.MIX`      | 4 050 | 223 | 140 | 30 | 397 | 360 |  37 | 43 | 129.75 | 130 | 5, 8, 11, 13, 15 | 6, 10, 12, 14, 16 | Far Out, Ship On My Trail |
| `HOOL.MIX`     | 4 319 | 250 | 140 | 30 | 460 | 440 |  20 | 23 | 145.00 | 152 | 10, 13, 15 | 1, 11, 14, 16 | listen-to-da-beat-a-gat |
| `MELODESK.MIX` | 6 236 | 249 | 140 | 24 | 684 | 627 |  57 | 45 | 145.00 | 146 | 2, 7, 9, 11, 15 | 1, 6, 10, 12, 14, 16 | Melodesk |
| `SOAP.MIX`     | 3 525 | 145 | 135 | 28 | 356 | 342 |  14 | 26 |  87.00 |  96 | 2, 4, 10, 13 | 1, 5, 11, 14 | dedicated to thorre |
| `START.MIX`    | 5 225 | 236 | 146 | 30 | 467 | 360 | 107 | 44 | 132.88 | 134 | 7, 9, 11, 13, 15 | 8, 10, 12, 14, 16 | here we go |
| `STRAIGHT.MIX` | 3 306 | 149 | 135 | 28 | 314 | 291 |  23 | 16 |  89.00 |  90 | 15 | 14, 16 | 2nd Attempt |
| `STRING.MIX`   | 2 387 | 129 | 137 | 28 | 206 | 200 |   6 | 26 |  74.00 |  77 | 5, 8, 9, 11, 13 | 6, 7, 10, 12, 14 | urban blues |
| `SUMMER.MIX`   | 5 469 | 391 | 145 | 30 | 513 | 415 |  98 | 61 | 217.00 | 220 | 9, 11, 13, 15 | 3, 10, 12, 14, 16 | summer coleur and bush |
| `WAMBAM.MIX`   | 2 144 | 111 | 137 | 28 | 171 | 166 |   5 | 26 |  64.00 |  66 | 4, 13, 15 | 5, 14, 16 | sis is what se dj  does |

Totals: **52 369 bytes**, **130 pads**, **0 events**, **42 199 bytes of
pattern**, **5 084 records** (4 562 clips, 522 hits), **362 distinct ids**,
13 songs.

## 2. Observations

* **Every song has the same seven kit boxes and the same ten-pad layout**; the
  pad prefix is byte-identical in all 13 files, and the ten pad names are the
  same in every song (all with sample id 0).
* **No song has imported-sample events**; the pattern block runs straight into
  the trailer and section 17's count is 0.
* **Two files are the 14-track variant**: `BUBBLE` and `STRAIGHT` store track
  count 14, sample set `Techno eJay ` and pan their last three entries as
  T14/T16 right, T15 left.  The other eleven store 16 and `Techno eJay 2 `.
* **`BUBBLE` and `STRAIGHT` share the title `2nd Attempt`** but are different
  songs (339 vs 314 records, 3 251 vs 3 306 bytes).
* **Hits range from 0 to 125 per song.**  `BUBBLE` is clips-only; `CLOUDS` and
  `START` are the most hit-heavy (125 and 107).  Clips are always the majority.
* **Records per song: 171 … 684** (`WAMBAM` … `MELODESK`); pattern size
  1 354 … 5 465 bytes (`WAMBAM` … `MELODESK`), 80.6 % of the corpus.
* **The pan layout is not a fixed pattern.**  Only `START` is a clean
  5-left/5-right split with the first six tracks centred.  `BUBBLE` and
  `STRAIGHT` pan only the last three tracks; `E_FUNK`, `SOAP` and `STRING` pan
  middle tracks; `HOOL` even pans T1 right.  `SOAP`'s T16 word is the single
  value 3 in the corpus.
* **Sample ids are dense in the RAVE20 bank but narrow per song**: 16 … 61
  distinct ids per song, drawn from 13 016 … 17 012, all present in
  `RAVE20.INF`.

## 3. Pan matrix (all 16 tracks)

`B` = both, `L` = left, `R` = right, `?` = the unexplained value 3.  Read from
the 16 pan words after the title.  Words beyond the stored track count (14) are
still present and are shown.

| file | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | T9 | T10 | T11 | T12 | T13 | T14 | T15 | T16 |
|------|----|----|----|----|----|----|----|----|----|-----|-----|-----|-----|-----|-----|-----|
| BUBBLE   | B | B | B | B | B | B | B | B | B | B | B | B | B | R | L | R |
| CLOUDS   | B | B | B | B | B | B | B | L | R | B | L | R | L | R | L | R |
| EDGE     | B | B | B | B | B | B | B | B | B | B | L | R | L | R | L | R |
| E_FUNK   | B | B | L | R | B | B | B | L | L | R | B | B | R | B | B | R |
| FAR      | B | B | B | B | L | R | B | L | B | R | L | R | L | R | L | R |
| HOOL     | R | B | B | B | B | B | B | B | B | L | R | B | L | R | L | R |
| MELODESK | R | L | B | B | B | R | L | B | L | R | L | R | B | R | L | R |
| SOAP     | R | L | B | L | R | B | B | B | B | L | R | B | L | R | B | ? |
| START    | B | B | B | B | B | B | L | R | L | R | L | R | L | R | L | R |
| STRAIGHT | B | B | B | B | B | B | B | B | B | B | B | B | B | R | L | R |
| STRING   | B | B | B | B | L | R | R | L | L | R | L | R | L | R | B | B |
| SUMMER   | B | B | R | B | B | B | B | B | L | R | L | R | L | R | L | R |
| WAMBAM   | B | B | B | L | R | B | B | B | B | B | B | B | L | R | L | R |

## 4. Generated artifacts

`reverse/techno/decoded/<name>.json` exists for all 13 songs and contains the
header words, author/ident/title, the 16 track records, kit boxes, pads with
names and ids, pattern length and hex, the decoded pattern sections (each
record's kind, sample id and start bar) and the (empty) event list.
