# How the format was recovered (method, evidence, dead ends)

## 1. Constraints

* No program from the repository was executed — everything is static reading
  of data files.
* No file outside this project was read or written.
* The tooling under `libs/mix/rave/` is an independent copy: it does not import
  or reuse code from `libs/mix/dance/`.  The `.PXD` codec is a fresh Python
  implementation of the algorithm published by the `ejay_pxd` project, not a
  copy of the Dance decoder.
* Python 3 only (`python`, 3.14), `numpy` for the audio paths; `bash` (Git
  Bash on Windows) for running the scripts.

## 2. Starting point: the size

Every `*.MIX` is at least **11 234** bytes and two sizes exist (11 276 and
11 326).  11 234 looked like a complete structure:

```
11234 = 2 + 11232 = 2 + 702 * 8 * 2
```

i.e. a 2-byte signature plus `702 bars × 8 tracks × uint16`, which matches the
"8 tracks" layout known from Dance eJay and leaves a natural 702-bar song
capacity.  The extra 42 / 92 bytes became the "bank block" (§6).

The signature is `0x0A07` in all 15 files, one greater than the Dance song
signature `0x0A06`; the bank block uses `0x0A08`, as in Dance's v8 blocks.

## 3. Tempo: why a bar is 58 800 samples

Tempo is not stored.  Three independent measurements pin the bar to
**58 800 samples** at 44.1 kHz, which is 4 beats at **180 BPM**:

1. **Placement tiling.**  For every pair of consecutive placements on the same
   track, compare the bar gap with the first sample's declared length.  Of the
   4 757 pairs whose first sample resolves, **3 896 (81.9 %)** have the next
   onset exactly `declared_count` samples later — the samples tile seamlessly
   at 58 800 samples per bar.  Reading the same gaps as 117 600-sample bars
   fits only **166 (3.5 %)**.
2. **Declared lengths.**  `declared_count / 58 800` is a whole number for
   **1 145 of the 1 149** catalogue records; the four exceptions are within
   3.2 % (they are listed in `SAMPLES.md` §1).  No other divisor near this
   value fits the corpus.
3. **Metadata.**  Every `.PXD` that has a `tPxD` header ends its metadata with
   the line `58800` (1 148 files; the one headerless file has no metadata).
   The 128 `HYPER` files declare 14 700 or 29 400 samples — exactly 1/4 and
   1/2 of 58 800 — which is consistent but not used by the songs.

At 180 BPM 4/4, a bar is `4 * 60/180 = 4/3 ≈ 1.333 s`; the 702-bar grid is
≈ 936 s ≈ 15.6 min.  The corpus's longest grid is 526 bars (`VIENI`).

## 4. What each grid claim rests on

| claim | evidence |
|-------|----------|
| signature `0x0A07` | first word of all 15 files is `0x0A07`, no other value |
| 702 × 8 grid of `uint16` | file size arithmetic; grid ends exactly at `0x2BE2`; the tail of the grid is zero |
| bar-major, tracks interleaved | sample ids recur at a period of 8 words and never repeat inside a bar; every slot index (mod 8) behaves as one continuous instrumental lane over a whole song (`MIXES.md` §4); the corpus reaches exactly 8 occupied slots in 50 bars |
| no bar holds > 8 samples | maximum occupancy over 5 329 bars is exactly 8 |
| 0 = empty | the zero-filled tail; lanes are sparse exactly where nothing sounds |
| song length from last non-empty bar | the dense region ends at the last occupied slot; times derived this way are musically plausible |
| 180 BPM not stored | no tempo field anywhere in the 11 234-byte structure; the three measurements in §3 |
| id = `731` + `RAVE/EJAY/PXD` record | `START` bars 0–4 show exactly the samples those ids name (§5); `MAX` order does not fit |
| no pan field | the grid has one `uint16` per lane; `L`/`R` labels are spread over T1–T8 (§5) |
| bank-block layout | byte-exact re-encoding of all 15 files, including both trailer variants and `NODRUGS`' extra 50 bytes |

## 5. Cross-validation of the sample numbering

The id order comes from `RAVE/EJAY/PXD`, not from `MAX`:

1. `RAVE/EJAY/PXD` holds 1 149 six-field records (path, empty, category,
   nominal bars, group, name); `id = 731 + index`, label = `group + " " + name`.
2. The first records are bass samples (`wood walk 1`, `wood walk 2`, …), the
   last is the voice record `http://www.eJay.com` (id 1879) — the catalogue is
   grouped by category, not alphabetically.
3. eJay's display for `START.MIX` bars 0–4 — `thumb`, `scream L`,
   `scream R`, `this is  MC magic`, `hihat distorted 1`, `distorted motion 1`,
   `life in space`, `eJay 5` — matches ids 1094, 1075, 1076, 1846, 1018,
   1400, 1850, 1755 exactly (`SAMPLES.md` §1).
4. Musical sense of the decoded dumps: T7/T8 are the `scream L`/`scream R`
   pair in the first bar, T1 carries the vocal `this is  MC magic` and
   `life in space`, T5 the `distorted motion` layer.

