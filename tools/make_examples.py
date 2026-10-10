"""Build the example world ``examples/showcase.redsim.json``.

Usage (from the repository root)::

    PYTHONPATH=src python -m tools.make_examples

Each circuit sits in its own row, with input on the east (+x) side and output on the west,
so with the stored camera (looking south) signals flow from left to right on screen. Every
row is a group with ports, so the Contraptions → Groups panel shows live values. Components
are placed with player semantics (``Document.place``/``use``) and settled before saving.
"""

from __future__ import annotations

from pathlib import Path

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.editor.groups import Group, Port
from redsim.editor.placement import PlaceRequest
from redsim.world import blocks
from redsim.world.block import Block

OUTPUT = Path(__file__).resolve().parents[1] / "examples" / "showcase.redsim.json"

ON_FLOOR = PlaceRequest(Direction.UP, yaw=0, pitch=60)  # clicking the top of a block
LOOK_WEST = PlaceRequest(Direction.UP, yaw=90, pitch=60)  # diodes then output west
LOOK_EAST_LEVEL = PlaceRequest(Direction.UP, yaw=270, pitch=0)  # pistons then face west


def on_east_face() -> PlaceRequest:
    """Clicking a block's east face (wall levers/torches pointing east)."""
    return PlaceRequest(Direction.EAST, yaw=90, pitch=0)


def on_west_face() -> PlaceRequest:
    return PlaceRequest(Direction.WEST, yaw=270, pitch=0)


#: Rows are laid out at z = 0…27 and shifted onto the 32×32 floor (z from -16 to 15).
Z_SHIFT = -12


def at(pos: Pos) -> Pos:
    return (pos[0], pos[1], pos[2] + Z_SHIFT)


class Builder:
    def __init__(self) -> None:
        self.doc = Document.new_flat()

    def place(self, pos: Pos, block: Block, request: PlaceRequest = ON_FLOOR) -> None:
        self.doc.place(at(pos), block, request)

    def use(self, pos: Pos) -> None:
        self.doc.use(at(pos))

    def solid(self, pos: Pos, block: Block = blocks.STONE) -> None:
        self.doc.setblock(at(pos), block.default_state)

    def group(self, name: str, low: Pos, high: Pos, ports: list[Port]) -> None:
        moved = [Port(p.name, at(p.pos), p.role) for p in ports]
        self.doc.groups.add(Group(name, Region.from_corners(at(low), at(high)), moved))
        for port in moved:
            self.doc.assign_section(port.pos, "input" if port.role == "input" else "output")

    def mark(self, section: str, *positions: Pos) -> None:
        for pos in positions:
            self.doc.assign_section(at(pos), section)


