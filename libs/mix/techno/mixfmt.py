"""Reader/writer for Techno eJay 2 ``*.MIX`` song files.

Reversed from the thirteen files in ``disks/Techno_eJay/MIX``.  Nothing here
executes the original binaries; it only reads data.  This module is
independent of the other eJay trees in ``apps/emp/src/format/``.

Layout summary (little-endian, offsets in bytes)
------------------------------------------------
    0x00  uint16  signature (0x0889 in every file seen)
    0x02  uint16  0
    0x04  uint16  ``field_04`` (varies per file; meaning unknown)
    0x06  uint16  0
    0x08  uint16  140 (bpm)
    0x0A  uint16  ``field_0a`` (134..158 in this corpus)
    0x0C  uint16  0
    0x0E  uint16  ``field_0e`` (24, 28 or 30 in this corpus)
    0x10  cstring author
          cstring identification string (``#SKKENNUNG#:0000000``)
          uint8   1, uint16 length, "title\\0\\x01"
          uint16  pan, uint16 volume          x 16 tracks
          uint16  x 6  (0, 0, 0, 0, 0, 14 or 16)
          cstring "Techno eJay 2 " + uint8 1 (two files say "Techno eJay ")
          uint16  9 (constant in this corpus)
          box list: uint32 lo, uint32 hi, uint16 length, "name\\0\\x01",
                    terminated by uint32 0, uint32 0
          pad prefix: two 12-byte empty pad records and a four-byte record
                     tag
          pad list:  uint8[4] record tag, uint16 sample id, uint16 length,
                     "name\\0\\x01", 8-byte word tail     x 10 pads
          pattern:  22-byte preamble, 17 section headers, then 7-byte clips
                     and 17-byte hits (see :func:`decode_pattern`)
          event list: 27-byte tail, uint16 length, "name\\0\\x01",
                     uint16 length, "number\\0\\x01"
          trailer:  uint32 0x018A7AA9 (``A9 7A 8A 01``)

The 16 track records carry a stereo assignment and a 16-bit volume.  The
reading 0 = both channels, 1 = left only, 2 = right only is the Dance eJay 2
one, supported here by the value range and by L/R pairs in the samples; one
word in the corpus is 3 (``SOAP.MIX`` track 16) and stays unexplained.  The
separate drum track (the extra track "0" in the eJay UI) is not in that table;
its ten Groove Generator pads are the pad records.

The ``pattern`` bytes are preserved verbatim, but :func:`decode_pattern`
exposes their structure: a 22-byte preamble, then seventeen headers of
``uint8 index, uint16 count, uint16 0``.  Sections 1-16 belong to the sixteen
audio tracks and hold ``count`` records in time order; section 17's count is
the number of imported events and carries no records.  Two record shapes are
interleaved, told apart by the word at offset 3: a seven-byte **clip**
(``uint8 byte0``, ``uint8 byte1``, negated ``int8`` two-bar block index,
``uint16 0xFFFF``, ``uint16`` sample id) and a seventeen-byte **hit**
(``uint32`` position, ``uint8 0``, ``uint16`` sample id, ten unknown bytes).
A clip starts at ``2 * |block| - 1 + (255 - byte1) / 128`` bars and a hit at
``position / 32768 + 1`` bars; both mappings are documented in ``FORMAT.md``.
With them, all 5 084 records across the corpus run in non-decreasing time
order inside their track.  ``byte0`` and a hit's trailing bytes remain
uninterpreted; playback (``mixplayer.py``) cuts a record where the next record
on its track starts, because no clip length is stored.

Arrangement sample ids index ``RAVE20.INF`` (``disks/Techno_eJay/EJAY/PXD``),
which numbers them 13000 .. 17014.  The ten drum-pad records carry id 0 and a
free-text name; they are not catalogue references in this corpus.  The uint16
at offset 5 of an event tail is not a catalogue id: it is >= 7200 and
increases from one event to the next, so it is exposed as ``Event.instance``.
"""

from __future__ import annotations

import os
import struct
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from libs.mix.contracts import SampleCatalog, SectionMix  # noqa: E402

SIGNATURE = 0x0889
TRAILER = b'\xa9\x7a\x8a\x01'
TRACKS = 16
PADS = 10
BPM = 140
BEATS_PER_BAR = 4

#: Four-byte tag that introduces a pad record (and the empty pad records).
RECORD_TAG = b'\x02\x00\x00\x01'
SAMPLE_SET = 'Techno eJay 2 '
PAN_BOTH, PAN_LEFT, PAN_RIGHT = 0, 1, 2
PAN_NAMES = {PAN_BOTH: 'both', PAN_LEFT: 'left', PAN_RIGHT: 'right'}

