# EMP TUI — `emp-tui.exe` / `mixtui.py`

`apps/emp/src/mixtui.py` is the interactive frontend for the same player core
as the EMP CLI.  It lists the mixes in one folder, loads the one you select,
plays a bar range, exports that range to WAV and shows what each track is
sounding.  The packaged Windows binary is `dist/emp-tui/emp-tui.exe`.

## Requirements

* Python 3.14, `numpy`, and the optional `textual` package.  Without
  `textual` the program prints:

  ```
  apps/emp/src/mixtui.py needs the optional textual package:
    python -m pip install textual
  ```

  and exits 2.
* `sounddevice` for live playback.  Export works without it.
* eJay data under `disks/` as described in
  [eJay data](README.md#ejay-data).

## Starting it

```bash
python apps/emp/src/mixtui.py DIRECTORY
emp-tui.exe DIRECTORY                    # packaged build
```

`DIRECTORY` is required, is not searched recursively, and is scanned for files
whose name ends in `.MIX` (any case).  The list is sorted and each row shows
the mix name and the detected format; a file whose signature is unknown is
listed as `unknown` and cannot be opened.  The first mix in the list is opened
automatically at startup.

```bash
python apps/emp/src/mixtui.py disks/Dance_eJay/MIX
python apps/emp/src/mixtui.py disks/Dance_2/MIX
```

The command line takes no `--from`, `--bars` or `--wav`: those are set in the
window.  `--version` prints the version (`1.0.0`); `--help` works even when
`textual` is not installed.

## The window

```
┌ mixes ─────────────────────┐ ┌ summary ──────────────────────────────┐
│ mix            format      │ │ START.MIX: 90 bars (154.3 s), …       │
│ START.MIX      Dance eJay  │ ├───────────────────────────────────────┤
│ …                          │ │ #  pan      playing                   │
│ [Play]  [Export]           │ │ 1  centre   kick I basic              │
│ out.wav                    │ │ …                                     │
│ [from bar] [bars (0 = all)]│ │ ▓▓▓▓▓▓░░░░░░░░░░ progress              │
│ [ ] Loop                   │ │ playing  bar 34  12.0 / 154.3 s …     │
│ [Pause] [Stop]             │ │ log                                    │
│ [seek bar] [Seek]          │ └───────────────────────────────────────┘
│ [gain]     [Set]           │
└────────────────────────────┘
```

* **Mixes table** — the scans of `DIRECTORY`; selecting a row loads that mix.
* **Play** — start live playback of the selected range.
* **Export** — render the selected range to the WAV path in the text field
  (default `out.wav`).
* **from bar** — first bar of the selection.  It is prefilled with the
  format's default (`0` for the two 1.x grid families, `1` for the two eJay 2
  families) when a mix is first opened.
* **bars (0 = all)** — number of bars; `0` selects to the end.
* **Loop** — loops the range during playback.
* **Pause / Stop** — pause the running transport (the button changes to
  `Resume`) or stop it.
* **seek bar + Seek** — jump within the playing range.
* **gain + Set** — change the gain while playing or for the next playback or
  export.
* **summary** — the same line the CLI prints for the loaded song.
* **tracks table** — one row per track: its number, its pan (`centre`,
  `left`, `right`, or the format's own wording), and the catalogue label of
  the sample currently sounding on it.  The label clears when the sample ends.
* **progress bar and status** — `state  bar N  elapsed / total seconds  gain`.
* **log** — decode messages, per-bar progress, export results and errors.

## Working with a mix

### Choosing a mix

Move the row cursor with the arrow keys (or click a row), then press `Enter`
to load it.  Loading replaces the current mix and stops any playback.  The
*from bar* field is filled with the format's default only when it is empty;
the other fields keep their current values.

### Playing

Enter a start bar and a bar count, tick **Loop** if wanted, then activate
**Play**.  Playback needs `sounddevice`; if it is missing the log says
`sounddevice is not available (…)`.  If the range is invalid (a non-numeric
bar, or a start past the end) the log explains and nothing plays.  Pressing
Play while something is already playing restarts from the fields as they are
now.

### Pausing, stopping and seeking

**Pause** suspends the transport and becomes **Resume**.  **Stop** ends it.
**Seek** needs a current transport: without one the log says `nothing playing;
press Play first`.  A seek bar outside the current selection is clamped to it;
seeking a finished transport leaves it paused, ready for Resume.

### Changing the gain

Enter a non-negative multiplier (for example `0.8`) and activate **Set** or
press `Enter` in the field.  While a transport is playing or paused the value
is applied on top of the song's automatic gain; with no transport it becomes
the song gain used by the next playback and export.  The log prints the
multiplier and the effective total, e.g. `gain 0.80 (effective 0.29)`.

### Exporting

Set the WAV path, choose the range, then activate **Export**.  The file is
written in a background thread, so the interface stays responsive; the log
prints `rendering bars …` and then `wrote …`, or `render failed: …`.  The WAV
is 16-bit stereo at 44.1 kHz and holds exactly the selected bars.  For the same
song, bars and target it is byte-identical to the EMP CLI's `--wav` output,
because both call the same render path.  `Loop` does not affect an export.
(The missing-audio log message says “use Render instead”; it refers to this
**Export** button.)

## Keys

| key | action |
|---|---|
| `Enter` | load the highlighted mix, activate the focused button, or submit the focused seek/gain field |
| `↑` `↓` | move within the focused table |
| `Tab` / `Shift+Tab` | move focus between the tables, fields and buttons |
| `Ctrl+Q` | quit |
| `Ctrl+C` | show a reminder of the quit key; it does not quit |

The Footer at the bottom shows the bindings that apply at the moment.

## Exit status and messages

| status | when |
|---|---|
| `0` | the window was closed normally |
| `2` | `textual` is missing, `DIRECTORY` does not exist, or the arguments are invalid |

`DIRECTORY` that is a file or does not exist is reported as
`…: not a directory`.  Unreadable mixes and catalogue errors are shown in the
log without closing the application.

## Notes

* Bar numbers follow the format: `0`-based for `dance`, `rave` and `hiphop`,
  `1`-based for `dance2` and `techno`.  The status line uses the same numbers
  as the row you typed.
* The mix list is a single folder.  Point the program at each tree's `MIX`
  folder in turn; it does not merge the five trees.
* Opening a mix decodes every sample it references, so the first open of a
  large song can take a moment; the log shows `decoding N sample files…`.
