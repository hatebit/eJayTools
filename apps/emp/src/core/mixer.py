"""Summing placements and applying output gain."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .model import LoadedSong, Placement


def mix_placements(placements: Sequence[Placement], start: int,
                   frames: int) -> np.ndarray:
    """Sum ``frames`` stereo samples from absolute sample ``start``.

    No gain and no clipping.  The loop never breaks early: section-format
    placements are not sorted by onset.
    """
    out = np.zeros((frames, 2), dtype=np.float32)
    end = start + frames
    for placement in placements:
        if placement.onset >= end or placement.stop <= start:
            continue
        first = placement.onset if placement.onset > start else start
        last = placement.stop if placement.stop < end else end
        chunk = placement.audio[first - placement.onset:last - placement.onset]
        if placement.left:
            if placement.left == 1.0:
                out[first - start:last - start, 0] += chunk
            else:
                out[first - start:last - start, 0] += chunk * placement.left
        if placement.right:
            if placement.right == 1.0:
                out[first - start:last - start, 1] += chunk
            else:
                out[first - start:last - start, 1] += chunk * placement.right
    return out


def apply_gain(out: np.ndarray, gain: float) -> np.ndarray:
    """Apply gain in place and clip to [-1, 1].

    ``gain`` must be a Python ``float`` so the multiply stays in float32.
    """
    if gain != 1.0:
        out *= gain
    np.clip(out, -1.0, 1.0, out=out)
    return out


class Mixer:
    """Mixes a loaded song's placements."""

    def __init__(self, song: LoadedSong):
        self.song = song

    def mix(self, start: int, frames: int) -> np.ndarray:
        """Sum ``frames`` stereo samples from absolute sample ``start``."""
        return mix_placements(self.song.placements, start, frames)
