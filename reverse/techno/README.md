# Techno eJay 2 `*.MIX` — reversed format, tools and player

Reverse-engineered description of the 13 songs in `disks/Techno_eJay/MIX`, plus
the tooling to decode, verify and re-encode them and to play them from the
shipped samples.

Nothing here executes the programs in the repository: the format was recovered
by reading data files (`.MIX`, `EJAY/PXD/RAVE20` + `RAVE20.INF`, the standalone
`EJAY/PXD/HYP1` … `HYP4` samples) and proved by re-encoding every song byte for
byte.  This tree is independent of `libs/mix/dance`,
`libs/mix/rave`, `libs/mix/hiphop` and
`libs/mix/dance2`; the `.PXD` decoder is the shared package in
`libs/pxd/`, which none of the trees imports from one another.

Techno eJay's songs use the eJay 2 **section-based** layout, not the 702 × 8
grid of the eJay 1.x series.  The file signature is `0x0889`, tempo is stored as
140 BPM, and there is no bank block: sample ids are looked up in
`RAVE20.INF`.

## Documentation map

| file | contents |
|------|----------|
| [`FORMAT.md`](FORMAT.md) | byte-level spec: header, strings, track table, kit boxes, pads, pattern block, worked example |
| [`SAMPLES.md`](SAMPLES.md) | `RAVE20.INF` ids, the `HYP1` … `HYP4` standalone samples, pads and the unused kit boxes |
| [`PXD.md`](PXD.md) | the `tPxD` container and audio codec |
| [`MIXES.md`](MIXES.md) | all 13 songs with measured statistics and the pan matrix |
| [`METHOD.md`](METHOD.md) | evidence, checks, dead ends and unknowns |

## Tools

The parser lives in `libs/mix/techno/` and the player runtime in
`apps/emp/src/format/techno/`; this directory keeps the
prose, `mixdump.py` and the generated artifacts.

Pure Python 3.  `mixfmt.py`, `mixdump.py` and `mixrender.py` are
standard-library only; the shared `.PXD` codec (`libs/pxd/`) and the
player core need `numpy`.

```
python reverse/techno/mixdump.py --all                                # readable dump
python reverse/techno/mixdump.py --summary --all                      # one line per song
python reverse/techno/mixdump.py --pattern START.MIX                  # bar-by-bar plan
python reverse/techno/mixdump.py --json reverse/techno/decoded --all
python reverse/techno/mixdump.py --verify --all                       # re-encode + byte-compare
python apps/emp/src/mixplayer.py --format techno START.MIX                    # play
python apps/emp/src/mixplayer.py --format techno START.MIX --wav out.wav      # render instead
python apps/emp/src/mixplayer.py --format techno START.MIX --from 1 --bars 8 --wav out.wav
python apps/emr/src/format/techno/mixrender.py --out reverse/techno/images --all
python libs/pxd disks/Techno_eJay/EJAY/PXD/RAVE20.INF --id 13016 --stats
python libs/pxd disks/Techno_eJay/EJAY/PXD/HYP1/BASS001.PXD --stats
```

* `mixfmt.py` — library: `Mix.parse/build`, `Box`, `Pad`, `Track`, `Event`,
  `Catalog` (`RAVE20.INF` id → group/name).
* `mixdump.py` — CLI dump / JSON / summary / timeline / round-trip verification.
* `adapter.py` — this tree's adapter for the shared player core
  (`apps/emp/src/core/`): timing, clip cut rule and sample lookup.
* `apps/emp/src/mixplayer.py` — the unified player for all five formats;
  live playback needs `sounddevice`, `--wav` renders without it.  `--format
  techno` names this tree explicitly.
* `apps/emr/src/format/techno/mixrender.py` — PNG arrangement renderer: shared
  engine in `apps/emr/src/render/`, Techno's `RAVE20` index and bar length in
  the provider; writes `images/`, one grid per song.
  `python apps/emr/src/mixrender.py` renders any format (`--format techno`).
* `libs/pxd/` — shared `tPxD` decoder plus `Bundle` for `RAVE20`
  and its twelve-line `.INF` index; standalone files decode directly.

## Format at a glance

Little-endian; sizes vary because a song is a sparse structure, not a fixed
grid: **2 144 … 6 236 bytes** across the corpus, **52 369 bytes** in total.

