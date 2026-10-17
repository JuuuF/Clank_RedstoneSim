"""Progress reports of long operations (opening a world): ``report(stage, done, total)``.

The stages a world load reports, in order: ``read`` (the file), ``world`` (its blocks),
``history`` (recorded edits re-run, by tick), ``chunks`` (a Minecraft save's chunks) and
``meshes`` (the view's chunk meshes). A report may raise to cancel the operation.
"""

from __future__ import annotations

from collections.abc import Callable

Report = Callable[[str, int, int], None]

__all__ = ["Report"]
