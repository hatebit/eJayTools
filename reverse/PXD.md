# PXD Format Documentation

## Overview

The `.PXD` format is a proprietary audio container and codec used by the eJay series (Dance, Rave, HipHop, Dance eJay 2, Techno eJay 2). All five products share the same codec implementation, now centralized in `libs/pxd/`.

The format stores mono 16-bit PCM audio at 44.1 kHz using a table-driven differential coding scheme.

## File Structure

### Standalone .PXD Files (Dance, Rave, HipHop eJay 1.x)

```
byte[4]  "tPxD"           # Magic header
uint8    n                # Length of metadata block
byte[n]  metadata         # Newline-separated text (usually sample name)
...      padding          # Up to marker 0x54
byte     0x54             # Stream marker
uint24   sample_count     # Declared number of decoded samples (little-endian)
byte[3]  skipped          # Three padding bytes
...      coded audio stream
```

### Headerless Variant (Rave eJay only)

One shipped file (`RAVE/BD/R1DA084.PXD`) lacks the `tPxD` header entirely and starts directly at the `0x54` marker. This is only accepted when `allow_headerless=True`.

### Bundled .PXD Files (Dance eJay 2, Techno eJay 2)

Dance eJay 2 and Techno eJay 2 concatenate multiple `tPxD` streams into a single data file, with a sibling `.INF` index describing each stream.

**Bundle files:**
- `DANCE20` + `DANCE20.INF` (Dance eJay 2 base samples)
- `DANCESK4` + `DANCESK4.INF` (Vol. 4 expansion)
- `DANCESK5` + `DANCESK5.INF` (Vol. 5 expansion)
- `DANCESK6` + `DANCESK6.INF` (Vol. 6 expansion)
- `RAVE20` + `RAVE20.INF` (Techno eJay 2 base samples)

## The Codec

### Table-Driven Differential Coding

The audio stream uses 256 adaptive tables, each holding up to 11 signed deltas (actually 8 entries + 3 for expansion, plus a sentinel).

- **Base delta table**: 256 pre-computed deltas (sign-extended, doubled)
- **Adaptive tables**: Initially filled with 5 zeros + sentinel (-1); rewritten during decoding
- **Opcodes** (1 byte each):
  - `0x00`–`0xF3`: Replay adaptive table `opcode`
  - `0xF4`–`0xFE`: Rewrite adaptive table `(opcode - 0xF3)` entries, then replay
  - `0xFF`: Replay single delta from base table (next byte is index)

### Decoding Algorithm

1. Read header, find `0x54` marker, read 24-bit sample count
2. Initialize 256 adaptive tables (5 zeros + sentinel each)
3. Process opcodes until end of stream or declared sample count reached
4. Accumulate deltas as running sum (32-bit, no clamping during accumulation)
5. Clamp final samples to int16 range [-32768, 32767]

## API Reference

### `libs.pxd.codec`

```python
from libs.pxd.codec import (
  decode, decode_file, write_wav,
  PxdSample, DELTA_TABLE, SAMPLE_RATE
)
```

#### `decode(data: bytes, truncate: bool = True, allow_headerless: bool = False) -> PxdSample`

Decode a complete `tPxD` stream from memory.

- `truncate`: Cut output to declared sample count (default: `True`)
- `allow_headerless`: Accept stream starting at `0x54` marker without `tPxD` header (default: `False`)

Returns a `PxdSample` with:
- `name`: First line of metadata (sample name)
- `strings`: All metadata lines
- `declared_count`: Sample count from header
- `samples`: `np.ndarray` of int16, mono, 44100 Hz
- `header_size`: Bytes before coded stream
- `duration`: `len(samples) / SAMPLE_RATE`

#### `decode_file(path, truncate=True, allow_headerless=False) -> PxdSample`

Convenience wrapper reading from file.

#### `write_wav(path, samples: np.ndarray, sample_rate=44100) -> None`

Write mono 16-bit WAV file.

#### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `SAMPLE_RATE` | 44100 | Audio sample rate (Hz) |
| `TABLE_SLOTS` | 256 | Number of adaptive tables |
| `ENTRIES_PER_TABLE` | 8 | Base entries per table |
| `MAX_DEFINED` | 11 | Max entries after rewrites |
| `SENTINEL` | -1 | End-of-table marker |
| `MARKER` | 0x54 | Stream start marker |
| `DELTA_TABLE` | list[256] | Pre-computed base deltas |

### `libs.pxd.bundle`

```python
from libs.pxd.bundle import Bundle, IndexRecord, read_index
```

#### `read_index(path) -> list[IndexRecord]`

Parse `.INF` index file without loading bundle data.

Each record is 12 CRLF lines:
```
sample_id, bank, PXD_file, offset, length, group, name,
flag1, flag2, "", 0, ""
```

#### `IndexRecord`

Fields: `sample_id`, `bank`, `file`, `offset`, `length`, `group`, `name`, `flag1`, `flag2`

Property: `label` = `"group name"` (or filename if empty)

#### `Bundle(data_path, inf_path)`

Load concatenated PXD data + `.INF` index.

- `records`: List of all `IndexRecord`
- `by_id`: Dict mapping `sample_id` -> `IndexRecord`
- `record_for(id) -> IndexRecord | None`
- `decode(record, truncate=None) -> PxdSample` (uses `truncate_default` if `None`)
- `decode_id(id, truncate=None) -> PxdSample`
- `truncate_default`: Class attribute (`True` for Techno, `False` for Dance 2)

## Per-Tree Entry Points

Each tree has a thin wrapper in `reverse/<tree>/pxd.py`:

| Tree | Module | Special Behavior |
|------|--------|------------------|
| Dance | `libs.pxd` | standard decode |
| Rave | `libs.pxd` | `allow_headerless=True` for `R1DA084.PXD` |
| HipHop | `libs.pxd` | standard decode |
| Dance 2 | `libs.pxd` | `Bundle` for `DANCE20` + `DANCESK4/5/6`; the player goes through `banks.py` |
| Techno | `libs.pxd` | `Bundle` for `RAVE20` (truncates by default) |

## Command Line Usage

```bash
# Standalone PXD file
python libs/pxd sample.PXD --stats --wav out.wav

# Bundle via .INF
python libs/pxd DANCE20.INF --id 1930 --stats --wav out.wav

# Bundle via data file + explicit .INF
python libs/pxd DANCE20 --inf DANCE20.INF --list

# Same command as a module, from the repository root
python -m libs.pxd sample.PXD --stats
```

### Options

| Option | Description |
|--------|-------------|
| `--id N` | Decode only this sample ID from bundle (repeatable) |
| `--wav PATH` | Write first decoded sample to WAV |
| `--stats` | Print peak, RMS, declared/decoded counts, clipped samples |
| `--list` | List index records only (no decoding) |
| `--inf PATH` | Explicit .INF for bundle data file |

## Verification

The shared decoder is byte-for-byte identical to the five original per-tree implementations:

```bash
python reverse/ejaypxd/check_equal.py --rev <commit-before-merge>
# Must print: "TOTAL X decodes, 0 differences"
```

## Notes

- Audio is always mono, 16-bit, 44.1 kHz
- The accumulator uses 32-bit integers; clamping only happens at output
- Dance 2's `truncate_default=False` preserves historical behavior; the player uses `banks.py` which overrides this
- No network access or external dependencies beyond `numpy` and stdlib
