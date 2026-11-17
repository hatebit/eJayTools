# Catalogue of the 15 songs

Measured with `mixdump.py` / `mixrender.py`; every number below is computed from
the files, not estimated.  Times use 180 BPM 4/4 (bar = `4/3 ≈ 1.333 s`).

## 1. Files

`bars` is the grid length (last occupied bar + 1, including unresolved low ids).
`audio` is the bar at which the last sample with shipped audio ends; when it is
smaller than `bars`, the tail of the grid contains only ids `1..15`, which the
player skips (silence).  `length` = `bars × 4/3`; `per bar` = `placed / bars`.

| file | bytes | tail | bank block | bars | audio | placed | distinct | max id | length | per bar |
|------|------:|-----:|------------|-----:|------:|-------:|---------:|-------:|-------:|--------:|
| `EARTH.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 513 | 163 | 318 | 40 | 1814 | 684.0 s | 0.620 |
| `GALACTIC.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 415 | 209 | 294 | 38 | 1856 | 553.3 s | 0.708 |
| `LAJALI.MIX` | 11276 | 42 | v8, 1 empty list, 18 B* | 306 | 307 | 559 | 53 | 1866 | 408.0 s | 1.827 |
| `MAGIC.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 508 | 240 | 445 | 49 | 1879 | 677.3 s | 0.876 |
| `NODRUGS.MIX` | 11326 | 92 | v8, 1 empty list, 68 B | 458 | 107 | 217 | 19 | 1873 | 610.7 s | 0.474 |
| `OHEJAY.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 145 | 146 | 322 | 35 | 1874 | 193.3 s | 2.221 |
| `PSYCOA.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 99 | 100 | 201 | 21 | 1877 | 132.0 s | 2.030 |
| `SCOOL.MIX` | 11276 | 42 | v8, 1 empty list, 18 B* | 217 | 218 | 447 | 31 | 1825 | 289.3 s | 2.060 |
| `START.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 115 | 117 | 221 | 63 | 1879 | 153.3 s | 1.922 |
| `TRANCE.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 497 | 158 | 324 | 49 | 1809 | 662.7 s | 0.652 |
| `VIENI.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 526 | 221 | 508 | 22 | 1828 | 701.3 s | 0.966 |
| `WARP.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 456 | 161 | 266 | 33 | 1799 | 608.0 s | 0.583 |
| `WOOF.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 93 | 94 | 239 | 15 | 1837 | 124.0 s | 2.570 |
| `XENON.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 504 | 155 | 329 | 75 | 1802 | 672.0 s | 0.653 |
| `XWING.MIX` | 11276 | 42 | v8, 1 empty list, 18 B | 477 | 196 | 336 | 44 | 1812 | 636.0 s | 0.704 |

`*` `LAJALI` and `SCOOL` use the trailer variant with the `01 00 02 00` pair
repeated; all other 18-byte trailers have it once.  `NODRUGS` carries the
18-byte standard trailer plus 50 extra bytes.  `tail` = bytes after `0x2BE2`.

`audio` can exceed `bars` by one or two bars when the last sample is longer
than the remaining grid: `START` 117, `OHEJAY` 146, `PSYCOA` 100, `SCOOL` 218,
`WOOF` 94, `LAJALI` 307.

## 2. Grouping

* **All 15 files** use the same bank-block shape: tag `0x0A08`, one list,
  version `Rave eJay 1.01`, and no boxes.  There is no "no block" variant and
  no v6 block in this corpus.
* **Trailer 18 B, standard** — 12 files: `EARTH`, `GALACTIC`, `MAGIC`,
  `OHEJAY`, `PSYCOA`, `START`, `TRANCE`, `VIENI`, `WARP`, `WOOF`, `XENON`,
  `XWING`.
* **Trailer 18 B, repeated pair** — `LAJALI`, `SCOOL`.
* **Trailer 68 B** — `NODRUGS` (standard 18 B + 50 B naming
  `c:\raveejay\hypersav\scool004.wav` and `hyper`).

## 3. Observations

* **No duplicates**: no two files are byte-identical, and no two song grids are
  identical.  (Unlike Dance, there is no `START`/`XPIPE`-style twin here.)
* **Grid length vs audible content**: grid length ranges from 93 bars
  (`WOOF`, 124 s) to 526 bars (`VIENI`, 701 s).  In **nine songs** the grid is
  padded far beyond the last shipped sample by unresolved low ids: `EARTH`
  (513 vs 163), `GALACTIC` (415 vs 209), `MAGIC` (508 vs 240), `NODRUGS`
  (458 vs 107), `TRANCE` (497 vs 158), `VIENI` (526 vs 221), `WARP` (456 vs
  161), `XENON` (504 vs 155) and `XWING` (477 vs 196).  The padded region is
  mostly empty; the player reports the skipped placements and plays silence.
* **Density** ranges from 0.474 placed samples per bar (`NODRUGS`) to 2.570
  (`WOOF`).  The dense short songs (`WOOF`, `OHEJAY`, `SCOOL`, `PSYCOA`,
  `START`) fill two to two-and-a-half lanes per bar on average; the long
  ambient/trance arrangements sit near 0.6.
* **Occupancy** over 5 329 bars: 3 645 empty (68.4 %), 510 with one sample,
  300 with two, 253 with three, 257 with four, 192 with five, 85 with six,
  37 with seven, and **50 bars with all eight**.  The maximum is exactly 8, the
  expected ceiling for 8 tracks.
* **All 8 lanes are used**, with a slight bias to the lower/middle tracks:
  T1 779, T2 717, T3 811, T4 728, T5 618, T6 527, T7 443, T8 403 placements;
  as a share of the 5 329 bars the lanes are occupied 14.6 %, 13.5 %, 15.2 %,
  13.7 %, 11.6 %, 9.9 %, 8.3 %, 7.6 % of the time.  No lane is reserved.
* **L/R labels are not tied to T7/T8**: of 871 placements whose label ends in
  `L` or `R`, 308 are on T7 and 309 on T8, but 127 are on T6, 62 on T5, 28 on
  T3, 23 on T2, 11 on T4 and 3 on T1.  Some pairs are split across T7/T8
  (`eJay 4 L/R`, 48 each; `house of  mystery L/R`, 44 each), others sit on
  T5/T6 or even both halves on one track.  The player therefore centres every
  lane.
* **Low ids** (`1..15`) account for 174 placements and are concentrated in
  `VIENI` (113 × id 12) and `TRANCE` (ids 1–15 in sequence).  They have no
  shipped audio; see `SAMPLES.md` §5.

## 4. `START.MIX` track lanes

The 115-bar intro is a clear example of the lane model: each slot index
behaves as one instrument stream across the whole song.

| lane | occupied | distinct samples | most used |
|------|---------:|----------------:|-----------|
| T1 | 45/115 | 10 | 865 "kick C  basic" (14 bars), 1155 "big party 1" (8), 1156 "big party 2" (8) |
| T2 | 39/115 | 10 | 814 "bang 1" (16), 1000 "hihat  vibe 1" (14), 961 "snare  muted 1" (2) |
| T3 | 19/115 | 10 | 1018 "hihat distorted 1" (6), 1044 "big  crash1" (3), 965 "snare fill nature 2" (3) |
| T4 | 31/115 | 12 | 801 "go ahead 1" (8), 803 "go ahead 3" (6), 814 "bang 1" (4) |
| T5 | 19/115 | 8 | 1400 "distorted motion 1" (11), 1401 "distorted motion 2" (2), 1332 "two tunes  delayed 1" (1) |
| T6 | 18/115 | 11 | 1713 "lonely tunes 1" (4), 1114 "cask" (3), 1460 "chills out of control" (2) |
| T7 | 28/115 | 6 | 1753 "eJay 4 L" (12), 1014 "hihat clear 1" (10), 1755 "eJay 5" (2) |
| T8 | 22/115 | 7 | 1754 "eJay 4 R" (12), 1097 "phone 1" (4), 1103 "crowd in the dome R" (2) |

`T1` is the kick/bass lane, `T2` the snare/hat layer, `T5` the
`distorted motion` loop, `T7`/`T8` the `eJay 4 L/R` pair — visible at a glance
in `images/start.png`.

## 5. Most used samples (corpus)

| id | placements | sample | file |
|----|-----------:|--------|------|
| 992 | 125 | "hihat  silver 1" | `BK/R1DC011.PXD` |
| 1250 | 123 | "dirty" | `BC/R1LA091.PXD` |
| 12 | 117 | unresolved (id < 731) | — |
| 814 | 111 | "bang 1" | `BQ/R1BS084.PXD` |
| 865 | 105 | "kick C  basic" | `BF/R1DA015.PXD` |
| 851 | 93 | "kick A  basic" | `BF/R1DA001.PXD` |
| 875 | 85 | "kick D  basic" | `BE/R1DA025.PXD` |
| 1014 | 82 | "hihat clear 1" | `BP/R1DC033.PXD` |
| 768 | 74 | "cool bass Seattle 2" | `BL/R1BS038.PXD` |
| 1391 | 59 | "rage 3" | `BP/R1SF087.PXD` |

The catalogue-range top ten is dominated by drums and short loops; the most
used single id is a hi-hat.  Id 12 is a low slot repeated by `VIENI`, not a
shipped sample.

## 6. Per-song artifacts

`reverse/rave/decoded/<name>.json` (full grid, per-sample path/name/category,
timings) and `reverse/rave/images/<name>.png` (arrangement grid) exist for all
15 songs.
