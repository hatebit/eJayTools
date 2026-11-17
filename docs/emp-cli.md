# EMP CLI — `emp-cli.exe` / `mixplayer.py`

`apps/emp/src/mixplayer.py` is the command-line player for all five supported
eJay `*.MIX` formats.  It either sends a selected bar range to the sound card
or renders that range to a WAV file.  The packaged Windows binary is
`dist/emp-cli/emp-cli.exe`; both take the same options.

## Requirements

* Python 3.14 and `numpy` for a source run.
* `sounddevice` for live playback.  It is imported lazily, so `--wav` works
  without it.
* One or more eJay installations under `disks/` (see
  [eJay data](README.md#ejay-data)).

## Synopsis

```bash
python apps/emp/src/mixplayer.py MIX [options]
emp-cli.exe MIX [options]              # packaged build
```

`MIX` is a path to a `.MIX` file or a bare song name.  Without `--wav` the
program plays the selection; with `--wav OUT` it writes the selection and
exits.

## Selecting the mix

* **Path** — the format is read from the file signature.  An unknown
  signature is reported as `unrecognised mix (unknown signature)`.
* **Bare name** — `START.MIX` or `START` is looked up in each present tree's
  `MIX` folder.  `START` exists in all five trees in a full installation, so
  the player prints every candidate and exits 2 until you name the format or
  pass a path:

  ```
  START.MIX is ambiguous:
    …/disks/Dance_eJay/MIX/START.MIX
    …/disks/Rave_eJay/MIX/START.MIX
    …/disks/Hiphop_eJay/MIX/START.MIX
    …/disks/Dance_2/MIX/START.MIX
    …/disks/Techno_eJay/MIX/START.MIX
  use --format <id> or pass a path
  ```

* **`--format`** — `dance`, `rave`, `hiphop`, `dance2` or `techno`.  It skips
  detection.  A path carrying a different signature is rejected with
  `… is not a <format> mix`.

## Bar numbers and the selected range

A song is measured in bars, and the player distinguishes two conventions:

| formats | bar numbering | default `--from` | track numbers |
|---|---|---|---|
| `dance`, `rave`, `hiphop` (702-bar grid) | `0` is the first bar | `0` | `1..8` |
| `dance2`, `techno` (section sequence) | `1` is the first bar | `1` | `1..16` |

The end of the printed range is exclusive.  `playing bars 82..90` is the
eight grid bars 82 through 89; a section-format selection from bar 1 for 12
bars prints `playing bars 1..12`, which is bars 1 through 12.

* `--bars N` selects `N` bars from `--from`.  `--bars 0` (the default) selects
  to the end of the song.
* A range is clamped to the song: `--bars` longer than the remaining song
  ends at the last bar.
* A first bar at or past the end is an error: `bar 500 is past the end (90
  bars)`.
* A negative `--bars` is rejected, not treated as an empty range.

The song's bar count includes samples that ring out past the last occupied
grid bar.  The player prints a note when that tail is audible, for example
`tail: samples ring out to bar 90 (arrangement ends at 83)`.

## Options

| option | meaning |
|---|---|
| `--format ID` | force a format instead of detecting it |
| `--from BAR` | first bar of the selection |
| `--bars N` | number of bars; `0` = to the end |
| `--solo LIST` | play only these tracks, e.g. `3` or `1,4` |
| `--mute LIST` | silence these tracks, e.g. `8` or `2,5` |
| `--gain X` | output gain; default is automatic peak normalisation |
| `--loop` | loop the selection during live playback |
| `--wav OUT` | render to `OUT` instead of playing |
| `--catalog LIST DIR BASE` | add an extra sample catalogue (repeatable; grid formats only) |
| `-v`, `--verbose` | log every decoded sample and per-track statistics |
| `--version` | print the version (`1.0.0`) and exit |

`--gain` sets an absolute gain.  Without it the loader measures the song's
peak estimate and sets `0.95 / peak`, bounded to 0.05–8.0, which leaves a
little headroom and is why the summary line shows values such as `gain 0.36`.

`--solo` and `--mute` are 1-based and may be combined; `--solo` keeps the
listed tracks audible and mutes the rest, then `--mute` removes any listed
track.  Out-of-range numbers are an argument error naming the valid range.

## Examples

```bash
# Detect the format and play from the first bar
python apps/emp/src/mixplayer.py disks/Dance_eJay/MIX/START.MIX

# Render eight bars starting at bar 82 (13.7 s at 140 BPM)
python apps/emp/src/mixplayer.py disks/Dance_eJay/MIX/START.MIX \
    --from 82 --bars 8 --wav out.wav

# A bare name in the ambiguous case needs the format
python apps/emp/src/mixplayer.py START.MIX --format rave --wav out.wav

# Dance eJay 2 numbers its first bar 1
python apps/emp/src/mixplayer.py OTHER.MIX --format dance2 --from 1 --bars 12 --wav out.wav

# Silence track 8 and loop the whole song while playing
python apps/emp/src/mixplayer.py disks/Hiphop_eJay/MIX/START.MIX --mute 8 --loop

# Custom gain with per-sample logging
python apps/emp/src/mixplayer.py START.MIX --format techno --gain 0.8 -v
```

The packaged build is used the same way:

```bash
dist/emp-cli/emp-cli.exe disks/Dance_eJay/MIX/START.MIX --from 82 --bars 8 --wav out.wav
```

## Output

A normal run prints the sample decode count, one summary line, any notes, the
selected range and — for live playback — a progress line:

```
  decoding 48 sample files...
START.MIX: 90 bars (154.3 s), 8 tracks (T7 left, T8 right), 48 samples used, gain 0.36
  tail: samples ring out to bar 90 (arrangement ends at 83)
  playing bars 82..90 (13.7 s)
  wrote out.wav
```

The summary is `<file>: <bars> bars (<seconds> s), <detail>, <n> samples used,
gain <x>`.  `<detail>` names the track count and the pan convention the format
uses (`centred`, or `T7 left, T8 right` for the stereo-paired Dance style).

With `-v` the run additionally logs every decoded sample as
`sample <id> <label> <path> <seconds>` (or `skip <id> <label> unavailable`),
then a per-track line `T1 <placed>/<distinct> …` and
`peak estimate <p> -> gain <g>`.

Live playback also prints a carriage-return progress line ending in `done`,
with the overflow count if the audio callback fell behind.  In `--wav` mode no
progress is printed.

## WAV export

`--wav OUT` writes a standard PCM file:

* 16-bit signed samples, two channels, interleaved;
* 44.1 kHz, the sample rate of every supported format;
* exactly the selected bars — `N × bar length` frames — mixed from the song's
  placements and the effective gain;
* `--loop` has no effect on a render, which is always written once.

For the same song, bars and output target, an export from the TUI is
byte-identical, because both frontends call the same
`PlayerApplication.render_wav`.

## Live playback

Without `--wav` the player opens `sounddevice` and streams the mix.  If the
package is unavailable it prints `sounddevice is not available; use --wav to
render instead` and exits 2.  A song with no usable samples prints `nothing to
play: no available samples` and exits 2.

`Ctrl+C` stops playback and exits 0.  `--loop` repeats the selected range; the
same range without `--loop` finishes and reports `done`.

## Extra catalogues

The three grid formats can take additional sample catalogues for an
installation the player does not know:

```bash
python apps/emp/src/mixplayer.py song.MIX \
    --catalog path/to/list.txt path/to/samples 10000
```

The three values are the catalogue list, the folder its sample paths are
relative to, and the sample id of its first record.  A list uses eJay's
six quoted fields per record (path, blank, category, number, group, name);
records are numbered `BASE + n`.  Catalogues are searched before the built-in
ones and may be repeated.  `--catalog` is an argument error for `dance2` and
`techno`, which look their ids up in `DANCE20.INF` and `RAVE20.INF` instead.

## Exit status and messages

| status | when |
|---|---|
| `0` | playback finished or was interrupted with `Ctrl+C`; WAV written |
| `2` | every error: bad arguments, unknown or ambiguous mix, missing file, wrong `--format`, past-the-end bar, bad catalogue, unreadable mix, no audio device |

Errors are printed on stderr.  The common ones are:

| message | fix |
|---|---|
| `no such mix: NAME` | check the path, or run from the repository root |
| `NAME is ambiguous:` | add `--format <id>` or pass the full path |
| `… is not a <format> mix` | the path has another format's signature |
| `unrecognised mix (unknown signature)` | the file is not one of the five formats |
| `bar N is past the end (M bars)` | choose a bar below `M` |
| `track numbers are 1..8` (or `1..16`) | correct the `--solo`/`--mute` list |
| `--catalog is not supported for …` | extra catalogues apply to grid formats only |
| `sounddevice is not available` | install `sounddevice` or use `--wav` |

## Per-format defaults

| format | display name in messages | tracks | bar (samples) | bar (seconds) |
|---|---|---|---|---|
| `dance` | Dance eJay 1.x | 8 | 75 600 | 1.714 |
| `rave` | Rave eJay 1.x | 8 | 58 800 | 1.333 |
| `hiphop` | HipHop eJay 1.x | 8 | 110 250 | 2.500 |
| `dance2` | Dance eJay 2 | 16 | 75 600 | 1.714 |
| `techno` | Techno eJay 2 | 16 | 75 600 | 1.714 |
