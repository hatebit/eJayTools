"""The bundled ``.INF`` sample indexes of Dance eJay 2.

Moved out of ``mixplayer.py`` unchanged: the records are looked up by id in the
four shipped bundles, never computed as ``base + index``.
"""

from __future__ import annotations

import os

import numpy as np

from apps.emp.src.format.ports import Reporter
from apps.emp.src.paths import data_root
from libs.pxd import IndexRecord, decode, read_index

ROOT = os.path.join(data_root(__file__), 'disks', 'Dance_2')
PXD_DIR = os.path.join(ROOT, 'D_ejay2', 'PXD')
BUNDLES = ('DANCE20', 'DANCESK4', 'DANCESK5', 'DANCESK6')


class Bank:
    """One ``.INF`` index and the bundle file its records point into."""

    def __init__(self, data_path: str, inf_path: str):
        self.data_path = data_path
        self.records = read_index(inf_path)
        self.by_id: dict[int, IndexRecord] = {}
        for record in self.records:
            self.by_id.setdefault(record.sample_id, record)

    def record_for(self, sample_id: int) -> IndexRecord | None:
        return self.by_id.get(sample_id)

    def audio(self, record: IndexRecord) -> np.ndarray:
        """Decode one indexed record to mono float32."""
        with open(self.data_path, 'rb') as fh:
            fh.seek(record.offset)
            blob = fh.read(record.length)
        return decode(blob).samples.astype(np.float32) / 32768.0


class Banks:
    """The sample ids of all four bundled indexes, decoded on first use."""

    def __init__(self, reporter: Reporter, directory: str = PXD_DIR):
        self.reporter = reporter
        self.banks: list[Bank] = []
        for name in BUNDLES:
            data_path = os.path.join(directory, name)
            inf_path = data_path + '.INF'
            if os.path.exists(data_path) and os.path.exists(inf_path):
                self.banks.append(Bank(data_path, inf_path))
        self.cache: dict[int, np.ndarray | None] = {}

    def find(self, sample_id: int):
        for bank in self.banks:
            record = bank.record_for(sample_id)
            if record is not None:
                return bank, record
        return None, None

    def label(self, sample_id: int) -> str:
        _bank, record = self.find(sample_id)
        return record.label if record is not None else '?'

    def audio(self, sample_id: int) -> np.ndarray | None:
        if sample_id not in self.cache:
            bank, record = self.find(sample_id)
            audio = None
            if bank is not None and record is not None:
                try:
                    audio = bank.audio(record)
                except Exception as exc:      # corrupt record: report and skip
                    self.reporter.warning('warning: sample %d: %s'
                                          % (sample_id, exc))
                    audio = None
            self.cache[sample_id] = (audio if audio is not None and len(audio)
                                     else None)
        return self.cache[sample_id]

