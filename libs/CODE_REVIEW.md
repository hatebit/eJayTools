# Code review: `libs/`

## Scope and method

Everything under `libs/` was read in full:

| Package    | Files                                                                                      |
|------------|--------------------------------------------------------------------------------------------|
| `libs/mix` | `contracts.py`, `dance/`, `dance2/`, `hiphop/`, `rave/`, `techno/` (each with `mixfmt.py`) |
| `libs/pxd` | `codec.py`, `bundle.py`, `cli.py`, `__main__.py`, `check_equal.py`, `__init__.py`          |

This is a static read-through. **No code was executed, no tests were run, and no `.MIX` / `.PXD` files from `disks/`
were available**, so every claim about real-file behaviour below is derived from the code and its own docstrings. Where
a finding depends on corpus facts I could not check, it says so. Findings are referenced by function/class name rather
than line number so they survive edits.

## Overall assessment

The code is well documented and carefully structured. The format docstrings (layout tables, notes on what is still
unknown) are unusually good for reverse-engineered formats. The "parse to a model, build back to identical bytes" design
with verbatim preservation of unknown regions is sound. `contracts.py` is a clean, minimal statement of what a format
library is.

The main weaknesses are:

1. One real round-trip bug in the Dance 2 / Techno writer (F1).
2. A platform-dependent file lookup bug in the Dance and HipHop catalogues (F2).
3. Inconsistent input validation and error types across the five parsers (F3).
4. A heuristic where a deterministic parse seems available (F4).
5. Heavy copy-paste between trees, which has already produced drift (copy-pasted comments, diverging behaviour of "
   identical" functions).

---

## Findings

Severity: **High** = incorrect behaviour that breaks a stated guarantee; **Medium** = robustness / maintainability risk
likely to bite; **Low** = polish.

### High

#### F1. Empty event `number` does not round-trip (`dance2/mixfmt.py`, `techno/mixfmt.py`)

`Mix.parse` explicitly supports an event whose second string has length 0:

```python
mix.events.append(Event(name[:-2]..., number[:-2]... if n2 else '', tail))
```

and `_valid_record` accepts `n2 == 0` when scanning for the event list. But `Mix.build` writes every event string
through `_encode_name`, which always emits `uint16 len+2`, the text, `NUL`, `0x01`. An empty `number` therefore becomes
`02 00 00 01` (4 bytes) instead of the original `00 00` (2 bytes). The result is not byte-identical, which violates the
`MixDocument.build` contract ("must reproduce the parsed bytes exactly").

Whether any file in the corpus triggers this is unknown to me, but the parser's special-casing suggests the author saw
or anticipated it.

*Fix:* distinguish "absent" from "empty", for example `Event.number: str | None` with `None` meaning a zero-length
field, and have `build` emit `b'\x00\x00'` for `None`. Add a corpus-wide `build(parse(x)) == x` test (see "Testing").

#### F2. Sample file lookup is case-sensitive off Windows (`dance/mixfmt.py`, `hiphop/mixfmt.py`)

`Catalog.__init__` indexes disk files with `os.path.normcase(os.path.normpath(full))`, and `abs_path` looks up the same
way. On Windows `normcase` lowercases; on Linux/macOS it is a no-op, so the match is case-sensitive.

The catalogues store suffixless paths in lower case (the HipHop docstring itself cites `special\hxdrum01` for the file
`SPECIAL/HXDRUM01.WAV`), and `_read` rebuilds the name as `basename + '.WAV'`, so the lookup key is `…/hxdrum01.WAV`
against a real file `…/HXDRUM01.WAV`. On a case-sensitive filesystem this misses and `abs_path` returns `None`.

The Rave tree already does this correctly (`rel.replace('\\','/').lower()` as the key, `record.path.lower()` as the
lookup).

*Fix:* use the Rave approach in Dance and HipHop. Because the five `Catalog` classes are near-duplicates (F9), this is a
good argument for sharing the catalogue code.

### Medium

#### F3. Inconsistent validation and error types across parsers

- `dance` and `rave` `BankBlock.parse` do no bounds checks. Truncated input raises `struct.error`; HipHop's
  `BankBlock.parse` raises `ValueError` with a message. A caller that catches `ValueError` will miss `struct.error` from
  two of the five trees.
- `dance2` / `techno` `Mix.parse` mixes `ValueError` (explicit checks), `struct.error`, and `IndexError` (for example
  `data[pos] != 1` when `pos == len(data)`). `_cstring` surfaces `data.index` failures as a bare
  `ValueError: subsection not found`.
- Zero-length names in `dance` / `rave` v8 blocks: `flag = data[pos + length - 1]` with `length == 0` reads the byte
  *before* the name (the high byte of the length field) and silently produces a wrong flag. HipHop guards this (
  `raw[-1] if length else 1`); Dance and Rave do not.
- `dance` / `rave` `BankBlock.parse` treats any signature other than `0x0A08` as v6 (`BANK_SIG_V6` is defined but never
  used). An unknown signature should probably be rejected, as HipHop does.
- `Mix.build` in the grid trees does not validate `len(grid) == BARS` or `len(bar) == TRACKS`. A wrong size produces a
  file whose bank block starts at the wrong offset, or a `struct.error` from `pack`.

*Fix:* define one `MixFormatError(ValueError)` (in `contracts.py`, standard library only) and convert low-level errors
at the `parse` boundary. Add bounds checks consistently.

#### F4. Event-list start is found by a heuristic scan (`dance2`, `techno`: `_find_event_start`)

The code tries every byte offset after the pad list and keeps the candidate whose chain of "valid-looking" records ends
exactly at the trailer with the highest count. That works on a known corpus but is a guess: a misaligned candidate
inside the pattern block can in principle form a valid chain, and unusual files fall back silently to "no events" (which
still round-trips because the bytes land in `pattern`, but loses the event data).

The docstrings state that pattern section 17's count is the number of imported events, and `decode_pattern` already
knows the record sizes. A deterministic alternative is: walk the 17 section headers from `pad_end` (same size rule as
`decode_pattern`) to find where the pattern ends, read `count` events from there, and check that the next bytes are the
trailer. The heuristic can stay as a fallback.

I have not verified that section 17's count equals the number of event records in every file, so check it against the
corpus before relying on it.

#### F5. `Catalogs.header_name` truncates names, differs from the codec, and caches by an unsafe key (`dance`, `hiphop`,
`rave`)

