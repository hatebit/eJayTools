# Adding a format tree

This is the procedure for adding a sixth eJay format to `libs/mix/` and
`apps/emp/src/format/`.  It assumes
the two shared layers described below and the repository rules in `AGENTS.md`:
the trees are independent, `mixfmt.py` stays standard-library only, and a
format is finished only when `mixdump.py --verify --all` reproduces every
shipped file byte for byte.

## 1. The design the five trees share

The five formats are not one implementation with switches.  They are five
independent libraries that expose the same **contract**.  Two families exist,
and the difference is in the file shape, not in the player.

| | grid family | section family |
|---|---|---|
| trees | `dance`, `rave`, `hiphop` | `dance2`, `techno` |
| song shape | fixed `BARS x TRACKS` grid, one `uint16` per slot | variable sequence of sections |
| song length | 11 234 bytes (HipHop adds a bank block) | 1 553 … 8 219 bytes, no grid |
| placement source | `Mix.events()` yields `(bar, track, sample_id)` | `Mix.pattern_sections()` yields clips and hits with a start bar |
| sample lookup | catalogue lists (`Catalog`, `Catalogs`) | `.INF` index (`Catalog`, `banks.py`) |
| extra block | `BankBlock` appended after the grid | pad prefix, pattern block, trailer inside the song |
| bar origin | 0 (the first bar is bar 0) | 1 (the first bar is bar 1) |
| peak strategy | `bar_peak_grid` | `bar_peak_sections` (Dance 2) or `rendered_peak` (Techno) |
| cut rule | the sample plays in full | a record is cut where the next record on its track starts |

Everything else is common:

```
libs/mix/<tree>/
  __init__.py
  mixfmt.py       the format library: parse/build, catalogues, ids, labels

apps/emp/src/format/<tree>/
  __init__.py
  banks.py        .INF bundle lookup (section family only)
  adapter.py      FormatAdapter: signature, timing, pan, peak, wording

apps/emr/src/format/<tree>/
  mixrender.py    PNG arrangement renderer (optional)

reverse/<tree>/
  README.md FORMAT.md METHOD.md SAMPLES.md MIXES.md [PXD.md]
  mixdump.py      dump, JSON export, byte-exact round-trip check
  decoded/ images/            generated, never hand-edited
```

The shared contracts are deliberately small:

```
libs/mix/contracts.py       MixDocument, GridMix, SectionMix,
                             BankBlockDocument, SampleCatalog
apps/emp/src/format/ports.py FormatAdapter, SampleSource, Reporter,
                             AudioSink, LiveOutput, LoadOptions
```

`libs/mix/contracts.py` is standard-library only and format-neutral, so
`mixfmt.py` can inherit from it without importing numpy or the player.
`apps/emp/src/format/ports.py` is the player-facing contract; its implementation
lives in `apps/emp/src/core/`, which never names a tree and never branches on
`format_id`.  `apps/emp/src/formats.py` is the only file that names all five adapters.

`python apps/emp/src/check_contracts.py` verifies the contract for every tree.
It prints `5/5 trees implement the shared contracts` and exits 0.

## 2. Pick the family before writing code

Read a few files under `disks/<tree>/MIX` and answer:

1. Is the song a fixed grid with a signature at offset 0 and a fixed byte
   length, or a variable header plus sections?  Grid → `GridMix`; sections →
   `SectionMix`.
2. Is the tempo stored, or derived from the sample metadata?  Store the answer
   as a module constant and use it in the adapter; do not add a core enum.
3. Are sample ids computed from a catalogue order, or looked up in an `.INF`
   index?  Write the rule down in `SAMPLES.md` before writing the adapter.
4. Is pan stored per track, or fixed by track number?  The adapter converts
   pan to `left`/`right` gains; the mixer never sees a pan word.
5. Does the format store a clip length?  If not, the adapter applies the cut
   rule and writes `Placement.stop`; the mixer never cuts or loops.

If a new format needs a change to `mix_placements` or `Placement`, stop: that
means the normalized model is incomplete, not that the adapter should special
case the engine.

## 3. Write the format library (`mixfmt.py`)

Start from the family contract and keep the module standard-library only.

```python
from __future__ import annotations

import os
import struct
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from libs.mix.contracts import GridMix, SampleCatalog  # noqa: E402

SIGNATURE = 0
x....  # the signature word, checked by the adapter
TRACKS = 8
BARS = 702
BPM = 140
BEATS_PER_BAR = 4


@dataclass
class Mix(GridMix):
    ...

    @property
    def song_length(self) -> int: ...

    def duration(self) -> float: ...

    def used_samples(self) -> list[int]: ...

    def track_usage(self) -> list[tuple[int, int]]: ...

    def events(self): ...

    @classmethod
    def parse(cls, data: bytes) -> "Mix": ...

    def build(self) -> bytes: ...


class Catalog(SampleCatalog):
    def record_for(self, sample_id): ...


def read_mix(path) -> Mix: ...


def write_mix(mix: Mix, path) -> None: ...
```

For a section format, subclass `SectionMix` instead and implement
`left_tracks`, `right_tracks` (properties), `bar_seconds()` and
`pattern_sections()`.  If the song carries a bank block, subclass
`BankBlockDocument` for its `parse`/`build`.

Rules that the ABCs cannot enforce:

* `parse` accepts one complete file image; `build` reproduces it exactly,
  including every unknown byte, trailer, table and pad prefix.  Keep raw bytes
  for fields whose meaning is unknown; do not normalise them.
* `read_mix`/`write_mix` stay module-level convenience functions.
* Keep `SIGNATURE`, `TRACKS`, the bar length and the tempo constants in the
  tree; the adapter imports them from here.
