"""Normalized song model shared by every eJay format adapter."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Placement:
    """One decoded sample placed on the absolute sample timeline."""

    onset: int          # absolute sample index, 0-based
    stop: int           # absolute sample index, exclusive
    audio: np.ndarray   # mono float32 in [-1, 1], full sample (not cut)
    left: float         # channel gain, 0.0 or 1.0 today
    right: float
    track: int          # 0-based track index
    label: str          # catalogue label, for display


@dataclass(frozen=True)
class TrackInfo:
    """Per-track statistics as the source format defines them."""

    index: int          # 0-based
    pan_name: str       # display only
    placed: int
    distinct: int


@dataclass(frozen=True)
class SongStats:
    """Sample and peak statistics of a loaded song."""

    missing: int
    missing_ids: frozenset[int]
    used_samples: int
    peak: float
    clips: int | None = None
    hits: int | None = None


@dataclass
class LoadedSong:
    """A mix decoded into placements, ready for the mixer."""

    path: str
    format_id: str
    sample_rate: int
    bar_samples: int
    bar_origin: int                 # 0 for grid formats, 1 for section formats
    bars: int                       # audible length, including ring-out
    arrangement_bars: int           # grid/pattern end without the ring-out
    tail_bars: int                  # ring-out end
    tracks: list[TrackInfo]
    placements: list[Placement]
    stats: SongStats
    gain: float
    detail: str                     # middle of the first summary line
    notes: list[str] = field(default_factory=list)

    def duration(self) -> float:
        """Playback length in seconds, including the ring-out tail."""
        return self.bars * self.bar_samples / self.sample_rate

    def summary(self) -> str:
        """The one-line description both frontends print."""
        return ('%s: %d bars (%.1f s), %s, gain %.2f'
                % (os.path.basename(self.path), self.bars, self.duration(),
                   self.detail, self.gain))
