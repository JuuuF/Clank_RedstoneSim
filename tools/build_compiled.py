"""Compile the simulator's hot core with mypyc (optional, for speed).

    python -m tools.build_compiled          # build (needs mypy and a C compiler)
    python -m tools.build_compiled --clean  # remove every compiled build

The build goes to ``build/compiled/<fingerprint>/`` (a copy of ``src/redsim`` with the
compiled modules next to their sources); ``redsim`` uses it only while the fingerprint
matches the current sources, so editing any source file falls back to plain Python until
the next build. Measured 2026-10-13: pistons on observer clocks 1.5×, dust update storms
1.7× faster (``python -m tools.bench``).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "redsim"

#: Modules compiled with mypyc: the engine core and the block behaviors. Not compiled:
#: ``sim/engine.py`` (a mypyc internal error), ``core/direction.py`` (its Enum crashes the
#: compiled module), ``world/blocks/foreign.py`` and ``__init__`` files, the editor, I/O and UI.
MODULES = [
    "core/pos.py",
    "core/javahash.py",
    "sim/neighbor_updater.py",
    "sim/ticks.py",
    "sim/level.py",
    "sim/trace.py",
    "world/block.py",
    "world/block_entity.py",
    "world/shape.py",
    "world/properties.py",
    *(
        f"world/blocks/{path.name}"
        for path in sorted((SOURCE / "world" / "blocks").glob("*.py"))
        if path.name not in ("__init__.py", "foreign.py")
    ),
]


def build() -> Path:
    sys.path.insert(0, str(ROOT / "src"))
    from redsim import COMPILED_ROOT, source_fingerprint

    target = COMPILED_ROOT / source_fingerprint()
    if (target / "redsim").is_dir():
        print(f"Up to date: {target}")
        return target
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copytree(SOURCE, work / "redsim", ignore=shutil.ignore_patterns("__pycache__"))
        command = [sys.executable, "-m", "mypyc", *(f"redsim/{m}" for m in MODULES)]
        result = subprocess.run(command, cwd=work, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout[-4000:], result.stderr[-4000:])
            raise SystemExit("mypyc failed (the sources run as plain Python as before).")
        shutil.rmtree(work / "build", ignore_errors=True)
        for leftover in work.rglob("*.c"):
            leftover.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(work, target)
    print(f"Built {len(MODULES)} modules into {target}")
    return target


def clean() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from redsim import COMPILED_ROOT

    shutil.rmtree(COMPILED_ROOT, ignore_errors=True)
    print(f"Removed {COMPILED_ROOT}")


if __name__ == "__main__":
    clean() if "--clean" in sys.argv[1:] else build()
