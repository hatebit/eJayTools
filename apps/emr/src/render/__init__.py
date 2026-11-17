"""Shared, format-neutral PNG arrangement renderer.

The engine knows the two eJay song shapes -- a fixed grid and a sequence of
pattern sections -- but no format name, signature or sample id.  Each format
tree supplies a small :class:`RenderFormat` provider; ``apps/emr/src/mixrender.py``
is the unified command and each ``apps/emr/src/format/<tree>/mixrender.py`` is a
fixed-format wrapper.  Nothing here imports numpy, the player core or a
format adapter, so the renderer stays standard-library only.
"""

