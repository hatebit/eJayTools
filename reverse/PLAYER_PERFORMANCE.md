# Placements, sample sharing and mixing performance

Design note for the shared player core (`apps/emp/src/core/`).  It records what the
current `LoadedSong` model does, how it is played, and what a bar-indexed mix
index could change.  It is not a format claim: no byte layout, sample id, label
or timing rule changes here.  Timings were measured on the development machine
on 2026-11-12 and are indicative, not a benchmark contract.

Read `AGENTS.md` first.  The invariants that constrain any change are:

* `mixfmt.Mix.build()` must stay byte-exact (`--verify --all`);
* the unified CLI and the per-tree wrappers must keep producing the same WAV;
* `apps/emp/src/core/` stays format-neutral: no tree name, signature or id rule.

## 1. Does a `LoadedSong` hold multiple placements for the same audio?

Yes.  A `LoadedSong` stores one `Placement` per arrangement occurrence, not one
per sample.  Repeats of the same sample id become separate `Placement` objects
that reference the same cached `audio` array.

Mechanism:

* occurrences with the same sample id are appended as separate placements by
  every adapter (`apps/emp/src/format/dance/adapter.py:130`, Rave, HipHop, Dance 2,
  Techno);
* audio comes from `SampleSource.audio()`, cached per sample id
  (`FileSampleSource._cache`, `apps/emp/src/core/sources.py:55-82`; `Banks.cache`,
  `apps/emp/src/format/dance2/banks.py:53` and `apps/emp/src/format/techno/banks.py`), so
  the second occurrence gets the same `numpy` array, no copy and no re-decode;
* the per-track `TrackInfo` fields `placed` and `distinct` are exactly this
  distinction: occurrences vs unique sample ids.

No sample data is duplicated:

* `audio()` returns `self._cache[sample_id]` with no `.copy()`;
* `Placement(audio=...)` stores that reference; `@dataclass(frozen=True)` only
  blocks attribute rebinding, it does not copy fields;
* the mixer slices `placement.audio[a:b]` (a view) and accumulates it, so
  rendering does not copy the sample buffer either (`apps/emp/src/core/mixer.py:26`).

Measured on `disks/Dance_eJay/MIX/START.MIX`:

```
placements                : 189
unique arrays             : 48
sum nbytes as occurrences : 142 430 112   (~136 MiB)
sum nbytes unique         :  42 638 308   (~41 MiB)
two placements share obj  : True
shares_memory between them: True
```

Consequences of sharing a pointer rather than copying:

* the array is writable; an in-place mutation would be visible to every
  placement of that sample and to the source cache (current code only reads it);
* each `Placement` keeps its **full** sample even when a section format cuts
  playback at `stop` (`apps/emp/src/core/model.py:16`: "full sample (not cut)");
* the arrays live as long as the `SampleSource`/`Banks` used during `load()`;
  the `LoadedSong` holds only the placement references.

## 2. How a `LoadedSong` is played

Playback never iterates the placements in order.  Every block asks the mixer for
a time window, and the mixer scans the whole flat list, filtering by
`onset`/`stop` (`apps/emp/src/core/mixer.py:21-37`).

**Live** (`apps/emp/src/core/session.py:282`, `apps/emp/src/core/sinks.py:51-67`):

1. `PlayerApplication.play(song, selection, loop)` builds a
   `Transport(song, selection, loop)`.
2. `SoundDeviceOutput.run(transport)` opens a stereo float32
   `sounddevice.OutputStream`; each callback calls `transport.fill(outdata)`.
3. `Transport.fill` (`session.py:103-131`) works in chunks:
   `mix_placements(self.song.placements, self.position, count)` →
   `apply_gain(block, self.song.gain * self.gain)` → copy into `outdata`.  It
   loops until the callback buffer is full, wraps to `start` when `loop` is on,
   otherwise zero-fills and finishes.  Pause writes zeros and keeps the
   position; `seek_bar` resets the position; `stop` marks the transport
   finished; per-bar progress events go through a `SimpleQueue`.

**Offline** (`session.py:329`, `RenderJob.run` at `session.py:221-232`): the same
`mix_placements` + `apply_gain`, one bar-sized block at a time, into `WavSink`
(16-bit stereo, clipped to ±32767).