#: Event tail layout: uint8 kind, uint8 channel byte, int24 pitch,
#: uint16 instance, then 20 bytes whose meaning is unknown.
EVENT_TAIL_BYTES = 27

#: The pattern block opens with this many bytes of unresolved settings.
PATTERN_HEAD = 22
#: Sections 1-16 hold records; section 17 is the imported-event count.
NOTE_SECTIONS = 16
EVENT_SECTION = 17
#: A clip record: byte0, byte1, block, 0xFFFF and a sample id.
NOTE_BYTES = 7
#: A hit record: position, 0, sample id and ten unknown bytes.
HIT_BYTES = 17
#: A clip's block n covers bars 2n-1 and 2n; byte1 counts down inside it.
BLOCK_BARS = 2
#: Units of 1/128 bar per step of a clip's ``byte1`` (255 counts down).
CLIP_UNITS_PER_BAR = 128
#: Units of 1/32768 bar per unit of a hit's position word.
HIT_UNITS_PER_BAR = 0x8000


def _cstring(data: bytes, pos: int) -> tuple[str, int]:
    """Read a NUL-terminated latin-1 string."""
    end = data.index(b'\x00', pos)
    return data[pos:end].decode('latin-1'), end + 1


def _cstring_bytes(data: bytes, pos: int) -> tuple[bytes, int]:
    end = data.index(b'\x00', pos)
    return data[pos:end], end + 1


@dataclass
class Track:
    """One of the sixteen audio tracks: stereo assignment and volume."""

    pan: int = PAN_BOTH
    volume: int = 0

    @property
    def pan_name(self) -> str:
        return PAN_NAMES.get(self.pan, 'unknown')


@dataclass
class Box:
    """One installed sample kit and the id range the song credits to it."""

    lo: int
    hi: int
    name: str


@dataclass
class Pad:
    """One Groove Generator drum pad.

    ``sample_id`` is 0 in every Techno file seen; the catalogue id lives in
    the arrangement records, not here.  ``pitch`` is a signed
    transpose in semitones (seen -12..+6); ``word2`` and ``word3`` are two
    unresolved 16-bit words and ``word4`` is 0, 1 or 2 in this corpus.
    """

    sample_id: int
    name: str
    pitch: int = 0
    word2: int = 0
    word3: int = 0
    word4: int = 0

    def tail(self) -> bytes:
        return struct.pack('<hHHH', self.pitch, self.word2, self.word3,
                           self.word4)


@dataclass
class Event:
    """One placed imported sample on an audio track.

    The two strings are stored the way eJay's catalogue stores names.
    ``tail`` keeps the full 27 bytes; :attr:`kind`, :attr:`channel`,
    :attr:`pitch` and :attr:`instance` are the decoded leading fields.
    """

    name: str
    number: str = ''
    tail: bytes = b'\x00' * EVENT_TAIL_BYTES

    @property
    def kind(self) -> int:
        return self.tail[0]

    @property
    def channel(self) -> int:
        """Channel byte, 0x7F or 0xFF in every event seen (meaning unknown)."""
        return self.tail[1]

    @property
    def pitch(self) -> int:
        raw = self.tail[2] | (self.tail[3] << 8) | (self.tail[4] << 16)
        return raw - 0x1000000 if raw & 0x800000 else raw

    @property
    def instance(self) -> int:
        return struct.unpack_from('<H', self.tail, 5)[0]


