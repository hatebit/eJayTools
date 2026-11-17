"""The eJay ``.PXD`` audio codec: one implementation for every tree.

The container and the audio codec were documented by the `ejay_pxd` project
(https://github.com/Alys-Elica/ejay_pxd, `pxd.cpp`); this is an independent
Python implementation of the same algorithm.  Dance, Rave, HipHop, Dance 2 and
Techno eJay 2 all use it, so the five per-tree copies were merged here.

Layout (little-endian):

    byte[4]  "tPxD"
    uint8    n                       length of the metadata block
    byte[n]  metadata                newline separated text (normally the name)
    ...      padding up to marker    0x54
    byte     0x54                    marker
    uint24   sample_count            number of decoded samples
    byte[3]  skipped
    ...      coded audio stream

One shipped Rave file (``RAVE/BD/R1DA084.PXD``) has **no** ``tPxD`` header: it
starts directly with the ``0x54`` marker and the uint24 count.  That shape is
only accepted when ``allow_headerless=True`` (the Rave tree asks for it), because
``0x54`` is ASCII ``T`` and arbitrary text would otherwise decode as audio.

The stream is a table-driven differential coder: 256 adaptive tables of up to
11 signed deltas each.  Each opcode either replays a table, replays a single
delta from the 256-entry base table, or rewrites part of a table and replays
it.  Samples are the running sum of the deltas (clamped to int16 on output
only, the accumulator itself is not clamped).  Audio is mono 16 bit 44100 Hz.
"""

from __future__ import annotations

import itertools
import wave

import numpy as np

SAMPLE_RATE = 44100
TABLE_SLOTS = 256
ENTRIES_PER_TABLE = 8
MAX_DEFINED = 11
SENTINEL = -1
MARKER = 0x54


def _i16(value: int) -> int:
    """Wrap to signed 16 bit, the way the C++ reference truncates."""
    value &= 0xFFFF
    return value - 0x10000 if value >= 0x8000 else value


def delta_table() -> list[int]:
    """The 256 entry base delta table (sign-extended, doubled)."""
    table = [0] * 256
    step = 2.2
    multiplier = 1.0565
    table[128] = 0
    for i in range(1, 128):
        previous = table[127 + i]
        increment = 1 if i < 6 else int(step - 0.52)
        table[128 + i] = _i16(previous + increment)
        step *= multiplier
        multiplier -= 0.00022
    table[0] = 0
    for i in range(1, 128):
        table[128 - i] = _i16(-table[128 + i])
    return [_i16(value << 1) for value in table]


DELTA_TABLE = delta_table()


class PxdSample:
    """One decoded sample."""

    def __init__(self, name: str, strings: list[str], count: int,
                 samples: np.ndarray, header_size: int):
        self.name = name
        self.strings = strings
        self.declared_count = count
        self.samples = samples          # int16, mono, 44100 Hz
        self.header_size = header_size  # bytes before the coded stream

    @property
    def duration(self) -> float:
        return len(self.samples) / SAMPLE_RATE

    def __repr__(self) -> str:
        return '<PxdSample %r %d samples (%.3f s)>' % (
            self.name, len(self.samples), self.duration)


def decode(data: bytes, truncate: bool = True,
           allow_headerless: bool = False) -> PxdSample:
    """Decode one ``tPxD`` stream (the whole of ``data``).

    ``truncate`` cuts the output to the declared sample count.
    ``allow_headerless`` accepts a stream that starts at the ``0x54`` marker.
    """
    if data[:4] == b'tPxD':
        if len(data) < 6:
            raise ValueError('not a tPxD stream')
        meta_len = data[4]
        if 5 + meta_len > len(data):
            raise ValueError('truncated metadata block')
        meta = data[5:5 + meta_len].decode('latin-1')
        strings = [line.rstrip('\r') for line in meta.split('\n')]
        name = strings[0] if strings else ''
        pos = 5 + meta_len
        while pos < len(data) and data[pos] != MARKER:
            pos += 1
        if pos >= len(data):
            raise ValueError('marker 0x54 not found')
        pos += 1
    elif allow_headerless:
        if not data or data[0] != MARKER:
            raise ValueError('not a tPxD file and no 0x54 marker')
        strings = []
        name = ''
        pos = 1
    else:
        raise ValueError('not a tPxD stream')

    if pos + 3 > len(data):
        raise ValueError('truncated sample count')
    count = data[pos] | (data[pos + 1] << 8) | (data[pos + 2] << 16)
    pos += 3 + 3  # sample count, then three skipped bytes
    header_size = pos

    adaptive = [0] * (TABLE_SLOTS * ENTRIES_PER_TABLE + MAX_DEFINED + 1)
    for table in range(TABLE_SLOTS):
        base = table * ENTRIES_PER_TABLE
        adaptive[base + 5] = SENTINEL   # five zero deltas then the sentinel

    table_size = len(adaptive)
    chunks: list[list[int]] = []
    emitted = 0
    limit = count if (truncate and count > 0) else None
    delta = DELTA_TABLE

    def take(run: list[int]) -> None:
        """Append a run, honouring the declared sample count exactly."""
        nonlocal emitted
        if limit is not None:
            room = limit - emitted
            run = run[:room] if room > 0 else []
        chunks.append(run)
        emitted += len(run)

    while pos < len(data):
        op = data[pos]
        pos += 1
        if op < 0xF4:
            base = op * ENTRIES_PER_TABLE
            run = []
            while base < table_size and adaptive[base] != SENTINEL:
                run.append(adaptive[base])
                base += 1
            take(run)
            continue

        if op == 0xFF:
            if pos >= len(data):
                break
            take([delta[data[pos]]])
            pos += 1
            continue

        run_len = op - 0xF3
        if pos >= len(data):
            break
        table = data[pos]
        pos += 1
        base = table * ENTRIES_PER_TABLE
        if base >= table_size:
            raise ValueError('adaptive table index out of range')
        run = []
        for i in range(run_len):
            if pos >= len(data):
                break
            value = delta[data[pos]]
            pos += 1
            if base + i < table_size:
                adaptive[base + i] = value
            run.append(value)
        sentinel = base + run_len
        if sentinel < table_size:
            adaptive[sentinel] = SENTINEL
        take(run)

    if chunks:
        deltas = np.fromiter(itertools.chain.from_iterable(chunks), dtype=np.int32)
        samples = np.cumsum(deltas, dtype=np.int32)
    else:
        samples = np.zeros(0, dtype=np.int32)
    np.clip(samples, -32768, 32767, out=samples)
    return PxdSample(name, strings, count, samples.astype(np.int16), header_size)


def decode_file(path, truncate: bool = True,
                allow_headerless: bool = False) -> PxdSample:
    """Decode a standalone ``.PXD`` file."""
    with open(path, 'rb') as fh:
        return decode(fh.read(), truncate=truncate,
                      allow_headerless=allow_headerless)


def write_wav(path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Write mono 16 bit samples to a WAV file."""
    data = np.asarray(samples, dtype=np.int16)
    with wave.open(path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(data.tobytes())