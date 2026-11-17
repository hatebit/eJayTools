# Catalogue of the 13 songs

Measured with `mixdump.py`; every number is computed from the files.  `field_04`
is the header word at `0x04`; it is plausibly a song length in bars, but that is
not proved.  `pan` lists the tracks whose pan word is 1 (left) or 2 (right); all
other tracks are 0 (both).  The three-state reading comes from eJay's
per-track speaker buttons and is an inference (`FORMAT.md` §4).

## 1. Files

| file | bytes | field_04 | field_0a | field_0e | pads | events | pattern | left | right | title |
|------|------:|---------:|---------:|---------:|-----:|-------:|--------:|------|-------|-------|
| `CAMRON.MIX`   | 7 330 | 209 | 140 | 26 | 10 |  93 | 2 634 | 10, 11, 13, 15 | 9, 12, 14, 16 | The Land of Camron |
| `HAPPY.MIX`    | 8 219 | 264 | 152 | 30 | 10 | 138 | 1 661 | 2, 8, 11, 13, 15 | 3, 9, 12, 14, 16 | Rock the Beat Remix |
| `HOUSE.MIX`    | 3 553 | 246 | 136 | 30 | 10 |   0 | 2 760 | 2, 9, 11 | 3, 10, 12 | House Mix |
| `LATIN.MIX`    | 3 999 | 185 | 140 | 30 | 10 |   0 | 3 206 | 2, 9, 11, 15 | 3, 10, 12, 16 | Latin Dance Mix |
| `LIFEXL.MIX`   | 6 280 | 150 | 140 | 26 | 10 |  78 | 1 969 | 11, 13, 15 | 12, 14, 16 | Art and Style Mix |
| `OTHER.MIX`    | 2 455 | 153 | 140 | 30 | 10 |   0 | 1 662 | 11, 13, 15 | 12, 14, 16 | He does it like no other |
| `PARTY.MIX`    | 2 948 | 162 | 144 | 30 | 10 |   8 | 1 836 | 11, 13, 15 | 12, 14, 16 | Short Cut Mix |
| `SENNER.MIX`   | 2 517 | 105 | 148 | 30 | 10 |  17 | 1 003 | 11, 13, 16 | 12, 14, 15 | Rock on the Mountains Remix |
| `START.MIX`    | 6 124 | 219 | 140 | 30 | 10 |  71 | 2 361 | 11, 13, 15 | 12, 14, 16 | Take me by the Hand |
| `STEP.MIX`     | 1 553 |  27 | 140 | 30 | 10 |  16 |   149 | 11, 13, 15 | 12, 14, 16 | Duck Dance |
| `TRANCE.MIX`   | 4 271 | 304 | 140 | 30 | 10 |   0 | 3 474 | 3, 9, 11, 13 | 2, 10, 12, 14 | Trance Mix |
| `TRIBUTE.MIX`  | 2 870 | 134 | 140 | 29 | 10 |   0 | 2 081 | 3, 5, 11 | 2, 4, 12 | Bring It On ! |
| `YOURTIME.MIX` | 4 485 | 202 | 140 | 30 | 10 |  28 | 2 445 | 9, 11, 13, 15 | 10, 12, 14, 16 | Don't Waste My Time Mix |

Totals: **56 604 bytes**, **130 pads**, **449 events**, **27 241 bytes of
pattern**, 13 songs.

## 2. Observations

* **Every song has the same seven kit boxes and the same ten-pad layout**; the
  pad prefix is byte-identical in all 13 files.
* **Panning is per song.**  Five songs (`LIFEXL`, `OTHER`, `PARTY`, `START`,
  `STEP`) use the default `T1–T10 both, T11/T13/T15 left, T12/T14/T16 right`.
  `CAMRON` moves the left/right pair to T9/T10 and T10 is left; `HAPPY` pans
  T2/T3 and T8/T9; `LATIN` pans T2/T3 and T9/T10; `SENNER` swaps the last pair
  (T15 right, T16 left); `TRANCE` pans T2/T3 and T9–T14; `TRIBUTE` pans T2–T5
  and T11/T12; `YOURTIME` pans T9–T16.  T1 is centred in every file.
