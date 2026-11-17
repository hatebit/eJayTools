# HipHop eJay 1.x `*.MIX` — reversed format, tools and notes

Reverse-engineered description of the 17 music files in
`disks/Hiphop_eJay/MIX`, plus the tooling to decode, verify, render and
re-encode them.

Nothing here executes the programs in the repository and nothing is read or
written outside this project: the format was recovered by reading the data
files (`.MIX`, `HIPHOP/EJAY/PXD`, `HIPHOP/EJAY/SPECIAL`, the `tPxD` headers of
the samples) and proved by re-encoding every decoded song byte for byte.

## Documentation map

| file | contents |
|------|----------|
| [`FORMAT.md`](FORMAT.md) | the byte-level format spec: header, song grid, sample ids, bank block, worked example |
| [`SAMPLES.md`](SAMPLES.md) | how sample ids map to `.PXD` files and `SPECIAL` WAVs: catalogues, numbering, manifests |
| [`MIXES.md`](MIXES.md) | catalogue of all 17 songs with measured statistics and arrangement observations |
| [`METHOD.md`](METHOD.md) | how each field was derived, the evidence, the dead ends and what is still unknown |
| [`PXD.md`](PXD.md) | the `.PXD` container and audio codec, and how the decoder was validated against all 1 341 samples |

## Tools

The parser lives in `libs/mix/hiphop/` and the player runtime in
`apps/emp/src/format/hiphop/`; this directory keeps the
prose, `mixdump.py` and the generated artifacts.

Pure Python 3, standard library only for the mix tools (no Pillow, no
third-party packages); `numpy` is needed by the shared `.PXD` codec
(`libs/pxd/`) and the player core.

```
python reverse/hiphop/mixdump.py --all                                # readable dump
python reverse/hiphop/mixdump.py disks/Hiphop_eJay/MIX/START.MIX           # one song
python reverse/hiphop/mixdump.py --json reverse/hiphop/decoded --all       # JSON per song
python reverse/hiphop/mixdump.py --verify --all                       # re-encode + byte-compare
python apps/emr/src/format/hiphop/mixrender.py --out reverse/hiphop/images --all # arrangement PNGs
python apps/emp/src/mixplayer.py --format hiphop START.MIX                    # play a song
python apps/emp/src/mixplayer.py --format hiphop START.MIX --wav out.wav      # render instead
```

* `mixfmt.py` — library: `Mix.parse/build`, `BankBlock`, `Catalog` (one list:
  id → path, name) and `Catalogs` (ordered set of lists), `events()`,
  `track_usage()`, `pan`, `duration()`.
* `mixdump.py` — CLI dump / JSON / round-trip verification.
* `apps/emr/src/format/hiphop/mixrender.py` — PNG renderer: x = bar, y = track,
  one coloured bar per placed sample, spanning the sample's length in bars; the
  canvas includes ringing tails (`reverse/hiphop/images/*.png`).
* `libs/pxd/` — the shared `.PXD` audio decoder (a Python port of
  the ejay_pxd algorithm, see `PXD.md`).
* `adapter.py` — this tree's adapter for the shared player core
  (`apps/emp/src/core/`): tempo, bar length, stored pan words, sample source.
* `apps/emp/src/mixplayer.py` — the unified player, one command for all five
  formats: plays a song through `sounddevice`, mixing the decoded samples at
  their bar positions; `--wav` renders to a file instead.  `--format hiphop`
  names this tree explicitly.

The three mix CLIs take `-v/--verbose`: `mixdump.py` and `mixrender.py` add
per-track placed/distinct counts (the dump also counts where each placement
resolves), and `mixplayer.py` logs every decoded sample and the gain estimate.

## Playback

The samples are cut at 96 BPM, so at 44.1 kHz a bar is exactly 110 250 samples
and every onset is an integer offset — the player mixes on the fly without
resampling, streaming through a `sounddevice.OutputStream` callback:

```
python apps/emp/src/mixplayer.py --format hiphop START.MIX               # whole song
python apps/emp/src/mixplayer.py --format hiphop START.MIX --bars 8      # first 8 bars
python apps/emp/src/mixplayer.py --format hiphop HIPHOP.MIX --from 16 --loop
python apps/emp/src/mixplayer.py --format hiphop START.MIX --solo 3      # only track 3
python apps/emp/src/mixplayer.py --format hiphop START.MIX --mute 7,8 --gain 0.8
python apps/emp/src/mixplayer.py --format hiphop VIBE.MIX --wav vibe.wav
```

