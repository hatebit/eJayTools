# How the format was recovered (method, evidence, dead ends)

## 1. Constraints

* No program from the repository was executed — everything is static reading
  of data files.
* No file outside this project was read or written.
* Python 3 only (`python`, 3.14), standard library; `bash` (Git Bash on
  Windows) for running the scripts.

## 2. Starting point: the size

Every `*.MIX` is at least **11 234** bytes and four distinct sizes exist
(11 234, 11 277, 11 333, 11 413). 11 234 looked like a complete structure:

```
11234 = 2 + 11232 = 2 + 702 * 8 * 2
```

i.e. a 2-byte signature plus `702 bars × 8 tracks × uint16`, which matches the
"8 tracks" in `Task.md` and leaves a natural 702-bar (~20 min at 140 BPM, 4/4)
song capacity. The extra 43 / 99 / 179 bytes became the "bank block" (§5).

## 3. What each claim rests on

| claim | evidence |
|-------|----------|
| signature `0x0A06` | first word of all 16 files is `0x0A06`, no other value |
| 702 × 8 grid of `uint16` | file size arithmetic; grid ends exactly at `0x2BE2`; the values in the tail of the grid are zero |
| bar-major, tracks interleaved | sample ids recur at a period of 8 words and never repeat inside a bar; every slot index (mod 8) behaves as one continuous instrumental lane over a whole song (`MIXES.md` §4); the v8 suffix even declares 8 tracks |
| no bar holds > 8 samples | maximum count over 5 456 bars of the corpus is exactly 8 |
| 0 = empty | the zero-filled tail; lanes are sparse exactly where nothing sounds |
| song length from last non-empty bar | the dense region always ends `2` bytes past the last occupied slot; times derived this way are musically plausible (intro 142 s, songs 10–13 min) |
| 140 BPM not stored | no tempo field anywhere in the 11 234-byte structure; `Task.md` states 140 BPM; all samples are cut to that tempo |
| id = `731` + `PXDDANCE` record | `START` bars 1–4 show exactly the samples those ids name (§4); `MAX` line order does not fit |
| names | read from the `tPxD` header of each sample (magic, length byte, text) |
| bank-block variants | byte-exact layouts re-encode identically (§5, `FORMAT.md` §4) |
| `nlists` | explains the otherwise stray `00 00` in v6/v8 `gung` blocks and makes both variants align (`FORMAT.md` §8) |

## 4. Cross-validation of the sample numbering

The id order comes from `PXDDANCE`, not from `MAX`:

1. `PXDDANCE` holds 1 352 six-field records (path, empty, category, number,
   group, name); `id = 731 + index`, label = `group + " " + name`.
2. eJay's display for `START.MIX` bars 1–4 — `SpaceKnock`, `XPipe 04`,
   `Robot vibrations`, `Myth * L Cut 2`, `Myth * R Cut 2` — matches ids 1186,
   1231, 1919, 973, 974 exactly (`SAMPLES.md` §1).
3. Musical sense of the decoded dumps: `T3` is `XPipe 04` for 25 bars, `T7`/`T8`
   are the `Myth * L/R Cut 2` pair, `T4` is `Robot vibrations`.

The `MAX` guess looked right for a reason worth recording: the base-26 code in
`.PXD` names equals the `MAX` line index (1 352/1 352), so the check was
self-consistent but proved only the *file* order.  The assumption
`id = MAX line` was never tested against eJay, and it was wrong.

## 5. The bank block

Groups were separated by file size, then compared byte by byte:

* 43-byte tails (`Dance eJay 1.01`): tag `0x0A08`, `nlists = 1`, version
  string + NUL + `0x01`, one empty list, then the 18-byte suffix.
* 99-byte tails (v6 `DanceMachine 1.05`): tag `0x0A06`, `nlists = 2`, raw
  version string, two box entries, then an empty second list, **no suffix**.
* 179-byte tails (`gung`): tag `0x0A08`, `nlists = 2`, version + NUL + flag, 3
  box entries, empty second list, suffix.

The first reading of the word after the tag was "an unknown flag (1 or 2)", and
the trailing `00 00` of the longer blocks looked like a terminator that was
"only written when boxes exist". Both oddities disappear when the word is read
as a **list count**: `1 or 2` counts lists, and each block then ends with the
last list it declared. That interpretation is what the current parser encodes,
and it re-encodes all 16 files byte for byte.

## 6. Dead ends

* **Public documentation**: web searches turned up nothing usable — generic
  "PXD" hits and one repository (`sp00nznet/ejay`) that documents eJay 2
  `.SCT`, not this format. No specification was available.
* **`DANCE/EJAY/INTRO.PXD`**: name suggests a song, but it is a 748 326-byte
  `tPxD` sample. No extra mix-format examples exist in the repository (only the
  16 `MIX/*.MIX` files; `SPECIAL/` holds `.WAV` samples), so the bank block had
  to be inferred from 11 examples in two variants.
* **`MIN`**: turned out to be an exact 897-line prefix of `MAX`, adding no new
  information about the id space.
* **`.PXD` audio payload**: not reversed by choice (task says not to try to play
  it); only the 5-byte header prefix is used.

## 7. Proof rather than plausibility

The strongest evidence for the whole model is the round trip: parse a file,
rebuild it from the structured model (signature, 702 × 8 grid, bank block) and
compare. `python reverse/dance/mixdump.py --verify --all` reports
**16/16 byte-identical**. A wrong bar/track order, wrong id width, wrong tail
layout or a missing byte would break it immediately.

## 8. What is still unknown

* meaning of the second box list (empty in all 11 blocks that have one),
* the 12 zero bytes, `1` and `2` at the end of the `0x0A08` suffix — constant in
  all six files, so nothing distinguishes the fields; only the leading `8` (the
  track count) is identifiable,
* why the `Dance eJay 1.01` writer declares no boxes although those songs use
  box samples (ids up to 4 727) — presumably the box list is only written when
  it differs from what the installation already knows,
* the v6 one-off `hi = 4500` vs v8 `4499` for the same box (only matters at id
  4500, which nothing uses),
* whether `0x0A06`'s low byte is a revision number (it tracks the structure:
  6 = v6 lists, 8 = v8 lists) — treated as a format tag, not a count,
* the `.PXD` audio payload and the remaining header fields.

A byte-level breakdown of how much of the corpus each of these affects is in
[`FORMAT.md`](FORMAT.md) §9: 142 of 180 657 bytes (0.079 %) have unknown meaning,
58 more are interpreted by inference, everything else is identified.

## 9. Reproducing the results

```
python reverse/dance/mixdump.py --verify --all                            # 16/16 byte-identical
python reverse/dance/mixdump.py --all                                     # readable dump, with sample names
python reverse/dance/mixdump.py --json reverse/dance/decoded --all        # machine-readable grids
python apps/emr/src/format/dance/mixrender.py --out reverse/dance/images --all  # arrangement PNGs
```
