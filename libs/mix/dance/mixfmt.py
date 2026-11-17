"""Reader/writer for Dance eJay 1.x ``*.MIX`` song files.

Reversed from the files in ``disks/Dance_eJay/MIX`` (see FORMAT.md for the derived
layout).  Nothing here executes the original binaries; it only reads data.

Layout summary
--------------
    0x0000  uint16   signature (0x0A06 in every file seen)
    0x0002  702*8*uint16  song grid: bar-major, 8 16-bit sample ids per bar
    0x2BE2  (optional) appended sample-bank block, see BankBlock

Sample ids index the catalogue lists: ``SPECIAL`` (ids 1..168) and the
``PXDDANCE`` bank (``731 + record``), with add-on boxes named by a song's
bank block.  ``MAX`` is a folder-sorted manifest, not the id order.
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

SIGNATURE = 0x0A06
TRACKS = 8
BARS = 702  # 0x2BE2 == 2 + BARS*TRACKS*2
SONG_BYTES = 2 + BARS * TRACKS * 2
BPM = 140
BEATS_PER_BAR = 4

#: Signature of the "new" (0x0A08) bank-block variant.
BANK_SIG_V8 = 0x0A08
BANK_SIG_V6 = 0x0A06

#: Fixed suffix the 0x0A08 writer puts after the box lists: WORD 8 (track
#: count), 12 zero bytes, WORD 1, WORD 2.
DEFAULT_EPILOGUE = struct.pack('<H', 8) + b'\x00' * 12 + struct.pack('<HH', 1, 2)


# --------------------------------------------------------------------------
# sample bank block (part appended after the song grid)
# --------------------------------------------------------------------------
@dataclass
class Box:
    """A sample box (add-on sample CD) covering sample ids ``lo..hi``."""

    lo: int
    hi: int
    name: str
    flag: int = 1  # 0x0A08 variant only: byte stored after the name


@dataclass
class BankBlock(BankBlockDocument):
    """Description of the sample boxes a song was made with.

    The block holds ``nlists`` lists of boxes.  The first list is the one the
    song uses; when a second list is present it is empty in all files seen.
    ``variant`` is ``"v6"`` (signature 0x0A06: names stored as raw characters)
    or ``"v8"`` (signature 0x0A08: every name followed by NUL + a 0x01 flag
    byte, plus an 18-byte suffix).
    """

    variant: str
    signature: int
    nlists: int
    version: str
    lists: list[list[Box]] = field(default_factory=list)
    epilogue: bytes = b''
    version_flag: int = 1

    @property
    def boxes(self) -> list[Box]:
        """Boxes of the first list (the ones the song references)."""
        return self.lists[0] if self.lists else []

    @classmethod
    def parse(cls, data: bytes) -> "BankBlock":
        signature, nlists, length = struct.unpack_from('<HHH', data, 0)
        variant = 'v8' if signature == BANK_SIG_V8 else 'v6'
        pos = 6
        version = _read_name(data, pos, length, variant)
        version_flag = data[pos + length - 1] if variant == 'v8' else 1
        pos += length
        lists = []
        for _ in range(nlists):
            (count,) = struct.unpack_from('<H', data, pos)
            pos += 2
            boxes = []
            for _ in range(count):
                lo, hi, blen = struct.unpack_from('<HHH', data, pos)
                pos += 6
                name = _read_name(data, pos, blen, variant)
                flag = data[pos + blen - 1] if variant == 'v8' else 1
                pos += blen
                boxes.append(Box(lo, hi, name, flag))
            lists.append(boxes)
        return cls(variant, signature, nlists, version, lists, data[pos:], version_flag)

    def build(self) -> bytes:
        out = bytearray(struct.pack('<HHH', self.signature, self.nlists, 0))
        out += _encode_name(self.version, self.variant, self.version_flag)
        struct.pack_into('<H', out, 4, len(out) - 6)
        for boxes in self.lists:
            out += struct.pack('<H', len(boxes))
            for box in boxes:
                out += struct.pack('<HHH', box.lo, box.hi, 0)
                start = len(out)
                out += _encode_name(box.name, self.variant, box.flag)
                struct.pack_into('<H', out, start - 2, len(out) - start)
        out += self.epilogue
        return bytes(out)

    def box_for(self, sample_id: int) -> Box | None:
        for boxes in self.lists:
            for box in boxes:
                if box.lo <= sample_id <= box.hi:
                    return box
        return None


def _read_name(data: bytes, pos: int, length: int, variant: str) -> str:
    raw = data[pos:pos + length]
    if variant == 'v8':
        raw = raw.split(b'\x00')[0]
    return raw.decode('latin-1')


def _encode_name(name: str, variant: str, flag: int) -> bytes:
    raw = name.encode('latin-1')
    if variant == 'v8':
        return raw + b'\x00' + bytes([flag])
    return raw


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
    def parse(cls, data: bytes) -> "Mix":
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
# sample catalogue (MAX file) and PXD name lookup
# --------------------------------------------------------------------------
#: Sample slots eJay reserves before ``PXDDANCE`` (base/import banks).
BANK_BASE = 731


@dataclass
class BankRecord:
    """One slot of eJay's sample bank list (``DANCE/EJAY/PXDDANCE``)."""

    path: str
    category: str
    number: str
    group: str
    name: str

    @property
    def label(self) -> str:
        """Name as the browser shows it, e.g. ``Myth * L Cut 2``."""
        return ('%s %s' % (self.group, self.name)).strip() or self.path