- It reads only `fh.read(160)` but honours a length byte up to 255, so names longer than about 155 bytes are silently
  cut.
- It joins *all* metadata lines with spaces and strips trailing NULs, while `libs.pxd.codec.decode` returns only the
  *first* line as `name` and does not strip NULs. The same file can therefore yield different "names" depending on the
  path taken.
- `_name_cache` is keyed by the displayed relative path. `Catalogs.extend()` is documented as merging catalogue sets
  from other installations; two installations with the same relative path would share cache entries and return the wrong
  name. Key it by the absolute path instead.
- `None` results are cached too, so a file that appears later is never picked up.

#### F7. `BankBlock.nlists` can disagree with `lists` (`dance`, `rave`)

`build` writes `self.nlists` into the header but serialises `self.lists`. If a caller adds or removes a list without
updating `nlists`, the output is corrupt. Derive the header value from `len(self.lists)` in `build` (and drop the stored
field or make it a property).

#### F8. Silent failure when catalogue files or directories are missing (all grid trees, and `dance2`/`techno`
`Catalog`)

`Catalog._read` returns `[]` if the list file does not exist, and `os.walk` on a missing `sample_dir` yields nothing. A
wrong root path therefore produces catalogues that resolve nothing, with no warning. Also, `Catalog.__init__` eagerly
walks the entire sample directory on construction, which can be slow on a full disc image and is repeated for every
`Catalogs.add`.

*Fix:* a `strict` option or a logged warning for missing inputs; build the `_disk` index lazily on first `abs_path`.

### Low

#### F9. Heavy duplication between trees (design trade-off, not a defect)

