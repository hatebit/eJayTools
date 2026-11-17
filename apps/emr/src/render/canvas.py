"""Standard-library PNG canvas and arrangement drawing.

The byte layout of the file and every pixel rule were moved here unchanged
from the four per-tree renderers: 8-bit RGB, filter type 0, zlib level 9, the
same 3x5 bitmap font, colours and margins.  That is what lets the refactored
renderer reproduce the existing PNGs exactly.
"""

from __future__ import annotations

import colorsys
import struct
import zlib

from apps.emr.src.render.layout import Layout

BG = (24, 24, 30)
TRACK_SEP = (52, 52, 62)
BEAT_LINE = (40, 40, 50)
BAR_LINE = (74, 74, 88)
TEXT = (196, 196, 206)
EMPTY_ROW = (34, 34, 42)

# 3x5 bitmap font: rows of 3 bits, '#' = ink
FONT = {
    '0': ('###', '#.#', '#.#', '#.#', '###'),
    '1': ('.#.', '##.', '.#.', '.#.', '###'),
    '2': ('###', '..#', '###', '#..', '###'),
    '3': ('###', '..#', '###', '..#', '###'),
    '4': ('#.#', '#.#', '###', '..#', '..#'),
    '5': ('###', '#..', '###', '..#', '###'),
    '6': ('###', '#..', '###', '#.#', '###'),
    '7': ('###', '..#', '..#', '..#', '..#'),
    '8': ('###', '#.#', '###', '#.#', '###'),
    '9': ('###', '#.#', '###', '..#', '###'),
    'T': ('###', '.#.', '.#.', '.#.', '.#.'),
    ' ': ('...', '...', '...', '...', '...'),
}


def write_png(path: str, width: int, height: int, rgb: bytearray) -> None:
    """Write an 8-bit RGB PNG with the standard library only."""
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0
        raw += rgb[y * stride:(y + 1) * stride]
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    blob = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', compressed) + chunk(b'IEND', b''))
    with open(path, 'wb') as fh:
        fh.write(blob)


class Canvas:
    """A tiny RGB raster with rectangle and bitmap-text operations."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.buf = bytearray(BG * (width * height))

    def rect(self, x0: int, y0: int, x1: int, y1: int, colour) -> None:
        x0 = max(0, min(self.width, x0))
        x1 = max(0, min(self.width, x1))
        y0 = max(0, min(self.height, y0))
        y1 = max(0, min(self.height, y1))
        if x1 <= x0 or y1 <= y0:
            return
        px = bytes(colour)
        run = px * (x1 - x0)
        for y in range(y0, y1):
            start = (y * self.width + x0) * 3
            self.buf[start:start + len(run)] = run

    def text(self, x: int, y: int, s: str, scale: int = 1, colour=TEXT) -> None:
        cx = x
        for ch in s.upper():
            glyph = FONT.get(ch)
            if glyph is None:
                cx += 4 * scale
                continue
            for row, bits in enumerate(glyph):
                for col, bit in enumerate(bits):
                    if bit == '#':
                        self.rect(cx + col * scale, y + row * scale,
                                  cx + (col + 1) * scale, y + (row + 1) * scale,
                                  colour)
            cx += 4 * scale


def colour_for(sample_id: int):
    """Stable, well-spread colour per sample id (golden-ratio hue steps)."""
    hue = (sample_id * 0.618033988749895) % 1.0
    sat = 0.72 if sample_id else 0.0
    r, g, b = colorsys.hsv_to_rgb(hue, sat, 0.98)
    return int(r * 255), int(g * 255), int(b * 255)


def draw(layout: Layout, path: str, cell_w: int = 0,
         cell_h: int = 18, bar_every: int = 4,
         label_every: int = 8) -> tuple[int, int]:
    """Draw one layout to ``path``; return ``(width, height)``."""
    bars = layout.bars
    if cell_w <= 0:
        # short songs get wide cells, long songs stay under ~2000 px
        cell_w = max(4, min(10, 900 // bars))
    margin_l, margin_t, margin_r, margin_b = 34, 16, 6, 6
    width = margin_l + bars * cell_w + margin_r
    height = margin_t + layout.track_count * cell_h + margin_b
    cv = Canvas(width, height)

    # alternating row bands + track separators
    for track in range(layout.track_count):
        y0 = margin_t + track * cell_h
        if track % 2 == 0:
            cv.rect(margin_l, y0, width - margin_r, y0 + cell_h, EMPTY_ROW)
        cv.rect(margin_l, y0, width - margin_r, y0 + 1, TRACK_SEP)
        cv.text(6, y0 + (cell_h - 5) // 2, 'T%d' % (track + 1), 1)

    # bar rulers: grid trees number from 0, section trees from 1
    if layout.bar_origin == 0:
        for bar in range(0, bars + 1, bar_every):
            x = margin_l + bar * cell_w
            if bar % label_every == 0:
                cv.rect(x, margin_t, x + 1, height - margin_b, BAR_LINE)
                cv.text(x + 1, 4, str(bar), 1)
            else:
                cv.rect(x, margin_t, x + 1, height - margin_b, BEAT_LINE)
    else:
        for bar in range(1, bars + 1, bar_every):
            x = margin_l + (bar - 1) * cell_w
            if (bar - 1) % label_every == 0:
                cv.rect(x, margin_t, x + 1, height - margin_b, BAR_LINE)
                cv.text(x + 1, 4, str(bar), 1)
            else:
                cv.rect(x, margin_t, x + 1, height - margin_b, BEAT_LINE)
    cv.rect(margin_l, margin_t, width - margin_r, margin_t + 1, TRACK_SEP)
    cv.rect(margin_l, height - margin_b, width - margin_r,
            height - margin_b + 1, TRACK_SEP)

    # records (one pixel gap at the end so the bar/track grid stays visible);
    # fractional starts are rounded to the pixel grid
    for span in layout.spans:
        x0 = margin_l + int(round(span.start * cell_w))
        x1 = margin_l + int(round(span.stop * cell_w)) - 1
        y0 = margin_t + span.track * cell_h + 1
        if x1 <= x0:
            x1 = x0 + 1
        cv.rect(x0, y0, x1, y0 + cell_h - 1, colour_for(span.sample_id))

    write_png(path, width, height, cv.buf)
    return width, height

