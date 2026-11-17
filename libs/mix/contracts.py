"""Abstract base classes shared by every ``libs/mix/<tree>/mixfmt.py``.

The five format trees stay independent; this module is the one place that states
what a format library *is*.  It knows no signature, file layout, sample id or
format name, and it imports nothing outside the standard library, so a
``mixfmt.py`` that inherits from it remains standard-library only.

Two document families exist, matching the two shapes found in ``disks/``:

* :class:`GridMix` -- a fixed ``BARS x TRACKS`` grid plus an optional bank block
  (Dance, Rave and HipHop eJay 1.x);
* :class:`SectionMix` -- a variable sequence of sections with a drum-pattern
  block (Dance eJay 2 and Techno eJay 2).

Both are :class:`MixDocument`: one complete file image parses to a model and
builds back to the same bytes.  :class:`SampleCatalog` is the id -> record
lookup both families expose; :class:`BankBlockDocument` is the appended
sample-bank block the grid family carries.

These are contracts, not helpers.  Shared behaviour that would change audio or
stdout belongs in the tree or in ``tools.emp.src.core``; do not move format facts here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SampleRecordInfo(Protocol):
    """The one member every catalogue record must expose."""

    @property
    def label(self) -> str: ...


class SampleCatalog(ABC):
    """An id -> sample-record index.

    Grid catalogues also expose ``path_for`` and ``abs_path``; section
    catalogues only expose the lookup, because their records live in a bundle.
    Only the common member belongs here.
    """

    @abstractmethod
    def record_for(self, sample_id: int) -> SampleRecordInfo | None:
        """Return the record for ``sample_id``, or ``None`` when absent."""


class MixDocument(ABC):
    """One song file that parses to a model and re-encodes byte-exactly."""

    @classmethod
    @abstractmethod
    def parse(cls, data: bytes) -> "MixDocument":
        """Parse one complete file image."""

    @abstractmethod
    def build(self) -> bytes:
        """Re-encode the model; must reproduce the parsed bytes exactly."""


class BankBlockDocument(ABC):
    """An appended sample-bank block that round-trips on its own."""

    @classmethod
    @abstractmethod
    def parse(cls, data: bytes) -> "BankBlockDocument":
        """Parse the appended block."""

    @abstractmethod
    def build(self) -> bytes:
        """Re-encode the block; must reproduce the parsed bytes exactly."""


class GridMix(MixDocument):
    """A fixed ``BARS x TRACKS`` grid, the eJay 1.x shape.

    The tree's module defines ``SIGNATURE``, ``TRACKS``, ``BARS``, ``BPM`` and
    ``BEATS_PER_BAR``; these are module facts, not class members.
    """

    @property
    @abstractmethod
    def song_length(self) -> int:
        """Bars up to and including the last non-empty slot."""

    @abstractmethod
    def duration(self) -> float:
        """Arrangement length in seconds."""

    @abstractmethod
    def used_samples(self) -> list[int]:
        """Sorted distinct non-zero sample ids in the grid."""

    @abstractmethod
    def track_usage(self) -> list[tuple[int, int]]:
        """``(placed, distinct)`` per track, T1 first."""

    @abstractmethod
    def events(self) -> Iterator[tuple[int, int, int]]:
        """Yield ``(bar, track, sample_id)`` for every placed sample."""


class SectionMix(MixDocument):
    """A variable section sequence, the eJay 2 shape.

    The tree's module defines ``SIGNATURE``, ``TRACKS``, ``PADS``, ``BPM`` and
    ``BEATS_PER_BAR``; these are module facts, not class members.
    """

    @property
    @abstractmethod
    def left_tracks(self) -> list[int]:
        """1-based indices of the tracks panned left."""

    @property
    @abstractmethod
    def right_tracks(self) -> list[int]:
        """1-based indices of the tracks panned right."""

    @abstractmethod
    def bar_seconds(self) -> float:
        """One bar in seconds at the stored tempo."""

    @abstractmethod
    def pattern_sections(self) -> list[Any] | None:
        """Decoded pattern sections, or ``None`` when the block is invalid."""

