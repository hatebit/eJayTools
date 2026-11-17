"""Shared decoder for eJay ``.PXD`` samples and their ``.INF`` bundles.One implementation for the Dance, Rave, HipHop, Dance 2 and Techno trees; every
tree decodes through this package.  Run ``python libs/pxd`` (or
``python -m libs.pxd`` from the repository root) for a generic command
line.
"""

from __future__ import annotations

from .bundle import Bundle, IndexRecord, read_index
from .codec import (DELTA_TABLE, ENTRIES_PER_TABLE, MARKER, MAX_DEFINED,
                    SAMPLE_RATE, SENTINEL, TABLE_SLOTS, PxdSample, decode,
                    decode_file, delta_table, write_wav)

__all__ = [
    'Bundle', 'IndexRecord', 'read_index',
    'DELTA_TABLE', 'ENTRIES_PER_TABLE', 'MARKER', 'MAX_DEFINED', 'SAMPLE_RATE',
    'SENTINEL', 'TABLE_SLOTS', 'PxdSample', 'decode', 'decode_file',
    'delta_table', 'write_wav',
]
