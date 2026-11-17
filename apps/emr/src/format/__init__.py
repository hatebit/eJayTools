"""One PNG provider per eJay format tree.

Each subpackage (``dance``, ``rave``, ``hiphop``, ``dance2``, ``techno``)
supplies only its tree's catalogue, bar length and default output; the drawing
engine in ``apps/emr/src/render/`` knows no format name.
"""

from __future__ import annotations