* **Five songs have no imported-sample events**: `HOUSE`, `LATIN`, `OTHER`,
  `TRANCE`, `TRIBUTE`.  Their pattern block runs straight into the trailer.
* **Events are dominated by one name per song** (`Happy` 138, `B!Yo_1` 93,
  `Lifestyle` 78, `Start` 71, `Yourtime` 28, `Senner` 17, `Party` 8).
  `STEP` is the exception: no name repeats — its 16 events hold the fragments
  `You`, `can`, `even`, `create`, … `generat`, `or   if`, `you`, `want`,
  `!!!!` and one empty string, i.e. the tutorial sentence at the file's own
  word breaks.  The second string is a decimal number (`1 … 71`) in 433 events
  and empty in all 16 `STEP` events.
* **Pad ids all resolve**: 81 distinct ids over 130 pads, labels such as
  `humn. 9`, `euro kick3`, `808 kick`, `clap 8`, `rock cut 1`.
* The pattern block is 149 … 3 474 bytes (`STEP` … `TRANCE`) and decodes in
  all thirteen songs: **3 654 clips and 16 hits** over the 16 track sections,
  21 of which are empty.  Records per song: `CAMRON` 361, `HAPPY` 222,
  `HOUSE` 379, `LATIN` 433 clips + 4 hits, `LIFEXL` 266, `OTHER` 193 clips +
  12 hits, `PARTY` 247, `SENNER` 128, `START` 322, `STEP` 6, `TRANCE` 481,
  `TRIBUTE` 282, `YOURTIME` 334.  Clip starts run from bar 1 to bar 176.5, and
  the corpus uses 500 distinct sample ids, all resolving (2 571 `DANCE20`,
  337 `DANCESK4`, 419 `DANCESK5`, 343 `DANCESK6`).
* No two files are byte-identical; sizes depend on the number of events and the
  pattern length.

## 3. Pan matrix (all 16 tracks)

`B` = both, `L` = left, `R` = right.  Read from the 16 pan words after the
title; `F` is `field_04`.

| file | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | T9 | T10 | T11 | T12 | T13 | T14 | T15 | T16 | F |
|------|----|----|----|----|----|----|----|----|----|-----|-----|-----|-----|-----|-----|-----|---|
| CAMRON | B | B | B | B | B | B | B | B | R | L | L | R | L | R | L | R | 209 |
| HAPPY | B | L | R | B | B | B | B | L | R | B | L | R | L | R | L | R | 264 |
| HOUSE | B | L | R | B | B | B | B | B | L | R | L | R | B | B | B | B | 246 |
| LATIN | B | L | R | B | B | B | B | B | L | R | L | R | L | R | L | R | 185 |
| LIFEXL | B | B | B | B | B | B | B | B | B | B | L | R | L | R | L | R | 150 |
| OTHER | B | B | B | B | B | B | B | B | B | B | L | R | L | R | L | R | 153 |
| PARTY | B | B | B | B | B | B | B | B | B | B | L | R | L | R | L | R | 162 |
| SENNER | B | B | B | B | B | B | B | B | B | B | L | R | L | R | R | L | 105 |
| START | B | B | B | B | B | B | B | B | B | B | L | R | L | R | L | R | 219 |
| STEP | B | B | B | B | B | B | B | B | B | B | L | R | L | R | L | R | 27 |
| TRANCE | B | R | L | B | B | B | B | B | L | R | L | R | L | R | B | B | 304 |
| TRIBUTE | B | R | L | R | L | B | B | B | B | B | L | R | B | B | B | B | 134 |
| YOURTIME | B | B | B | B | B | B | B | B | L | R | L | R | L | R | L | R | 202 |

The pan words for `HOUSE` and `LATIN` include T2/T3 despite those songs having
no events; panning is a property of the 16 audio lanes, not of the event list.

## 4. Generated artifacts

`reverse/dance2/decoded/<name>.json` exists for all 13 songs and contains the
header words, author/ident/title, the 16 track records, kit boxes, pads with
sample ids and names, pattern length and hex, the decoded pattern sections
(each record's kind, sample id and start bar) and every event (name, number,
tail fields).