def build() -> Document:
    b = Builder()

    # 1. Lever and lamp.
    b.place((6, 1, 0), blocks.LEVER)
    b.place((5, 1, 0), blocks.REDSTONE_LAMP)
    b.group("1 lever and lamp", (5, 1, 0), (6, 1, 0),
            [Port("lever", (6, 1, 0), "input"), Port("lamp", (5, 1, 0), "output")])  # fmt: skip

    # 2. Inverter: wall lever powers a block, a wall torch on its far side inverts.
    b.solid((5, 1, 3))
    b.place((6, 1, 3), blocks.LEVER, on_east_face())
    b.place((4, 1, 3), blocks.REDSTONE_TORCH, on_west_face())
    b.place((3, 1, 3), blocks.REDSTONE_LAMP)
    b.mark("processing", (5, 1, 3), (4, 1, 3))
    b.group("2 inverter", (3, 1, 3), (6, 1, 3),
            [Port("lever", (6, 1, 3), "input"), Port("lamp", (3, 1, 3), "output")])  # fmt: skip

    # 3. Dust line into a delay-4 repeater.
    b.place((7, 1, 6), blocks.LEVER)
    for x in range(3, 7):
        b.place((x, 1, 6), blocks.REDSTONE_WIRE)
    b.place((2, 1, 6), blocks.REPEATER, LOOK_WEST)
    for _ in range(3):
        b.use((2, 1, 6))  # delay 1 → 4 (8 game ticks)
    b.place((1, 1, 6), blocks.REDSTONE_LAMP)
    b.mark("processing", *[(x, 1, 6) for x in range(2, 7)])
    b.group("3 dust and repeater (delay 4)", (1, 1, 6), (7, 1, 6),
            [Port("lever", (7, 1, 6), "input"), Port("lamp", (1, 1, 6), "output")])  # fmt: skip

    # 4. Torch AND gate: two inverted inputs joined by dust, inverted again.
    for z in (9, 11):
        b.solid((6, 1, z))
        b.place((7, 1, z), blocks.LEVER, on_east_face())
        b.place((6, 2, z), blocks.REDSTONE_TORCH)
    b.solid((6, 1, 10))
    b.place((6, 2, 10), blocks.REDSTONE_WIRE)
    b.place((5, 1, 10), blocks.REDSTONE_TORCH, on_west_face())
    b.place((4, 1, 10), blocks.REDSTONE_LAMP)
    b.mark("processing", (6, 2, 9), (6, 2, 11), (6, 2, 10), (5, 1, 10))
    b.group("4 AND gate", (4, 1, 9), (7, 2, 11),
            [Port("A", (7, 1, 9), "input"), Port("B", (7, 1, 11), "input"),
             Port("A and B", (4, 1, 10), "output")])  # fmt: skip

    # 5. Comparator in subtract mode: cake (14) minus a dust side input (14 when on).
    b.place((6, 1, 14), blocks.CAKE)
    b.place((5, 1, 14), blocks.COMPARATOR, LOOK_WEST)
    b.use((5, 1, 14))  # compare → subtract
    b.place((4, 1, 14), blocks.REDSTONE_WIRE)
    b.place((3, 1, 14), blocks.REDSTONE_LAMP)
    b.place((5, 1, 17), blocks.LEVER)
    b.place((5, 1, 16), blocks.REDSTONE_WIRE)
    b.place((5, 1, 15), blocks.REDSTONE_WIRE)
    b.mark("processing", (6, 1, 14), (5, 1, 14), (4, 1, 14), (5, 1, 15), (5, 1, 16))
    b.group("5 comparator subtract (right-click the cake to eat)", (3, 1, 14), (6, 1, 17),
            [Port("side lever", (5, 1, 17), "input"), Port("comparator", (5, 1, 14), "output"),
             Port("lamp", (3, 1, 14), "output")])  # fmt: skip

    # 6. Sliding block: sticky piston.
    b.place((7, 1, 20), blocks.LEVER)
    b.place((6, 1, 20), blocks.STICKY_PISTON, LOOK_EAST_LEVEL)
    b.solid((5, 1, 20), blocks.OAK_PLANKS)
    b.mark("processing", (6, 1, 20))
    b.group("6 sliding block (sticky piston)", (3, 1, 20), (7, 1, 20),
            [Port("lever", (7, 1, 20), "input"), Port("piston", (6, 1, 20), "output")])  # fmt: skip

    # 7. 1x2 piston door: one lever powers the top piston directly and the bottom one by
    #    quasi-connectivity; the lever also updates the bottom piston (game-verified, EXP-018).
    b.solid((7, 1, 23))
    b.place((6, 1, 23), blocks.STICKY_PISTON, LOOK_EAST_LEVEL)
    b.place((6, 2, 23), blocks.STICKY_PISTON, LOOK_EAST_LEVEL)
    b.solid((5, 1, 23), blocks.OAK_PLANKS)
    b.solid((5, 2, 23), blocks.OAK_PLANKS)
    b.place((7, 2, 23), blocks.LEVER)
    b.mark("processing", (6, 1, 23), (6, 2, 23))
    b.group("7 piston door (QC)", (4, 1, 23), (7, 2, 23),
            [Port("lever", (7, 2, 23), "input"), Port("top piston", (6, 2, 23), "output"),
             Port("bottom piston", (6, 1, 23), "output")])  # fmt: skip

    # 8. Torch burnout loop (a quirk): the torch powers the block above it, which powers dust
    #    on the torch's own block. Run it: it flickers, burns out after 8 turn-offs within 60
    #    ticks and stays out until something updates it (EXP-005/006).
    b.solid((6, 1, 27))
    b.place((5, 1, 27), blocks.REDSTONE_TORCH, on_west_face())
    b.solid((5, 2, 27))
    b.place((6, 2, 27), blocks.REDSTONE_WIRE)
    b.mark("clock", (6, 1, 27), (5, 1, 27), (5, 2, 27), (6, 2, 27))
    b.group("8 torch burnout loop (quirk)", (5, 1, 27), (6, 2, 27),
            [Port("torch", (5, 1, 27), "output")])  # fmt: skip

    # Settle everything except the burnout loop (which keeps toggling while running).
    for _ in range(4):
        b.doc.run_tick()
    doc = b.doc
    doc.extra["camera"] = {"position": [4.5, 6.0, -6.0 + Z_SHIFT], "yaw": 0.0, "pitch": 33.0}
    return doc


def main() -> None:
    doc = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(f"wrote {OUTPUT} ({len(doc.level.blocks)} blocks, {len(doc.groups.groups)} groups)")


if __name__ == "__main__":
    main()
