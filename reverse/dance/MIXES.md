# Catalogue of the 16 songs

Measured with `mixdump.py` / `mixrender.py`; every number below is computed from
the files, not estimated. Times use 140 BPM 4/4 (bar = `12/7 ≈ 1.714 s`).

## 1. Files

| file | bytes | tail | bank block | bars | placed | distinct | max id | length | per bar |
|------|------:|-----:|------------|-----:|-------:|---------:|-------:|-------:|--------:|
| `DREAM.MIX` | 11413 | 179 | v8, nlists=2, `[3, 0]` | 444 | 179 | 57 | 4417 | 761.1 s | 0.40 |
| `DRUMSYNT.MIX` | 11333 | 99 | v6, nlists=2, `[2, 0]` | 428 | 180 | 56 | 3798 | 733.7 s | 0.42 |
| `FREAK.MIX` | 11234 | – | none | 416 | 250 | 29 | 2056 | 713.1 s | 0.60 |
| `LOVE.MIX` | 11234 | – | none | 69 | 126 | 29 | 1919 | 118.3 s | 1.83 |
| `MCXTREME.MIX` | 11277 | 43 | v8, nlists=1, `[0]` | 433 | 296 | 38 | 1985 | 742.3 s | 0.68 |
| `ORGANICS.MIX` | 11277 | 43 | v8, nlists=1, `[0]` | 378 | 219 | 21 | 1968 | 648.0 s | 0.58 |
| `RAPSVOIC.MIX` | 11333 | 99 | v6, nlists=2, `[2, 0]` | 444 | 179 | 57 | 4417 | 761.1 s | 0.40 |
| `SOFTVOX.MIX` | 11277 | 43 | v8, nlists=1, `[0]` | 398 | 266 | 30 | 4727 | 682.3 s | 0.67 |
| `SPACE.MIX` | 11413 | 179 | v8, nlists=2, `[3, 0]` | 440 | 283 | 103 | 5013 | 754.3 s | 0.64 |
| `START.MIX` | 11234 | – | none | 83 | 189 | 48 | 1989 | 142.3 s | 2.28 |
| `START_RE.MIX` | 11333 | 99 | v6, nlists=2, `[2, 0]` | 379 | 324 | 83 | 4419 | 649.7 s | 0.85 |
| `THEFLOW.MIX` | 11277 | 43 | v8, nlists=1, `[0]` | 433 | 217 | 39 | 4513 | 742.3 s | 0.50 |
| `WELCOME.MIX` | 11234 | – | none | 189 | 389 | 139 | 2066 | 324.0 s | 2.06 |
| `WETDANCE.MIX` | 11277 | 43 | v8, nlists=1, `[0]` | 423 | 231 | 35 | 2019 | 725.1 s | 0.55 |
| `XPIPE.MIX` | 11234 | – | none | 83 | 189 | 48 | 1989 | 142.3 s | 2.28 |
| `X_PERM.MIX` | 11277 | 43 | v8, nlists=1, `[0]` | 416 | 478 | 79 | 4417 | 713.1 s | 1.15 |

`tail` = bytes after `0x2BE2`; `[3, 0]` = number of boxes in list 1 and list 2;
`placed` = occupied slots, `per bar` = `placed / bars`.
`bars` is the arrangement (last occupied bar).  Playback continues until the
last placed sample has rung out: +7 bars for `START`/`XPIPE` (the closing sample
is 8 bars long) and +1 bar for `LOVE`, `FREAK`, `WELCOME`, `MCXTREME`,
`ORGANICS`, `SOFTVOX` and `X_PERM`.

## 2. Grouping

* **size 11234, no bank block – 5 files**: `FREAK`, `LOVE`, `START`, `WELCOME`,
  `XPIPE`. Made with the built-in catalogue only.
* **size 11277, `0x0A08`, one empty list, 18-byte suffix – 6 files**:
  `MCXTREME`, `ORGANICS`, `SOFTVOX`, `THEFLOW`, `WETDANCE`, `X_PERM`. Version
  string `Dance eJay 1.01`.
* **size 11333, `0x0A06` (v6), two lists, no suffix – 3 files**: `DRUMSYNT`,
  `RAPSVOIC`, `START_RE`. Version `DanceMachine 1.05`, boxes 3400–3899 and
  3900–4500.
* **size 11413, `0x0A08`, two lists, suffix – 2 files**: `DREAM`, `SPACE`.
  Version `gung DanceMachine 1.05`, boxes 3400–3899, 3900–4499, 4500–5199.

