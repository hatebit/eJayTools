# User manuals

These manuals cover the four applications in this repository.  Three are
frontends over the same five reverse-engineered eJay `*.MIX` formats; the
fourth converts individual `.PXD` samples to WAV.  None of them modifies the
eJay data under `disks/`.

| application | source entry point | binary | what it does | manual                   |
|---|---|---|---|--------------------------|
| EMP CLI | [`apps/emp/src/mixplayer.py`](https://github.com/hatebit/eJayTools/apps/emp/src/mixplayer.py) | `emp-cli.exe` | play a mix, or render a bar range to WAV | [emp-cli.md](emp-cli.md) |
| EMP TUI | [`apps/emp/src/mixtui.py`](https://github.com/hatebit/eJayTools/apps/emp/src/mixtui.py) | `emp-tui.exe` | the same player as an interactive terminal UI | [emp-tui.md](emp-tui.md) |
| EMR CLI | [`apps/emr/src/mixrender.py`](https://github.com/hatebit/eJayTools/apps/emr/src/mixrender.py) | `emr-cli.exe` | render arrangements as PNG track grids | [emr.md](emr.md)         |
| PXD to WAV | [`apps/pxd2wav/src/pxd2wav.py`](https://github.com/hatebit/eJayTools/apps/pxd2wav/src/pxd2wav.py) | `pxd2wav.exe` | convert one `.PXD` sample, or one bundle record, to a WAV | [pxd2wav.md](pxd2wav.md) |

The format specifications live under [`reverse/`](https://github.com/hatebit/eJayTools/reverse/); the
`reverse/<tree>/mixdump.py` dumpers and the `libs/pxd` codec CLI are
developer/research tools rather than end-user applications and are documented
in [the root README](https://github.com/hatebit/eJayTools/README.md) and each tree's `README.md`.

## Supported formats

Every application detects the format from the two-byte signature at the start
of the file.  The two command-line applications also accept `--format <id>` to
skip detection; the TUI detects the format of each file it lists.  The ids
are:

| `--format` | product | signature | tracks | bar length | tempo |
|---|---|---|---|---|---|
| `dance` | Dance eJay 1.x | `0x0A06` | 8 | 75 600 samples | 140 BPM |
| `rave` | Rave eJay 1.x | `0x0A07` | 8 | 58 800 samples | 180 BPM |
| `hiphop` | HipHop eJay 1.x | `0x0A08` | 8 | 110 250 samples | 96 BPM |
| `dance2` | Dance eJay 2 | `0x0A19` | 16 | 75 600 samples | 140 BPM |
| `techno` | Techno eJay 2 | `0x0889` | 16 | 75 600 samples | 140 BPM |

Bar lengths are at 44.1 kHz.  The three 1.x formats use a 702-bar grid and
count bars from 0; the two eJay 2 formats are section sequences and count bars
from 1.  Track numbers on the command line are always
1-based.

## Requirements

* Python 3.14 for source runs.
* `numpy` for the player applications and the `.PXD` converter, which all
  share the codec.
* `sounddevice` for live playback only.  WAV export and PNG rendering work
  without it.
* `textual` for the TUI only.  The two command-line applications do not need
  it.
* `tkinter` for the converter's window, and `tkinterdnd2` for its drag and
  drop.  A headless conversion needs neither.

The renderer and the parsers it imports are standard-library only.  There is
no installation step: run the scripts from a source checkout, or use the
packaged binaries.

## eJay data

The audio and songs are not part of this repository.  A source run expects
the five installations at:

```
disks/Dance_eJay/     disks/Rave_eJay/     disks/Hiphop_eJay/
disks/Dance_2/        disks/Techno_eJay/
```

The applications find that folder by walking up from their own source file
(for a packaged build, from the executable), so the current working directory
does not affect data lookup.  Set `EJAY_DATA_ROOT` to the repository root or
to the `disks` folder itself to override the search — the packaged binaries in
particular need this when the eJay data is not beside the executable.

Only the trees you use have to be present: a missing tree simply means its
songs are not found.  Data is read-only; no application writes under `disks/`.

## Conventions common to all manuals

* Relative output paths (`out.wav`, `--out out/images`) are resolved against
  the current working directory.
* A song argument may be a path or a bare song name.  A bare name is resolved
  against every present tree's `MIX` folder, with or without the `.MIX`
  suffix; a name that exists in more than one tree is reported as ambiguous
  until `--format` names the tree or a path disambiguates it.
* Exit status `0` means success.  A non-zero status is an error and is
  reported on stderr; the exact codes are listed in each manual.
* All four applications report version `1.0.0`.