Peak and gain estimation also loops over all placements
(`apps/emp/src/core/peak.py`), independently of order.

## 3. Are placements sorted?

| tree | sorted by onset? | why |
|---|---|---|
| Dance, Rave, HipHop | **yes** | the adapter builds `pending = [(bar * BAR_SAMPLES, sample_id, track), …]` then `pending.sort()`, i.e. lexical by (onset, sample id, track) |
| Dance 2, Techno | **no** | built in pattern-block order: section (track) order, then note order within each section |

Measured with the current adapters:

```
dance    placements= 189 sorted=True  first10=[0, 0, 75600, 151200, ...]
rave     placements= 221 sorted=True  first10=[0, 0, 0, 58800, 117600, ...]
hiphop   placements= 277 sorted=True  first10=[0, 0, 0, 110250, ...]
dance2   placements= 205 sorted=False first10=[1512000, 1663200, 1814400, ...]
techno   placements= 467 sorted=False first10=[3024000, 5140800, 5448000, ...]
```

The mixer documents this explicitly: "The loop never breaks early:
section-format placements are not sorted by onset" (`mixer.py:16-18`).  Each
rendered block therefore costs a full O(placements) scan in every format; no
binary search or interval index is used.  Correctness never depends on the
order.

## 4. Would sorting give a performance gain?

**Sorting alone buys almost nothing.**  What helps is not visiting placements
that cannot overlap the block.  Two different things are easy to conflate:

1. list order (sorted vs not) makes no difference to the mixer's cost: it scans
   everything either way;
2. an order/index that lets the mixer skip the prefix (placements that ended
   before the block) and the tail (placements that start after it) does.

A plain early break on `onset >= end` only skips the tail.  For a block late in
the song nearly every placement has `onset < end`, so little is skipped.  The
expensive part is the prefix, which needs a monotonic lower bound: sort by
onset, build `prefix_max_stop`, and `bisect_right(prefix_max_stop, start)` to
find the first placement that can still sound.  A per-bar span index is the
other shape (section 5).

Prototype results, full-song render, best of three runs, `float32` output
compared byte-for-byte with the current mixer:

| song | placements | block | current scan | sorted + early break | sorted + prefix-max-stop | per-bar span index |
|---|---|---|---|---|---|---|
| Dance START (90 bars) | 189 | 1 bar | 137 ms | 117 ms | 126 ms | 120 ms |
| Dance START | 189 | 512 | 1286 ms | 1201 ms | **724 ms** (1.8×) | 747 ms (1.7×) |
| HipHop START (429 bars) | 277 | 1 bar | 456 ms | 435 ms | **304 ms** (1.5×) | 457 ms |
| HipHop START | 277 | 512 | 9175 ms | 8738 ms | **1828 ms** (5.0×) | 1723 ms (5.3×) |
| Dance 2 OTHER (90 bars) | 205 | 1 bar | 112 ms | 123 ms | 105 ms | **100 ms** |
| Dance 2 OTHER | 205 | 512 | 1191 ms | 1052 ms | 743 ms (1.6×) | **682 ms** (1.7×) |
| Techno START (134 bars) | 467 | 1 bar | 155 ms | 174 ms | 166 ms | 166 ms |
| Techno START | 467 | 512 | 2707 ms | 2626 ms | **1140 ms** (2.4×) | 1129 ms (2.4×) |

Interpretation:

* at the real `render_wav` block size (one bar), per-block NumPy work dominates;
  even eliminating the scan gives only 1.1–1.5×;
* at small blocks (512 frames, the live-callback regime) the scan repeats tens
  of thousands of times, so skipping it gives 2–5×;
* live playback does **not** need this speed: 277 placement checks per 512-frame
  callback is roughly 80 µs against an 11.6 ms budget.  The gain is CPU and
  battery, not feasibility;
* `bar_peak_grid` and `bar_peak_sections` already bucket by bar and do not
  benefit.  Techno's `rendered_peak` calls the mixer per bar, so it inherits the
  same modest gain.

## 5. A map indexed by bar

A bar-indexed map is the natural shape for this player: selection is in bars,
`render_wav` emits one bar per block, progress events are per bar, and peak
estimation is per bar.  It is also the "span index" that measured best.

