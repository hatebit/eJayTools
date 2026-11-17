"""Reader/writer for HipHop eJay 1.x ``*.MIX`` song files.

Reversed from the files in ``disks/Hiphop_eJay/MIX`` (see FORMAT.md for the
derived layout).  Nothing here executes the original binaries; it only reads
data.

Layout summary
--------------
    0x0000  uint16   signature (0x0A08 in every file seen)
    0x0002  702*8*uint16  song grid: bar-major, 8 16-bit sample ids per bar
    0x2BE2  (always) appended sample-bank block, see BankBlock

Sample ids index the catalogue lists: ``SPECIAL`` (ids 1..101) and the
``HIPHOP/EJAY/PXD`` bank (``731 + record``).  ``MAX`` is a folder-sorted
manifest, not the id order.  Tempo is not stored: the samples are cut at
**96 BPM 4/4**, so a bar is 110 250 samples at 44.1 kHz.
"""

from __future__ import annotations

import os
import struct
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from libs.mix.contracts import (BankBlockDocument, GridMix,  # noqa: E402
                                           SampleCatalog)

SIGNATURE = 0x0A08
TRACKS = 8
BARS = 702  # 0x2BE2 == 2 + BARS*TRACKS*2
SONG_BYTES = 2 + BARS * TRACKS * 2
BPM = 96
BEATS_PER_BAR = 4
BAR_SAMPLES = 44100 * BEATS_PER_BAR * 60 // BPM  # 110 250, exact at 96 BPM

#: Signature of the bank block (the same tag the song header uses).
BANK_SIGNATURE = 0x0A08

#: Two 704-byte tables sit between the version string and the track table.
#: Each begins with the word 350 and is otherwise zero in all 17 files.
TABLE_BYTES = 704
TABLES_BYTES = 2 * TABLE_BYTES
TABLES_FIRST_WORD = 350

#: Pan words stored per track: 0 centre, 1 left, 2 right.
PAN_CENTRE = 0
PAN_LEFT = 1
PAN_RIGHT = 2
PAN_NAMES = {PAN_CENTRE: 'C', PAN_LEFT: 'L', PAN_RIGHT: 'R'}


def _empty_tables() -> bytes:
    """The two constant tables as observed: word 350 then 702 zero bytes."""
    half = struct.pack('<H', TABLES_FIRST_WORD) + b'\x00' * (TABLE_BYTES - 2)
    return half * 2


