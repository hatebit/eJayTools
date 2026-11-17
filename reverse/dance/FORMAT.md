# Dance eJay `*.MIX` format

Reversed from the 16 files in `disks/Dance_eJay/MIX`, cross-checked against
`disks/Dance_eJay/DANCE/EJAY/MAX` (sample catalogue) and the `tPxD` headers of the
sample files.  No binary from the repository was executed; everything below
comes from reading the data files.

Other documents: [`README.md`](README.md) (doc map, tools),
[`SAMPLES.md`](SAMPLES.md) (id → `.PXD`, boxes), [`MIXES.md`](MIXES.md)
(per-song statistics), [`METHOD.md`](METHOD.md) (evidence and unknowns).

Tooling (parser in `libs/mix/dance/`, adapter in
`apps/emp/src/format/dance/`):

```
python reverse/dance/mixdump.py --all                        # readable dump of every mix
python reverse/dance/mixdump.py --json reverse/dance/decoded --all
python reverse/dance/mixdump.py --verify --all               # re-encode, byte-compare
python apps/emr/src/format/dance/mixrender.py --out reverse/dance/images --all   # arrangement PNGs
```

## 1. Overall layout

All files are little-endian.

| offset   | size    | field |
|----------|---------|-------|
| `0x0000` | 2       | `uint16` signature, `0x0A06` in all 16 files |
| `0x0002` | 11232   | song grid: `702 * 8` `uint16` sample ids |
| `0x2BE2` | variable| optional sample-bank block (§4). Files without it are exactly 11234 bytes |

`0x2BE2 = 2 + 702*8*2`.  The grid is allocated for the maximum song length;
the tail of the grid is zero-filled, so the real song length is derived from
the data (§2).  Tail sizes seen: none, 43, 99 and 179 bytes.

Tempo is **not** stored: the samples are cut at **140 BPM, 4/4**
(`Task.md`), so one bar is `4 * 60/140 = 12/7 ≈ 1.714 s` and the maximum grid
(702 bars) is ≈ 20 minutes.

## 2. Song grid

The grid is **bar-major with the 8 tracks interleaved**:

```
slot(bar, track) = 0x0002 + (bar * 8 + track) * 2      bar = 0..701, track = 0..7
value            = sample id, 0 = empty slot
```

Evidence: the dense region of a mix ends exactly at the last occupied slot, so
the grid is one contiguous array; every slot index (mod 8) behaves as one
continuous instrumental lane across a whole song (`MIXES.md` §4 shows
`START.MIX` lane by lane); and over the whole corpus (5 456 bars) no bar ever
holds more than 8 samples, the ceiling for 8 tracks.  The `0x0A08` bank-block
suffix even writes the track count `8`.

* `track` is the position in the eJay track list (0-based; the GUI shows T1..T8).
  The tracks are mono lanes and the grid stores no pan value: T7 is hard left
  and T8 hard right, the other six are centred.  The corpus pairs `… L`
  samples on T7 with their `… R` counterparts on T8 (for example `Myth * L
  Cut 2` / `Myth * R Cut 2`), 142 bars in all, and no sample marked L ever
  appears on T8 or vice versa.
* `song_length` = index of the last bar with any non-zero slot, plus 1; a
  player keeps rendering until the last placed sample ends, which can be bars
  beyond that (`mixplayer.py`).
* time of a bar = `bar * 12/7` seconds.

## 3. Sample ids

A grid value is a **slot in eJay's sample bank**, not a line number in
`MAX`: `731 + n` is record `n` of `DANCE/EJAY/PXDDANCE` (1 352 records of six
quoted fields — path, empty, category, number, group, name).  The browser label
is `group + " " + name`, which is what `START.MIX` shows in its first bars:

| id   | record | file          | label               |
|------|-------:|---------------|---------------------|
| 973  | 242    | `AK/BYGY.PXD` | `Myth * L Cut 2`    |
| 974  | 243    | `AK/BXXY.PXD` | `Myth * R Cut 2`    |
| 1186 | 455    | `BI/ANLF.PXD` | `SpaceKnock`        |
| 1231 | 500    | `BC/AEIF.PXD` | `XPipe 04`          |
| 1919 | 1188   | `BN/AUOR.PXD` | `Robot vibrations`  |

`MAX` (2 845 entries) and `MIN` (897, an exact prefix) are installation
manifests in folder-sorted order: useful to know which files exist, but not the
id order.  The base-26 code in a `.PXD` name equals its `MAX` line index
(1 352/1 352 verified) — a self-consistent check that says nothing about ids
(`SAMPLES.md` §4).