### 5.1 Shape

```python
# apps/emp/src/core/model.py
@dataclass
class LoadedSong:
    ...
    placements: list[Placement]              # canonical, flat, in load order
    by_bar: list[list[Placement]] = field(init=False)

    def __post_init__(self) -> None:
        self.by_bar = [[] for _ in range(self.bars)]
        for p in self.placements:
            for bar in range(p.onset // self.bar_samples,
                             (p.stop - 1) // self.bar_samples + 1):
                self.by_bar[bar].append(p)
```

* **Dense `list`, not `dict`.**  Bar indices are `0 .. bars-1` (internal 0-based,
  unrelated to `bar_origin = 1` for section formats), `bars` is known once the
  placements exist, and list indexing is cheaper and smaller than dict hashing.
  Empty bars are just `[]`.
* **Register under every bar the placement sounds in**, `[onset, stop)`, not
  only its onset bar.  Samples ring into later bars; see section 6.
* **Keep `placements` as the canonical flat list.**  The map is derived.
  Consumers that need each placement once — track statistics (`placed`,
  `distinct`), `cli.py:198`, `mixtui.py:205,380`, peak accumulation — keep using
  it.  A placement spanning *k* bars is referenced *k* times in the map, so
  iterating the map alone would double-count it.
* **Same `Placement` objects and the same `audio` array in every bucket.**  The
  map adds references, not sample data.

Building the map in `LoadedSong.__post_init__` keeps it format-neutral and
avoids touching all five adapters.

### 5.2 Query: split at bar boundaries, do not dedupe

```python
def mix_bars(by_bar, bar_samples, start, frames):
    out = np.zeros((frames, 2), dtype=np.float32)
    pos = start
    while pos < start + frames:
        bar = pos // bar_samples
        seg_end = min(start + frames, (bar + 1) * bar_samples)
        for p in by_bar[bar]:
            ...  # same filter/slice as today, written at pos - start
        pos = seg_end
    return out
```

Splitting avoids the one real correctness trap: a placement that spans a bar
boundary lives in two buckets, so a single multi-bar lookup that concatenated
buckets would mix it twice.  It also makes each lookup O(1); a 512-frame
callback crosses a bar boundary only once every ~110–215 blocks.

Splitting preserves exactness **by construction**: each output sample belongs to
exactly one bar segment, and each bucket was built in the original placement
order, so contributions to that sample are added in the same relative order as
today.  This does not rely on the fact that the current quantized `float32` sums
happen to be exact.  Verified: whole-song renders were bit-identical for all
four songs tested.

### 5.3 Measured with a `list[list[Placement]]`

Full-song render, best of three, map built in placement order, blocks split at
bar boundaries:

| song | block | current scan | bar map | speed-up | identical |
|---|---|---|---|---|---|
| Dance START (N=189) | 1 bar | 137 ms | 120 ms | 1.1× | yes |
| Dance START | 512 | 1286 ms | 794 ms | 1.6× | yes |
| HipHop START (N=277) | 1 bar | 456 ms | 353 ms | 1.3× | yes |
| HipHop START | 512 | 9175 ms | 1833 ms | 5.0× | yes |
| Dance 2 OTHER (N=205) | 1 bar | 112 ms | 87 ms | 1.3× | yes |
| Dance 2 OTHER | 512 | 1191 ms | 631 ms | 1.9× | yes |
| Techno START (N=467) | 1 bar | 155 ms | 150 ms | 1.0× | yes |
| Techno START | 512 | 2707 ms | 1085 ms | 2.5× | yes |

The pattern is consistent: a 1.1–1.3× win at the real `render_wav` block size,
and 1.6–5× at small streaming blocks.

### 5.4 Corpus cost

All 48 Dance/Rave/HipHop mixes plus five each of Dance 2 and Techno:

| tree | placements | map references | ratio | longest span |
|---|---|---|---|---|
| Dance | 2 689 | 6 186 | 2.30× | 25 bars (`WELCOME.MIX`) |
| Rave | 4 852 | 12 912 | 2.66× | 16 bars |
| HipHop | 5 488 | 8 282 | 1.51× | 6 bars |
| Dance 2 (5 files) | 1 376 | 3 405 | 2.47× | 8 bars |
| Techno (5 files) | 2 423 | 5 072 | 2.09× | 16 bars |
| **All sampled** | **16 828** | **35 857** | **2.13×** | 25 bars |

