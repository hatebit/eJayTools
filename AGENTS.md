# AGENTS.md

Repository-specific instructions for coding agents. Read this before changing
anything here.

## What this repository is

Reverse-engineered specifications of the Dance eJay, Rave eJay and HipHop eJay
1.x `*.MIX` arrangement formats and of the section-based eJay 2 `*.MIX` formats
(Dance eJay 2 in `D_ejay2`, Techno eJay 2), plus pure-Python tooling and players
for them.  The five trees are independent: none may import another's code.
Shared, format-neutral packages include the `.PXD` codec in `libs/pxd/`
(one implementation; every tree decodes through it) and the standard-library
format contracts in `libs/mix/` (each tree's `mixfmt.py` subclasses
them).  The format-neutral player core in `apps/emp/src/core/`, the shared PNG
renderer in `apps/emr/src/render/` and the unified CLIs
`apps/emp/src/mixplayer.py` and `apps/emr/src/mixrender.py` sit on top and
never import one tree from another.  `apps/emp/src/formats.py` names all five
adapters and `apps/emr/src/render/registry.py` names all five render providers.
The value of the repo is the **documentation and the byte-exact writer**; a
change that makes output "render fine" but no longer re-encodes identically is
a regression.

```
disks/Dance_eJay/   eJay data — read-only, gitignored (242 MB)
disks/Rave_eJay/    eJay data — read-only, gitignored
disks/Hiphop_eJay/  eJay data — read-only, gitignored
disks/Dance_2/      eJay data — read-only, gitignored (D_ejay2 install)
disks/Techno_eJay/  eJay data — read-only, gitignored (Techno eJay 2 install)
reverse/dance/      Dance prose docs, mixdump.py + generated decoded/ and images/
reverse/rave/       Rave prose docs, mixdump.py + generated decoded/ and images/
reverse/hiphop/     HipHop prose docs, mixdump.py + generated decoded/ and images/
reverse/dance2/     Dance eJay 2 prose docs, mixdump.py + generated decoded/ and images/
reverse/techno/     Techno eJay 2 prose docs, mixdump.py + generated decoded/ and images/
apps/emp/src/core/          shared headless player core (format-neutral, numpy)
libs/pxd/                    shared .PXD codec + .INF bundle reader (numpy)
apps/emr/src/render/         shared PNG renderer: canvas, layouts, header-only
                             sample probes, CLI and the five-provider registry
                             (stdlib only)
libs/mix/                    shared mix-format contracts and parsers
                             (standard-library only)
libs/mix/<tree>/             mixfmt.py, shared by the player and the renderer
apps/emp/src/format/         player runtime: ports.py and one package per tree
apps/emp/src/format/<tree>/  adapter.py and banks.py
apps/emr/src/format/<tree>/  per-tree PNG provider: catalogue, bar length and
                             default output
apps/emp/src/check_contracts.py  structural check: every tree implements the ABCs
reverse/ADDING_A_FORMAT.md   procedure for a sixth format tree
apps/emp/src/formats.py     composition root: the only module naming all five
                             adapters
apps/emp/src/mixplayer.py   unified CLI (detects the format from the signature)
apps/emr/src/mixrender.py    unified PNG renderer (detects the format)
apps/emr/packaging/          PyInstaller spec, build and release wrappers for
                             `emr-cli`
apps/emp/src/mixtui.py      Textual frontend (optional dependency)
apps/emp/src/paths.py       locate disks/ in a source checkout or a frozen build
apps/emp/packaging/         PyInstaller specs, bundle builders and release
                             uploaders
```

The only source of format truth is the data under `disks/`. There is no
upstream spec to consult.

## Ground rules

* **Never execute anything under `disks/`.** It holds eJay data and binaries;
  read files, decode bytes, but do not launch them.
* **Do not edit or reformat `disks/`.** No rewriting `.MIX`, `.PXD`, `.WAV` or
  catalogue files. Tests read them; nothing should write there.
* Work inside this repository. No network access is needed for any check.
* If data must move, update the `ROOT` constant in each tree's `adapter.py`
  (and `PXD_DIR` in `banks.py` where present), in `mixdump.py`, in each
  `apps/emr/src/format/<tree>/mixrender.py` **and** every `disks/…` path in the
  docs of the affected tree in the same change.

## Environment

