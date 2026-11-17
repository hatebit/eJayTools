# Dance eJay 2 `*.MIX` — reversed format, tools and notes

Reverse-engineered description of the 13 songs in `disks/Dance_2/MIX`, plus the
tooling to decode, verify and re-encode them and to read the sample containers
they use.

Nothing here executes the programs in the repository: the format was recovered
by reading data files (`.MIX`, `D_ejay2/PXD/DANCE20` + `DANCE20.INF`, the
`DANCESK*` add-on banks, `ejay/Audio_*`) and proved by re-encoding every song
byte for byte.  This tree is independent of `libs/mix/dance`,
`libs/mix/rave` and `libs/mix/hiphop`; the `.PXD`
decoder is the shared package in `libs/pxd/`, which none of the trees
imports from one another.

## Documentation map

| file | contents |
|------|----------|
| [`FORMAT.md`](FORMAT.md) | byte-level spec: header, strings, track table, kit boxes, pads, pattern block, events, worked example |
| [`SAMPLES.md`](SAMPLES.md) | sample ids: `DANCE20.INF`, the add-on banks, `Audio_*`, `PXD10`, what is missing |
| [`PXD.md`](PXD.md) | the `tPxD` container and audio codec, bundled and standalone samples |
| [`MIXES.md`](MIXES.md) | all 13 songs with measured statistics |
| [`METHOD.md`](METHOD.md) | evidence, the parser bug that was found and fixed, dead ends, unknowns |

## Tools

The parser lives in `libs/mix/dance2/` and the player runtime in
`apps/emp/src/format/dance2/`; this directory keeps the
prose, `mixdump.py` and the generated artifacts.

Pure Python 3.  `mixfmt.py` and `mixdump.py` are standard-library only; the
shared `.PXD` codec (`libs/pxd/`) and the player core need `numpy`.

```
python reverse/dance2/mixdump.py --all                                # readable dump
python reverse/dance2/mixdump.py --summary --all                      # one line per song
python reverse/dance2/mixdump.py --pattern OTHER.MIX                  # bar-by-bar plan
python reverse/dance2/mixdump.py --json reverse/dance2/decoded --all
python reverse/dance2/mixdump.py --verify --all                       # re-encode + byte-compare
python apps/emp/src/mixplayer.py --format dance2 OTHER.MIX --from 1 --bars 10 --wav out.wav
python apps/emr/src/format/dance2/mixrender.py --out reverse/dance2/images --all
python libs/pxd disks/Dance_2/D_ejay2/PXD/DANCE20.INF --id 1930 --stats
python libs/pxd disks/Dance_2/D_ejay2/ejay/DINTRO.PXD --stats
```

* `mixfmt.py` — library: `Mix.parse/build`, `Box`, `Pad`, `Track`, `Event`,
  `Catalog` (`DANCE20.INF` id → group/name).
* `mixdump.py` — CLI dump / JSON / summary / pattern timeline / round-trip
  verification.
* `adapter.py` — this tree's adapter for the shared player core
  (`apps/emp/src/core/`): timing, clip cut rule and sample lookup.
* `apps/emp/src/mixplayer.py` — the unified player for all five formats;
  live playback needs `sounddevice`, `--wav` renders without it.  `--format
  dance2` names this tree explicitly.
* `apps/emr/src/format/dance2/mixrender.py` — PNG arrangement renderer
  (standard library `zlib`, no Pillow); writes `images/`, one grid per song.
* `libs/pxd/` — shared `tPxD` decoder plus `Bundle` for the
  concatenated files (`DANCE20`, `DANCESK4/5/6`) and their 12-line `.INF`
  indexes.

The player renders the arrangement: the pattern block decodes in full
(section = track, 3 654 seven-byte clips and 16 seventeen-byte hits, each with
a start bar; `FORMAT.md` §7) and the mapping matches eJay's own arrangement
of `OTHER.MIX` for its first ten bars.  The file stores no clip length, so the
player cuts a record where the next record on the same track starts and plays
its whole sample otherwise — it never loops or stretches.  That is the one part
of playback the format does not state; a hit's ten trailing bytes are not used
by the player at all.  `mixrender.py` draws the same spans as a PNG track grid,
so `images/` shows exactly what the player sounds.

## Format at a glance

Little-endian.  Sizes vary because the song is a sparse structure, not a fixed
grid: 1 553 … 8 219 bytes across the corpus, 56 604 bytes in total.

