# Rave eJay 1.x `*.MIX` — reversed format, tools and notes

Reverse-engineered description of the 15 music files in `disks/Rave_eJay/MIX`,
plus the tooling to decode, verify, render and re-encode them.

Nothing here executes the programs in the repository and nothing is read or
written outside this project: the format was recovered by reading the data
files (`.MIX`, `RAVE/EJAY/PXD`, the `tPxD` headers of the samples) and proved
by re-encoding every decoded song byte for byte.  The code is an independent
copy under `libs/mix/rave/`; it does not import anything from
`libs/mix/dance/`, and the `.PXD` codec is the shared package in
`libs/pxd/`.

## Documentation map

| file | contents |
|------|----------|
| [`FORMAT.md`](FORMAT.md) | the byte-level format spec: header, song grid, sample ids, bank block, worked example |
| [`SAMPLES.md`](SAMPLES.md) | how sample ids map to the `.PXD` files: catalogue, numbering, low ids, HYPER bank, what is missing |
| [`MIXES.md`](MIXES.md) | catalogue of all 15 songs with measured statistics and arrangement observations |
| [`METHOD.md`](METHOD.md) | how each field was derived, the evidence, the dead ends and what is still unknown |
| [`PXD.md`](PXD.md) | the `.PXD` container and audio codec, validated against all 1 149 catalogue samples |

## Tools

The parser lives in `libs/mix/rave/` and the player runtime in
`apps/emp/src/format/rave/`; this directory keeps the
prose, `mixdump.py` and the generated artifacts.

Pure Python 3. `mixfmt.py`, `mixdump.py` and `mixrender.py` are standard
library only (no Pillow); the shared `.PXD` codec (`libs/pxd/`) and
the player core need `numpy`, and live playback additionally needs
`sounddevice`.

```
python reverse/rave/mixdump.py --all                                    # readable dump
python reverse/rave/mixdump.py disks/Rave_eJay/MIX/START.MIX            # one song
python reverse/rave/mixdump.py --json reverse/rave/decoded --all        # JSON per song
python reverse/rave/mixdump.py --verify --all                           # re-encode + byte-compare
python apps/emr/src/format/rave/mixrender.py --out reverse/rave/images --all  # arrangement PNGs
python apps/emp/src/mixplayer.py --format rave START.MIX                        # play a song
python apps/emp/src/mixplayer.py --format rave START.MIX --wav out.wav          # render instead
python libs/pxd disks/Rave_eJay/RAVE/BQ/R1BS001.PXD --stats
```

* `mixfmt.py` — library: `Mix.parse/build`, `BankBlock`, `Catalog` (id → path,
  category, nominal bars, group, name) and `Catalogs`, `events()`,
  `track_usage()`, `duration()`.
* `mixdump.py` — CLI dump / JSON / round-trip verification.
* `apps/emr/src/format/rave/mixrender.py` — PNG renderer: x = bar, y = track,
  one coloured bar per placed sample, spanning the sample's length in bars; the
  canvas includes ringing tails (`reverse/rave/images/*.png`).
* `libs/pxd/` — the shared `.PXD` audio decoder, an independent
  Python implementation of the `ejay_pxd` algorithm (see `PXD.md`).
* `adapter.py` — this tree's adapter for the shared player core
  (`apps/emp/src/core/`): tempo, bar length, pan rule and sample source.
* `apps/emp/src/mixplayer.py` — the unified player, one command for all five
  formats: plays a song through `sounddevice`, mixing the decoded samples at
  their bar positions; `--wav` renders to a file instead.  `--format rave`
  names this tree explicitly.

The three mix CLIs take `-v/--verbose`: `mixdump.py` and `mixrender.py` add
per-track placed/distinct counts (the dump also counts where each placement
resolves), and `mixplayer.py` logs every decoded sample and the gain estimate.

## Playback

The samples are cut at **180 BPM 4/4**, so at 44.1 kHz a bar is exactly
**58 800 samples** and every onset is an integer offset — the player mixes on
the fly without resampling, streaming through a `sounddevice.OutputStream`
callback:

```
python apps/emp/src/mixplayer.py --format rave START.MIX               # whole song
python apps/emp/src/mixplayer.py --format rave START.MIX --bars 8      # first 8 bars
python apps/emp/src/mixplayer.py --format rave START.MIX --from 32 --loop
python apps/emp/src/mixplayer.py --format rave START.MIX --solo 3      # only track 3
python apps/emp/src/mixplayer.py --format rave START.MIX --mute 7,8 --gain 0.8
python apps/emp/src/mixplayer.py --format rave VIENI.MIX --wav vieni.wav
```

