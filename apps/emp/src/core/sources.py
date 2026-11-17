"""Sample sources: catalogue files (WAV/PXD) and bundled ``.INF`` banks."""

from __future__ import annotations

import wave
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from apps.emp.src.format.ports import Reporter, SampleSource

SAMPLE_RATE = 44100


class Decoder(Protocol):
    """A tree's ``pxd.decode_file``: path -> object with ``.samples``."""

    def __call__(self, path: str): ...


@dataclass(frozen=True)
class SampleRef:
    """Display label and relative path of one resolvable sample id."""

    label: str
    path: str | None


def read_wav(path: str, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Read a mono 16-bit WAV at ``sample_rate`` to float32 in [-1, 1]."""
    with wave.open(path, 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(),
                wav.getframerate()) != (1, 2, sample_rate):
            raise ValueError('unsupported WAV: %d ch, %d bit, %d Hz'
                             % (wav.getnchannels(), 8 * wav.getsampwidth(),
                                wav.getframerate()))
        data = wav.readframes(wav.getnframes())
    return np.frombuffer(data, dtype='<i2').astype(np.float32) / 32768.0


class FileSampleSource(SampleSource):
    """Catalogue-backed samples: ``.wav`` decoded directly, else a ``.PXD``.

    ``catalogs`` is duck-typed on ``abs_path``, ``sample_name`` and
    ``path_for`` so the core does not import a format tree.
    """

    def __init__(self, catalogs, decoder: Decoder, reporter: Reporter,
                 sample_rate: int = SAMPLE_RATE):
        self.catalogs = catalogs
        self.decoder = decoder
        self.reporter = reporter
        self.sample_rate = sample_rate
        self._cache: dict[int, np.ndarray | None] = {}

    def ref(self, sample_id: int) -> SampleRef | None:
        """Display reference, or ``None`` when the id resolves to no file."""
        if not self.catalogs.abs_path(sample_id):
            return None
        return SampleRef(self.catalogs.sample_name(sample_id) or '?',
                         self.catalogs.path_for(sample_id) or '?')

    def audio(self, sample_id: int) -> np.ndarray | None:
        """Decoded mono float32, cached; ``None`` when missing or corrupt."""
        if sample_id not in self._cache:
            audio = None
            path = self.catalogs.abs_path(sample_id)
            if path is not None:
                try:
                    if path.lower().endswith('.wav'):
                        audio = read_wav(path, self.sample_rate)
                    else:
                        audio = (self.decoder(path).samples.astype(np.float32)
                                 / 32768.0)
                except Exception as exc:  # corrupt/odd file: keep going
                    self.reporter.warning('warning: %s: %s' % (path, exc))
                    audio = None
                if audio is not None and not len(audio):
                    audio = None
            self._cache[sample_id] = audio
        return self._cache[sample_id]


class BundleSampleSource(SampleSource):
    """Samples looked up in a tree's bundled ``.INF`` indexes.

    ``banks`` is the tree's own ``Banks`` object, duck-typed on ``find``,
    ``label`` and ``audio``; it reports corrupt records through the reporter
    it was built with, so both frontends see the warning.
    """

    def __init__(self, banks):
        self.banks = banks

    def ref(self, sample_id: int) -> SampleRef | None:
        bank, record = self.banks.find(sample_id)
        if bank is None or record is None:
            return None
        return SampleRef(record.label, None)

    def audio(self, sample_id: int) -> np.ndarray | None:
        return self.banks.audio(sample_id)