@dataclass
class Note:
    """One pattern record, kept verbatim in ``raw``.

    The word at offset 3 selects the shape: ``0xFFFF`` marks a seven-byte
    **clip**, any other value a seventeen-byte **hit**.

    A clip is ``uint8 byte0`` (0 or 3), ``uint8 byte1``, ``int8 block``,
    ``uint16 0xFFFF`` and a ``uint16`` sample id.  ``block`` is negated and its
    magnitude indexes a two-bar block (block 1 = bars 1-2); ``byte1`` counts
    down in units of 1/128 bar inside that block, so the clip starts at
    ``2 * |block| - 1 + (255 - byte1) / 128`` (see :attr:`start_bar`).

    A hit is ``uint32 position`` (1/32768 bar per unit), ``uint8 0``, a
    ``uint16`` sample id and ten bytes of which eight are zero in every hit
    seen; the last two are uninterpreted.  ``byte0`` of a clip is also
    uninterpreted.
    """

    raw: bytes

    @property
    def is_hit(self) -> bool:
        """True for the seventeen-byte form."""
        return len(self.raw) == HIT_BYTES

    @property
    def byte0(self) -> int:
        return self.raw[0]

    @property
    def byte1(self) -> int:
        return self.raw[1]

    @property
    def block(self) -> int | None:
        """Two-bar block index of a clip (1..88 here), ``None`` for a hit."""
        if self.is_hit:
            return None
        return abs(struct.unpack_from('<b', self.raw, 2)[0])

    @property
    def word(self) -> int:
        return struct.unpack_from('<H', self.raw, 3)[0]

    @property
    def sample_id(self) -> int:
        return struct.unpack_from('<H', self.raw, 5)[0]

    @property
    def start_bar(self) -> float:
        """Start position in bars, counted from 1."""
        if self.is_hit:
            position = struct.unpack_from('<I', self.raw, 0)[0]
            return position / HIT_UNITS_PER_BAR + 1
        return (BLOCK_BARS * (abs(struct.unpack_from('<b', self.raw, 2)[0]) - 1)
                + 1 + (255 - self.byte1) / CLIP_UNITS_PER_BAR)

    @property
    def hit_tail(self) -> bytes:
        """The ten bytes after a hit's sample id (empty for a clip)."""
        return self.raw[NOTE_BYTES:]


@dataclass
class Section:
    """One header of a pattern block and, for sections 1-16, its records."""

    index: int
    notes: list[Note] = field(default_factory=list)
    tail_count: int = 0


def decode_pattern(data: bytes) -> list[Section] | None:
    """Decode a pattern block, or return ``None`` if it does not fit.

    All thirteen shipped blocks decode exactly, down to the block length.
    Structure and each record's start bar are decoded; the bytes are still
    written back verbatim from ``Mix.pattern``.
    """
    if len(data) < PATTERN_HEAD:
        return None
    pos = PATTERN_HEAD
    sections: list[Section] = []
    for index in range(1, EVENT_SECTION + 1):
        header = data[pos:pos + 5]
        if len(header) < 5 or header[0] != index or header[3] or header[4]:
            return None
        count = struct.unpack_from('<H', header, 1)[0]
        pos += 5
        if index == EVENT_SECTION:
            sections.append(Section(index, [], count))
            break
        notes: list[Note] = []
        for _ in range(count):
            head = data[pos:pos + NOTE_BYTES]
            if len(head) < NOTE_BYTES:
                return None
            size = (NOTE_BYTES
                    if struct.unpack_from('<H', head, 3)[0] == 0xFFFF
                    else HIT_BYTES)
            raw = data[pos:pos + size]
            if len(raw) < size:
                return None
            notes.append(Note(raw))
            pos += size
        sections.append(Section(index, notes))
    return sections if pos == len(data) else None


