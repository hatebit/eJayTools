# PXD to WAV — `pxd2wav.exe` / `pxd2wav.py`

`apps/pxd2wav/src/pxd2wav.py` converts eJay `.PXD` samples to mono 16-bit
44.1 kHz WAV files.  It decodes a single standalone sample, or one record of an
eJay 2 bundle chosen from its `.INF` index.  The packaged Windows binary is
`dist/pxd2wav/pxd2wav.exe`; both take the same options, and both open the same
window when no file is given.

## Requirements

* Python 3.14 and `numpy` for a source run.  The decoder is the shared
  `libs/pxd` codec, the same one the player and the renderer use.
* `tkinter` for the window (part of CPython on Windows; a headless
  conversion does not touch it).
* `tkinterdnd2` for drag and drop only.  Without it the window still works
  through the Open button.
* No eJay installation is required: the tool takes any sample path.  The
  shipped samples live under `disks/`, which is not part of this repository.

## Synopsis

```bash
python apps/pxd2wav/src/pxd2wav.py SAMPLE.PXD [OUT.WAV] [options]
python apps/pxd2wav/src/pxd2wav.py BUNDLE.INF --id ID [OUT.WAV]
python apps/pxd2wav/src/pxd2wav.py                     # window
pxd2wav.exe SAMPLE.PXD [OUT.WAV]                       # packaged build
```

`OUT.WAV` defaults to the input name with a `.wav` extension, in the same
folder: `AAAF.PXD` becomes `AAAF.wav`, and a bundle record becomes
`<bundle>_<id>.wav` (`DANCE20_1512.wav`).

## Standalone samples

A standalone sample is one `tPxD` stream: the header carries a text name and
the declared sample count, and the stream is a table-driven differential coder.
The tool writes exactly the declared number of samples, so the WAV frame count
matches what the sample states.

```bash
python apps/pxd2wav/src/pxd2wav.py disks/Dance_eJay/DANCE/BA/AAAF.PXD
```

```text
AAAF.PXD -> AAAF.wav  (Ray: 37800 samples, 0.857 s)
```

The name in the summary comes from the metadata block with its NUL padding
removed; `(unnamed)` is printed when a sample carries no name.

## Bundles

Dance eJay 2 and Techno eJay 2 keep many samples in one data file described by
a sibling `.INF` index (`DANCE20` with `DANCE20.INF`, `RAVE20` with
`RAVE20.INF`).  The data file has no extension, so either half identifies the
bundle:

```bash
python apps/pxd2wav/src/pxd2wav.py disks/Dance_2/D_ejay2/PXD/DANCE20.INF --id 1512
python apps/pxd2wav/src/pxd2wav.py disks/Techno_eJay/EJAY/PXD/RAVE20 --id 13016
python apps/pxd2wav/src/pxd2wav.py BUNDLE --inf BUNDLE.INF --id 1512 OUT.WAV
```

```text
DANCE20.INF [id 1512] -> DANCE20_1512.wav  (euro kick3: 9450 samples, 0.214 s)
```

Sample ids are the index's own; they are not offsets or positions in the
bundle.  `DANCE20.INF` lists 1 957 records numbered 1…1957, and 1512 is
simply the first in file order; `RAVE20.INF` lists 4 015 numbered
13 000…17 014.  The ids a song refers to are scattered across those
ranges.  Use `--list` to see which ids an index holds:

```bash
python apps/pxd2wav/src/pxd2wav.py DANCE20.INF --list
```

```text
  1512  euro kick3
  1490  nord lead4
  …
```

Asking for a bundle without choosing a record is not an error in the file but
an incomplete command; it prints the record count and exits 2.  An id the index
does not hold exits 1 with `sample id N not in …INF`.

## The window

Run the script or the executable with no file argument.  The window offers
one drop zone and two steps:

1. **Open a sample.**  Drop a `.PXD`, an `.INF` or an extensionless bundle
   onto the window, or use **Open…**.  Dragging is available when
   `tkinterdnd2` is installed; otherwise the zone says so and the button is the
   only way in.
