"""Stock peak estimators and the automatic gain rule.

Peak estimation is format behaviour: each adapter picks the function that
matches its documented behaviour.  Do not unify them.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .mixer import mix_placements
from .model import Placement


def bar_peak_grid(placements: Sequence[Placement], bars: int,
                  bar_samples: int) -> float:
    """Per-bar summed sample peaks, per channel (Dance, Rave, HipHop)."""
    if not placements:
        return 0.0
    left = np.zeros(bars + 1, dtype=np.float32)
    right = np.zeros(bars + 1, dtype=np.float32)
    for placement in placements:
        if not len(placement.audio):
            continue
        peak = float(np.max(np.abs(placement.audio)))
        first = placement.onset // bar_samples
        last = min(bars, (placement.onset + len(placement.audio)
                          + bar_samples - 1) // bar_samples)
        if placement.left:
            left[first:last] += peak * placement.left
        if placement.right:
            right[first:last] += peak * placement.right
    return float(max(left.max(), right.max()))


def bar_peak_sections(placements: Sequence[Placement], bars: int,
                      bar_samples: int) -> float:
    """Per-bar summed sample peaks, clamped to the rendered bars (Dance 2)."""
    if not placements:
        return 0.0
    left = np.zeros(bars, dtype=np.float32)
    right = np.zeros(bars, dtype=np.float32)
    for placement in placements:
        if not len(placement.audio):
            continue
        peak = float(np.max(np.abs(placement.audio)))
        first = min(bars - 1, placement.onset // bar_samples)
        last = min(bars, -(-placement.stop // bar_samples))
        if last <= first:
            last = first + 1
        if placement.left:
            left[first:last] += peak * placement.left
        if placement.right:
            right[first:last] += peak * placement.right
    return float(max(left.max(), right.max()))


def rendered_peak(placements: Sequence[Placement], bars: int,
                  bar_samples: int) -> float:
    """Exact peak of the unity-gain render, one bar at a time (Techno)."""
    peak = 0.0
    for bar in range(bars):
        chunk = mix_placements(placements, bar * bar_samples,
                               min(bar_samples, (bars - bar) * bar_samples))
        if len(chunk):
            peak = max(peak, float(np.max(np.abs(chunk))))
    return peak


def auto_gain(peak: float) -> float:
    """Peak-normalising gain, bounded to [0.05, 8.0]."""
    if peak > 0:
        return min(8.0, max(0.05, 0.95 / peak))
    return 1.0