`dance`, `hiphop` and `rave` share near-identical `Mix`, `Catalog`, `Catalogs`, `BankRecord` and `header_name` code;
`dance2` and `techno` are almost line-for-line copies (including `decode_pattern`, `Note`, `Event`,
`_find_event_start`). `contracts.py` states the trees are meant to stay independent, so this is deliberate and I would
not call it wrong. But it has a cost, and drift is already visible:

- F2: Rave's lookup is right, Dance's and HipHop's are not.
- F3: HipHop validates what Dance/Rave do not.
- `describe()` has a `bank` parameter in Dance/Rave but not HipHop.
- A comment in `techno/_find_event_start` lists "HOUSE, LATIN, OTHER, TRANCE and TRIBUTE" as the files with no
  imported-sample events. Those look like Dance 2 file names copied over; the Techno docstring mentions `SOAP.MIX`.
  Verify and correct.

Format facts (offsets, constants, signatures) should stay per tree. Behaviour that is not a format fact (catalogue file
parsing, case-insensitive lookup, name cache, `read_mix`/`write_mix`, the `.INF` reader) could live in one shared
standard-library helper module without breaking the "no format facts in shared code" rule.

#### F10. `libs/pxd/codec.py`

- The accumulator is `np.int32` (`np.cumsum(..., dtype=np.int32)`) and is clipped only afterwards. The docstring says
  the accumulator is "not clamped", so crafted or corrupt input can overflow int32 silently. `np.int64` removes the
  question.
- Once `limit` samples have been emitted, the loop keeps decoding the rest of the stream and discards the output. A
  `break` when `room <= 0` would save work (this is pure-Python per-byte code, so it matters for large files).
- `if base >= table_size: raise ValueError('adaptive table index out of range')` can never fire:
  `base <= 255 * 8 = 2040` and `table_size = 2060`. Either remove it or tighten the table size logic it was meant to
  guard.
- Truncated streams are accepted silently (the loop just ends), and `header_size` can exceed `len(data)` when the
  count/skip bytes are cut off. The mismatch between `declared_count` and `len(samples)` is exposed, which is a
  reasonable choice, but it should be documented as the intended error signal.
- `count == 0` disables truncation (`limit = count if truncate and count > 0 else None`). Probably intentional; worth a
  comment.

#### F11. `libs/pxd/bundle.py`

- `read_index` falls back to `start = 0` when `[SAMPLES]` is missing, whereas `dance2`/`techno` `Catalog._read` returns
  no records in the same situation. Same format, different behaviour.
- `Bundle.decode` slices `data[offset:offset+length]` without checking the range, so a bad index entry yields a silently
  shortened blob.
- `Bundle.truncate_default = True` while the docstring notes Dance 2 "historically used `False`". Any Dance 2 caller
  that does not pass `truncate=False` explicitly now behaves differently from before. `check_equal` reports how many
  records are affected; make sure callers are updated.
- `Bundle._read_index` is a staticmethod that just forwards to `read_index`; harmless, but the indirection is unneeded.
- A stride-12 reader has no resynchronisation: a single extra or missing line in the `.INF` shifts every later record (
  bad records are skipped with `continue`, but misalignment is not detected).

#### F12. `libs/pxd/cli.py`

- `main()` accepts `bundle_cls` and `allow_headerless` for per-tree wrappers, yet the module docstring says "there are
  no per-tree wrappers". Either remove the parameters or restore the wrappers (Rave needs `allow_headerless=True` for
  `R1DA084.PXD`, which plain `python -m libs.pxd` will reject).
- Any exception from one file aborts the whole run with a traceback; the return code is always `0`. Catch per-file
  errors, report them, and return non-zero.
- `--wav` is implemented by mutating `args.wav = None` after the first write. Works, but is surprising; a local flag is
  clearer.
- `--inf` applies to every positional file; combining it with `.inf` arguments is ambiguous and not rejected.

#### F13. `sys.path` manipulation in every `mixfmt.py`

Each of the five modules inserts the repository root at `sys.path[0]` at import time (so repeated imports add duplicate
entries), and `libs/pxd/__main__.py` and `check_equal.py` do something similar. This makes imports order-dependent and
can shadow other top-level modules. Prefer running with `python -m`, setting `PYTHONPATH`, or adding a `pyproject.toml`
and installing in editable mode, then delete the hacks. Related: `libs` is a very generic top-level package name and may
collide with another `libs` on `sys.path`.

