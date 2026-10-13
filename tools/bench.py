"""Speed measurements to compare before and after changes (doc/refactor-plan.md).

    python -m tools.bench            # all
    python -m tools.bench engine     # selected: engine, wires, mesh, world

Each benchmark prints one line: name, the measured value and its unit. Numbers depend on
the machine; compare runs on the same machine only.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _pistons() -> object:
    """168 sticky pistons on observer clocks (every tick busy with block events)."""
    from redsim.editor.document import Document
    from redsim.world import blocks

    parse = blocks.parse_state
    doc = Document.new_flat()
    with doc.batch():
        for x in range(-12, 12, 4):
            for z in range(-14, 14):
                doc.setblock((x, 1, z), parse("sticky_piston[facing=up]"))
                doc.setblock((x, 2, z), parse("stone"))
                doc.setblock((x + 1, 1, z), parse("observer[facing=east]"))
                doc.setblock((x + 2, 1, z), parse("observer[facing=west]"))
    doc.run_ticks(2)
    doc.setblock((-11, 1, 0), parse("stone"))  # starts the clocks
    doc.run_ticks(10)
    return doc


def bench_engine() -> tuple[str, float, str]:
    doc = _pistons()
    start = time.perf_counter()
    doc.run_ticks(40)  # type: ignore[attr-defined]
    return "engine: 168 pistons on observer clocks", 40 / (time.perf_counter() - start), "ticks/s"


def bench_wires() -> tuple[str, float, str]:
    """A 15-long dust line toggled by a lever every tick (wire update storms)."""
    from redsim.editor.document import Document
    from redsim.world import blocks

    doc = Document.new_flat()
    with doc.batch():
        for row in range(8):
            z = row * 3
            doc.setblock((0, 1, z), blocks.parse_state("lever[face=floor,facing=east]"))
            for x in range(1, 16):
                doc.setblock((x, 1, z), blocks.REDSTONE_WIRE.default_state)
    doc.run_ticks(1)
    start = time.perf_counter()
    for _ in range(40):
        for row in range(8):
            doc.use((0, 1, row * 3))
        doc.run_ticks(1)
    return "engine: 8 dust lines toggled every tick", 40 / (time.perf_counter() - start), "ticks/s"


def bench_mesh() -> tuple[str, float, str]:
    from redsim.editor.document import Document
    from redsim.ui.geometry import ChunkedMesh, Mesher

    doc = Document.open(Path("examples/showcase.redsim.json"))
    mesher = Mesher()
    try:
        from redsim.ui.viewport import game_textures

        assets, atlas = game_textures()
        if atlas is not None:
            mesher = Mesher(assets, atlas)
    except Exception:  # noqa: BLE001 - textures are optional here
        pass
    start = time.perf_counter()
    for _ in range(5):
        ChunkedMesh(mesher).update(doc.level)
    return "mesh: full build of the showcase", (time.perf_counter() - start) / 5 * 1000, "ms"


def bench_world() -> tuple[str, float, str]:
    from redsim.mcworld.importer import open_world

    save = Path("data/minecraft_saves/Redstone")
    if not save.exists():
        return "world: open the example save (radius 4)", float("nan"), "s (no save)"
    start = time.perf_counter()
    open_world(save, radius=4)
    return "world: open the example save (radius 4)", time.perf_counter() - start, "s"


BENCHES: dict[str, Callable[[], tuple[str, float, str]]] = {
    "engine": bench_engine,
    "wires": bench_wires,
    "mesh": bench_mesh,
    "world": bench_world,
}


def main(names: list[str]) -> None:
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])  # block previews need Qt
    for name in names or list(BENCHES):
        title, value, unit = BENCHES[name]()
        print(f"{title:48s} {value:10.2f} {unit}")


if __name__ == "__main__":
    main(sys.argv[1:])