* Windows 10/11 with **Git Bash**; use POSIX syntax (`ls`, `mv`, `rm`, `/dev/null`).
* `python` is Python 3.14 (3.14.7 at time of writing). Run scripts from the
  repository root; they locate the data relative to their own file.
* Dependencies: `numpy` (required by `libs/pxd/` and the
  `apps/emp/src/core/` player core), `sounddevice` (live playback only, imported lazily by the sink)
  and `textual` (the `apps/emp/src/mixtui.py` TUI only, also imported lazily).
  `libs/mix/`, `apps/emr/src/render/`, `mixfmt.py`, `mixdump.py` and
  `mixrender.py` must stay standard-library only — the PNG writer uses `zlib`
  + `struct` rather than Pillow. Do not add dependencies for those.
  `pyinstaller` is build-time only, for `apps/emp/packaging/build_emp_cli.py`,
  `apps/emp/packaging/build_emp_tui.py` and `apps/emr/packaging/build_emr_cli.py`;
  the TUI bundle also needs `textual` installed.
  The GitHub CLI `gh` is upload-time only, for the two `release_emp_*.py`
  scripts; `apps/emp/packaging/empbundle.py` holds their shared code.
* No test framework, no CI. Verification is the CLI checks below.

## Checks (run after any change)

```bash
python apps/emp/src/check_contracts.py                    # must print 5/5
python reverse/dance/mixdump.py --verify --all              # must print 16/16
python reverse/dance/mixdump.py disks/Dance_eJay/MIX/START.MIX | head
python reverse/dance/mixdump.py --json reverse/dance/decoded --all
python libs/pxd disks/Dance_eJay/DANCE/BA/AAAF.PXD --stats
python libs/pxd/check_equal.py --rev <commit before the merge>   # 0 differences
python apps/emp/src/mixplayer.py --format dance START.MIX --from 82 --bars 8 --wav out.wav

python reverse/rave/mixdump.py --verify --all               # must print 15/15
python reverse/rave/mixdump.py disks/Rave_eJay/MIX/START.MIX | head
python reverse/rave/mixdump.py --json reverse/rave/decoded --all
python libs/pxd disks/Rave_eJay/RAVE/BQ/R1BS001.PXD --stats
python apps/emp/src/mixplayer.py --format rave START.MIX --from 82 --bars 8 --wav out.wav

python reverse/hiphop/mixdump.py --verify --all             # must print 17/17
python reverse/hiphop/mixdump.py disks/Hiphop_eJay/MIX/START.MIX | head
python reverse/hiphop/mixdump.py --json reverse/hiphop/decoded --all
python libs/pxd disks/Hiphop_eJay/HIPHOP/AA/H1BS001.PXD --stats
python apps/emp/src/mixplayer.py --format hiphop START.MIX --from 82 --bars 8 --wav out.wav

python reverse/dance2/mixdump.py --verify --all            # must print 13/13
python reverse/dance2/mixdump.py disks/Dance_2/MIX/START.MIX | head
python reverse/dance2/mixdump.py --pattern disks/Dance_2/MIX/OTHER.MIX | head
python reverse/dance2/mixdump.py --json reverse/dance2/decoded --all
python apps/emp/src/mixplayer.py --format dance2 OTHER.MIX --from 1 --bars 12 --wav out.wav
python apps/emr/src/format/dance2/mixrender.py --out reverse/dance2/images --all
python libs/pxd disks/Dance_2/D_ejay2/PXD/DANCE20.INF --id 1930 --stats

python reverse/techno/mixdump.py --verify --all            # must print 13/13
python reverse/techno/mixdump.py disks/Techno_eJay/MIX/START.MIX | head
python reverse/techno/mixdump.py --pattern START.MIX | head
python reverse/techno/mixdump.py --json reverse/techno/decoded --all
python libs/pxd disks/Techno_eJay/EJAY/PXD/RAVE20.INF --id 13016 --stats
python apps/emp/src/mixplayer.py --format techno START.MIX --from 1 --bars 8 --wav out.wav
python apps/emr/src/format/techno/mixrender.py --out reverse/techno/images --all

python apps/emp/src/mixplayer.py START.MIX                 # 5 candidates listed, exit 2
python apps/emp/src/mixplayer.py disks/Dance_eJay/MIX/START.MIX --wav out.wav
python apps/emp/src/mixplayer.py disks/Rave_eJay/MIX/START.MIX --format dance --wav out.wav  # exit 2
python apps/emr/src/mixrender.py START.MIX                 # 5 candidates listed, exit 2
python apps/emr/src/mixrender.py --all --out out/images     # 74 PNGs
python apps/emr/src/mixrender.py --format dance disks/Rave_eJay/MIX/START.MIX --out out/images  # exit 2
python apps/emp/src/mixtui.py --help                       # works without textual
```