# --------------------------------------------------------------------------
# sample bank block (always appended after the song grid)
# --------------------------------------------------------------------------
@dataclass
class BankBlock(BankBlockDocument):
    """The sample-bank description a song was saved with.

    After the tag, list count and version string (the same shape the Dance
    ``0x0A08`` block uses) the HipHop block carries more than Dance does:

    ``tables``       1 408 bytes, two 704-byte tables.  Each starts with the
                     word 350 and is zero for the remaining 702 bytes in every
                     file of the corpus; they are kept verbatim because their
                     purpose is not established (FORMAT.md §4).
    ``head``         four ``uint16``; ``[1, X, 0, 0]`` in every file.  ``X``
                     takes six values across the 17 files and is 11 025 in
                     twelve of them; meaning unknown.
    ``track_count``  ``8`` in every file.
    ``pan``          one word per track: 0 centre, 1 left, 2 right.  The
                     default is ``[0]*6 + [1, 2]`` and some songs deviate.
    """

    signature: int = BANK_SIGNATURE
    nlists: int = 1
    version: str = 'HipHop eJay 1.01'
    version_flag: int = 1
    tables: bytes = field(default_factory=_empty_tables)
    head: list[int] = field(default_factory=lambda: [1, 11025, 0, 0])
    track_count: int = TRACKS
    pan: list[int] = field(default_factory=lambda: [0] * 6 + [1, 2])

    @classmethod
    def parse(cls, data: bytes) -> 'BankBlock':
        if len(data) < 6:
            raise ValueError('truncated bank block')
        signature, nlists, length = struct.unpack_from('<HHH', data, 0)
        if signature != BANK_SIGNATURE:
            raise ValueError('unexpected bank signature 0x%04x' % signature)
        if 6 + length > len(data):
            raise ValueError('truncated version string')
        raw = data[6:6 + length]
        version = raw.split(b'\x00')[0].decode('latin-1')
        version_flag = raw[-1] if length else 1
        pos = 6 + length
        tables = data[pos:pos + TABLES_BYTES]
        if len(tables) != TABLES_BYTES:
            raise ValueError('truncated bank tables')
        pos += TABLES_BYTES
        if pos + 8 + 2 + 2 * TRACKS > len(data):
            raise ValueError('truncated bank trailer')
        head = list(struct.unpack_from('<4H', data, pos))
        pos += 8
        (track_count,) = struct.unpack_from('<H', data, pos)
        pos += 2
        pan = list(struct.unpack_from('<%dH' % TRACKS, data, pos))
        pos += 2 * TRACKS
        if pos != len(data):
            raise ValueError('%d trailing bytes after the bank block' % (len(data) - pos))
        return cls(signature, nlists, version, version_flag, tables, head,
                   track_count, pan)

    def build(self) -> bytes:
        if len(self.tables) != TABLES_BYTES:
            raise ValueError('bank tables must be %d bytes' % TABLES_BYTES)
        raw = self.version.encode('latin-1') + b'\x00' + bytes([self.version_flag])
        out = bytearray(struct.pack('<HHH', self.signature, self.nlists, len(raw)))
        out += raw
        out += self.tables
        out += struct.pack('<4H', *self.head)
        out += struct.pack('<H', self.track_count)
        out += struct.pack('<%dH' % TRACKS, *self.pan)
        return bytes(out)

    def pan_name(self, track: int) -> str:
        """``C``, ``L`` or ``R`` for a track, ``?`` for an unknown word."""
        return PAN_NAMES.get(self.pan[track], '?')


# --------------------------------------------------------------------------
# song
# --------------------------------------------------------------------------
@dataclass
class Mix(GridMix):
    signature: int = SIGNATURE
    #: ``grid[bar][track]``, sample id or 0 for an empty slot
    grid: list[list[int]] = field(default_factory=lambda: [[0] * TRACKS for _ in range(BARS)])
    bank: BankBlock | None = None

    # -- convenience -------------------------------------------------------
    @property
    def song_length(self) -> int:
        """Number of bars up to and including the last non-empty slot."""
        for bar in range(BARS - 1, -1, -1):
            if any(self.grid[bar]):
                return bar + 1
        return 0

    @property
    def pan(self) -> list[int]:
        """Per-track pan words from the bank block (all centre if absent)."""
        return list(self.bank.pan) if self.bank else [PAN_CENTRE] * TRACKS

    def duration(self) -> float:
        return self.song_length * BEATS_PER_BAR * 60.0 / BPM

    def used_samples(self) -> list[int]:
        return sorted({v for bar in self.grid for v in bar if v})

    def track_usage(self) -> list[tuple[int, int]]:
        """Placed samples and distinct ids per track, T1 first."""
        placed = [0] * TRACKS
        distinct = [set() for _ in range(TRACKS)]
        for _bar, track, sample_id in self.events():
            placed[track] += 1
            distinct[track].add(sample_id)
        return [(placed[i], len(distinct[i])) for i in range(TRACKS)]

    def events(self):
        """Yield ``(bar, track, sample_id)`` for every placed sample."""
        for bar, slots in enumerate(self.grid):
            for track, sid in enumerate(slots):
                if sid:
                    yield bar, track, sid

    # -- serialisation -----------------------------------------------------
    @classmethod
    def parse(cls, data: bytes) -> 'Mix':
        if len(data) < SONG_BYTES:
            raise ValueError('file shorter than the %d byte song grid' % SONG_BYTES)
        (signature,) = struct.unpack_from('<H', data, 0)
        body = struct.unpack_from('<%dH' % (BARS * TRACKS), data, 2)
        grid = [list(body[i * TRACKS:(i + 1) * TRACKS]) for i in range(BARS)]
        bank = BankBlock.parse(data[SONG_BYTES:]) if len(data) > SONG_BYTES else None
        return cls(signature, grid, bank)

    def build(self) -> bytes:
        out = bytearray(struct.pack('<H', self.signature))
        for bar in self.grid:
            out += struct.pack('<%dH' % TRACKS, *bar)
        if self.bank is not None:
            out += self.bank.build()
        return bytes(out)


