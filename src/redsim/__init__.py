"""Minecraft Java Edition 26.3 redstone simulator.

The simulation core (``redsim.core``, ``redsim.world``, ``redsim.sim``, ``redsim.io``) never
imports Qt. The PySide6 user interface lives in ``redsim.ui``.

Speed: ``python -m tools.build_compiled`` compiles the hot core with mypyc into
``build/compiled/<fingerprint>/``. It is used only while it was built from exactly the
current sources (the fingerprint covers every source file), so a stale build never runs;
``REDSIM_PURE=1`` turns it off.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

GAME_VERSION = "26.3"

PACKAGE = Path(__file__).resolve().parent  # always the sources, also with a compiled build
REPO_ROOT = PACKAGE.parents[1]  # data/, examples/ and build/ live here
COMPILED_ROOT = REPO_ROOT / "build" / "compiled"


def source_fingerprint() -> str:
    """A digest of every Python source of the package (names and contents)."""
    digest = hashlib.sha256()
    for path in sorted(PACKAGE.rglob("*.py")):
        digest.update(str(path.relative_to(PACKAGE)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def _use_compiled_build() -> str | None:
    """Put a matching compiled build in front of the sources; returns its folder."""
    if os.environ.get("REDSIM_PURE") or not COMPILED_ROOT.is_dir():
        return None
    build = COMPILED_ROOT / source_fingerprint()
    if not (build / "redsim").is_dir():
        return None
    sys.path.insert(0, str(build))  # mypyc's shared runtime module lives at its top
    __path__.insert(0, str(build / "redsim"))
    return str(build)


COMPILED = _use_compiled_build()