#### F14. `events` means two different things

In `GridMix`, `events()` is a method yielding `(bar, track, sample_id)`. In the `dance2`/`techno` `Mix` (a
`SectionMix`), `events` is a *list of `Event`* field. Code that handles both families polymorphically will break on
this. Consider renaming one of them (for example `imported_events`) before more callers depend on it.

#### F15. Typing and annotation slips

- `_valid_record(...) -> tuple[int, int] | None` actually returns an `int` (record length) or `None` (both `dance2` and
  `techno`).
- `GridMix.events()` is annotated `Iterator[tuple[int, int, int]]` in the contract but the concrete `Mix.events()`
  methods have no annotation.
- `pattern_sections() -> list[Any] | None` could be generic over the section type.
- `MixDocument.parse` / `BankBlockDocument.parse` return the base type; `typing.Self` would give callers the concrete
  type (needs 3.11+, or `typing_extensions`).
- `BankBlockDocument` and `MixDocument` have identical interfaces; fine as separate names, but they could share a base.

#### F16. Dead code, redundant imports, and stale documentation

- Apparently unused inside their files: `_cstring_bytes` and `NOTE_SECTIONS` (`dance2`, `techno`); `BANK_SIG_V6` (
  `dance`, `rave`); `DEFAULT_EPILOGUE` (`dance`). They may be used from outside `libs/`; I could not check.
- `PADS = 10` is documented as a module fact, but `parse` accepts any number of pad records and `build` does not enforce
  it.
- Many functions do `import os` locally although `os` is imported at module level.
- `Mix.bar_seconds()` in `dance2`/`techno` divides by `self.bpm`; a parsed file with `bpm == 0` raises
  `ZeroDivisionError`.
- Stale paths in docstrings: `dance2`/`techno` refer to `apps/emp/src/format/…`, `contracts.py` mentions
  `tools.emp.src.core`, `check_equal.py` refers to `reverse/<tree>/pxd.py`. None of these match the current `libs/`
  layout, but I could not see the rest of the repository to know which still exist.
- `libs/pxd/__init__.py` docstring has a missing line break: "…bundles.One implementation…".
- `write_mix` writes in place; a crash mid-write leaves a truncated file. Write to a temporary file and `os.replace`.

---

## Testing

There are no tests under `libs/`. Given that byte-exact round-tripping is the central promise of this code, the
highest-value additions are:

1. A corpus test: for every `.MIX` under `disks/`, `Mix.parse(data).build() == data` for each tree. This would catch F1
   immediately if the corpus triggers it.
2. Synthetic malformed-input tests (truncated at every offset, zero-length names) asserting a single exception type (
   F3).
3. A catalogue test that runs on a case-sensitive filesystem or with a mocked `normcase` (F2).
4. Golden-output tests for `codec.decode` on a few small `.PXD` files, so the pure-Python decoder can be optimised
   safely.

## Suggested order of work

1. Fix F1 (writer) and F2 (case-sensitive lookup); both are small and local.
2. Add the corpus round-trip test.
3. Introduce one `MixFormatError` and consistent bounds checks (F3, F7).
4. Replace or back up `_find_event_start` with the section-count parse (F4).
5. Decide whether to share the non-format-fact code between trees (F9), then remove the `sys.path` hacks (F13).
6. Clean up the Low items.

## What is done well

- Format knowledge is captured in precise layout tables, including explicit "meaning unknown" markers, and unknown bytes
  are preserved verbatim instead of guessed.
- `contracts.py` keeps the shared surface tiny and standard-library only.
- `codec.py` documents the algorithm clearly and handles the headerless Rave file as an explicit opt-in rather than
  guessing.
- `check_equal.py` is a thoughtful way to prove a refactor did not change behaviour.
- Constants carry derivations in comments (bar sizes, `0x2BE2 == 2 + BARS*TRACKS*2`), which makes the numbers checkable.
