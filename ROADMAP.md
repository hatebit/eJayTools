# ROADMAP

Planned direction for eJayTools. The repository's value is the documentation and
the byte-exact writer; every item below must preserve that and stay honest about
what is verified versus unknown. Items are ordered by priority, not by date.

## Guiding constraints

* **Build on the normalized model.** Exporters read `LoadedSong`
  (`apps/emp/src/core/model.py`): `placements` (`onset`, `stop`, `audio`, `left`,
  `right`, `track`, `label`), `bar_samples`, `sample_rate`, `tracks`, `gain`.
  Never branch on `format_id` in the core (the CI import audit enforces this).
* **Five trees stay independent.** A new exporter is a sibling of the player, not
  a cross-tree import.

## Now

### 1. MP3 export
- [ ] `mixplayer.py … --format mp3 out.mp3` (and TUI *Export*) writes an MP3 of
  the same selection.
- **Approach:** add `Mp3Sink(AudioSink)` in `apps/emp/src/core/sinks.py`, mirroring
  `WavSink`. `RenderJob` already takes a `sink_factory`, so MP3 versus WAV is
  only the factory. Encode through an optional backend: primary `soundfile`
  (libsndfile ≥ 1.1 can write MP3), fallback to an `ffmpeg`/`lame` subprocess.
  Add an optional group `mp3` in `pyproject.toml`; import lazily and fail with a
  clear message when it is missing (the `TEXTUAL_ERROR` pattern).
- **Open:** MP3 is lossy and has encoder delay, so byte-identical does not apply.
  Acceptance is duration match and a stated round-trip tolerance, not equality.
- **Acceptance:** `--wav` output is unchanged (byte-identical regression check);
  `--format mp3` decodes back to the same duration; `--wav` keeps working with no
  optional dependency installed.

### 2. DAWproject export (`.dawproject`)
- [ ] Export any `.MIX` to a `.dawproject` file that opens in Bitwig Studio,
  Studio One and Cubase.
- **Format (verified against `bitwig/dawproject` v1.0):** a `.dawproject` file is
  a ZIP containing `project.xml` (and optional `metadata.xml`) plus the audio
  files it references; XML is UTF-8 and the schema is `Project.xsd`. `Transport`
  carries tempo and time signature; `Structure` holds tracks and channels;
  `Arrangement` holds lanes of clips, each clip referencing an `<Audio><File>`.
- **Approach:** a new standard-library-only package `libs/dawproject/`
  (`zipfile` + `xml.etree.ElementTree`), mapping from `LoadedSong` only:
  - `<Transport>`: `Tempo` from the tree (Dance / Dance 2 / Techno 140, Rave 180,
    HipHop 96 — the adapters already know these) and `TimeSignature` 4/4.
  - `<Structure>`: one `<Track contentType="audio">` + `<Channel>` per
    `LoadedSong.tracks` (8 or 16), pan from the adapter's rule (eJay 0/1/2 →
    0.5/0/1 normalized) and volume; one `<Track role="master">`.
  - `<Arrangement>`: `<Lanes timeUnit="beats">`, one `<Clip>` per `Placement` at
    `time = onset / (bar_samples / 4)` and
    `duration = (stop − onset) / (bar_samples / 4)`; `playStart = 0`, and **no**
    `loopStart`/`loopEnd`, because the player never loops or stretches a clip.
  - Audio: decode each distinct sample once with `libs.pxd` (`decode` /
    `decode_file`) and write mono 16-bit WAV into `audio/` via the existing
    `write_wav`; reference each by relative path.
- **CLI:** `mixplayer.py … --dawproject out.dawproject` plus `--all` for a folder;
  optionally a dedicated `apps/emp/src/mixexport.py`.