## 3. Observations

* **Duplicates**: `START.MIX` ≡ `XPIPE.MIX` and `DREAM.MIX` ≡ `RAPSVOIC.MIX`,
  byte for byte — i.e. two copies of each, one of them under a second name.
* **Length spread**: 69 bars (118 s, `LOVE`) to 444 bars (761 s, `DREAM` /
  `RAPSVOIC`, 12.7 min). Nothing comes near the 702-bar / ~20 min capacity of
  the grid.
* **Density** ranges from 0.40 placed samples per bar (`DREAM`, `RAPSVOIC`,
  sparse ambient/dub arrangements) to 2.28 (the 83-bar intro `START`/`XPIPE`,
  nearly every bar fully populated). The long "song" mixes are all between
  0.40 and 1.15.
* **No bar ever holds more than 8 samples** — with 5 456 bars in the corpus the
  maximum is exactly 8, which is the expected ceiling for 8 tracks.
* All 8 track lanes are used in the corpus, but the top lanes are favoured:
  T1 685, T2 568, T3 489, T4 474, T5 551, T6 398, T7 396, T8 434 placements;
  as a share of the 5 456 bars the lanes are occupied 12.6 %, 10.4 %, 9.0 %,
  8.7 %, 10.1 %, 7.3 %, 7.3 %, 8.0 % of the time. No lane is reserved.
* **Box samples** (declared box ids, `3 400` and up) account for 567 placements
  in the `Dance eJay 1.01` group, 390 in the v6 `DanceMachine 1.05` group and
  349 in the `gung` group — so add-on boxes are central, not decorative.
* **`SPECIAL` WAV samples** (ids `1, 2, 3, 4, 8, 9` — 109 placements) live in
  `disks/Dance_eJay/SPECIAL`, so `FREAK`, `MCXTREME`, `ORGANICS` and `WETDANCE` now
  play complete; the remaining 1 306 skipped placements are add-on box ids
  (`SAMPLES.md` §5).

## 4. `START.MIX` track lanes

The 83-bar intro is the clearest example of the lane model: each slot index
behaves as one instrument stream across the whole song.

| lane | occupied | distinct samples | most used |
|------|---------:|----------------:|-----------|
| T1 | 41/83 | 8 | 746 "Grp. 1 Vers16" (13 bars), 843 "Perc.L Vers8" (12) |
| T2 | 20/83 | 5 | 857 "Sharp *" (10), 839 "Perc. Vers5" (4) |
| T3 | 31/83 | 6 | 1231 "XPipe 04" (25), 815 "Grp.7 Vers13" (2) |
| T4 | 20/83 | 9 | 1919 "Robot vibrations" (11), 1284 "Snare fill 01" (2) |
| T5 | 31/83 | 7 | 1213 "Fly is dead" (9), 1231 "XPipe 04" (8) |
| T6 | 15/83 | 9 | 1185 "touch-tt-touch-tt **" (6), 1727 "WHAT" (2) |
| T7 | 16/83 | 9 | 973 "Myth * L Cut 2" (4), 1052 "Funny Mix ** L" (3) |
| T8 | 15/83 | 8 | 974 "Myth * R Cut 2" (4), 1053 "Funny Mix ** R" (3) |

`T3` is the `XPipe 04` loop that runs almost the whole intro (25 of 31 occupied
bars on the same sample), `T4` `Robot vibrations`, `T7`/`T8` the `Myth * L/R
Cut 2` pair — visible at a glance in `images/start.png`.

## 5. Most used samples (corpus)

| id | placements | sample |
|----|-----------:|--------|
| 1423 | 91 | "Kick B Fig.21" (`BO/AVIU.PXD`) |
| 4416 | 69 | box `3900–4499` "Drams && Synthies" + 516 |
| 1231 | 66 | "XPipe 04" (`BC/AEIF.PXD`) |
| 4060 | 65 | box `3900–4499` "Drams && Synthies" + 160 |
| 1327 | 62 | "Hihat electric 1" (`BP/AXVU.PXD`) |
| 738 | 61 | "Grp. 1 Vers8" (`BL/AQQO.PXD`) |

## 6. Per-song artifacts

`reverse/dance/decoded/<name>.json` (full grid, per-sample path/name/box, timings) and
`reverse/dance/images/<name>.png` (arrangement grid) exist for all 16 songs.
