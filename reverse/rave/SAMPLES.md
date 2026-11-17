# Sample ids, the sample bank and `.PXD` files

How a `uint16` in a `.MIX` grid becomes a sample file, and what the repository
actually ships.

## 1. Where the id comes from: `RAVE/EJAY/PXD`

`RAVE/EJAY/PXD` is eJay's sample bank, one record of **six quoted fields**
per sample, separated by CRLF:

```
"bq\r1bs001.pxd"  ""  "bass"  "2"  "wood walk"  "1"
 path           blank  cat.   bars  group        name
```

(in order: path, an always-empty field, category, nominal length in bars,
group, name).  The first record is:

```
"bq\r1bs001.pxd"
""
"bass"
"2"
"wood walk"
"1"
```

* **1 149 records** ⇒ `id = 731 + record index`, i.e. ids **731 … 1879**.
* The label the browser shows is `group + " " + name`, verbatim.  That is why
  the first bars of `START.MIX` read like this:

| bar | track | id | record | file | label |
|----:|------:|---:|-------:|------|-------|
| 0 | T4 | 1094 | 363 | `AB/R1FX018.PXD` | `thumb` |
| 0 | T7 | 1075 | 344 | `BN/R1FX001L.PXD` | `scream L` |
| 0 | T8 | 1076 | 345 | `BJ/R1FX001R.PXD` | `scream R` |
| 1 | T1 | 1846 | 1115 | `BR/R1VX102.PXD` | `this is  MC magic` |
| 2 | T3 | 1018 | 287 | `BN/R1DC037.PXD` | `hihat distorted 1` |
| 2 | T5 | 1400 | 669 | `AE/R1SF096.PXD` | `distorted motion 1` |
| 3 | T1 | 1850 | 1119 | `BQ/R1VX106.PXD` | `life in space` |
| 4 | T3 | 1018 | 287 | `BN/R1DC037.PXD` | `hihat distorted 1` |
| 4 | T6 | 1755 | 1024 | `BR/R1VX016.PXD` | `eJay 5` |

The offset is a constant, not a per-category thing: ids 1018/1075/1076 and
1094 and 1400 and 1755 and 1846/1850 all satisfy `id − record = 731`, and
1018/1075 differ by 57 exactly like their records (287/344).

Labels keep the catalogue's spacing, including double spaces
(`hihat  silver 1`, `no  name`, `this is  MC magic`) and records whose name is
a URL (`1879` = `http://www.eJay.com`).  Do not "tidy" them.

### Nominal length field

The numeric field is the **nominal loop length in bars**.  It equals
`declared_count / 58 800` exactly for **1 145 of the 1 149** records:

| bars | records |
|-----:|--------:|
| 2 | 589 |
| 4 | 248 |
| 1 | 141 |
| 8 | 84 |
| 3 | 46 |
| 16 | 21 |
| 12 | 10 |
| 5 | 5 |
| 6 | 2 |
| 20 | 2 |
| 11 | 1 |

The four exceptions are all within 3.2 % of the nominal value; they are
declared lengths, not a different musical length:

| id | file | bars | declared samples | nominal | label |
|---:|------|-----:|-----------------:|--------:|-------|
| 1059 | `BG/R1DF013.PXD` | 2 | 119 438 | 117 600 | `wood 2` |
| 1097 | `BD/R1FX021.PXD` | 1 | 58 801 | 58 800 | `phone 1` |
| 1345 | `BH/R1SF047.PXD` | 2 | 119 438 | 117 600 | `just some thing 1` |
| 1800 | `BD/R1VX060.PXD` | 1 | 56 963 | 58 800 | `trans lunar` |

### Categories

The catalogue's category field is one of eight values:

| category | records |
|----------|--------:|
| drum | 224 |
| sequence | 165 |
| sphere | 164 |
| loop | 142 |
| voice | 141 |
| bass | 120 |
| special | 116 |
| effect | 77 |

## 2. What is on disk

* The 1 149 shipped `.PXD` files are exactly the 1 149 `RAVE/EJAY/PXD`
  records, in folders `AA … AK` and `BA … BS` (30 folders).
* Catalogue paths are relative to `disks/Rave_eJay/RAVE/` and are matched
  case-insensitively: the catalogue stores `bq\r1bs001.pxd`, the file on disk
  is `BQ/R1BS001.PXD`.
* `MAX` (3 145 lines) and `MIN` (860 lines) are installation manifests:
  relative paths, folder-sorted, **not** the id order.  `MAX` is 1 149 main
  samples + 128 `hyper` + 1 868 `rekit1/2/3` entries; `MIN` is 732 main
  samples + the same 128 `hyper` entries.
* `RAVE/EJAY/INTRO.PXD` is a `tPxD` **sample** (1 025 436 bytes, metadata
  `Rave eJay Intro`, declared 1 234 800 samples = exactly 21 bars), not a song.
* `RAVE/HYPER` holds 128 samples (`R1HG0001 … R1HG0128`).  `RAVE/EJAY/HYPSOUND`
  lists them in eight categories — Vibes 18, Rave 16, Trash 13, Hardbass 17,
  Softbass 17, Space 14, Comic 16, Strikes 17 — and their metadata category is
  `hyper`.  They are 1/4-bar or 1/2-bar one-shots (14 700 or 29 400 declared
  samples), not whole-bar loops.