Ids `731..2082` exist on disk (the 1 352 samples in `AA…AL` / `BA…BW`, exactly
the `PXDDANCE` records) and `1..168` are the `SPECIAL` WAVs; `169..730` are
empty import slots, and the `dmkit` files listed in `MAX` are not used by any
shipped song.
`DANCE/EJAY/INTRO.PXD` is a `tPxD` sample, not a song.  See `SAMPLES.md`.

Ids from `3 400` are add-on sample boxes, resolved through the bank block
(§4): a mix uses `box.lo + n`.  Example: `SPACE.MIX` slot value `4595`
falls into the box declared as `4500..5199` ("Space Sounds") and is that box's
sample 95.  Blocks with an empty box list cannot resolve such ids (see
`SAMPLES.md` §5).

Special values seen in the grid:

* `0` – empty slot.
* `1..168` – `SPECIAL` samples (`disks/Dance_eJay/SPECIAL/*.WAV`), `id = record + 1`;
  used in six songs (109 placements).  `169..730` are empty import slots.

## 4. Bank block (appended, optional)

Present when the song was made with an installation whose sample boxes differ
from the built-in catalogue.  The first `uint16` is a variant tag: `0x0A06`
(v6) stores names as raw characters, `0x0A08` (v8) stores each name followed
by NUL plus a `0x01` flag byte and appends an 18-byte suffix.  Both variants
after the tag are identical in shape:

```
uint16  tag         0x0A06 (v6) or 0x0A08 (v8)
uint16  nlists      number of box lists (1 or 2 in this set)
uint16  len         length of the version string
byte    version[len]  v6: raw characters, e.g. "DanceMachine 1.05"
                      v8: characters + NUL + 0x01
repeat nlists times:
    uint16 count        entries in this list
    count * {
        uint16 lo       first sample id of the box
        uint16 hi       last sample id of the box
        uint16 len      v6: character count; v8: characters + 2
        byte   name[len]  v6: raw characters
                          v8: characters + NUL + 0x01
    }
v8 only, 18 bytes:
    uint16 8            track count
    byte   12*0         always zero
    uint16 1
    uint16 2
```

Names are raw bytes in the code page of the program (read as latin-1).

Observed blocks — the word I first took for an unknown flag is the list count,
which is what makes the two variants line up exactly:

| file(s)                                   | tag      | nlists | list 1    | list 2 | 18-byte suffix |
|-------------------------------------------|----------|--------|-----------|--------|----------------|
| `DRUMSYNT`, `RAPSVOIC`, `START_RE`         | `0x0A06` | 2      | 2 boxes (`3400..3899`, `3900..4500`) | empty | no |
| `DREAM`, `SPACE`                          | `0x0A08` | 2      | 3 boxes (`3400..3899`, `3900..4499`, `4500..5199`) | empty | yes |
| `MCXTREME`, `ORGANICS`, `SOFTVOX`, `THEFLOW`, `WETDANCE`, `X_PERM` | `0x0A08` | 1 | 0 boxes | — | yes |
| `FREAK`, `LOVE`, `START`, `WELCOME`, `XPIPE` | —      | —      | no block at all | — | — |

Box names: `3400..3899` "Raps && Vocals" / "DanceMachine Sample-Kit Vol. 1",
`3900..4499` "Drams && Synthies" / "…Vol. 2", `4500..5199` "Space Sounds" —
all under the sample-set name `gung`.  Version strings: `Dance eJay 1.01`,
`DanceMachine 1.05` (v6), `gung DanceMachine 1.05` (v8).

## 5. Worked example — `START.MIX`

```
0x0000: 06 0A            signature
0x0002: 86 04            slot(bar 0, track 1)  = 1186 -> BI/ANLF.PXD  "SpaceKnock"
0x0004: CF 04            slot(bar 0, track 2)  = 1231 -> BC/AEIF.PXD  "XPipe 04"
0x0006: 00 00            slot(bar 0, track 3)  = empty
...
0x002E: CD 03            slot(bar 2, track 6)  = 973  -> AK/BYGY.PXD  "Myth * L Cut 2"
0x0030: CE 03            slot(bar 2, track 7)  = 974  -> AK/BXXY.PXD  "Myth * R Cut 2"
```

`START.MIX`: 83 bars, 189 placed samples, 48 distinct samples, 142.3 s.
`START.MIX` ≡ `XPIPE.MIX` and `DREAM.MIX` ≡ `RAPSVOIC.MIX` (byte identical).

## 6. Visualising an arrangement

`mixrender.py` draws one PNG per mix: x = bar, y = track (T1 on top), one
coloured cell per placed sample, ruler every 4 bars (labelled every 8).  The
colour is derived from the sample id alone (`hue = id * 0.618 mod 1`), so a
repeated sample is always the same colour and loops/fills stand out.

