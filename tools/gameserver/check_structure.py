"""Check a structure file written by the simulator (Region → Export selection as
schematic…, ``.nbt``) in the real game: it is placed with ``/place template`` in the
sandboxed server's world and every block, a chest's contents and a sign's text are
compared with the simulator's.

Usage (from the repository root)::

    python -m tools.gameserver.check_structure
"""

from __future__ import annotations

import sys

from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.io.schematics import write_schematic
from redsim.world import blocks
from tools.gameserver.compare import discover_state
from tools.gameserver.server import SANDBOX, GameServer

ORIGIN = (0, -60, 40)  # on the superflat sandbox world's ground (grass at y -61)


def build() -> Document:
    doc = Document.new_flat()
    p = blocks.parse_state
    doc.setblock((0, 1, 0), p("repeater[facing=east,delay=3]"))
    doc.setblock((1, 1, 0), p("redstone_wire[east=side,west=side]"))
    doc.setblock((2, 1, 0), p("sticky_piston[facing=up]"))
    doc.setblock((0, 1, 2), p("chest[facing=south]"))
    doc.set_container_slot((0, 1, 2), 3, "minecraft:redstone", 17)
    doc.setblock((1, 1, 2), p("oak_sign[rotation=4]"))
    doc.set_sign_text((1, 1, 2), "front", ["structure"])
    doc.setblock((2, 2, 2), p("minecraft:oak_stairs[facing=north,half=bottom]"))
    doc.setblock((2, 1, 2), p("comparator[facing=west,mode=subtract]"))
    return doc


def main(argv: list[str]) -> int:
    doc = build()
    prefab = doc.copy(Region((0, 1, 0), (2, 2, 2)))
    failures = []
    with GameServer(fresh_world=True) as server:
        folder = SANDBOX / "world" / "generated" / "minecraft" / "structure"
        folder.mkdir(parents=True, exist_ok=True)
        write_schematic(folder / "redsim_check.nbt", prefab)
        x0, y0, z0 = ORIGIN
        server.command(f"forceload add {x0} {z0}")
        result = server.command(f"place template minecraft:redsim_check {x0} {y0} {z0}").text
        print(result.strip()[-80:])
        for dx, dy, dz, text, _ in prefab.blocks:
            pos = (x0 + dx, y0 + dy, z0 + dz)
            ok = server.test_blocks([(pos, text)])[0]
            if not ok:
                failures.append(f"{pos}: expected {text}, game has {discover_state(server, pos)}")
        chest = server.command(f"data get block {x0} {y0} {z0 + 2} Items").text
        if 'id: "minecraft:redstone"' not in chest or "count: 17" not in chest:
            failures.append(f"chest contents: {chest.strip()[-80:]}")
        sign = server.command(f"data get block {x0 + 1} {y0} {z0 + 2} front_text.messages[0]").text
        if "structure" not in sign:
            failures.append(f"sign text: {sign.strip()[-80:]}")
    for failure in failures:
        print("FAIL", failure)
    print(f"{len(prefab.blocks)} cells compared:", "MATCH" if not failures else "MISMATCH")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
