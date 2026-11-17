"""Bundled ``.PXD`` containers and their ``.INF`` sample index.

Dance eJay 2 (``DANCE20``, ``DANCESK4``..``6``) and Techno eJay 2 (``RAVE20``)
keep many ``tPxD`` streams in one file, described by a sibling ``.INF``.  Each
index record is twelve CRLF lines::

    sample id, bank, PXD file name, offset, length, group, name,
    flag 1, flag 2, "", 0, ""

:func:`read_index` reads the index on its own, so a caller that needs a few
samples (the players) does not load the whole bundle.
"""

from __future__ import annotations

import os

from .codec import PxdSample, decode


class IndexRecord:
    """One twelve-line record of an eJay 2 ``.INF`` sample index."""

    def __init__(self, fields: list[str]):
        self.fields = fields
        self.sample_id = int(fields[0])
        self.bank = int(fields[1])
        self.file = fields[2]
        self.offset = int(fields[3])
        self.length = int(fields[4])
        self.group = fields[5]
        self.name = fields[6]
        self.flag1 = int(fields[7])
        self.flag2 = int(fields[8])

    @property
    def label(self) -> str:
        return ('%s %s' % (self.group, self.name)).strip() or self.file

    def __repr__(self) -> str:
        return '<IndexRecord %d %r %d+%d>' % (self.sample_id, self.label,
                                              self.offset, self.length)


def read_index(path) -> list[IndexRecord]:
    """Read an ``.INF`` index without loading the sample bundle it describes."""
    with open(path, 'rb') as fh:
        text = fh.read().decode('latin-1')
    lines = [line.strip() for line in text.splitlines()]
    try:
        start = lines.index('[SAMPLES]') + 1
    except ValueError:
        start = 0
    body = lines[start:]
    records = []
    for i in range(0, len(body) - 11, 12):
        fields = [field.strip('"') for field in body[i:i + 12]]
        try:
            records.append(IndexRecord(fields))
        except ValueError:
            continue
    return records


class Bundle:
    """A concatenated PXD file plus its ``.INF`` index.

    ``truncate_default`` is what :meth:`decode` does when the caller does not
    say: cut each stream to its declared sample count (``True``) or keep every
    decoded sample (``False``).  The Dance 2 tree historically used ``False``.
    """

    truncate_default = True

    def __init__(self, data_path, inf_path):
        self.data_path = os.fspath(data_path)
        self.inf_path = os.fspath(inf_path)
        with open(self.data_path, 'rb') as fh:
            self.data = fh.read()
        self.records = self._read_index(self.inf_path)
        self.by_id: dict[int, IndexRecord] = {}
        for record in self.records:
            self.by_id.setdefault(record.sample_id, record)

    @staticmethod
    def _read_index(path) -> list[IndexRecord]:
        return read_index(path)

    def record_for(self, sample_id: int) -> IndexRecord | None:
        return self.by_id.get(sample_id)

    def decode(self, record: IndexRecord,
               truncate: bool | None = None) -> PxdSample:
        if truncate is None:
            truncate = self.truncate_default
        blob = self.data[record.offset:record.offset + record.length]
        return decode(blob, truncate=truncate)

    def decode_id(self, sample_id: int,
                  truncate: bool | None = None) -> PxdSample:
        record = self.record_for(sample_id)
        if record is None:
            raise KeyError('sample id %d not in %s' % (sample_id, self.inf_path))
        return self.decode(record, truncate=truncate)

    def __len__(self) -> int:
        return len(self.records)