```
python apps/emr/src/format/dance/mixrender.py --out reverse/dance/images --all
python apps/emr/src/format/dance/mixrender.py --out reverse/dance/images --cell-w 8 --cell-h 22 disks/Dance_eJay/MIX/START.MIX
```

PNG is written with `zlib` + `struct` only (no Pillow), 8-bit RGB.  The cell
width defaults to `900 / song_length` clamped to 4..10 px per bar (override
with `--cell-w`), and the track rows are `--cell-h` tall.

For listening rather than looking, `mixplayer.py` decodes the `.PXD` samples
(`PXD.md`) and streams the mix through `sounddevice`; one bar is exactly
75 600 samples at 140 BPM / 44.1 kHz, so onsets need no resampling.

## 7. Verification

`mixdump.py --verify` parses every file and re-encodes it from the decoded
model (signature, 702×8 grid, bank block): **16/16 files reproduce
byte-identically**, including both bank-block variants and both list counts.

## 8. Byte comparison of the two variants — what the open points come down to

**(a) The `uint16` after the tag is `nlists`, the number of box lists.**
Reading it as a count makes every tail consistent: a v8 block with no boxes
declares `nlists = 1` and its `00 00` is that list's count, then the suffix
follows; `gung` blocks declare `nlists = 2`, write 3 boxes and a second
`00 00` list; v6 blocks declare `nlists = 2`, write 2 boxes and a second empty
list.  Reading the same word as a flag leaves the trailing `00 00` unexplained
and would break the v6/v8 alignment.  What the second list is *for* cannot be
told from these files: it is empty in all 11 blocks that have one.

**(b) The 18-byte v8 suffix is a later-writer addition.**
v6 blocks end immediately after the lists (99 bytes total); every v8 block
carries the same 18 bytes, byte for byte: `08 00`, 12 × `00`, `01 00 02 00`.
Its first word equals **8**, the number of tracks the grid is divided into, so
that word is almost certainly the track count; the remaining 14 bytes are
constant in all six v8 files, so nothing in this corpus distinguishes a field
boundary there — the 12 zero bytes fit 8 per-track flags plus one 32-bit zero,
but that is a reading, not evidence.

**(c) v6 writes `hi = 4500` where v8 writes `4499` for the same box.**
v6's first box (`3400..3899`) matches v8 exactly; only the second entry is one
larger, i.e. v6's "Vol. 2" boundary is exclusive, not inclusive.  The dispute
only matters at id `4500`, which no file uses — highest ids per box:
`START_RE` 4419, `DREAM` 4417, `SPACE` 5013 (box `4500..5199`).  So both
readings give the same answer for every sample actually referenced, and the
box resolver treats `hi` as inclusive (as v8 writes it).

**(d) `0x0A06` is a format tag, not a size.**  The same file can carry
`0x0A06` in its song header and `0x0A08` in its bank block (`X_PERM`,
`MCXTREME`, …); one installation cannot have two sample counts, so the two
words cannot both be counts.  `0x0A06` = 2566 and `0x0A08` = 2568 also match
no catalogue in the repository (`MAX` 2845, `MIN` 897, files on disk 1352).
Both values share the high byte `0x0A`, and the low byte tracks the structure
being used (6 = v6 lists, 8 = v8 lists), so the field is read as
"family 10, revision 6/8".

## 9. Byte accounting — what is still unknown

Across the 16 files (180 657 bytes in total):

| region | bytes | status |
|--------|------:|--------|
| signature (`0x0A06`) | 32 | value constant; identified as a format tag, exact meaning inferred |
| song grid | 179 712 | fully identified |
| bank-block fields (tags, `nlists`, lengths, version strings, box ids and names) | 745 | fully identified |
| second box-list counts (`00 00`) | 10 | layout identified, purpose of list 2 unknown |
| v8 name flag bytes (`0x01`) | 14 | position identified, meaning unknown |
| v8 suffix track-count word (`08 00`) | 16 | value 8; track count by inference |
| v8 suffix: 12 zero bytes + `01 00 02 00` | 128 | unknown |
| **total** | **180 657** | |

So **142 bytes (0.079 %) have unknown meaning** and **58 more are known in position
but interpreted by inference** (track word 16, second-list counts 10, signature
32).  Every byte of every file is located, and the writer reproduces all
180 657 of them exactly.

Data-level gaps (the bytes are understood, the samples are not):

* 1 112 placements reference `dmkit` samples listed in `MAX` but not shipped —
  id and path known, name unknown;
* 567 placements in the `Dance eJay 1.01` group reference ids ≥ 2 845 although
  those files declare no boxes — the id is known, the sample identity can only
  be inferred from ranges other mixes declare;
* 1 577 placements resolve to a shipped `.PXD` (175 distinct files).