@dataclass
class Mix(SectionMix):
    """A complete Techno eJay 2 song file."""

    signature: int = SIGNATURE
    field_04: int = 0
    bpm: int = BPM
    field_0a: int = 0
    field_0e: int = 0
    author: str = ''
    ident: str = ''
    title: str = ''
    tracks: list[Track] = field(default_factory=lambda: [Track() for _ in range(TRACKS)])
    trailing_words: tuple[int, ...] = (0, 0, 0, 0, 0, TRACKS)
    sample_set: str = SAMPLE_SET
    marker: int = 9
    boxes: list[Box] = field(default_factory=list)
    pad_prefix: bytes = b''
    pads: list[Pad] = field(default_factory=list)
    pattern: bytes = b''
    events: list[Event] = field(default_factory=list)
    trailer: bytes = TRAILER

    # -- convenience -------------------------------------------------------
    @property
    def left_tracks(self) -> list[int]:
        return [i + 1 for i, t in enumerate(self.tracks) if t.pan == PAN_LEFT]

    @property
    def right_tracks(self) -> list[int]:
        return [i + 1 for i, t in enumerate(self.tracks) if t.pan == PAN_RIGHT]

    def bar_seconds(self) -> float:
        return BEATS_PER_BAR * 60.0 / self.bpm

    def pattern_sections(self) -> list[Section] | None:
        """Decoded drum-pattern sections, or ``None`` when undecodable."""
        return decode_pattern(self.pattern)

    # -- serialisation -----------------------------------------------------
    @classmethod
    def parse(cls, data: bytes) -> 'Mix':
        if len(data) < 0x40 or data[-4:] != TRAILER:
            raise ValueError('not a Techno eJay 2 MIX file (bad magic)')
        mix = cls()
        (mix.signature, zero_a, mix.field_04, zero_b, mix.bpm,
         mix.field_0a, zero_c, mix.field_0e) = struct.unpack_from('<8H', data, 0)
        if zero_a or zero_b or zero_c:
            raise ValueError('unexpected non-zero header word')

        pos = 16
        mix.author, pos = _cstring(data, pos)
        mix.ident, pos = _cstring(data, pos)
        if data[pos] != 1:
            raise ValueError('title record flag != 1')
        title_len = struct.unpack_from('<H', data, pos + 1)[0]
        if data[pos + 3 + title_len - 2:pos + 3 + title_len] != b'\x00\x01':
            raise ValueError('title record is not NUL+0x01 terminated')
        mix.title = data[pos + 3:pos + 3 + title_len - 2].decode('latin-1')
        pos += 3 + title_len

        mix.tracks = [Track(*struct.unpack_from('<HH', data, pos + 4 * i))
                      for i in range(TRACKS)]
        pos += 4 * TRACKS
        mix.trailing_words = struct.unpack_from('<6H', data, pos)
        pos += 12

        mix.sample_set, pos = _cstring(data, pos)
        if data[pos] != 1:
            raise ValueError('sample-set flag != 1')
        pos += 1
        mix.marker = struct.unpack_from('<H', data, pos)[0]
        pos += 2

        while True:
            lo, hi = struct.unpack_from('<II', data, pos)
            if lo == 0 and hi == 0:
                pos += 8
                break
            length = struct.unpack_from('<H', data, pos + 8)[0]
            name = data[pos + 10:pos + 10 + length]
            if name[-2:] != b'\x00\x01':
                raise ValueError('box name is not NUL+0x01 terminated')
            mix.boxes.append(Box(lo, hi, name[:-2].decode('latin-1')))
            pos += 10 + length

        prefix_start = pos
        while data[pos:pos + 4] == RECORD_TAG:
            sid, length = struct.unpack_from('<HH', data, pos + 4)
            if sid or length:
                break
            pos += 12
        if data[pos:pos + 4] != RECORD_TAG:
            raise ValueError('pad prefix marker missing')
        pos += 4
        mix.pad_prefix = data[prefix_start:pos]

        while data[pos:pos + 4] == RECORD_TAG:
            sid, length = struct.unpack_from('<HH', data, pos + 4)
            if not (2 <= length <= 200):
                break
            name = data[pos + 8:pos + 8 + length]
            if name[-2:] != b'\x00\x01' or b'\x00' in name[:-2]:
                break
            tail = data[pos + 8 + length:pos + 8 + length + 8]
            if len(tail) != 8:
                break
            pitch, word2, word3, word4 = struct.unpack('<hHHH', tail)
            mix.pads.append(Pad(sid, name[:-2].decode('latin-1'),
                                pitch, word2, word3, word4))
            pos += 8 + length + 8

        pad_end = pos
        event_start = _find_event_start(data, pad_end)
        mix.pattern = data[pad_end:event_start]

        pos = event_start
        while pos < len(data) - 4:
            tail = data[pos:pos + EVENT_TAIL_BYTES]
            pos += EVENT_TAIL_BYTES
            n1 = struct.unpack_from('<H', data, pos)[0]
            name = data[pos + 2:pos + 2 + n1]
            pos += 2 + n1
            n2 = struct.unpack_from('<H', data, pos)[0]
            number = data[pos + 2:pos + 2 + n2]
            pos += 2 + n2
            mix.events.append(Event(name[:-2].decode('latin-1'),
                                    number[:-2].decode('latin-1') if n2 else '',
                                    tail))
        if pos != len(data) - 4:
            raise ValueError('event list does not end at the trailer')
        return mix

    def build(self) -> bytes:
        out = bytearray(struct.pack('<8H', self.signature, 0, self.field_04,
                                    0, self.bpm, self.field_0a, 0,
                                    self.field_0e))
        out += self.author.encode('latin-1') + b'\x00'
        out += self.ident.encode('latin-1') + b'\x00'
        out += b'\x01' + _encode_name(self.title)
        for track in self.tracks:
            out += struct.pack('<HH', track.pan, track.volume)
        out += struct.pack('<6H', *self.trailing_words)
        out += self.sample_set.encode('latin-1') + b'\x00\x01'
        out += struct.pack('<H', self.marker)
        for box in self.boxes:
            out += struct.pack('<II', box.lo, box.hi)
            out += _encode_name(box.name)
        out += b'\x00' * 8
        out += self.pad_prefix
        for pad in self.pads:
            out += RECORD_TAG + struct.pack('<HH', pad.sample_id,
                                            len(pad.name) + 2)
            out += pad.name.encode('latin-1') + b'\x00\x01'
            out += pad.tail()
        out += self.pattern
        for event in self.events:
            out += event.tail
            out += _encode_name(event.name)
            out += _encode_name(event.number)
        out += self.trailer
        return bytes(out)


