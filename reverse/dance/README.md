# Dance eJay 1.x `*.MIX` — reversed format, tools and notes

Reverse-engineered description of the 16 music files in `disks/Dance_eJay/MIX`, plus
the tooling to decode, verify, render and re-encode them.

Nothing here executes the programs in the repository and nothing is read or
written outside this project: the format was recovered by reading the data
files (`.MIX`, `DANCE/EJAY/MAX`, the `tPxD` headers of the samples) and proved
by re-encoding every decoded song byte for byte.

## Documentation map

| file | contents |
|------|----------|
| [`FORMAT.md`](FORMAT.md) | the byte-level format spec: header, song grid, sample ids, bank block, worked example |
| [`SAMPLES.md`](SAMPLES.md) | how sample ids map to the `.PXD` files: catalogue files, numbering scheme, boxes, what is missing |
| [`MIXES.md`](MIXES.md) | catalogue of all 16 songs with measured statistics and arrangement observations |
| [`METHOD.md`](METHOD.md) | how each field was derived, the evidence, the dead ends and what is still unknown |
| [`PXD.md`](PXD.md) | the `.PXD` container and audio codec, and how the decoder was validated against all 1 352 samples |

## Tools

The parser lives in `libs/mix/dance/` and the player runtime in
`apps/emp/src/format/dance/`; this directory keeps the
prose, `mixdump.py` and the generated artifacts.

Pure Python 3, standard library only (no Pillow, no third-party packages).

```
python reverse/dance/mixdump.py --all                                # readable dump
python reverse/dance/mixdump.py disks/Dance_eJay/MIX/START.MIX             # one song
python reverse/dance/mixdump.py --json reverse/dance/decoded --all         # JSON per song
python reverse/dance/mixdump.py --verify --all                       # re-encode + byte-compare
python apps/emr/src/format/dance/mixrender.py --out reverse/dance/images --all   # arrangement PNGs
python apps/emp/src/mixplayer.py --format dance START.MIX                    # play a song
python apps/emp/src/mixplayer.py --format dance START.MIX --wav out.wav      # render instead
```

* `mixfmt.py` — library: `Mix.parse/build`, `BankBlock`, `Catalog` (one list:
  id → path, name, box) and `Catalogs` (ordered set of lists), `events()`,
  `track_usage()`, `duration()`.
* `mixdump.py` — CLI dump / JSON / round-trip verification.
* `apps/emr/src/format/dance/mixrender.py` — PNG renderer: x = bar, y = track,
  one coloured bar per placed sample, spanning the sample's length in bars; the
  canvas includes ringing tails (`reverse/dance/images/*.png`).
* `libs/pxd/` — the shared `.PXD` audio decoder (a Python port of
  the ejay_pxd algorithm, see `PXD.md`); every tree decodes through it.
* `adapter.py` — this tree's adapter for the shared player core
  (`apps/emp/src/core/`): tempo, bar length, pan rule and sample source.
* `apps/emp/src/mixplayer.py` — the unified player, one command for all five
  formats: plays a song through `sounddevice`, mixing the decoded samples at
  their bar positions; `--wav` renders to a file instead.  `--format dance`
  names this tree explicitly.

The three mix CLIs take `-v/--verbose`: `mixdump.py` and `mixrender.py` add
per-track placed/distinct counts (the dump also counts where each placement
resolves), and `mixplayer.py` logs every decoded sample and the gain estimate.

## Playback

The samples are cut at 140 BPM, so at 44.1 kHz a bar is exactly 75 600 samples
and every onset is an integer offset — the player mixes on the fly without
resampling, streaming through a `sounddevice.OutputStream` callback:

```
python apps/emp/src/mixplayer.py --format dance START.MIX               # whole song
python apps/emp/src/mixplayer.py --format dance START.MIX --bars 8      # first 8 bars
python apps/emp/src/mixplayer.py --format dance X_PERM.MIX --from 200 --loop
python apps/emp/src/mixplayer.py --format dance START.MIX --solo 3      # only track 3
python apps/emp/src/mixplayer.py --format dance START.MIX --mute 7,8 --gain 0.8
python apps/emp/src/mixplayer.py --format dance SPACE.MIX --wav space.wav
```

Sample lookup goes through an ordered set of catalogues.  The regular
`PXDDANCE` bank (ids 731+) and `SPECIAL` (WAV samples, ids 1+) are separate
lists, loaded as two `mixfmt.Catalog` objects in a `mixfmt.Catalogs`; the
player accepts further lists with `--catalog LIST DIR BASE` (repeatable,
searched before the built-in Dance lists), so an installation or sample set
can be added without merging its id space into the Dance bank.

Output is stereo.  The tracks are mono lanes and the grid stores no pan, so
the player applies the corpus rule: T7 is hard left, T8 hard right and T1–T6
are centred (the mixes pair `… L` samples on T7 with `… R` samples on T8).
Gain is normalised per song from the per-channel summed sample peaks (all
samples peak at or below −6 dBFS, eight layers would clip otherwise), with
`--gain` to override.
A song plays until the last placed sample has rung out, not just to the last
occupied bar: `START`/`XPIPE` run 90 bars although the grid stops at 83.
Placements whose sample is not on disk (add-on box ids, empty import slots)
are skipped and reported, so such songs play with those parts missing.

## Format at a glance

Little-endian. `0x2BE2 = 2 + 702 × 8 × 2` is the size of the song part; files
that are exactly 11234 bytes carry nothing else.

| offset | size | field |
|--------|------|-------|
| `0x0000` | 2 | signature `0x0A06` (all 16 files) |
| `0x0002` | 11232 | song grid: 702 bars × 8 tracks × `uint16` sample id, bar-major, 0 = empty |
| `0x2BE2` | variable | optional sample-bank block (two variants, `0x0A06` / `0x0A08`) |

* tempo is not stored — the samples are cut at **140 BPM 4/4** (`Task.md`), so
  a bar is `12/7 ≈ 1.714 s`;
* a sample id is a **slot in eJay's sample bank**: `731 + n` is record `n`
  of `DANCE/EJAY/PXDDANCE` (1 352 records of path, category, number, group,
  name; the label is `group + " " + name`);
* ids `1..168` are `SPECIAL` WAV samples (`disks/Dance_eJay/SPECIAL`), `169..730`
  are empty import slots, and ids from `3 400` are add-on sample boxes named
  in the bank block (see `SAMPLES.md`).

## Results

* **16/16 songs decode and re-encode byte-identically**, including both
  bank-block variants and both list counts (`mixdump.py --verify --all`).
* 5 456 bars, 3 995 placed samples, 588 distinct samples used.
* 8 tracks declared and all 8 used; longest song 444 bars ≈ 12.7 min.
* `START.MIX` ≡ `XPIPE.MIX` byte-identical; `DREAM.MIX` and `RAPSVOIC.MIX`
  share an identical song grid and differ only in their bank block.
* Sample ids resolve to shipped audio for 2 689 of 3 995 placements (324 of
  the 588 distinct ids): 2 580 to `.PXD` files, 109 to `SPECIAL` WAVs.  The
  other 1 306 use add-on box ids, whose samples are not in this copy.