Cross-tree import audit (all three commands must print nothing):

```bash
grep -rnE '^\s*(from|import)\s+(dance2?|rave|hiphop|techno)\b' reverse tools --include='*.py'
grep -rnE '^\s*(from|import)\s+(dance2?|rave|hiphop|techno)\b' apps/emp/src/core --include='*.py'
grep -rnE 'format_id\s*(==|!=|in)\b' apps/emp/src/core --include='*.py'
```

The unified CLI must produce the same WAV, stdout, stderr and exit status for
the same song whether the format is detected or named with `--format`, and all
five adapters must import in one process.  A WAV rendered from
`apps/emp/src/mixtui.py` (same bars, same target) must be byte-identical to
`apps/emp/src/mixplayer.py --from … --bars … --wav`; both
use `PlayerApplication.render_wav`, so this compares the frontends, not the
mixer.

Expected: `5/5 trees implement the shared contracts`; `16/16`, `15/15` and
`17/17` files round-trip byte-identically; Dance
PXD stats peak ≤ 0.501 and a bar-aligned duration (1 343 of 1 352 are whole-bar
loops, nine are one-shot FX); Rave PXD stats peak ≤ 0.500 and a 58 800-sample
bar (1 145 of 1 149 are whole-bar loops); HipHop PXD stats peak ≤ 0.393 and a
110 250-sample bar (1 339 of 1 341 are whole-bar loops); the Dance START render
reports 90 bars, the Rave START render 117 bars, the HipHop START render 429
bars, and all write 8 bars for `--from 82 --bars 8`. Dance 2's 13 files must
round-trip byte-identically and its `DANCE20` samples decode with peak ≤ 0.4854;
`--pattern` on `OTHER.MIX` must list `heart beat` on bars 1-12 and the two
`bloose` pairs on bars 5 and 9, and `mixplayer.py OTHER.MIX --from 1 --bars 12
--wav out.wav` must write a 907 200-frame stereo WAV (12 bars), and
`mixrender.py --all` must write 13 PNGs. Techno's 13 files must round-trip
byte-identically, `--pattern` on `START.MIX` must start with bar 41 T1 clip id
13818, the referenced `RAVE20` sample 13016 must decode to 75 600 samples with
peak ≤ 0.360, `mixplayer.py START.MIX --from 1 --bars 8 --wav out.wav` must
write a 604 800-frame stereo WAV, and `mixrender.py --all` must write 13 PNGs.
The unified `apps/emr/src/mixrender.py --all` must write 74 PNGs, and each format's
per-tree wrapper and the unified command must produce byte-identical files.
Delete any temporary `out/`, `out.wav`, `out2.wav` and `__pycache__/`
afterwards — they are not tracked.

`decoded/` and `images/` are generated. Regenerate them; never hand-edit.

## Invariants

* A song is 11 234 bytes: 2-byte signature + 702 bars × 8 tracks × `uint16`.
* `BARS = 702`, `TRACKS = 8`, `SONG_BYTES = 11234`, bar = 75 600 samples at
  44.1 kHz / 140 BPM.
* `mixfmt.Mix.build()` must reproduce the input bytes exactly; verify with
  `--verify --all` rather than trusting a spot check.
* Sample ids: `BANK_BASE = 731` (`731..2082` → `PXDDANCE` records, `id = 731 +
  index`); `1..168` → `SPECIAL` WAVs (`id = record index + 1`); `169..730`
  empty; `3 400+` add-on boxes from the song's bank block.
* Arrangement length is the last occupied bar + 1, but playback ends when the
  last placed sample ends. Keep `Song.bars` (audio) distinct from
  `Mix.song_length` (grid).
* Labels come from the catalogue (`group + " " + name`), verbatim. Do not
  invent prettier names for odd records such as `sharp* [Special] waves1`.

Rave invariants:

* A song is 11 234 bytes: 2-byte signature `0x0A07` + 702 bars × 8 tracks ×
  `uint16`, always followed by a bank block.
* `BARS = 702`, `TRACKS = 8`, `SONG_BYTES = 11234`, bar = 58 800 samples at
  44.1 kHz / 180 BPM.
* `mixfmt.Mix.build()` must reproduce the input bytes exactly, including the
  bank block trailer (`--verify --all` → 15/15).
* Sample ids: `BANK_BASE = 731` (`731..1879` → `RAVE/EJAY/PXD` records,
  `id = 731 + index`); `1..15` are used but unresolved (no shipped audio);
  `16..730` empty; no add-on boxes in this corpus.
* The bank trailer is preserved verbatim (18 bytes, two variants, plus
  `NODRUGS`' 68-byte tail). Only its leading word `8` is interpreted.
* `song_length` (grid) can exceed the audible end because low ids pad the
tail; keep `Song.bars` (audio) distinct from `Mix.song_length` (grid).

HipHop invariants:

* A song is 12 692 bytes: 2-byte signature `0x0A08` + 702 bars × 8 tracks ×
  `uint16`, always followed by the **1 458-byte** bank block (all 17 files).
* `BARS = 702`, `TRACKS = 8`, `SONG_BYTES = 11234`, bar = 110 250 samples at
  44.1 kHz / 96 BPM.
* `mixfmt.Mix.build()` must reproduce the input bytes exactly, including the
  two constant 704-byte tables and the per-song head/pan words
  (`--verify --all` → 17/17).
* Sample ids: `BANK_BASE = 731` (`731..2071` → 1 341 `HIPHOP/EJAY/PXD`
  records, `id = 731 + index`); `1..101` → `SPECIAL` WAVs (`id = record
  index + 1`); `102..730` empty; no add-on boxes in this corpus.
* The 1 408-byte table region is identical in all 17 files and preserved
  verbatim; its meaning is unknown. The `head` word `X` is per-song and also
  unknown; do not reorder or normalise either.
* Pan is one word per track in the bank block: 0 centre, 1 left, 2 right
  (inferred). The track-count word is 8.

Dance 2 invariants:

* A song is a **variable-length sequence of sections**, 1 553 … 8 219 bytes in
  this corpus (56 604 bytes over 13 files), signature `0x0A19`. There is no
  702-bar grid and no bank block.
* Tempo is stored: header word `0x08` is 140 in all files, and a bar is 75 600
  samples at 44.1 kHz / 140 BPM, like Dance eJay 1.x.
* 16 track records of (pan, volume); pan is 0/1/2 and read as both/left/right
  by inference. The drum track is separate: a 28-byte pad prefix, ten pad
  records and the pattern block.
* Pad sample ids are **looked up in `DANCE20.INF`**, not computed: the 1 957
  records are ordered by file offset (ids `1..1957`, first record id 1512), so
  never use `base + index` here. `DANCESK4/5/6` supply ids in the Vol. 4–6
  boxes.
* `mixfmt.Mix.build()` must reproduce the input bytes exactly, including the
  28-byte pad prefix, the 20 unknown bytes of every event tail, the pattern
  block and the trailer `0x018A7AA9` (`--verify --all` → 13/13).
* The pattern block decodes: 22-byte preamble, 17 section headers, section `n`
  = track `n`, then 3 654 seven-byte **clips** (start bar
  `2·|block| − 1 + (255 − byte1)/128`) and 16 seventeen-byte **hits**
  (`position/32768 + 1`), interleaved and told apart by the `0xFFFF` word at
  offset 3; see `mixfmt.decode_pattern`. Keep the bytes verbatim. A clip's
  `byte0` and a hit's ten trailing bytes are still unknown. `mixplayer.py`
  cuts a clip where the next record on its track starts and never loops or
  stretches it; do not invent looping or stretching for this tree.

Techno eJay 2 invariants:

* A song is a **variable-length sequence of sections**, 2 144 … 6 236 bytes in
  this corpus (52 369 bytes over 13 files), signature `0x0889`.  There is no
  702-bar grid and no bank block.
* Tempo is stored: header word `0x08` is 140 in all files, and a bar is 75 600
  samples at 44.1 kHz / 140 BPM.
* 16 track records of (pan, volume); pan 0/1/2 read as both/left/right, and one
  word in the corpus is 3 (`SOAP.MIX` T16, unknown — the player treats it as
  both).  The six trailer words end in track count 14 (`BUBBLE`, `STRAIGHT`)
  or 16.  The sample set is `Techno eJay 2 ` or `Techno eJay `.
* Sample ids are **looked up in `EJAY/PXD/RAVE20.INF`**, never computed: 4 015
  contiguous ids `13 000 … 17 014`, records ordered by file offset.  The seven
  kit boxes declare `2 000 … 7 199` and no song uses those ids.
* The ten pads all have sample id 0 and free-text names; they are not audio
  references.  No song has imported-sample events.
* The pattern block decodes: 22-byte preamble (first 18 bytes constant, word 9
  = `len(pattern) − 18`), 17 section headers, then 7-byte **clips** and
  17-byte **hits** (`0xFFFF` at offset 3 selects a clip).  Section `n` is track
  `n`; 4 562 clips and 522 hits in the corpus.  Keep the bytes verbatim.  A
  clip's `byte0` is 0 here and a hit's ten trailing bytes are unknown.
* `mixfmt.Mix.build()` must reproduce every input byte (`--verify --all` →
  13/13), including the pad prefix, the pattern block and the trailer
  `0x018A7AA9`.  `mixplayer.py` cuts a record at the next record on its track.

## Packaging and binaries

Two players and the renderer are packaged:

| Binary | Entry point | Output |
|---|---|---|
| `emp-cli` | `apps/emp/src/mixplayer.py` | `dist/emp-cli/emp-cli.exe` |
| `emp-tui` | `apps/emp/src/mixtui.py` | `dist/emp-tui/emp-tui.exe` |
| `emr-cli` | `apps/emr/src/mixrender.py` | `dist/emr-cli/emr-cli.exe` |

`apps/emp/packaging/build_emp_cli.py`,
`apps/emp/packaging/build_emp_tui.py`
and `apps/emr/packaging/build_emr_cli.py` build the one-dir PyInstaller
bundles; each has its spec and release script beside it, and the build and
upload code is shared:

```bash
python -m pip install pyinstaller numpy sounddevice textual
python apps/emp/packaging/build_emp_cli.py --clean
python apps/emp/packaging/build_emp_tui.py --clean
python apps/emr/packaging/build_emr_cli.py --clean
dist/emp-cli/emp-cli.exe disks/Dance_eJay/MIX/START.MIX --from 82 --bars 8 --wav out.wav
dist/emp-tui/emp-tui.exe disks/Dance_eJay/MIX/START.MIX
dist/emr-cli/emr-cli.exe --all --out out/images
```

Each bundle is its executable plus an `_internal/` folder; zip the whole
folder to move it. eJay data is not embedded (2.6 GB in this checkout). The
binaries read `disks/` from `EJAY_DATA_ROOT` or from the nearest folder above
the executable that contains a `disks` directory, so a bundle built inside the
repository finds this checkout and a distributed copy needs its own `disks/`
beside it. `apps/emp/src/paths.py` implements that lookup for source runs and frozen
builds alike, and the render providers call it too. `sounddevice` and its
PortAudio DLL are bundled when the package is installed at build time; `--wav`
works without them. The TUI bundle also carries `textual` and its CSS and
metadata. `emr-cli` needs neither: it bundles no third-party package (the
renderer and the parsers it imports are standard-library only) and is 23 MB on
Windows x64.

The `release_*.py` script beside each build wrapper zips a bundle and publishes
it as a GitHub release with `gh` (authenticate once with `gh auth login`):

```bash
python apps/emp/packaging/release_emp_cli.py --tag emp-cli-v0.1.0
python apps/emp/packaging/release_emp_tui.py --tag emp-tui-v0.1.0 --dry-run
python apps/emr/packaging/release_emr_cli.py --tag emr-cli-v0.1.0 --dry-run
```

The archives are `dist/emp-cli-<version>-<os>-<arch>.zip`,
`dist/emp-tui-<version>-<os>-<arch>.zip` and
`dist/emr-cli-<version>-<os>-<arch>.zip`, where `<version>` is `VERSION` in
that target's CLI module (`apps/emp/src/core/cli.py` for the two players,
`apps/emr/src/render/cli.py` for the renderer; the Windows x64 archives are
23 MB, 34 MB and 10 MB). The scripts ask for confirmation, tag the release at
the current commit and put the archive's SHA-256 in the notes; `--draft`,
`--prerelease`, `--notes-file`
and `--replace` cover the usual variations. The shared build, zip and upload
code lives in `apps/emp/packaging/empbundle.py`.