def _encode_name(text: str) -> bytes:
    """uint16 length followed by text, NUL and the 0x01 flag byte."""
    raw = text.encode('latin-1')
    return struct.pack('<H', len(raw) + 2) + raw + b'\x00\x01'


def _valid_record(data: bytes, pos: int) -> tuple[int, int] | None:
    """Length of the event record at ``pos``, or ``None`` if it is not one."""
    end = len(data) - 4
    if pos + EVENT_TAIL_BYTES + 4 > end:
        return None
    tail = data[pos:pos + EVENT_TAIL_BYTES]
    if tail[0] != 2 or tail[1] not in (0x7F, 0xFF):
        return None
    p = pos + EVENT_TAIL_BYTES
    n1 = struct.unpack_from('<H', data, p)[0]
    if not (2 <= n1 <= 80) or p + 2 + n1 > end:
        return None
    s1 = data[p + 2:p + 2 + n1]
    if s1[-2:] != b'\x00\x01' or b'\x00' in s1[:-2]:
        return None
    p += 2 + n1
    n2 = struct.unpack_from('<H', data, p)[0]
    if n2 > 80 or p + 2 + n2 > end:
        return None
    s2 = data[p + 2:p + 2 + n2]
    if n2 and (s2[-2:] != b'\x00\x01' or b'\x00' in s2[:-2]):
        return None
    return p + 2 + n2 - pos


def _find_event_start(data: bytes, start: int) -> int:
    """Offset of the first event record: the best chain that ends at the trailer."""
    best_pos, best_count = -1, 0
    for candidate in range(start, len(data) - EVENT_TAIL_BYTES - 4):
        pos, count = candidate, 0
        while pos < len(data) - 4 and data[pos:pos + 4] != TRAILER:
            length = _valid_record(data, pos)
            if length is None:
                break
            pos += length
            count += 1
        if pos == len(data) - 4 and count > best_count:
            best_pos, best_count = candidate, count
    if best_pos < 0:
        # HOUSE, LATIN, OTHER, TRANCE and TRIBUTE carry no imported-sample
        # events: the pattern block runs straight into the trailer.
        return len(data) - 4
    return best_pos


# --------------------------------------------------------------------------
# sample catalogue (RAVE20.INF) for labels
# --------------------------------------------------------------------------
@dataclass
class SampleRecord:
    """One record of a Techno eJay 2 ``*.INF`` sample index."""

    sample_id: int
    bank: int
    file: str
    offset: int
    length: int
    group: str
    name: str
    flag1: int
    flag2: int

    @property
    def label(self) -> str:
        return ('%s %s' % (self.group, self.name)).strip() or self.file


class Catalog(SampleCatalog):
    """The ``RAVE20.INF`` index, used to label arrangement sample ids."""

    def __init__(self, inf_path):
        import os
        self.inf_path = os.fspath(inf_path)
        self.records: list[SampleRecord] = []
        self.by_id: dict[int, SampleRecord] = {}
        if os.path.exists(self.inf_path):
            self._read()

    def _read(self) -> None:
        with open(self.inf_path, 'rb') as fh:
            text = fh.read().decode('latin-1')
        lines = [line.strip() for line in text.splitlines()]
        try:
            start = lines.index('[SAMPLES]') + 1
        except ValueError:
            return
        body = lines[start:]
        for i in range(0, len(body) - 11, 12):
            fields = [f.strip('"') for f in body[i:i + 12]]
            try:
                record = SampleRecord(int(fields[0]), int(fields[1]),
                                      fields[2], int(fields[3]),
                                      int(fields[4]), fields[5], fields[6],
                                      int(fields[7]), int(fields[8]))
            except ValueError:
                continue
            self.records.append(record)
            self.by_id.setdefault(record.sample_id, record)

    def record_for(self, sample_id: int) -> SampleRecord | None:
        return self.by_id.get(sample_id)


def techno_catalog(root) -> Catalog:
    """The catalogue at ``disks/Techno_eJay/EJAY/PXD/RAVE20.INF``."""
    import os
    root = os.fspath(root)
    return Catalog(os.path.join(root, 'EJAY', 'PXD', 'RAVE20.INF'))


def read_mix(path) -> Mix:
    with open(path, 'rb') as fh:
        return Mix.parse(fh.read())


def write_mix(mix: Mix, path) -> None:
    with open(path, 'wb') as fh:
        fh.write(mix.build())