* No add-on sample boxes are shipped for this eJay release, and no shipped song uses
  ids above 1 879.

## 3. The `.PXD` file itself

```
offset 0  byte[4]  ASCII "tPxD"
offset 4  uint8    length of the metadata block
offset 5  byte[n]  metadata: CRLF-separated text, NUL padded
```

after some padding: a `0x54` marker, a `uint24` sample count, then the coded
audio.  The container and codec are documented in [`PXD.md`](PXD.md);
the shared `libs/pxd/` package decodes them and the player plays
them.

The bank label is the authoritative name.  The header text is a second, often
split copy (`['trans', 'lunar', 'Rave eJay', '', 'voice', '58800']`), and one
file (`RAVE/BD/R1DA084.PXD`) has no `tPxD` header at all — it starts at the
`0x54` marker.  Do not rely on the header for identification.

## 4. `MAX`, `MIN` and the file names

`MAX` and `MIN` are folder-sorted, not catalogue order:

```
MAX  first: ba\r1da006.pxd, ba\r1da008.pxd
     last:  REKIT3\17\R4VX302L.PXD, REKIT3\17\R4VX302R.PXD
MIN  first: ba\r1da006.pxd, ba\r1da008.pxd
     last:  hyper\r1hg0127.pxd, hyper\r1hg0128.pxd
```

The Rave `.PXD` names are `R1` + a two-letter bank (`BS`, `DA`, `DC`, `DF`,
`FX`, `LA`, `SF`, `SQ`, `SR`, `VX`, `HG`) + a three-digit number, optionally
with `L`/`R`.  Unlike the Dance names there is no base-26 index relation to
`MAX`, so `MAX` cannot be used to derive ids at all.  The only id order is the
record order in `RAVE/EJAY/PXD`.

## 5. Ids below the bank list

Ids **1 … 15** are used by the shipped songs (174 placements), but no sample
file for them is shipped.  Ids **16 … 730** are not used.  The per-id totals
across the corpus are:

| id | placements | id | placements |
|---:|-----------:|---:|-----------:|
| 1 | 1 | 9 | 2 |
| 2 | 13 | 10 | 2 |
| 3 | 12 | 11 | 1 |
| 4 | 7 | 12 | 117 |
| 5 | 1 | 13 | 1 |
| 6 | 2 | 14 | 2 |
| 7 | 2 | 15 | 1 |
| 8 | 10 | | |

By song:

| file | low-id placements | detail |
|------|------------------:|--------|
| `EARTH` | 1 | id 4 at bar 512 (the last bar) |
| `GALACTIC` | 1 | id 4 at bar 414 (the last bar) |
| `MAGIC` | 4 | id 6; id 8 at bars 505–507 |
| `NODRUGS` | 8 | ids 4, 8, 12 |
| `TRANCE` | 17 | ids 1–15 in a sequence around bars 478–496 |
| `VIENI` | 113 | id 12 from bar 382 to bar 525 |
| `WARP` | 3 | ids 9, 10, 12 |
| `XENON` | 11 | id 3 at bars 413–503 |
| `XWING` | 16 | ids 2, 4, 14 |

Two patterns are visible but not explained: `TRANCE` uses all fifteen ids in
order, and `VIENI` repeats id 12 to pad its grid from bar 382 to 525, long
after its last shipped sample (bar 221).  The low slots are therefore at least
partly **placeholders / markers**, not necessarily missing music.  What the
eJay played for them is unknown.

The separate `RAVE/HYPER` bank is **not** assumed to fill these slots.  The
`NODRUGS.MIX` trailer does contain a stale-looking reference to
`c:\raveejay\hypersav\scool004.wav` and the string `hyper`, which shows that a
hyper sample was involved in building that song, but no grid id in
`731..1879` references the HYPER bank and no mapping from ids `1..15` to its
128 files can be proved from the data.

## 6. Usage summary across the corpus

* 5 026 placed samples, **411 distinct** ids.
* **4 852 placements (396 ids)** resolve to shipped `.PXD` audio.
* **174 placements (15 ids)** use ids `1..15` and stay unresolved.
* Every catalogue id `731..1879` has a file on disk (1 149/1 149), so a
  catalogue-range id never fails to resolve.
* Most used: `992` "hihat  silver 1" (125 placements), `1250` "dirty" (123),
  `12` (117, low id), `814` "bang 1" (111), `865` "kick C  basic" (105),
  `851` "kick A  basic" (93), `875` "kick D  basic" (85), `1014` "hihat clear
  1" (82), `768` "cool bass Seattle 2" (74), `1391` "rage 3" (59).
* No placement uses an add-on box id and the bank block declares no boxes, so
  the box-resolution path in `mixfmt.py` is never exercised by this corpus.

## 7. Notes

* The catalogue is the id order; `MAX`/`MIN` are only file inventories.
* The headerless `RAVE/BD/R1DA084.PXD` is still catalogue record 203
  (id 934) and is decoded from its `0x54` marker (58 799 decoded samples,
  58 800 declared).
* Four catalogue records have a declared length slightly different from
  `number × 58 800` (§1); the player uses the declared count, which is
  authoritative for playback.
