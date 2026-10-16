"""Build the circuit library's worlds and structure files from their scripts.

Usage (from the repository root)::

    PYTHONPATH=src python -m tools.make_circuits [NAME ...]

For every ``examples/circuits/NAME.cli.txt`` (or the names given) this runs the script
into ``examples/circuits/NAME.redsim.json`` (the world, to open in the editor or inspect
with ``redsim-cli``) and exports the module, the box of the script's ``prefab save``
line, to ``examples/circuits/NAME.nbt``: a structure file that other scripts paste with
``import examples/circuits/NAME.nbt at POS [rotate N]`` (doc/redstone/circuits.md).
The script must pass its own ``check``; otherwise nothing is written for it.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

from redsim.cli.main import main

ROOT = Path(__file__).resolve().parents[1]
CIRCUITS = ROOT / "examples" / "circuits"
PREFAB = re.compile(r"^prefab save \S+ (-?\d+ -?\d+ -?\d+) (-?\d+ -?\d+ -?\d+)\s*$", re.M)


class _Stdin(io.StringIO):
    def isatty(self) -> bool:
        return False


def build(script: Path) -> str:
    name = script.name.removesuffix(".cli.txt")
    world = CIRCUITS / f"{name}.redsim.json"
    text = script.read_text()
    out = io.StringIO()
    if main([str(world)], stdin=_Stdin(text), out=out) != 0 or "FAIL" in out.getvalue():
        return f"{name}: the script failed, nothing written\n{out.getvalue()}"
    box = PREFAB.search(text)
    if box is None:
        return f"{name}: world written; no 'prefab save' line, so no .nbt"
    nbt = CIRCUITS / f"{name}.nbt"
    out = io.StringIO()
    args = ["export", str(nbt), "from", *box.group(1).split(), *box.group(2).split()]
    if main([str(world), "--dry-run", *args], out=out) != 0:
        return f"{name}: export failed\n{out.getvalue()}"
    return f"{name}: {world.relative_to(ROOT)}, {nbt.relative_to(ROOT)}"


def run(names: list[str]) -> int:
    scripts = sorted(CIRCUITS.glob("*.cli.txt"))
    if names:
        scripts = [s for s in scripts if s.name.removesuffix(".cli.txt") in names]
    failed = 0
    for script in scripts:
        line = build(script)
        failed += "failed" in line
        print(line)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