2. **Choose and save.**  A standalone sample is summarised immediately and
   **Save WAV…** becomes available.  A bundle fills the sample list instead:
   - type into *Sample id or name* to filter the list by either field;
   - press `Enter` with a number to jump to that id;
   - click a row to decode it.

   The summary then reads `id <n>  <group> <name>` above the length and
   duration, and the save dialog proposes `<bundle>_<id>.wav`.

Errors are reported in the status line under the buttons: a file that is not a
`tPxD` stream, an index without its data file, or an unwritable output path
each leave the window open and usable.

## Options

| option | meaning |
|---|---|
| `FILE` | a `.PXD` sample, an `.INF` index or a bundle data file |
| `OUT` | output `.wav` (default: the input name with `.wav`) |
| `--inf PATH` | index for a bundle passed as `FILE` |
| `--id N` | sample id to take from a bundle |
| `--list` | print the ids and names a bundle holds, then exit |
| `--check` | report the decoder, Tk and drag-and-drop state of this build, then exit |
| `-h`, `--help` | print the usage line and exit |
| `--version` | print the version (`1.0.0`) and exit |

`--check` is how a packaged build is verified.  It prints the executable name,
the Python version and whether the run is a frozen bundle, the `numpy` and Tk
versions, and whether TkDND loaded:

```text
pxd2wav.exe (1.0.0)
python 3.14.7, frozen bundle
numpy 2.4.4
tkinter 9.0
drag and drop: yes
```

## Examples

```bash
# One sample, name taken from the input
python apps/pxd2wav/src/pxd2wav.py disks/Dance_eJay/DANCE/BA/AAAF.PXD

# Explicit output, from another working directory
python apps/pxd2wav/src/pxd2wav.py ../disks/Rave_eJay/RAVE/BQ/R1BS001.PXD out.wav

# A Dance 2 record by id, and the same record through the other half of the pair
python apps/pxd2wav/src/pxd2wav.py disks/Dance_2/D_ejay2/PXD/DANCE20.INF --id 1512 out.wav
python apps/pxd2wav/src/pxd2wav.py disks/Dance_2/D_ejay2/PXD/DANCE20 --id 1512 out.wav

# A Techno eJay 2 sample: the id the tooling quotes for START.MIX
python apps/pxd2wav/src/pxd2wav.py disks/Techno_eJay/EJAY/PXD/RAVE20 --id 13016 kick.wav

# What is in an index?
python apps/pxd2wav/src/pxd2wav.py disks/Techno_eJay/EJAY/PXD/RAVE20.INF --list | head
```

The packaged build is used the same way:

```bash
dist/pxd2wav/pxd2wav.exe disks/Dance_eJay/DANCE/BA/AAAF.PXD out.wav
dist/pxd2wav/pxd2wav.exe --check
```

## Output

The WAV is always the same shape:

* 16-bit signed samples, one channel, interleaved by definition;
* 44.1 kHz, the rate of every supported sample container;
* exactly the sample's declared frame count — the tool truncates rather than
  padding, which is what the index and the codec header both state.

One summary line is printed per conversion: `<input> -> <output>
(<name>: <frames> samples, <seconds> s)`, or `<index> [id <n>] -> <output>
(<name>: …)` for a bundle record.  Nothing is printed while decoding.

## Exit status

| status | when |
|---|---|
| `0` | the WAV was written, or the window closed, or `--list` / `--check` finished |
| `1` | the sample could not be decoded or the output could not be written: not a `tPxD` stream, truncated header, absent id, unreadable file |
| `2` | the arguments were invalid, or a bundle was given without `--id` and without `--list` |

Errors are printed on stderr as `<file>: <message>`.  A missing file reports
the `OSError` text, and a file that is not a sample reports `not a tPxD
stream`.

## Notes

* The window needs a display; the headless path does not, so a conversion
  works over a remote shell.  Passing a file never opens a window.
* The single headerless Rave file `RAVE/BD/R1DA084.PXD` is rejected: a stream
  without the `tPxD` magic is only accepted where the format asks for it, which
  this generic converter cannot infer from one file.
* A bundle record is decoded from its own slice of the data file, so a corrupt
  record fails alone; the rest of the index stays usable.
* Modifying or creating samples is out of scope: the tool writes WAV only.