| section | contents |
|---------|----------|
| header, 16 bytes | signature `0x0889`, tempo **140**, three unknown words |
| strings | author (NUL), identification (NUL), title (`0x01` + length + text + NUL + `0x01`) |
| track table | 16 × (pan, volume); pan 0/1/2 read as both/left/right |
| six words | `0, 0, 0, 0, 0, 14 or 16` |
| sample set | `Techno eJay 2 ` (two files: `Techno eJay `), marker `9` |
| kit boxes | 7 × id range + product name, then an 8-zero terminator |
| pad prefix | 28 constant bytes, then **10 drum pads** (id 0, name, pitch, three words) |
| pattern block | 22-byte preamble, 17 section headers, 7-byte clips and 17-byte hits, each with a start bar |
| events | none in this corpus |
| trailer | `A9 7A 8A 01` |

* **140 BPM** is stored at `0x08` in every file, so a 4/4 bar is exactly
  **75 600 samples** at 44.1 kHz.
* **16 audio tracks** with a pan and a volume word each.  All 259 pan words are
  0, 1 or 2 except one 3 (`SOAP.MIX` track 16).
* The pattern block is the arrangement, not a separate drum lane: section `n`
  holds the records of track `n`.  There are **4 562 clips and 522 hits** in the
  corpus, and every one is in non-decreasing time order inside its section.
* Sample ids are **`RAVE20.INF` ids**: 4 015 records, contiguous
  **13 000 … 17 014**, fetched from the 429 MB `RAVE20` container.  All 362 ids
  used by the songs resolve.
* The seven kit boxes declare ids `2 000 … 7 199` but no arrangement record uses
  them; they are inherited product declarations, not the id source.

## Results

* **13/13 songs decode and re-encode byte-identically** (`mixdump.py --verify
  --all`), including the pattern block and the trailer.
* 52 369 bytes total; **42 199 bytes (80.6 %) are the pattern block**, decoded as
  a 22-byte preamble, 17 headers and 5 084 records (4 562 clips, 522 hits), each
  with a measured start bar.  The preamble's ninth word equals the block length
  minus 18 in every file.
* **130 drum pads**, ten fixed names, all with sample id 0; pitch −7 … 0,
  `word2` 0, `word3` 17 840 … 26 578, `word4` 0/1/2.  They carry no catalogue
  id, so the player does not use them.
* **0 imported-sample events** in all 13 files.
* **362 distinct arrangement sample ids**, all present in `RAVE20.INF`; the 362
  records decode with peak **0.4509** and 361 are whole bars (one is 76 040
  samples, 1.0058 bars).
* All **504** standalone `HYP1` … `HYP4` samples decode, peak **0.4987**.
* `mixplayer.py` mixes the records on a 44.1 kHz stereo timeline and normalises
  to the measured mix peak.  `START.MIX` is 134 bars (229.7 s); its first eight
  bars render to a 604 800-frame stereo WAV with peak 0.41.
* `mixrender.py` writes 13 PNG grids in `images/`, one per song; the songs are
  66 … 220 bars wide and the images are 700 … 940 px at 4 … 10 px per bar,
  with the 16 tracks as rows and the bar ruler numbered from 1.

## Playback model

The file stores no clip length.  A record plays from its start bar, is cut where
the next record on the same track starts, and otherwise plays its whole sample;
the player never loops or stretches a sample.  That rule is not stated by the
format, so it is the first place to look if a render differs from eJay.
Tracks are mono lanes routed by the stored pan word.  The stored per-track
volume is not applied.  A record whose sample is missing is skipped and
reported, but no id used by this corpus is missing.

## Scope and caveats

* The pattern block decodes in full.  Still uninterpreted: a clip's `byte0`
  (always 0 here), a hit's ten trailing bytes and the last `uint32` of the
  preamble (the size word is understood, this one is not).
* `field_04` (111 … 391), `field_0a` (134 … 158), `field_0e` (24/28/30), the
  marker `9` and the pad words `word3`/`word4` are uninterpreted.
* Pan 0/1/2 = both/left/right is an inference from the value range and from
  `…L`/`…R` sample pairs; the single value 3 is unknown and the player treats it
  as both.
* The kit boxes name Dance eJay products whose ids no song uses, and the pads
  have no resolvable id; neither affects playback.
* Documentation numbers are measured from the shipped files; the commands in
  the docs reproduce them.
