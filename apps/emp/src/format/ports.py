"""Abstract base classes for the shared eJay player core.

Only contracts live here; implementations live elsewhere.  The format trees
subclass :class:`FormatAdapter`, the core implements the remaining ports.  The
format-neutral rule still holds: nothing here names a format, and no engine
code may branch on ``format_id``.

:class:`SampleRef` is a structural protocol on purpose: it is a two-property
view over a tree record, not a class the trees construct.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Protocol, Sequence

import numpy as np

from apps.emp.src.core.model import LoadedSong, Placement


CatalogSpec = tuple[str, str, str]


@dataclass
class LoadOptions:
    """Everything a frontend may ask an adapter to change while loading."""

    solo: set[int] | None = None
    mute: set[int] | None = None
    gain: float | None = None
    catalog_specs: list[CatalogSpec] = field(default_factory=list)
    verbose: bool = False


class SampleRef(Protocol):
    """Display information for one resolvable sample id."""

    @property
    def label(self) -> str: ...

    @property
    def path(self) -> str | None: ...


class SampleSource(ABC):
    """Resolves sample ids and returns cached mono float32 audio."""

    @abstractmethod
    def ref(self, sample_id: int) -> SampleRef | None:
        """Display reference, or ``None`` when the id does not resolve."""

    @abstractmethod
    def audio(self, sample_id: int) -> np.ndarray | None:
        """Decoded mono float32 sample, cached; ``None`` when unavailable."""


class Reporter(ABC):
    """Receives every line a frontend may display."""

    @abstractmethod
    def info(self, text: str) -> None: ...

    @abstractmethod
    def warning(self, text: str) -> None: ...

    @abstractmethod
    def decoding(self, count: int) -> None: ...

    @abstractmethod
    def sample(self, sample_id: int, label: str, path: str | None,
               seconds: float) -> None: ...

    @abstractmethod
    def skipped(self, sample_id: int, label: str) -> None: ...

    @abstractmethod
    def progress(self, position: int, total: int, bar: int) -> None: ...

    @abstractmethod
    def finished(self, overflows: int, bar: int, total: float) -> None: ...


class AudioSink(ABC):
    """Offline, push-based output."""

    @abstractmethod
    def write(self, block: np.ndarray) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class LiveOutput(ABC):
    """Live, pull-based output."""

    @abstractmethod
    def run(self, transport: object, on_progress: Callable[[], None] | None = None,
            poll: float = 0.1) -> int:
        """Stream ``transport``; return the overflow count."""


PeakFunction = Callable[[Sequence[Placement], int, int], float]


class FormatAdapter(ABC):
    """Everything format-specific a frontend needs.

    Subclasses set the descriptive attributes and implement the three methods.
    The adapter owns format facts (signature, bar length, pan rule, cut rule,
    peak strategy and wording); the core owns nothing format-specific.
    """

    format_id: str
    format_version: str
    display_name: str
    mix_dir: str
    track_count: int
    supports_catalog: bool
    bar_origin: int
    default_start_bar: int
    description: str
    from_help: str | None
    catalog_help: str | None

    @abstractmethod
    def matches(self, path: str, head: bytes, size: int) -> bool:
        """True when this adapter recognises the file."""

    @abstractmethod
    def resolve(self, name: str) -> str | None:
        """Turn a command-line name into a path, or return it unchanged."""

    @abstractmethod
    def load(self, path: str, options: LoadOptions,
             reporter: Reporter) -> LoadedSong:
        """Read a mix, decode what it needs and return the normalized model."""

