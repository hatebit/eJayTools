# EMR CLI — `emr-cli.exe` / `mixrender.py`

`apps/emr/src/mixrender.py` renders an eJay arrangement as a PNG track grid:
one horizontal row per track, time running left to right, and one coloured
block per placed sample.  It is the drawing counterpart of the EMP player and
can be used to inspect a song without decoding its audio.  The packaged
Windows binary is `dist/emr-cli/emr-cli.exe`.

## Requirements

* Python 3.14.  The renderer and the parsers it imports use the standard
  library only: no `numpy`, `sounddevice` or `textual`.
* eJay data under `disks/` (see [eJay data](README.md#ejay-data)).  The
  renderer reads the song plus the sample headers it needs to measure length;
  it decodes no audio.

## Synopsis

```bash
python apps/emr/src/mixrender.py [FILES …] [options]
emr-cli.exe [FILES …] [options]           # packaged build
```

With no `FILES` the program behaves like `--all`: it renders every mix in the
selected format(s).  Each `FILES` entry may be a path or a bare song name.

## Selecting mixes

* **Path** — the format is taken from the two-byte signature.  An unknown
  signature is reported as `unrecognised mix (unknown signature)`.
* **Bare name** — the name is looked up in every present tree's `MIX` folder,
  with or without the `.MIX` suffix.  A name present in several trees is
  ambiguous and prints every candidate:

  ```
  START.MIX is ambiguous:
    …/disks/Dance_eJay/MIX/START.MIX
    …
  use --format <id> or pass a path
  ```

* **`--format`** — `dance`, `rave`, `hiphop`, `dance2` or `techno`; skips
  detection and restricts `--all` to that tree.  A path with another format's
  signature is rejected with `… is not a <format> mix`.
* **`--all`** — every `*.MIX` in the selected tree(s).

All names are located before anything is drawn: one bad name aborts the run
with exit 2.

## Output location and names

* Without `--out`, each image goes to that format's generated folder:
  `reverse/dance/images`, `reverse/rave/images`, `reverse/hiphop/images`,
  `reverse/dance2/images`, `reverse/techno/images`.
* With `--out DIR` and mixes from a single format, all images go directly into
  `DIR`.
* With `--out DIR` and mixes from more than one format, each format gets a
  subfolder: `DIR/dance/`, `DIR/rave/`, `DIR/hiphop/`, `DIR/dance2/`,
  `DIR/techno/`.  This is what `--all --out out/images` does.

The file name is the mix's base name in lower case plus `.png`:
`START.MIX` becomes `start.png`, `OTHER.MIX` becomes `other.png`.  Existing
files are overwritten.

## The image

The PNG is 8-bit RGB and drawn with the standard library, so a given song and
option set always produces the same pixels.

* One row per track, labelled `T1` … `T8` (grid formats) or `T1` … `T16`
  (eJay 2 formats), with alternating row bands and a separator above each
  row.
* A bar ruler.  Grid formats number from bar `0`; section formats number from
  bar `1`.  A vertical line is drawn every 4 bars and labelled every 8.
* One coloured block per placed sample or pattern record.  The colour is a
  stable hue derived from the sample id, so the same sample has the same
  colour in every image.  A grid block extends by the sample's own length (one
  bar when the length cannot be probed); an eJay 2 record ends where the next
  record on that track starts, or where the sample ends, whichever comes first.  Fractional starts are rounded to the
  pixel grid, and a block is always at least one pixel wide.
* Image size follows the two cell options plus fixed margins:
  `width = 34 + bars × cell-w + 6` and
  `height = 16 + tracks × cell-h + 6`.

## Options

| option | meaning |
|---|---|
| `--format ID` | force a format instead of detecting it (absent on the per-tree wrappers) |
| `--all` | render every mix in the selected format(s) |
| `--out DIR` | output directory; default `reverse/<format>/images` |
| `--cell-w N` | pixels per bar; default automatic, chosen from the song length and clamped to 4–10; a value of 0 or less also means automatic |
| `--cell-h N` | pixels per track (default 18) |
| `-v`, `--verbose` | print per-track placement statistics |
| `--version` | print the version (`1.0.0`) and exit |

## Examples

```bash
# Every mix of every installed tree, into the per-format folders under out/
python apps/emr/src/mixrender.py --all --out out/images

# One song, detected, into its usual folder
python apps/emr/src/mixrender.py disks/Dance_eJay/MIX/START.MIX

# A bare, ambiguous name needs the format
python apps/emr/src/mixrender.py START.MIX --format techno --out reverse/techno/images

# Wider cells for a short song
python apps/emr/src/mixrender.py OTHER.MIX --format dance2 --out out/images --cell-w 10 --cell-h 24

# Regenerate the checked-in images for one tree
python apps/emr/src/format/dance2/mixrender.py --out reverse/dance2/images --all
```

The packaged build works the same way:

```bash
dist/emr-cli/emr-cli.exe --all --out out/images
```

## Output

One line per rendered file:

```
START.MIX      90 bars (83 in grid), 189 samples -> reverse/dance/images/start.png (940x166)
OTHER.MIX      90 bars, 205 records -> reverse/dance2/images/other.png (940x310)
```

The fields are the mix name, the song length (a grid format also shows its
raw `song_length` when samples ring out beyond the last occupied bar), the
number of spans drawn — `samples` for the grid formats, `records`
for the eJay 2 pattern formats — the output path and the pixel size.

With `-v` a second line per song gives the per-track counts: `T1 <placed>/<distinct>`
for grid formats and `T1 <placed>` for section formats.

## Per-tree wrappers

Each tree also has a fixed-format wrapper that takes the same options except
`--format` and defaults to that tree's folder:

```
apps/emr/src/format/dance/mixrender.py
apps/emr/src/format/rave/mixrender.py
apps/emr/src/format/hiphop/mixrender.py
apps/emr/src/format/dance2/mixrender.py
apps/emr/src/format/techno/mixrender.py
```

The unified command and a wrapper produce byte-identical files for the same
song and options.  `apps/emr/src/render/registry.py` is the composition root
that lists the five providers.

## Exit status

| status | when |
|---|---|
| `0` | every requested image was written |
| `1` | at least one song could not be rendered; the others were still written, and the failure was printed as `<file> <error>` on stderr |
| `2` | a mix name could not be located, a `--format` did not match, or the arguments were invalid |

A missing output directory is created.

## Notes

`reverse/<tree>/images/` is generated output.  Regenerate it with this tool
rather than editing the PNGs by hand; the documentation trees refer to those
images as the illustrations of each song.