`.github/workflows/release.yml` runs those same scripts on a `windows-latest`
runner when a `v*` tag is pushed, or when it is dispatched with a version. It
builds all three bundles once, smoke-tests the executables with `--version`,
then publishes `emp-cli-<tag>`, `emp-tui-<tag>` and `emr-cli-<tag>` releases
with the zips attached, using the workflow's `GITHUB_TOKEN`. Re-running a tag
refreshes the archive on the existing release instead of failing.

## Where to change things

* The shared contracts: `libs/mix/contracts.py` (`GridMix`,
  `SectionMix`, `MixDocument`, `BankBlockDocument`, `SampleCatalog`) and
  `apps/emp/src/format/ports.py` (`FormatAdapter`, `SampleSource`, `Reporter`,
  `AudioSink`, `LiveOutput`).  Each `Mix`, `BankBlock` and `Catalog` subclasses
  the format contract; each adapter subclasses `FormatAdapter`.  Do not put a
  format name, signature or id rule in either module.
* Parsing, writing, ids, labels: `libs/mix/<tree>/mixfmt.py` (`Mix`,
  `BankBlock`, `Catalog`).  HipHop's `BankBlock` also carries `tables`,
  `head`, `track_count` and `pan`.  Dance 2's and Techno's `Mix` carry
  `pad_prefix`, `pads`, `pattern` (raw bytes) and `events`; their `Catalog`
  reads `DANCE20.INF` and `RAVE20.INF` respectively.
