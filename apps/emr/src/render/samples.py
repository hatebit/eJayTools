"""Sample-length probes for the PNG renderer.

Only headers are read: a ``tPxD`` stream declares its frame count near the
start, and a RIFF/WAVE header declares it in the ``fmt``/``data`` chunks.  No
audio is decoded, so this module stays standard-library only and a render does
not depend on numpy or the player core.
"""

from __future__ import annotations

import math
import wave


def _pxd_frames(head: bytes, allow_headerless: bool = False) -> int | None:
    """Declared sample count from a ``tPxD`` header, or ``None``."""
    if allow_headerless and len(head) >= 7 and head[0] == 0x54:
        pos = 0
    elif len(head) >= 7 and head[:4] == b'tPxD':
        pos = 5 + head[4]
        while pos < len(head) and head[pos] != 0x54:
            pos += 1
    else:
        return None
    if pos + 3 >= len(head):
        return None
    return head[pos + 1] | (head[pos + 2] << 8) | (head[pos + 3] << 16)


def _wav_frames(path: str) -> tuple[int, int] | None:
    """``(frames, rate)`` from a RIFF/WAVE file, if it can be read."""
    try:
        with wave.open(path, 'rb') as wav:
            return wav.getnframes(), wav.getframerate()
    except (OSError, wave.Error):
        return None


def grid_sample_bars(path: str, samples_per_bar: int, beats_per_bar: int,
                     bpm: int, allow_headerless: bool = False) -> int:
    """Length of a grid sample file in whole bars, at least 1."""
    try:
        with open(path, 'rb') as fh:
            head = fh.read(512)
    except OSError:
        return 1
    if head[:4] == b'tPxD' or (allow_headerless and head[:1] == b'\x54'):
        frames = _pxd_frames(head, allow_headerless)
        if frames is None:
            return 1
        return max(1, math.ceil(frames / samples_per_bar - 1e-9))
    if head[:4] == b'RIFF':
        info = _wav_frames(path)
        if info is None:
            return 1
        frames, rate = info
        bar = rate * beats_per_bar * 60 / bpm
        return max(1, math.ceil(frames / bar - 1e-9))
    return 1


class BundleIndex:
    """Sample id -> ``(bundle path, offset, length)`` for section trees.

    The records come from a tree's own ``mixfmt.Catalog``; this class only
    knows the common ``sample_id``/``offset``/``length`` members, so no tree
    or ``.INF`` parser is imported here.
    """

    def __init__(self, bundles):
        self.entries: dict[int, tuple[str, int, int]] = {}
        for data_path, records in bundles:
            for record in records:
                self.entries.setdefault(
                    record.sample_id, (data_path, record.offset, record.length))

    def frames(self, sample_id: int) -> int | None:
        """Declared sample count of ``sample_id``, or ``None`` if unknown."""
        entry = self.entries.get(sample_id)
        if entry is None:
            return None
        data_path, offset, length = entry
        try:
            with open(data_path, 'rb') as fh:
                fh.seek(offset)
                head = fh.read(min(length, 2048))
        except OSError:
            return None
        return _pxd_frames(head)


def section_sample_bars(index: BundleIndex, sample_id: int,
                        bar_samples: int) -> float:
    """Length of a section sample in whole bars, at least 1."""
    frames = index.frames(sample_id)
    if not frames:
        return 1.0
    return max(1, math.ceil(frames / bar_samples - 1e-9))

