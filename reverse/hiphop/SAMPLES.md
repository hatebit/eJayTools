# Sample ids, the sample bank and `.PXD` files

How a `uint16` in a `.MIX` grid becomes a sample file, and what the repository
actually ships.

## 1. Where the id comes from: `HIPHOP/EJAY/PXD`

`PXD` is eJay's sample bank, one record of **six quoted fields** per
sample, separated by CRLF:

```
"aa\h1bs001.pxd"   ""   "bass"  "2"  "dirty slurpy"  "the one"
 path             (blank) cat.  flag  group           name
```

* **1 341 records** ⇒ `id = 731 + record index`, i.e. ids **731 … 2071**.
* The label the browser shows is `group + " " + name`; `START.MIX` reads
  exactly like that in its first bars:

| bar | track | id | record | file | label |
|----:|------:|---:|-------:|------|-------|
| 1 | T3 | 1025 | 294 | `BH/H1EX021.PXD` | `help me` |
| 1 | T4 | 1022 | 291 | `BF/H1EX018.PXD` | `hard breath` |
| 1 | T7 | 1649 | 918 | `BH/H1RP056.PXD` | `hiphp jam` |
| 2 | T8 | 1650 | 919 | `BG/H1RP057.PXD` | `gang slang` |
| 3 | T3 | 775 | 44 | `BR/H1BS045.PXD` | `goldfinger the bow 1` |
| 5 | T5 | 2040 | 1309 | `BK/H1ZZ003.PXD` | `scrat rush` |

The offset is constant: ids 1025/1022/1649/775/2040 and their records differ by
exactly 731.  The corpus also reaches the top of the list: the highest id used
anywhere is **2071 = 731 + 1 340**, the last `PXD` record.

Records by category: 239 effect, 234 rap, 209 loop, 146 drum, 141 key,
128 bass, 124 voice, 120 guitar.

## 2. What is on disk

* The 1 341 shipped `.PXD` files are exactly the 1 341 `PXD` records, in 35
  folders: `AA … AQ` and `BA … BR`, 33 of them with 39 samples (`BO` 40,
  `AC` 38, `AQ` 15), plus the `SCRATCH` folder of 40 WAVs.
* `MAX` has **1 381** lines: the 1 341 `.pxd` paths followed by the 40
  `scratch\*.wav` paths.  `MIN` has **743** lines, 703 of them `.pxd` and all
  40 scratch WAVs.  Every `MIN` line also occurs in `MAX`; `MIN` is a sorted
  subset, not a prefix (unlike Dance eJay, whose `MIN` is a prefix of `MAX`).
  Both are installation manifests in folder path order, **not** the id order.
* `disks/Hiphop_eJay/SPECIAL` holds the 101 WAV samples of the `SPECIAL` list —
  mono 16-bit 44.1 kHz, **220 500 frames (5.0 s = two bars)** each, one per
  record (`special\hxdrum01` → `HXDRUM01.WAV`).
* `HIPHOP/SCRATCH` holds 40 scratch WAVs; they are not in either catalogue list
  (they appear only in `MAX`/`MIN`), and no grid id references them.

## 3. The `.PXD` file itself

```
offset 0  byte[4]  ASCII "tPxD"
offset 4  uint8    length of the metadata block
offset 5  byte[n]  metadata: newline-separated text, NUL padded
```
after some padding: a `0x54` marker, a `uint24` sample count, then the coded
audio.  The container and codec are documented in [`PXD.md`](PXD.md);
the shared `libs/pxd/` package decodes them and the player plays
them.

The bank label is the authoritative name.  The header text is a second copy
and is normally the same string (e.g. `dirty slurpy` for `H1BS001.PXD`); some
headers hold truncated or padded names, so the catalogue is used for display.

## 4. Ids below and above the bank list

* **Below**: ids `1 … 101` are the `SPECIAL` records — `id = record + 1`, audio
  in `disks/Hiphop_eJay/SPECIAL/<stem>.WAV`.  All 101 files exist, so every one
  of the 327 `SPECIAL` placements plays.  The grids use 14 of them:
  `1, 2, 3, 4` and `6 … 15`.
* **Gap**: ids `102 … 730` are eJay's empty import slots.  No shipped song
  uses one.
* **Above**: ids `3 400+` are add-on sample boxes in Dance eJay; this HipHop
  corpus uses **no** add-on ids.  The largest id in the corpus is 2071, the
  last `PXD` record, and every one of the 5 488 placements resolves to a file
  on disk.

## 5. Usage summary across the corpus

* 5 488 placed samples, **531 distinct** ids.
* **5 161 placements (517 ids)** resolve to `.PXD` files and **327 placements
  (14 ids)** to `SPECIAL` WAVs; **0** placements are unresolved.
* Most used: `958` "tamb tam" (136 placements), `1536` "hand dry" (122),
  `1559` "organ rsta2" (113), `8` "rattle snake" (SPECIAL, 99), `897`
  "kickH off" (83), `1464` "genY clear shock" (71).
* The two catalogue lists are independent id spaces: `Sample 8` is the eighth
  `SPECIAL` WAV, not `PXD` record 8 (which is id 739).