# --------------------------------------------------------------------------
# sample catalogue (PXD / SPECIAL lists) and PXD name lookup
# --------------------------------------------------------------------------
#: Sample slots eJay reserves before the ``HIPHOP/EJAY/PXD`` bank.
BANK_BASE = 731
#: First id of the ``SPECIAL`` WAV list.
SPECIAL_BASE = 1


@dataclass
class BankRecord:
    """One slot of eJay's sample bank list."""

    path: str
    category: str
    number: str
    group: str
    name: str

    @property
    def label(self) -> str:
        """Name as the browser shows it, e.g. ``dirty slurpy the one``."""
        return ('%s %s' % (self.group, self.name)).strip() or self.path


class Catalog(SampleCatalog):
    """One sample catalogue list and the directory its audio files live in.

    A list is eJay's six quoted fields per record (path, empty, category,
    number, group, name), CRLF separated.  ``base`` is the id of the first
    record, so id ``base + n`` is record ``n``.  Record paths are relative to
    ``sample_dir``; a path without a suffix is read as a ``.WAV`` stem, which
    is how the ``SPECIAL`` list stores ``special\\hxdrum01`` for
    ``SPECIAL/HXDRUM01.WAV``.  ``prefix`` is prepended to the displayed path.

    ``MAX``/``MIN`` are installation manifests in a different, folder-sorted
    order; they are not catalogue lists and are not needed for id lookup.
    """

    def __init__(self, list_path, sample_dir, base, prefix: str = ''):
        import os
        self.list_path = os.fspath(list_path)
        self.sample_dir = os.fspath(sample_dir)
        self.base = int(base)
        self.prefix = prefix
        self.records = self._read(self.list_path)
        self._disk = {}
        for dirpath, _dirnames, filenames in os.walk(self.sample_dir):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                self._disk[os.path.normcase(os.path.normpath(full))] = full

    def _read(self, path) -> list[BankRecord]:
        import os
        if not os.path.exists(path):
            return []
        with open(path, 'rb') as fh:
            lines = [ln.strip() for ln in fh.read().decode('latin-1').splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        if len(lines) % 6:
            raise ValueError('%s: %d lines is not a multiple of 6'
                             % (path, len(lines)))
        records = []
        for i in range(0, len(lines), 6):
            fields = [f.strip('"') for f in lines[i:i + 6]]
            path_, _blank, category, number, group, name = fields
            rel = path_.replace('\\', '/')
            if not os.path.splitext(rel)[1]:
                rel = os.path.basename(rel) + '.WAV'
            records.append(BankRecord(rel, category, number, group, name))
        return records

    def record_for(self, sample_id: int) -> "BankRecord | None":
        """Record for ``sample_id`` if this list covers it, else ``None``."""
        index = sample_id - self.base
        if 0 <= index < len(self.records):
            return self.records[index]
        return None

    def path_for(self, sample_id: int) -> str | None:
        """Displayed relative path (``SPECIAL/HXDRUM01.WAV`` style) or ``None``."""
        record = self.record_for(sample_id)
        return self.prefix + record.path if record is not None else None

    def abs_path(self, sample_id: int) -> str | None:
        """Path of the sample file on disk, or ``None`` if it is not there."""
        import os
        record = self.record_for(sample_id)
        if record is None:
            return None
        key = os.path.normcase(os.path.normpath(
            os.path.join(self.sample_dir, record.path)))
        return self._disk.get(key)


class Catalogs:
    """An ordered set of catalogues; ids resolve through the first match.

    The HipHop installation contributes two independent lists: the regular
    ``.PXD`` bank (``HIPHOP/EJAY/PXD``, ids from 731) and ``SPECIAL`` (WAV
    samples, ids from 1).  More lists can be appended with :meth:`add`, which
    is how the player takes further catalogues for other installations.
    """

    def __init__(self, catalogs=()):
        self.catalogs = list(catalogs)
        self._name_cache: dict[str, str | None] = {}

    def add(self, list_path, sample_dir, base, prefix: str = '') -> Catalog:
        """Append a catalogue list, its sample directory and its first id."""
        catalog = Catalog(list_path, sample_dir, base, prefix)
        self.catalogs.append(catalog)
        return catalog

    def extend(self, catalogs) -> None:
        """Append every catalogue of another :class:`Catalogs` set."""
        self.catalogs.extend(catalogs.catalogs)

    def find(self, sample_id: int) -> "tuple[Catalog, BankRecord] | None":
        """First ``(catalog, record)`` covering ``sample_id``, if any."""
        for catalog in self.catalogs:
            record = catalog.record_for(sample_id)
            if record is not None:
                return catalog, record
        return None

    def record_for(self, sample_id: int) -> "BankRecord | None":
        """Sample record for an id, from the first catalogue that has it."""
        found = self.find(sample_id)
        return found[1] if found is not None else None

    def path_for(self, sample_id: int) -> str | None:
        """Displayed relative path from the first catalogue that has the id."""
        found = self.find(sample_id)
        return found[0].path_for(sample_id) if found is not None else None

    def abs_path(self, sample_id: int) -> str | None:
        found = self.find(sample_id)
        return found[0].abs_path(sample_id) if found is not None else None

    def sample_name(self, sample_id: int) -> str | None:
        """Browser label from the first catalogue that has the id."""
        found = self.find(sample_id)
        return found[1].label if found is not None else None

    def header_name(self, sample_id: int) -> str | None:
        """Name stored in the ``PXD`` header (``tPxD`` + length + name)."""
        import os
        rel = self.path_for(sample_id)
        if rel is None:
            return None
        if rel in self._name_cache:
            return self._name_cache[rel]
        path = self.abs_path(sample_id)
        name = None
        if path and os.path.exists(path):
            with open(path, 'rb') as fh:
                head = fh.read(160)
            if head[:4] == b'tPxD':
                length = head[4]
                name = head[5:5 + length].decode('latin-1')
                name = name.replace('\r', ' ').replace('\n', ' ').rstrip('\x00')
        self._name_cache[rel] = name
        return name

    def describe(self, sample_id: int) -> dict:
        """Resolve a sample id to ``{id, path, name, category, number, group}``."""
        info = {'id': sample_id, 'path': None, 'name': None,
                'category': None, 'number': None, 'group': None}
        found = self.find(sample_id)
        if found is not None:
            info.update(path=found[0].path_for(sample_id), name=found[1].label,
                        category=found[1].category, number=found[1].number,
                        group=found[1].group)
        return info


def hiphop_catalogs(root) -> Catalogs:
    """The two HipHop eJay catalogues: the ``.PXD`` bank and ``SPECIAL`` WAVs."""
    import os
    root = os.fspath(root)
    hiphop = os.path.join(root, 'HIPHOP')
    return Catalogs([
        Catalog(os.path.join(hiphop, 'EJAY', 'PXD'), hiphop, BANK_BASE),
        Catalog(os.path.join(hiphop, 'EJAY', 'SPECIAL'),
                os.path.join(root, 'SPECIAL'), SPECIAL_BASE, 'SPECIAL/'),
    ])


# --------------------------------------------------------------------------
# plain helpers
# --------------------------------------------------------------------------
def read_mix(path) -> Mix:
    with open(path, 'rb') as fh:
        return Mix.parse(fh.read())


def write_mix(mix: Mix, path) -> None:
    with open(path, 'wb') as fh:
        fh.write(mix.build())


def bar_seconds() -> float:
    return BEATS_PER_BAR * 60.0 / BPM

