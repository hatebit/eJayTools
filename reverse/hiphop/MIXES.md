# Catalogue of the 17 songs

Measured with `mixdump.py` / `mixrender.py`; every number below is computed from
the files, not estimated.  Times use 96 BPM 4/4 (bar = 2.5 s).  `pan` is
`T1…T8`, with `C` centre, `L` left, `R` right (`FORMAT.md` §4c).

## 1. Files

| file | bytes | tail | bars | placed | distinct | max id | length | per bar | pan |
|------|------:|-----:|-----:|-------:|---------:|-------:|-------:|--------:|-----|
| `BCAUSE.MIX`    | 12692 | 1458 | 431 | 217 | 53 | 2067 | 1077.5 s | 0.50 | `CCCCCCLR` |
| `DUTCH.MIX`     | 12692 | 1458 | 423 | 197 | 67 | 1861 | 1057.5 s | 0.47 | `CCCCCCRL` |
| `FEEDHIP.MIX`   | 12692 | 1458 | 124 | 496 | 41 | 1995 |  310.0 s | 4.00 | `CCCCCCRL` |
| `GOODMOOD.MIX`  | 12692 | 1458 | 442 | 549 | 48 | 2067 | 1105.0 s | 1.24 | `CCCCLRRL` |
| `HIPHOP.MIX`    | 12692 | 1458 |  51 | 111 | 14 | 1853 |  127.5 s | 2.18 | `CCRCCLCC` |
| `HIPHOUSE.MIX`  | 12692 | 1458 | 404 | 448 | 45 | 2059 | 1010.0 s | 1.11 | `CCCCCCLR` |
| `JUNGLE.MIX`    | 12692 | 1458 | 396 | 378 | 45 | 1898 |  990.0 s | 0.95 | `CCCCCCLR` |
| `MYSELF.MIX`    | 12692 | 1458 | 103 | 306 | 25 | 1991 |  257.5 s | 2.97 | `CCCCCCCC` |
| `RAGE.MIX`      | 12692 | 1458 | 457 | 311 | 30 | 1934 | 1142.5 s | 0.68 | `CCCCCCLR` |
| `SHYGIRL.MIX`   | 12692 | 1458 | 451 | 331 | 46 | 1930 | 1127.5 s | 0.73 | `CCCCCCLR` |
| `SLOWUP.MIX`    | 12692 | 1458 |  65 | 195 | 33 | 2031 |  162.5 s | 3.00 | `CCCCCCLR` |
| `START.MIX`     | 12692 | 1458 | 429 | 277 | 65 | 2071 | 1072.5 s | 0.65 | `CCCCCCLR` |
| `SUMMER.MIX`    | 12692 | 1458 | 418 | 256 | 36 | 1996 | 1045.0 s | 0.61 | `CCCCCCLR` |
| `SWEET.MIX`     | 12692 | 1458 | 434 | 233 | 70 | 2064 | 1085.0 s | 0.54 | `CCCCCCLR` |
| `UPDOWN.MIX`    | 12692 | 1458 | 429 | 291 | 39 | 2060 | 1072.5 s | 0.68 | `CCCCCCLR` |
| `VIBE.MIX`      | 12692 | 1458 | 425 | 448 | 88 | 2067 | 1062.5 s | 1.05 | `CCCCCCLR` |
| `XDAYS.MIX`     | 12692 | 1458 | 481 | 444 | 43 | 2058 | 1202.5 s | 0.92 | `CCCCCCCC` |

`tail` = bytes after `0x2BE2` (constant here); `placed` = occupied slots;
`per bar` = `placed / bars`; `bars` is the arrangement (last occupied bar).
Only `MYSELF` plays past its grid: its last sample rings out one bar later
(104 played bars, 103 in the grid) — see `mixrender.py` / `mixplayer.py`.

## 2. Totals and grouping

* 17 songs, **5 963 bars**, **5 488 placed samples**, **531 distinct ids**
  (517 `.PXD` ids + 14 `SPECIAL` WAV ids), 5 161 placements through `.PXD`
  files and 327 through `SPECIAL` WAVs.  No placement is unresolved.
* All files are the same size with the same bank block; they differ only in
  the grid, the `head` word and the `pan` words.
* Pan groups: 11 files use the default `T7 L, T8 R`; `DUTCH`/`FEEDHIP` swap
  the pair; `GOODMOOD` pans T5–T8 as L/R/R/L; `HIPHOP` pans T3 right and T6
  left; `MYSELF` and `XDAYS` are fully centred.
* No two files are byte-identical and no two share a grid.
* Length spread: 51 bars (127.5 s, `HIPHOP`) to 481 bars (1202.5 s,
  `XDAYS`, 20 min); nothing comes near the 702-bar / 29.25 min capacity.
* Density ranges from 0.47 placed samples per bar (`DUTCH`) to 4.00
  (`FEEDHIP`, a 124-bar almost fully populated mix).
* Track usage over the corpus, T1…T8: 780, 758, 764, 725, 822, 655, 476, 508
  placements (123, 131, 136, 168, 167, 107, 100, 101 distinct ids).  All eight
  lanes are used; no lane is reserved.

## 3. Most used samples (corpus)

| id | placements | sample |
|----|-----------:|--------|
| 958 | 136 | `tamb tam` (`BN/H1DC007.PXD`) |
| 1536 | 122 | `hand dry` (`BB/H1LC003.PXD`) |
| 1559 | 113 | `organ rsta2` (`BI/H1OL021.PXD`) |
| 8 | 99 | `rattle snake` (`SPECIAL/HXDRUM08.WAV`) |
| 897 | 83 | `kickH off` (`BA/H1DA538.PXD`) |
| 1464 | 71 | `genY clear shock` (`AH/H1LA332.PXD`) |
| 879 | 68 | `kickD off` (`BA/H1DA519.PXD`) |
| 952 | 67 | `hat A first accent` (`AI/H1DC001.PXD`) |

## 4. `START.MIX` track lanes

| lane | occupied | distinct samples | dominant material |
|------|---------:|----------------:|-------------------|
| T1 | 33/429 | 6 | `dirty store sub wear` (15 bars) |
| T2 | 48/429 | 7 | `hat A first accent` (21), `snreI flow1` (20) |
| T3 | 41/429 | 10 | `snreF flow1` (12), `tin loop straight` (10) |
| T4 | 42/429 | 11 | `do it easy ...` (14), `hard breath` (6) |
| T5 | 35/429 | 21 | `keep it movin 2` (4) |
| T6 | 27/429 | 10 | `count in brother!` (8) |
| T7 | 24/429 | 14 | `yeah` (4), `orchestra hit` (3) |
| T8 | 27/429 | 13 | `yeah` (4), `rattle snake` (4) |

The intro's first bars place a vocal on T3/T4, then the drum lanes T2/T3 take
over from bar 4, which is why the `start.png` image shows a dense left-hand
block and sparse outer lanes.

## 5. Per-song artifacts

`reverse/hiphop/decoded/<name>.json` (full grid, per-sample path/name, bank
fields, timings) and `reverse/hiphop/images/<name>.png` (arrangement grid)
exist for all 17 songs.
