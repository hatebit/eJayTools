# Sample ids and containers

Techno eJay 2 resolves arrangement sample ids through **`EJAY/PXD/RAVE20.INF`**
into the concatenated `EJAY/PXD/RAVE20` container.  The pads carry no catalogue
id, and the seven kit boxes declare id ranges that no song uses.

## 1. `RAVE20.INF`

The index is a CRLF text file.  It starts with fourteen header lines (the last
of which is `[SAMPLES]`), then 4 015 records of twelve lines:

```
sample id, bank, PXD file name, offset, length, group, name,
flag 1, flag 2, "", 0, ""
```

Measured properties:

| property | value |
|----------|-------|
| records | **4 015** |
| ids | contiguous **13 000 … 17 014** |
| bank word | `6` in every record |
| file names | 4 015 distinct (`T1FX544`, `T1LA699`, `T1SQ057R`, …) |
| groups | 730 distinct (`jam-`, `dist.`, `esoteric files`, …) |
| offset coverage | 0 … 429 261 617, contiguous to the end of `RAVE20` |
| label | group + space + name, or the file name when both are empty |

The records are ordered by **offset**, not by id, so ids must be looked up
through the index.  The arrangement ids used by the 13 songs fall in
**13 016 … 17 012**; all **362** distinct ids are present.

Typical labels: `splish 2`, `dance tech1`, `sub zone1`, `effected female 2R`,
`esoteric files 4R`.  The `…L`/`…R` suffixes are stereo halves; the `2R`/`4R`
tails also occur in group names.

## 2. `RAVE20` container

`PXD/RAVE20` is 429 261 617 bytes: a plain concatenation of `tPxD` streams with
no header of its own.  `RAVE20.INF` slices it into 4 015 streams; the first
starts at 0 and the last ends exactly at the file size.

The 362 ids used by the songs were decoded for this tree:

| check | result |
|-------|--------|
| decoded without error | **362 / 362** |
| whole-bar lengths | 361 (bar = 75 600 samples) |
| outlier | id 16 862, 76 040 samples (1.0058 bars) |
| highest peak | **0.4509** (−6.9 dBFS) |
| lengths seen | 1, 2, 3, 4, 6, 7, 8, 10 and 16 bars |

The whole container was not decoded end to end; only ids the arrangements
reference were.  See [`PXD.md`](PXD.md) for the codec.

## 3. `HYP1` … `HYP4` standalone samples

`PXD/HYP1` (146 files), `HYP2` (81), `HYP3` (97) and `HYP4` (180) hold **504**
single-stream `tPxD` files, one sample each, named `BASS###`, `CLAP###`,
`HIHAT###`, `FX###`, `SYNTH###` and similar.  There is no `.INF` index for
them, and **no arrangement id references them**.  All 504 decode; the highest
peak is **0.4987**, and most are fractions of a bar (191 half-bar, 168 quarter-
bar, 37 eighth-bar, 96 one-bar, plus a few others).  They are not used by
`mixplayer.py`.

## 4. Drum pads

Each song has ten pad records.  Their `sample_id` is **0** in all 130 records,
and their names (`eurokick5`, `elec.sn 2`, `808cl.hat2`, `808op.hat`, `crash2`,
`clap8`, `darabuka2`, `egg2`, `hit5`, `humn.13`) do not occur in
`RAVE20.INF`.  There is therefore no audio to resolve: the pads are a stored
drum-machine setup, not part of the arrangement.

## 5. Kit boxes

All songs declare the same seven boxes, ranging from 2 000 to 7 199, with Dance
product names.  No arrangement record uses an id in that range, and the names
(`DanceMachine`, `Dance eJay 1.0`, …) do not describe the RAVE20 bank.  The
boxes are preserved and printed by `mixdump.py`, but playback ignores them.

## 6. What is missing

Nothing used by the songs is missing: every one of the 5 084 records resolves
to a shipped sample.  The tree does not claim that every one of the 4 015
`RAVE20` records decodes, only the 362 referenced by the corpus.