Sample lookup goes through an ordered set of catalogues.  The regular
`HIPHOP/EJAY/PXD` bank (ids 731+) and `SPECIAL` (WAV samples, ids 1+) are
separate lists, loaded as two `mixfmt.Catalog` objects in a
`mixfmt.Catalogs`; the player accepts further lists with
`--catalog LIST DIR BASE` (repeatable, searched before the built-in HipHop
lists), so an installation or sample set can be added without merging its id
space into the HipHop bank.

Output is stereo.  Unlike Dance eJay, the pan is stored: the bank block ends
with one word per track (0 centre, 1 left, 2 right) and the player uses it, so
the default `T1–T6 centred, T7 left, T8 right` is not hard-coded — `DUTCH`,
`FEEDHIP`, `GOODMOOD` and `HIPHOP` pan differently (`FORMAT.md` §4c).
Gain is normalised per song from the per-channel summed sample peaks (the
decoded samples peak at or below −8 dBFS, eight layers would clip otherwise),
with `--gain` to override.
A song plays until the last placed sample has rung out, not just to the last
occupied bar: `MYSELF` runs 104 bars although the grid stops at 103.
Placements whose sample is not on disk are skipped and reported — none are
missing in this corpus.

## Format at a glance

Little-endian. `0x2BE2 = 2 + 702 × 8 × 2` is the size of the song part; every
file adds the same 1 458-byte bank block, so all 17 are exactly 12 692 bytes.

| offset | size | field |
|--------|------|-------|
| `0x0000` | 2 | signature `0x0A08` (all 17 files) |
| `0x0002` | 11232 | song grid: 702 bars × 8 tracks × `uint16` sample id, bar-major, 0 = empty |
| `0x2BE2` | 1458 | sample-bank block: tag, version, two 704-byte tables, 4-word head, track count, 8 pan words |

* tempo is not stored — the samples are cut at **96 BPM 4/4**, so a bar is
  `4 × 60/96 = 2.5 s` = **110 250 samples**;
* a sample id is a **slot in eJay's sample bank**: `731 + n` is record `n`
  of `HIPHOP/EJAY/PXD` (1 341 records; the label is `group + " " + name`), and
  `1 + n` is record `n` of `HIPHOP/EJAY/SPECIAL` (101 WAV samples);
* ids `102..730` are empty import slots; no add-on boxes are used by this
  corpus, and all 5 488 placements resolve (see `SAMPLES.md`);
* the block stores one pan word per track: 0 centre, 1 left, 2 right.

## Results

* **17/17 songs decode and re-encode byte-identically** (`mixdump.py --verify
  --all`), including the two constant tables and the per-song `head`/`pan`
  words.
* 5 963 bars, 5 488 placed samples, 531 distinct samples used.
* 8 tracks declared and all 8 used; longest song 481 bars = 1202.5 s (20 min),
  shortest 51 bars = 127.5 s.
* No duplicate songs: all 17 files and grids are distinct.
* Every placement resolves: 5 161 through `.PXD` files, 327 through `SPECIAL`
  WAVs.
* All 1 341 catalogued `.PXD` files decode cleanly; 1 339 are whole 110 250-
  sample bars, two are one-shots/FX, and every peak stays at or below 0.393.
* All 101 `SPECIAL` WAVs are mono 16-bit 44.1 kHz, 220 500 frames (two bars).

## Scope and caveats

* 24 072 of 215 764 bytes (11.2 %) have no established meaning: the two
  704-byte tables (identical in all 17 files) and the `head` words.  Their
  positions and constant values are documented in `FORMAT.md` §4 and kept
  verbatim by the writer; nothing is guessed silently.
* The per-track `pan` words and the track-count word are read by inference
  (`FORMAT.md` §4c); the value range, the common default and the independent
  Dance corpus all support the reading, but no file states it.
* The `.PXD` decoder is a port of the algorithm published by the `ejay_pxd`
  project, re-implemented independently in the Dance, Rave and HipHop trees;
  it is validated by size, duration and peak.
* Documentation numbers are measured from the shipped files, not estimated;
  the commands in the docs reproduce them.