The index is about 36 k list slots plus a few thousand list objects in the
sampled corpus: a few hundred kB to ~1 MB, against tens of MB of shared sample
audio.  Building it is ~36 k appends, under a millisecond per song.

## 6. Correctness constraints and traps

1. **Onset-only bucketing is wrong.**  Samples ring past their starting bar, so
   a placement must be indexed for every bar in `[onset, stop)`.  A deliberately
   naive onset-bar bucket missed ring-outs and differed from the current output
   by up to 0.83 in amplitude.
2. **Reordering changes `float32` summation in principle.**  It happens to be
   bit-identical here because decoded samples are exact multiples of 2⁻¹⁵ and
   partial sums stay far below 512, so the sums are exact.  That is a property
   of the current data and gains, not a guarantee; fractional pan or gain would
   break it.  The bar-split construction keeps the original order per output
   sample and is identical by construction.
3. **Multi-bar blocks need splitting or dedupe.**  Do not concatenate adjacent
   buckets for one lookup.
4. **Empty songs and empty bars.**  Guard `bars == 0`; `by_bar` is then empty.
   The existing `if not song.placements` checks still work.
5. **`bar_origin` is user numbering.**  The map uses internal 0-based
   `onset // bar_samples`, so the section formats' `bar_origin = 1` does not
   enter the index.
6. **Any change must keep the WAV byte-identical** and pass the wrapper vs
   unified comparison.  The mixer's "never breaks early" docstring must be
   removed with the change.

## 7. Impact on the rest of the core

* `mixer.py`: `mix_placements(placements, start, frames)` becomes the map query;
  `Mixer.mix` and the two call sites (`session.py:125`, `session.py:228`) pass
  `song.by_bar`.
* `peak.py`: `bar_peak_grid`/`bar_peak_sections` can keep consuming the flat
  list; they are one-time and already roughly O(N + bars).  Techno's
  `rendered_peak` goes through the mixer and inherits the speed-up.  If one code
  path is preferred, the peak functions can consume buckets and produce the same
  per-bar sum, because a *k*-bar placement contributes to the same *k* buckets
  the current range loop uses.
* `formats.py`/adapters: no change if the map is built in
  `LoadedSong.__post_init__`.
* `cli.py`, `mixtui.py`: keep using `song.placements` for truthiness and the
  per-track display index.
* `ports.py`: `PeakFunction` is not used by the current adapters, so its
  signature does not need to change unless the peak functions are moved to the
  map.

## 8. Recommendation

* Do not sort the section formats just for speed; a plain sort plus early break
  is close to noise at `render_wav` block sizes and changes accumulation order.
* If the mixer is changed, add the per-bar index in `LoadedSong.__post_init__`,
  keep the flat `placements` list, split lookups at bar boundaries, and verify
  whole-song renders are byte-identical for all five formats.
* Expected effect: 1.1–1.3× for `render_wav`, 1.6–5× for small streaming
  blocks; no change to real-time feasibility, ids, labels or file output.
* If live CPU becomes the target, the bar map is the enabling step for a small
  LRU of **pre-mixed bars** (pre-gain): one bar is `bar_samples × 2 × 4` bytes
  (~0.6 MB Dance/Rave/Dance 2/Techno, ~0.9 MB HipHop), and 8–16 bars is
  5–14 MB.  Full-song pre-render is 54–378 MB and is not viable.

## 9. Reproduction notes

The measurements above came from throwaway scripts outside the repository
(`bar_map.py`, `bench_mix.py`, `spans_subset.py` under the session temp
directory).  They:

1. load a mix through `apps.emp.src.formats.REGISTRY` with `LoadOptions()` and
   `NullReporter()`;
2. render the whole song in fixed-size blocks with
   `apps.emp.src.core.mixer.mix_placements`, then with each prototype;
3. compare the two `float32` arrays with `numpy.array_equal` (and report the
   maximum absolute difference when they differ);
4. take the best of three wall-clock runs.

If this work is pursued, the benchmark should become a checked-in script with
the same byte-equality assertion, so a future change cannot silently alter the
audio.