* Dance 2 and Techno `.PXD` bundles: `libs/pxd/bundle.py` (`Bundle`,
  `read_index`); their `.INF` indexes are read, not regenerated.  `Bundle`
  carries a `truncate_default` switch and the player goes through `banks.py`,
  which truncates at the declared sample count.  Rave's decode path passes
  `allow_headerless=True` for `R1DA084.PXD`; no other tree accepts a headerless
  stream.
* Dump/JSON/verify behaviour: `reverse/<tree>/mixdump.py`. PNG output: `apps/emr/src/render/`
  (canvas, layouts, sample probes, CLI, registry); each
  `apps/emr/src/format/<tree>/mixrender.py` supplies only its catalogue, bar
  length and default output.  `apps/emr/src/mixrender.py` is the unified entry
  point.
* Audio decode: `libs/pxd/codec.py`, with `libs/pxd/cli.py`
  as its command line (`python libs/pxd`); mixing, gain, peak and
  playback:
  `apps/emp/src/core/` (`mixer`, `peak`, `sinks`, `session`). Per-format
  loading, pan rule, timing, peak strategy and wording:
  `apps/emp/src/format/<tree>/adapter.py`. Transport state machine, pause/resume, seek and
  runtime gain: `Transport` in `apps/emp/src/core/session.py`.
  Unified entry point: `apps/emp/src/mixplayer.py` with `--format <tree>`.  Unified
  renderer: `apps/emr/src/mixrender.py`; `apps/emr/src/format/<tree>/mixrender.py` is the
  same kind of fixed-format wrapper, and `apps/emr/src/render/registry.py` is the
  render composition root.  TUI:
  `apps/emp/src/mixtui.py` on the same `PlayerApplication` and `RecordingReporter`;
  `apps/emp/src/formats.py` is the adapter registry both frontends share.
* When a mapping or count changes, update the numbers **and** prose in the
  root `README.md` and in that tree's `README.md`, `SAMPLES.md`, `FORMAT.md`
  and `MIXES.md` in the same commit. The docs quote exact totals; stale
  numbers are bugs.

## Style

* Match the existing code: 4-space indent, `from __future__ import annotations`,
  type hints on public functions, a one-line docstring minimum, `argparse`
  CLIs with `main()` returning an exit status.
* Docstrings and docs use measured language: state what was verified, label
  unknowns as unknown (see `METHOD.md`), avoid speculation.
* Keep diffs minimal and scoped; no unrelated reformatting of data, docs or
  generated artifacts.
* Do not commit `__pycache__/`, `out/`, or throwaway WAV/PNG output.