* Do not import another tree, and do not import `apps.emp.src.core` from `mixfmt.py`.
* Keep the two families' semantics: `song_length` is a property on the grid
  family; `pattern_sections` returns `None` when the block does not decode.
* Never invent looping or stretching for a format that stores none.

Prove the library before touching the player:

```bash
python reverse/<tree>/mixdump.py --verify --all          # must print N/N
```

## 4. Add the tools

* `mixdump.py`: standard-library only, same three modes as the existing trees
  (`--json`, `--verify`, `--all`, plus `--pattern` for the section family).
* `.PXD` decoding needs no per-tree file: call `libs/pxd/` directly.
  Pass `allow_headerless=True` only if the tree really ships a headerless
  stream (Rave does; nobody else does).
* `banks.py`: only for a section tree whose samples live in `.INF` bundles.
  Move nothing into the shared core until two trees are proven identical; the
  two existing copies are kept separate on purpose.
* `mixrender.py`: optional, and it lives in
  `apps/emr/src/format/<tree>/mixrender.py`.  Add it when the tree has an
  arrangement grid or decoded pattern that is useful to look at.  It supplies a
  `RenderFormat` (signature, `MIX` directory, default output and a
  `layout(path)` function) from `apps/emr/src/render/`; the drawing, PNG writer
  and CLI are shared by all trees.

## 5. Write the adapter (`adapter.py`)

The adapter is the only place that knows format facts.  Subclass
`FormatAdapter`:

```python
from apps.emp.src.format.ports import FormatAdapter, LoadOptions, Reporter


class MyAdapter(FormatAdapter):
    format_id = 'myformat'
    display_name = 'My eJay 1.x'
    mix_dir = MIXDIR
    track_count = TRACKS
    supports_catalog = True
    bar_origin = 0
    default_start_bar = 0
    description = 'play a My eJay .MIX through sounddevice'
    from_help = None
    catalog_help = 'add a catalogue list, its sample directory and first id'

    def matches(self, path: str, head: bytes, size: int) -> bool:
        return len(head) >= 2 and struct.unpack('<H', head[:2])[0] == mixfmt.SIGNATURE

    def resolve(self, name: str) -> str | None:
        ...

    def load(self, path: str, options: LoadOptions,
             reporter: Reporter) -> LoadedSong:
        ...
```

`load` does all format work before the mixer sees anything:

1. read the mix with `mixfmt.read_mix`;
2. filter tracks with `options.solo`/`options.mute`;
3. build a `FileSampleSource` (catalogue trees) or `BundleSampleSource`
   (section trees) and decode only the ids that are needed;
4. apply the pan rule and, for section trees, the cut rule; write `Placement`
   objects with absolute `onset`/`stop` in samples, the 0-based `track` and the
   catalogue `label` used by the TUI;
5. compute `bars`, `arrangement_bars`, `tail_bars` and the peak with the
   family's peak function;
6. resolve the gain (`options.gain` or `auto_gain(peak)`);
7. return `LoadedSong` with `detail` and already-worded `notes`.

Do not reorder placements: the float32 sums depend on insertion order, and
reordering can change WAV bytes at rounding boundaries.

## 6. Wire the frontends

* Register the adapter in `apps/emp/src/formats.py`; that is the only place that
  names all five adapters.  If the tree has a renderer, add its `RenderFormat`
  to `apps/emr/src/render/registry.py`, which is the only renderer file naming all
  five providers.  Add the new package and its family to `TREES` in
  `apps/emp/src/check_contracts.py` so the structural check covers it.
* Do not add a per-format branch to `apps.emp.src.core`; add a generic helper or a
  port instead.

## 7. Document and check

Update these in the same change:

* the new tree's `README.md`, `FORMAT.md`, `METHOD.md`, `SAMPLES.md`,
  `MIXES.md` (and `PXD.md` if it has a decoder);
* the root `README.md` layout and quick start;
* `AGENTS.md`: layout, invariants, the checks block and the `--verify` count;
* `apps/emp/src/formats.py` and the root layout if the tree adds a new sample shape.

Then run:

```bash
python reverse/<tree>/mixdump.py --verify --all           # N/N
python reverse/<tree>/mixdump.py --json reverse/<tree>/decoded --all
python apps/emp/src/mixplayer.py --format <id> START.MIX --from 1 --bars 8 --wav out.wav
python apps/emr/src/format/<tree>/mixrender.py --out reverse/<tree>/images --all
python apps/emr/src/mixrender.py --format <id> --all --out out/images
python apps/emp/src/check_contracts.py                        # 6/6 after registration
python apps/emp/src/mixplayer.py START.MIX                     # lists N candidates
```

Run the three cross-tree import audits from `AGENTS.md` and confirm that
`apps/emp/src/core/` still contains no `format_id == ...` branch.

## 8. Common mistakes

* **A round-trip that is "close enough".**  It is a regression.  If `build`
  cannot reproduce an unknown field, keep the original bytes; do not drop the
  field.
* **A prettier label.**  Labels come from the catalogue verbatim, including
  odd names.  Do not invent display names.
* **Sorting placements.**  Insertion order is part of the audio output.
* **Using `break` on an unsorted placement list.**  Section placements are not
  onset-sorted; the mixer must `continue`.
* **A changed peak or gain.**  Peak is format behaviour; changing the strategy
  changes the automatic gain and therefore every rendered WAV.
* **A new shared helper with format names.**  If it needs `if format_id ==`,
  it belongs in the adapter, not in the core.
* **Editing `decoded/` or `images/`.**  They are generated; regenerate them.
