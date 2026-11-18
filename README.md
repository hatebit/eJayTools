# eJayTools

[![CI](https://github.com/hatebit/eJayTools/actions/workflows/ci.yml/badge.svg)](https://github.com/hatebit/eJayTools/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/hatebit/eJayTools?label=latest%20release)](https://github.com/hatebit/eJayTools/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![Pages](https://img.shields.io/badge/Pages-live-brightgreen)](https://hatebit.github.io/eJayTools/)

**Live website:** https://hatebit.github.io/eJayTools/

Reverse-engineered descriptions of the Dance eJay, Rave eJay and HipHop eJay
1.x `*.MIX` song formats and of the section-based eJay 2 formats (Dance,
Techno), with the pure-Python tooling that decodes, verifies, renders and
re-encodes them, and players that mix the original samples back together.

All five formats were recovered by reading data files only. No program from any
eJay installation is executed, and every decoded song is proved by re-encoding
it byte for byte.

| format | signature | songs | tempo | bar | samples |
|--------|-----------|-------|-------|-----|---------|
| Dance eJay | `0x0A06` | 16 | 140 BPM | 75 600 | `PXDDANCE` (1 352) + 168 `SPECIAL` WAVs |
| Rave eJay | `0x0A07` | 15 | 180 BPM | 58 800 | `RAVE/EJAY/PXD` (1 149) |
| HipHop eJay | `0x0A08` | 17 | 96 BPM | 110 250 | `HIPHOP/EJAY/PXD` (1 341) + 101 `SPECIAL` WAVs |
| Dance eJay 2 | `0x0A19` | 13 | 140 BPM | 75 600 | `DANCE20` (1 957) + `DANCESK4/5/6` |
| Techno eJay 2 | `0x0889` | 13 | 140 BPM | 75 600 | `RAVE20` (4 015) |

Bar lengths are in samples at 44.1 kHz. The three 1.x formats are a 702-bar ×
8-track `uint16` grid followed by a bank block; the two eJay 2 formats are
variable-length section sequences whose drum pattern is decoded down to each
record's start bar. Each tree's `FORMAT.md` has the byte-level detail.

## Quick start

Set the environment up once with [uv](https://docs.astral.sh/uv/) (recommended),
which reads `pyproject.toml` and the committed `uv.lock` and creates `.venv`:

```bash
uv sync --all-extras          # numpy + sounddevice + textual + tkinterdnd2
uv run python apps/emp/src/mixplayer.py --version
```

Then run from the repository root, with the eJay data present under `disks/`
(all five trees for `--all`; see [Data](#data)). Prefix the commands below with
`uv run` to use the uv environment, or use plain `python` when the dependencies
are already installed:

```bash
python reverse/dance/mixdump.py --verify --all                    # every song re-encodes exactly
python reverse/dance/mixdump.py --json reverse/dance/decoded --all
python apps/emr/src/mixrender.py --all --out out/images                 # one PNG per song

python apps/emp/src/mixplayer.py disks/Dance_eJay/MIX/START.MIX --from 82 --bars 8 --wav out.wav
python apps/emp/src/mixplayer.py disks/Rave_eJay/MIX/START.MIX --from 82 --bars 8 --wav out.wav
python apps/emp/src/mixplayer.py disks/Hiphop_eJay/MIX/START.MIX --from 82 --bars 8 --wav out.wav
python apps/emp/src/mixplayer.py disks/Dance_2/MIX/OTHER.MIX --from 1 --bars 12 --wav out.wav
python apps/emp/src/mixplayer.py disks/Techno_eJay/MIX/START.MIX --from 1 --bars 8 --wav out.wav
```

Every tree's `mixdump.py` takes the same options (`--all`, `--verify`,
`--json`, and `--pattern` for the eJay 2 trees); each tree's `README.md` lists
its own examples.

`python apps/emp/src/mixplayer.py` runs one player for every format: it
detects the
tree from the file signature and lists all candidates when a bare name exists
in several trees (`--format dance|rave|hiphop|dance2|techno` forces one).
Options: `--from`, `--bars`, `--solo`, `--mute`, `--gain`, `--loop`, `--wav`,
`--catalog`, `--verbose` and `--version`. Playback needs `sounddevice`;
`--wav` renders without it.

`python apps/emr/src/mixrender.py` is the same frontend for PNG arrangements
(`--format`, `--all`, `--out`, `--cell-w`, `--cell-h`); without `--out` it
writes to `reverse/<format>/images`.

`python apps/emp/src/mixtui.py disks/Dance_eJay/MIX` opens the same player as a
Textual TUI: pick a mix, then play, pause, seek or export the selected bars. A
TUI render is byte-identical to the CLI's for the same bars. It needs the
optional `textual` package; the CLIs do not.

`python apps/pxd2wav/src/pxd2wav.py` converts samples rather than mixes: with
no arguments it opens a small window (drop a `.PXD`, or an eJay 2 `.INF` bundle
and pick one of its samples by id), with a path it converts headlessly
(`AAAF.PXD out.wav`, `DANCE20.INF --id 1512 out.wav`), and `--list` prints the
ids an index holds.

## Requirements

* Python 3.14 (developed on 3.14.7, Windows + Git Bash).
* [uv](https://docs.astral.sh/uv/) for the recommended setup: `uv sync` reads
  `pyproject.toml` and `uv.lock`; `uv run <command>` runs inside that
  environment. Plain `pip install` works too.
* `numpy` for the `.PXD` codec and the player core.
* `sounddevice` for live playback only.
* `textual` for the TUI only.
* `tkinterdnd2` for the converter window's drag and drop only.
* `mixfmt.py`, `mixdump.py`, `mixrender.py` and `apps/emr/src/render/` use the
  standard library only.

The optional groups in `pyproject.toml` are `playback`, `tui` and `pxd2wav`
(`uv sync --extra tui`, `--all-extras` installs everything); `pyinstaller` is in
the `dev` group for building the bundles.

## Documentation

End-user manuals for the four applications (`emp-cli`, `emp-tui`, `emr-cli`
and `pxd2wav`) are in [`docs/`](docs/), with an index of the shared
conventions.

Each format has a documentation tree under `reverse/` with the same six files:

| file | contents |
|------|----------|
| `README.md` | overview, playback model, results |
| `FORMAT.md` | byte-level spec and worked example |
| `SAMPLES.md` | sample-id mapping and what is missing |
| `PXD.md` | `.PXD` container and audio codec |
| `MIXES.md` | every song with measured statistics |
| `METHOD.md` | evidence, dead ends and open questions |

| format | folder |
|--------|--------|
| Dance eJay | [`reverse/dance/`](reverse/dance/) |
| Rave eJay | [`reverse/rave/`](reverse/rave/) |
| HipHop eJay | [`reverse/hiphop/`](reverse/hiphop/) |
| Dance eJay 2 | [`reverse/dance2/`](reverse/dance2/) |
| Techno eJay 2 | [`reverse/techno/`](reverse/techno/) |

`reverse/ADDING_A_FORMAT.md` describes how a sixth format tree is added.

## Data

`disks/` is gitignored, so a clone contains the code and docs but not the
audio. Drop an installation at `disks/Dance_eJay/`, `disks/Rave_eJay/`,
`disks/Hiphop_eJay/`, `disks/Dance_2/` and/or `disks/Techno_eJay/` and the
matching tooling runs. The data is read-only; nothing here writes to it.

## Repository layout

```
disks/Dance_eJay/        eJay data, not tracked by git (242 MB)
├─ MIX/                  16 songs, 11 234 or 11 413 bytes each
├─ DANCE/                sample banks: AA…AL, BA…BW (.PXD), EJAY/ catalogues
└─ SPECIAL/              168 WAV samples (ids 1…168)

disks/Rave_eJay/         eJay data, not tracked by git
├─ MIX/                  15 songs, 11 276 or 11 326 bytes each
└─ RAVE/                 sample banks: AA…AK, BA…BS, HYPER (.PXD), EJAY/ catalogues

disks/Hiphop_eJay/       eJay data, not tracked by git
├─ MIX/                  17 songs, 12 692 bytes each
├─ HIPHOP/               sample banks: AA…BR (.PXD), SCRATCH WAVs, EJAY/ catalogues
└─ SPECIAL/              101 WAV samples (ids 1…101)

disks/Dance_2/           eJay data, not tracked by git
├─ MIX/                  13 songs, 1 553 … 8 219 bytes each
└─ D_ejay2/
   ├─ PXD/               DANCE20 + DANCE20.INF, DANCESK4/5/6 (+ .INF)
   └─ ejay/              Audio_d/e/f demo .PXD, PXD10 catalogue, METRO, intro

disks/Techno_eJay/       eJay data, not tracked by git
├─ MIX/                  13 songs, 2 144 … 6 236 bytes each
└─ EJAY/PXD/             RAVE20 + RAVE20.INF, HYP1 … HYP4 standalone .PXD

reverse/dance/           Dance docs + generated decoded/ and images/
reverse/dance2/          Dance eJay 2 docs + generated decoded/ and images/
reverse/hiphop/          HipHop docs + generated decoded/ and images/
reverse/rave/            Rave docs + generated decoded/ and images/
reverse/techno/          Techno eJay 2 docs + generated decoded/ and images/
apps/emp/src/core/          shared, format-neutral player core (mixing, sinks, CLI)
libs/pxd/                    shared .PXD codec + .INF bundle reader
libs/mix/                    shared mix-format contracts and parsers (stdlib only)
libs/mix/<tree>/             mixfmt.py, shared by the player and the renderer
apps/emp/src/format/         player runtime: ports.py and per-format adapters
apps/emp/src/format/<tree>/  adapter.py and, for eJay 2, banks.py
apps/emr/src/format/<tree>/ per-tree PNG provider: catalogue, bar length, output
apps/emr/src/render/        shared PNG engine: canvas, layouts, sample probes, registry
apps/emp/src/paths.py       locate disks/ in a source checkout or a frozen build
apps/emp/src/               unified mixplayer.py and mixtui.py
apps/emr/src/mixrender.py    unified PNG renderer (detects the format)
apps/emr/packaging/          PyInstaller spec and build wrapper for emr-cli
apps/emp/packaging/         PyInstaller specs, bundle builders, release uploaders
```

The five `libs/mix/<tree>/` parsers and their `apps/emp/src/format/<tree>/`
runtimes are independent: none imports another's code. `apps/emp/src/formats.py` is the one composition root that
names all five, and the player core and shared contracts name no format.

## Binaries

`apps/emp/packaging/build_emp_cli.py` and
`apps/emp/packaging/build_emp_tui.py` build one-dir PyInstaller bundles of
`apps/emp/src/mixplayer.py` (`emp-cli`) and `apps/emp/src/mixtui.py`
(`emp-tui`); `apps/emp/packaging/release_emp_*.py` zip and publish them as
GitHub releases with `gh`. `apps/emr/packaging/build_emr_cli.py` and
`apps/emr/packaging/release_emr_cli.py` do the same for the PNG renderer as
`emr-cli`. `apps/pxd2wav/packaging/build_pxd2wav.py` and
`apps/pxd2wav/packaging/release_pxd2wav.py` do the same for the converter as
`pxd2wav`, bundling `tkinterdnd2` so drag and drop works in the frozen build.
`.github/workflows/release-emp-cli.yml`, `release-emp-tui.yml`,
`release-emr-cli.yml` and `release-pxd2wav.yml` each build and publish one tool
on their own Windows runner: a `v*` tag releases all four, a `<tool>-v*` tag
just that one. Build,
release and data-path details are in [`AGENTS.md`](AGENTS.md).

## Licence

[MIT](LICENSE), © 2026 Nelson Gonçalves. The licence covers this repository's
code and documentation. The eJay software, the sample banks and the names in
their catalogues remain with their owners: no eJay data is included here, and
this project is not affiliated with the original eJay publishers.