class Catalog(SampleCatalog):
    """One sample catalogue list and the directory its audio files live in.

    A list is eJay's six quoted fields per record (path, empty, category,
    number, group, name), CRLF separated.  ``base`` is the id of the first
    record, so id ``base + n`` is record ``n``.  Record paths are relative to
    ``sample_dir``; a path without a suffix is read as a ``.WAV`` stem, which
    is how the ``SPECIAL`` list stores ``special\\D5BS735`` for
    ``SPECIAL/D5BS735.WAV``.  ``prefix`` is prepended to the displayed path.

    ``MAX``/``MIN`` are installation manifests in a different, folder-sorted
    order; they are not catalogue lists and are not needed for id lookup.
    Ids past every catalogue belong to add-on sample boxes, which the ``.MIX``
    bank block names.
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
        """Displayed relative path (``SPECIAL/D5BS735.WAV`` style) or ``None``."""
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

    The Dance installation contributes two independent lists: the regular
    ``.PXD`` bank (``PXDDANCE``, ids from 731) and ``SPECIAL`` (WAV samples,
    ids from 1).  More lists can be appended with :meth:`add`, which is how
    the player takes further catalogues for other installations or sets.
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

    def describe(self, sample_id: int, bank: BankBlock | None = None) -> dict:
        """Resolve a sample id to ``{id, path, name, box}``."""
        info = {'id': sample_id, 'path': None, 'name': None, 'box': None,
                'category': None, 'number': None, 'group': None}
        found = self.find(sample_id)
        if found is not None:
            info.update(path=found[0].path_for(sample_id), name=found[1].label,
                        category=found[1].category, number=found[1].number,
                        group=found[1].group)
            return info
        if bank is not None:
            box = bank.box_for(sample_id)
            if box is not None:
                info['box'] = box.name
                info['name'] = '%s + %d' % (box.name, sample_id - box.lo)
        return info


def dance_catalogs(root) -> Catalogs:
    """The two Dance eJay catalogues: the ``.PXD`` bank and ``SPECIAL`` WAVs."""
    import os
    root = os.fspath(root)
    dance = os.path.join(root, 'DANCE')
    return Catalogs([
        Catalog(os.path.join(dance, 'EJAY', 'PXDDANCE'), dance, BANK_BASE),
        Catalog(os.path.join(dance, 'EJAY', 'SPECIAL'),
                os.path.join(root, 'SPECIAL'), 1, 'SPECIAL/'),
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

