# Sample ids, the sample bank and `.PXD` files

How a `uint16` in a `.MIX` grid becomes a sample file, and what the repository
actually ships.

## 1. Where the id comes from: `DANCE/EJAY/PXDDANCE`

`PXDDANCE` is eJay's sample bank, one record of **six quoted fields** per
sample, separated by CRLF:

```
"bc\aeif.pxd"   "effect"  "4"  "XPipe"  "04"
 path           (blank)   cat.  group    name
```

(in order: path, an always-empty field, category, a numeric flag, group, name).

* **1 352 records** ⇒ `id = 731 + record index`, i.e. ids **731 … 2082**.
* The label the browser shows is `group + " " + name` — that is why the first
  four bars of `START.MIX` read exactly like this:

| bar | track | id | record | file | label |
|----:|------:|---:|-------:|------|-------|
| 1 | T2 | 1186 | 455 | `BI/ANLF.PXD` | `SpaceKnock` |
| 1 | T3 | 1231 | 500 | `BC/AEIF.PXD` | `XPipe 04` |
| 2 | T3 | 1231 | 500 | `BC/AEIF.PXD` | `XPipe 04` |
| 3 | T3 | 1231 | 500 | `BC/AEIF.PXD` | `XPipe 04` |
| 3 | T4 | 1919 | 1188 | `BN/AUOR.PXD` | `Robot vibrations` |
| 3 | T7 | 973 | 242 | `AK/BYGY.PXD` | `Myth * L Cut 2` |
| 3 | T8 | 974 | 243 | `AK/BXXY.PXD` | `Myth * R Cut 2` |
| 4 | T3 | 1231 | 500 | `BC/AEIF.PXD` | `XPipe 04` |

The offset is a constant, not a per-category thing: ids 973/974 and 1186/1231
and 1919 all satisfy `id − record = 731`, and ids 1186/1231 even differ by 45
exactly like their records (455/500).

Ids **1 … 168** are the `SPECIAL` WAV samples (`id = record + 1`), ids
**169 … 730** are empty import slots, and ids from **3 400** are add-on sample
boxes (§5).

## 2. What is on disk

* The 1 352 shipped `.PXD` files are exactly the 1 352 `PXDDANCE` records, in
  the folders `AA … AL` and `BA … BW` (35 folders, 26–39 samples each).
* `MAX` (2 845 lines) and `MIN` (897 lines, an exact prefix of `MAX`) are
  installation manifests: relative paths, folder-sorted, **not** the id order.
* The 1 493 `MAX` entries under `dmkit1/01 … dmkit3/14` are not shipped, and no
  shipped song references them (they have no ids in this scheme).
* `DANCE/EJAY/INTRO.PXD` is a `tPxD` **sample** (748 326 bytes), not a song.
* `disks/Dance_eJay/SPECIAL` holds the 168 WAV samples of the `SPECIAL` list — mono
  16-bit 44.1 kHz, 1–8 bar loops — one per record (`special\D5BS735` →
  `D5BS735.WAV`).

## 3. The `.PXD` file itself

```
offset 0  byte[4]  ASCII "tPxD"
offset 4  uint8    length of the metadata block
offset 5  byte[n]  metadata: newline-separated text, NUL padded
```
after some padding: a `0x54` marker, a `uint24` sample count, then the coded
audio. The container and codec are documented in `PXD.md`; the shared
`libs/pxd/` package decodes them and the player plays them.

The bank label is the authoritative name. The header text is a second, often
padded copy (`GrabAgirl`, `Come on!`), and for a few samples the header holds
engineering notes instead of a name — do not rely on it for identification.

## 4. `MAX`, `MIN` and the base-26 file names

The first three letters of a `.PXD` file name are a base-26 number with `A = 0`
and equal that file's **`MAX` line index**:

```
id_in_MAX = (c0-'A')*26² + (c1-'A')*26 + (c2-'A')
```

Checked for all 1 352 shipped samples: 1 352 matches, 0 mismatches. Examples:
`BCQ` = 1·676 + 2·26 + 16 = 744 → `MAX` line 745 (`BT/BCQF.PXD`).

That relation is real but it is **not** the mix id: `BC/AEIF.PXD` is `MAX`
line 112 while its id is 1231 (`AEI` = 112). `MAX` orders files by folder
(`BA … BW`, then `AA … AL`, then `dmkit*`), which is why the earlier guess
"id = `MAX` line" produced wrong names while still passing its own base-26
self-check.

## 5. Ids below and above the bank list

**Below**: ids `1 … 168` are the `SPECIAL` records — `id = record + 1`, audio in
`disks/Dance_eJay/SPECIAL/<stem>.WAV`.  All 168 files exist (mono 16-bit 44.1 kHz,
whole-bar lengths), so the 109 placements that use ids `1, 2, 3, 4, 8, 9` play.
Ids `169 … 730` are eJay's empty import slots and stay unresolved.

**Above**: ids `3 400+` are add-on sample boxes. The layout is declared in the
optional bank block of the `.MIX` (`FORMAT.md` §4):

| ids | box name | sample set |
|-----|----------|------------|
| 3400–3899 | `gung -SAMPLE BOX- [Raps && Vocals]` | `gung`, also `DanceMachine Sample-Kit Vol. 1` |
| 3900–4499 | `gung -SAMPLE BOX- [Drams && Synthies]` | `gung`, also `… Vol. 2` |
| 4500–5199 | `gung -SAMPLE BOX- [Space Sounds]` | `gung` |

A box id resolves as `box.lo + n`, e.g. `4595` = "Space Sounds" sample 95, and
`mixdump.py` prints it that way.

Caveat found in the data: not every `0x0A08` block declares its boxes. The six
mixes with the version string `Dance eJay 1.01` (and one other) carry a single,
empty box list, yet `SOFTVOX` (max id 4727), `THEFLOW` (4513) and `X_PERM`
(4417) clearly use box samples. For those, the box has to be inferred from the
ranges other mixes declare — e.g. 4417 falls in `3900–4499` "Drams &&
Synthies" — and `mixdump.py` honestly prints such ids as unresolved (`?`)
rather than guessing.

## 6. Usage summary across the corpus

* 3 995 placed samples, **588 distinct** ids.
* **2 689 placements (324 ids)** resolve to shipped audio — 2 580 through
  `.PXD` files and 109 through `SPECIAL` WAVs; the other 1 306 are add-on box
  ids.
* Most used: `1423` "Kick B Fig.21" (91 placements), `4416` (69, box),
  `1231` "XPipe 04" (66), `4060` (65, box), `1327` "Hihat electric 1" (62),
  `738` "Grp. 1 Vers8" (61).

## 7. Correction

Earlier revisions of these notes claimed `id = MAX` line number and derived
"control samples" from that. The mapping above comes from `PXDDANCE` and was
checked against eJay: it is the one that reproduces the sample names shown
for `START.MIX` (§1).
