"""Player ports and one runtime package per eJay format.

``ports.py`` holds the player-facing ABCs.  The five subpackages (``dance``,
``rave``, ``hiphop``, ``dance2``, ``techno``) are independent runtimes: the
adapter and, for the section family, the `.INF` banks.  The shared mix
contracts and parsers live in ``libs/mix/``; the PNG renderers live in
``apps/emr/src/format/``.
"""

from __future__ import annotations