Sample lookup goes through an ordered set of catalogues.  The built-in Rave
list is `RAVE/EJAY/PXD` (ids from 731, audio under `RAVE/`); the player accepts
further lists with `--catalog LIST DIR BASE` (repeatable, searched before the
built-in list), so another installation or sample set can be added without
merging its id space into the Rave bank.

Output is stereo.  The tracks are mono lanes and the grid stores no pan, so
the player mixes every track centred.  This is deliberately different from the
Dance eJay player: in this corpus 871 placements carry a label ending in `L`
or `R`, and although most sit on T7/T8 (308/309), 254 sit on T1–T6 (T6 alone
has 127), sometimes both halves on one track.  There is no track-based pan rule
the data supports.

Gain is normalised per song from the per-channel summed sample peaks (all
catalogue samples peak at or below 0.500, eight layers would clip otherwise),
with `--gain` to override.  A song plays to the end of its grid, and further
only if the last placed sample with shipped audio rings out beyond the grid
(`START` runs 117 bars although the grid stops at 115).  Placements whose
sample is not on disk — the low ids `1..15` — are skipped and reported.  Some
songs pad the grid with those ids long after the music stops (`VIENI` reaches
bar 526, while its last shipped sample ends at bar 221); the player reports the
skipped placements and plays the intervening bars as silence.

## Format at a glance

Little-endian. `0x2BE2 = 2 + 702 × 8 × 2` is the size of the song part; every
file is larger because a bank block follows it.

| offset | size | field |
|--------|------|-------|
| `0x0000` | 2 | signature `0x0A07` (all 15 files) |
| `0x0002` | 11 232 | song grid: 702 bars × 8 tracks × `uint16` sample id, bar-major, 0 = empty |
| `0x2BE2` | variable | bank block: `0x0A08`, one empty list, then a verbatim trailer (42 or 92 bytes total) |

* tempo is not stored — the samples are cut at **180 BPM 4/4**, so a bar is
  `4/3 ≈ 1.333 s` and 58 800 samples at 44.1 kHz;
* a sample id is a **slot in eJay's sample bank**: `731 + n` is record `n`
  of `RAVE/EJAY/PXD` (1 149 records of path, empty, category, nominal bars,
  group, name; the label is `group + " " + name`);
* ids `1..15` are used (174 placements) but have no shipped audio; `169..730`
  are empty import slots.  This corpus uses no add-on box ids, and the bank
  block declares no boxes (see `SAMPLES.md`).

## Results

* **15/15 songs decode and re-encode byte-identically**, including the two
  trailer variants and the 50-byte extra tail of `NODRUGS.MIX`
  (`mixdump.py --verify --all`).
* 5 329 bars, 5 026 placed samples, 411 distinct sample ids.
* 8 tracks declared and all 8 used; longest grid 526 bars (`VIENI`, ≈ 11.7 min),
  shortest 93 bars (`WOOF`, ≈ 2.1 min).  No two files or grids are identical.
* 4 852 placements (396 distinct ids) resolve to shipped `.PXD` audio; the
  other 174 placements use ids `1..15`, which are not shipped, so those parts
  are skipped.
* All 1 149 catalogued `.PXD` files decode cleanly; 1 145 are whole 58 800-
  sample loops, four have a slightly different declared length, and every peak
  stays at or below 0.500.  One file (`RAVE/BD/R1DA084.PXD`) has no `tPxD`
  header at all and is decoded from its `0x54` marker.
* The separate `RAVE/HYPER` bank (128 samples) also decodes, but no id in
  `731..1879` references it; the low ids are not assumed to map to it.

## Scope and caveats

* The bank trailer is preserved verbatim.  Its first word is the track count
  `8`; the remaining 290 bytes have no confirmed meaning, so they are copied,
  not interpreted (`FORMAT.md` §8).
* Ids `1..15` are unresolved: 174 placements, no shipped audio.  `TRANCE`
  uses all fifteen in a sequence and `VIENI` repeats id `12` 113 times; what
  eJay played for them is unknown.
* The `.PXD` decoder is an independent Python port of the algorithm published
  by the `ejay_pxd` project, validated by size, duration and peak.
* Documentation numbers are measured from the shipped files, not estimated;
  the commands in the docs reproduce them.