- **Open:** one audio file per sample with clip references (recommended, smaller)
  versus one file per clip; bake per-placement `left`/`right` gain into clip gain
  or use the channel pan (recommended: channel pan, clip gain 1.0, matching
  eJay's one-pan-per-track model).
- **Acceptance:** `unzip -l` lists `project.xml`, `metadata.xml` and
  `audio/*.wav`; `project.xml` validates against `Project.xsd`; the file opens in
  Bitwig; a standard-library unit test builds a synthetic `LoadedSong` (no
  `disks/`) and round-trips the XML through `ElementTree`, so it runs in `ci.yml`.

### 3. Stems export
- [ ] `mixplayer.py … --stems DIR` writes one dry WAV per track.
- **Approach:** group `LoadedSong.placements` by `track` and render each group
  with `mix_placements`, reusing `RenderJob`. No new dependency.
- **Acceptance:** the sum of the stems equals the `--wav` master within the gain
  factor; standard-library only.

### 4. Automated tests, lint and types
- [ ] Make "byte-exact and provably so" enforced automatically, not by hand.
- **Approach:** a `tests/` tree with (a) standard-library unit tests for
  `libs/mix` build/read against tiny committed fixtures (one truncated `.MIX` per
  family and one small `.PXD`), (b) a synthetic-`LoadedSong` test for the
  DAWproject writer and the stems exporter, (c) the cross-tree import audit as a
  test. Add `[tool.pytest]`, `[tool.ruff]` and `[tool.mypy]` to `pyproject.toml`
  and run them in `ci.yml`. Add `.gitattributes` (`* text=auto`,
  `*.MIX`/`*.PXD`/`*.WAV`/`*.PNG` binary) and `.editorconfig`.
- **Acceptance:** `ci.yml` runs pytest, ruff and mypy; the data-dependent
  `--verify --all` stays documented as a local-only check.

## Next

### 5. MP3 / OGG / FLAC sample import
- [ ] Use an MP3/OGG/FLAC file as a custom sample through a new `SampleSource`.
- **Approach:** extend `apps/emp/src/core/sources.py` (`read_wav` → `read_audio`)
  with a lazy `soundfile` backend; keep the standard-library path for WAV. Decide
  the id namespace for imported samples first: eJay's id space is fixed
  (`BANK_BASE`…), so imported audio needs a separate namespace or a sidecar.
- **Acceptance:** an imported loop decodes to mono float32 and can be placed like
  any other sample.

### 6. FLAC / OGG export
- [ ] `--format flac|ogg` beside WAV and MP3.
- **Approach:** the same sink abstraction as MP3; `soundfile` covers all three.

### 7. Resolve the documented unknowns
- [ ] Close the open questions recorded in each `reverse/<tree>/METHOD.md`
  (for example the Dance `head` word, the HipHop table and `head` word, Rave ids
  1…15, and the eJay 2 22-byte preamble's first 18 bytes, a clip's `byte0` and a
  hit's ten trailing bytes).
- **Approach:** controlled render comparisons with the existing player and
  `mixrender.py` to infer meaning; record evidence only, never guesses.
- **Acceptance:** each resolved item moves from "unknown" to "verified" with a
  reproducible check; anything unresolved stays labelled unknown.

### 8. Batch conversion
- [ ] Convert a whole `disks/<tree>/MIX/` folder to `.dawproject` / `.wav` /
  `.mp3` in one command.
- **Approach:** `--all` on the export CLI, reusing the registry; parallel where
  safe.

## Later

### 9. A sixth format tree
- [ ] Apply `reverse/ADDING_A_FORMAT.md` to another eJay title, keeping the five
  trees independent and the cross-tree import audit green.

### 10. Sample cache and streaming
- [ ] Cache decoded samples across placements and exports (DAWproject and stems
  decode each sample once) and stream large banks instead of loading whole files.

### 11. Waveform, spectrogram and HTML report
- [ ] A PNG waveform per song (reusing the `apps/emr` canvas) and a static HTML
  report per song, as companions to the existing arrangement renders.

### 12. Packaging beyond Windows
- [ ] Linux and macOS bundles (today only Windows x64), Homebrew and winget;
  keep `emr-cli` dependency-free.

## Non-goals

* **MIDI note export.** eJay songs are sample placements, not note data: the 1.x
  grids and the eJay 2 pattern block reference samples, not pitches. A faithful
  MIDI export is not possible from the format; a drum-map reduction would be
  lossy and speculative, so it is out of scope.
* **A native `.MIX` editor.** The repository documents and re-encodes; it is not
  aiming to become a DAW.
* **Bundling eJay data.** `disks/` stays gitignored and out of every artifact.

## Definition of done (cross-cutting)

Each item lands with the documentation updated (root plus the affected tree's
`README`/`FORMAT`, per the "where to change things" rule in `AGENTS.md`), the
matching check in `AGENTS.md` green, and no change to the `--verify --all` totals.