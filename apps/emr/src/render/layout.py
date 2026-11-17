"""Format-neutral layouts for the PNG renderer.

A :class:`Layout` is everything the canvas needs: coloured spans in bars, the
number of bar columns, the ruler numbering and the per-track statistics for
``-v``.  :func:`grid_layout` and :func:`section_layout` build it from a tree's
``mixfmt.Mix`` without naming a format.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from apps.emr.src.render.samples import grid_sample_bars, section_sample_bars


@dataclass(frozen=True)
class Span:
    """One coloured bar of an arrangement, in bar units."""

    start: float       # zero-based, inclusive
    stop: float        # zero-based, exclusive
    track: int         # zero-based
    sample_id: int


@dataclass(frozen=True)
class Layout:
    """Everything the shared canvas needs to draw one song."""

    spans: list[Span]
    bars: int
    track_count: int
    bar_origin: int                   # 0 = grid numbering, 1 = section numbering
    grid_bars: int | None             # Mix.song_length for grid trees
    unit: str                         # "samples" (grid) or "records" (sections)
    track_stats: list[tuple[int, int | None]]


@dataclass(frozen=True)
class RenderFormat:
    """A format tree's contribution to the shared renderer."""

    format_id: str
    display_name: str
    signature: int
    mix_dir: str
    default_out: str
    layout: Callable[[str], Layout]


def grid_layout(mix: Any, catalogs: Any, samples_per_bar: int,
                beats_per_bar: int, bpm: int,
                allow_headerless: bool = False) -> Layout:
    """Build the layout of a fixed ``BARS x TRACKS`` grid mix."""
    spans: list[Span] = []
    lengths: dict[str, int] = {}
    end_bar = mix.song_length
    for bar, track, sample_id in mix.events():
        span = 1
        sample_path = catalogs.abs_path(sample_id)
        if sample_path is not None:
            if sample_path not in lengths:
                lengths[sample_path] = grid_sample_bars(
                    sample_path, samples_per_bar, beats_per_bar, bpm,
                    allow_headerless)
            span = lengths[sample_path]
        spans.append(Span(bar, bar + span, track, sample_id))
        end_bar = max(end_bar, bar + span)

    stats = [(placed, distinct) for placed, distinct in mix.track_usage()]
    return Layout(
        spans=spans,
        bars=max(end_bar, 1),
        track_count=len(stats),
        bar_origin=0,
        grid_bars=mix.song_length,
        unit='samples',
        track_stats=stats,
    )


def section_layout(mix: Any, sample_index: Any, bar_samples: int) -> Layout:
    """Build the layout of a section/pattern mix.

    ``stop`` is where the player stops a record: the next record on the same
    track, or the end of the sample, whichever comes first.  The search is the
    original one -- the next record *in list order* whose start is strictly
    later -- because the pattern bytes, not a sort, define the cut.
    """
    sections = mix.pattern_sections()
    if sections is None:
        raise ValueError('the pattern block does not decode')

    lengths: dict[int, float] = {}

    def sample_bars(sample_id: int) -> float:
        if sample_id not in lengths:
            lengths[sample_id] = section_sample_bars(
                sample_index, sample_id, bar_samples)
        return lengths[sample_id]

    spans: list[Span] = []
    stats: list[tuple[int, int | None]] = []
    end = 0.0
    for section in sections[:-1]:
        track = section.index - 1
        notes = section.notes
        stats.append((len(notes), None))
        for position, note in enumerate(notes):
            later = next((other.start_bar for other in notes[position + 1:]
                          if other.start_bar > note.start_bar), None)
            start = note.start_bar - 1
            stop = start + sample_bars(note.sample_id)
            if later is not None:
                stop = min(stop, later - 1)
            if stop <= start:
                stop = start + 1 / 128      # a zero-width record still shows
            spans.append(Span(start, stop, track, note.sample_id))
            end = max(end, stop)

    return Layout(
        spans=spans,
        bars=max(1, int(math.ceil(end - 1e-9))),
        track_count=len(stats),
        bar_origin=1,
        grid_bars=None,
        unit='records',
        track_stats=stats,
    )

