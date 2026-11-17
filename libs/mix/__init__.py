"""Shared mix-format library: the contracts and the five parsers.

``contracts.py`` holds the standard-library ABCs each ``mixfmt.py``
subclasses.  The five subpackages (``dance``, ``rave``, ``hiphop``,
``dance2``, ``techno``) hold one parser each, used by the player in
``apps/emp`` and the PNG renderer in ``apps/emr``.
"""

from __future__ import annotations
