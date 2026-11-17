"""Shared headless player core for the eJay ``*.MIX`` format trees.

The core knows nothing about a specific format: adapters live in
``apps/emp/src/format/<tree>/adapter.py`` and the composition roots are
``apps/emp/src/formats.py`` and ``apps/emp/src/mixplayer.py``.
"""

from __future__ import annotations