The nominal length field independently ties records to audio: for 1 145 of
1 149 records, `number × 58 800` equals the declared sample count in the
`.PXD` header.  That is a second, internal check that the record order and the
file paths belong together.

`MAX` and `MIN` were not usable as an id order: they are folder-sorted lists
of paths (`MAX` 3 145, `MIN` 860) with no relation to the catalogue sequence.
The Rave file names are `R1xxNNN`, not a base-26 index, so there is no
self-consistent "line number" trap of the kind found in the Dance data.

## 6. The bank block

All 15 files have the same shape, so it was recognised quickly by file size:

* 42-byte tails (`14 files`): tag `0x0A08`, `nlists = 1`, version string
  `"Rave eJay 1.01"` + NUL + `0x01`, one empty list, then an 18-byte trailer.
* 92-byte tail (`NODRUGS`): the same block, but the trailer is 68 bytes.

The 18-byte trailer has two variants: twelve files end with 12 zero bytes then
`01 00 02 00`; `LAJALI` and `SCOOL` have 8 zero bytes then `01 00 02 00`
twice.  The first word is `08 00` in every file — the track count — and the
rest is constant enough that only the leading word is identifiable.  Rather
than guess, the parser stores the whole trailer verbatim; that is what makes
the writer byte-exact.

`NODRUGS`' extra 50 bytes are readable as a fragment of a serialised sample
reference: `"ool"`, a length-prefixed `"004"`, a length-prefixed
`c:\raveejay\hypersav\scool004.wav`, and a length-prefixed `"hyper"`.  It is
preserved but not interpreted.  It is the only evidence in the corpus that a
hyper sample was involved in a song, and it does not give a grid-id mapping.

The bank block declares **no boxes**, and no shipped song uses an add-on box
id, so there is no box-resolution problem here (unlike Dance).

## 7. Dead ends

* **Public documentation**: no usable specification of the Rave `*.MIX`
  format was found.  The public eJay work that exists documents the `.PXD`
  codec (`ejay_pxd`), not this container.
* **`RAVE/EJAY/INTRO.PXD`**: the name suggests a song, but it is a 1 025 436-
  byte `tPxD` sample, 21 bars long.  It is not a second mix format.
* **`MAX` / `MIN`**: folder-sorted inventories; `MIN` is a subset of `MAX`,
  not an id list.  They add no ordering information.
* **`RAVE/HYPER`**: 128 samples in eight categories, but no id in `731..1879`
  references them and the low ids cannot be proved to map to them.  The
  `NODRUGS` trailer is a hint, not a mapping.
* **Low ids `1..15`**: 174 placements, no shipped audio.  `TRANCE` uses all
  fifteen in sequence and `VIENI` repeats id 12 113 times; both look like
  placeholders, but eJay's meaning for the slots is unknown.
* **`.PXD` audio payload**: the codec was implemented from the published
  `ejay_pxd` algorithm and validated by size, duration and peak; it was not
  independently reverse-engineered from the bitstream.

## 8. Proof rather than plausibility

The strongest evidence for the whole model is the round trip: parse a file,
rebuild it from the structured model (signature, 702 × 8 grid, bank block) and
compare.  `python reverse/rave/mixdump.py --verify --all` reports
**15/15 byte-identical**.  A wrong bar/track order, wrong id width, wrong tail
layout or a missing byte would break it immediately.

The second proof is musical: the decoded ids produce coherent labels for the
first bars of `START` (`thumb`, `scream L/R`, `this is  MC magic`,
`life in space`) and the arrangement lanes stay on one instrument for bars at a
time (`MIXES.md` §4).

## 9. What is still unknown

* the meaning of the 18-byte trailer beyond its leading track-count word, and
  why `LAJALI`/`SCOOL` write the `01 00 02 00` pair twice,
* the 50 extra `NODRUGS` trailer bytes (structure partly readable, purpose
  unknown),
* the mapping of ids `1..15` to audio (if any); the HYPER bank is a candidate
  but not proved,
* why `VIENI` pads its grid with id 12 and `TRANCE` walks through ids 1–15 —
  placeholders, markers, or a sample set that is simply absent,
* whether the low byte of `0x0A07` is a revision number (it is one greater
  than Dance's `0x0A06`, and the bank tag is `0x0A08`), treated here as a
  format tag,
* the `.PXD` header fields beyond the metadata text and the declared count.

A byte-level breakdown of how much of the corpus each of these affects is in
[`FORMAT.md`](FORMAT.md) §8: 290 trailer bytes + 15 version-flag bytes =
305 of 169 190 bytes (0.18 %) have no confirmed meaning, and the 30 signature
bytes are a constant format tag.  Every byte is located and the writer
reproduces all 169 190 exactly.

## 10. Reproducing the results

```
python reverse/rave/mixdump.py --verify --all                          # 15/15 byte-identical
python reverse/rave/mixdump.py --all                                   # readable dump, with sample names
python reverse/rave/mixdump.py --json reverse/rave/decoded --all       # machine-readable grids
python apps/emr/src/format/rave/mixrender.py --out reverse/rave/images --all # arrangement PNGs
python libs/pxd/ disks/Rave_eJay/RAVE/BQ/R1BS001.PXD --stats
```