| offset | field |
|--------|-------|
| `0x00` | `uint16` signature `0x0A19` (all 13 files) |
| `0x02` | three silent `uint16`s and four values: `field_04`, tempo `140`, `field_0a`, `field_0e` (§2) |
| `0x10` | author and identification strings, then the title record |
| … | 16 × (`uint16` pan, `uint16` volume), six trailer words, sample-set string, `uint16 9` |
| … | seven sample-kit boxes (id range + name), terminator |
| … | pad prefix, 10 drum-pad records (sample id, name, 8-byte tail) |
| … | drum-pattern block: 22-byte preamble, 17 section headers, 7-byte clips and 17-byte hits with start bars (§7) |
| … | imported-sample events: 27-byte tail + name + number, repeated |
| end | trailer `A9 7A 8A 01` |

* **140 BPM** is stored in the header (word at `0x08`) in every file, matching
  the tempo of eJay, so a 4/4 bar is exactly **75 600 samples** at 44.1 kHz.
* **16 audio tracks.** Each has a pan word and a volume word.  Pan takes the
  values 0, 1 and 2; eJay exposes exactly three speaker states per track
  (both, left, right), so the reading is **0 = both, 1 = left, 2 = right**
  (inferred from the manual and the value range, not stated by the file).
* The extra track **“0”** in eJay is the separate **drum track**.  It has
  no row in the 16-track table; its ten Groove Generator pads and its hit
  pattern are the pad list and the pattern block.  That mapping follows the
  manual and the file layout; the pattern encoding is described in §7.
* Sample ids in the pad records are **`DANCE20.INF` ids** (`1 … 1957`): all 81
  distinct pad ids across the corpus resolve to a record, and the record's
  group/name produces the label shown by eJay (`humn. 9` for
  `humn.9`/id 1930).
* The seven kit boxes declare id ranges **2 000 … 7 199** for eJay's
  sample kits.  The shipped add-on banks cover the Vol. 4–6 ranges
  (`DANCESK4/5/6`, ids `5100 … 7063`); no shipped container covers
  `2 000 … 5 099`.

## Results

* **13/13 songs decode and re-encode byte-identically** (`mixdump.py --verify
  --all`), including the pad prefix, the kit-box terminator and the event
  trailer.
* 56 604 bytes total; **27 241 bytes (48.1 %) are the pattern block**, decoded
  as a 22-byte preamble, 17 headers and 3 670 records (3 654 clips, 16 hits),
  each with a measured start bar.
* **130 drum pads** (10 per song), **81 distinct sample ids**, all present in
  `DANCE20.INF`; pitch −12 … +12; `word4` is only 0, 1 or 2.
* **449 imported-sample events** in 8 songs; the other 5 songs have no event
  list at all (`HOUSE`, `LATIN`, `OTHER`, `TRANCE`, `TRIBUTE`).
* **1 957 / 1 957 `DANCE20` samples decode**, covering all 231 270 914 bytes of
  the container; peak stays at or below **0.4854** (−6.3 dBFS).
* Rendering `OTHER.MIX` per track puts the twelve `heart beat` hits on bars
  1-12, the `bloose` pairs on bars 5 and 9 and `grave beat 2` from bar 9, i.e.
  the arrangement the dump lists; the whole song renders 90 bars (154.3 s).
* The add-on banks `DANCESK4` (598 records), `DANCESK5` (677) and `DANCESK6`
  (564) are contiguous and fully indexed; their audio was not decoded here.
* **119 standalone `tPxD` streams decode** (118 in `Audio_d/e/f` plus
  `DINTRO.PXD`); `METRO.PXD` is a RIFF/WAVE file, not `tPxD`.
* `PXD10` is a 1 352-entry catalogue whose sample paths are **absent** from the
  shipped tree; it is not the index of the `Audio_*` files
  (`SAMPLES.md` §4).

## Scope and caveats

* The pattern block — the largest single region of the format — decodes as
  seventeen `u8 index, u16 count, u16 0` headers, 3 654 clips and 16 hits,
  each with a start bar (`FORMAT.md` §7).  Still uninterpreted: the 22-byte
  preamble, a clip's `byte0` and a hit's ten trailing bytes.  The player cuts a
  clip at the next record on its track and never loops; whether eJay does
  the same is not recorded in the file.
* `field_04` (27 … 304) is plausibly a song length in bars, but no field in the
  file states that; it is documented as unknown rather than named.
* `field_0a` (136 … 152), `field_0e` (26 … 30), the constant `uint16 9` and the
  pad-tail words `word2`/`word3`/`word4` are uninterpreted.
* Each event keeps a 27-byte tail; its first 7 bytes decode as kind `2`, a
  channel byte (`0x7F`/`0xFF`), an int24 pitch and a `uint16` instance
  (`7200 … 7335`).  The remaining 20 bytes are preserved but unknown.
* The kit boxes name add-on products whose samples are not shipped
  (`2 000 … 5 099`), so those references cannot be resolved.
* Documentation numbers are measured from the shipped files; the commands in
  the docs reproduce them.
