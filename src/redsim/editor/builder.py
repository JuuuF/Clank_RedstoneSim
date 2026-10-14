"""Building example worlds in code: the showcase (``tools/make_examples.py``) and the
tutorial world (``redsim.tutorial.world``).

A ``Builder`` holds a new document on a floor of any size and places blocks relative to a
movable origin (one district or station at a time). Components are placed like a player
places them (``Document.place``/``use``) or set with ``/setblock`` semantics, block-entity
data included, so everything is built through the same edits a user makes. Signs label
the stations; groups and sections annotate them.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.editor.groups import Group, Port
from redsim.editor.placement import PlaceRequest
from redsim.sim.engine import Engine
from redsim.world import blocks
from redsim.world.block import Block

#: Clicking the top of a block while looking south (the camera's usual direction).
ON_FLOOR = PlaceRequest(Direction.UP, yaw=0, pitch=60)
#: Looking west at the top of a block: diodes then output west, observers look east.
LOOK_WEST = PlaceRequest(Direction.UP, yaw=90, pitch=60)
#: Looking east, level: pistons then face west.
LOOK_EAST_LEVEL = PlaceRequest(Direction.UP, yaw=270, pitch=0)
#: Clicking a block's east face (wall levers, torches and buttons pointing east).
ON_EAST_FACE = PlaceRequest(Direction.EAST, yaw=90, pitch=0)
#: Clicking a block's west face.
ON_WEST_FACE = PlaceRequest(Direction.WEST, yaw=270, pitch=0)


def items(*stacks: tuple[str, int]) -> dict[str, Any]:
    """Container data holding ``stacks`` in slots 0, 1, … (``/setblock … {Items: […]}``)."""
    return {
        "Items": [
            {"Slot": slot, "id": item if ":" in item else f"minecraft:{item}", "count": count}
            for slot, (item, count) in enumerate(stacks)
        ]
    }


class Builder:
    """A new world with a floor from ``low`` to ``high`` (x, z, inclusive) at y=0 of
    ``floor`` (placed without updates, like terrain); ``pads`` are areas (x0, z0, x1, z1)
    of other floor blocks on top of it, e.g. a stone square under each district."""

    def __init__(
        self,
        low: tuple[int, int],
        high: tuple[int, int],
        floor: str = "minecraft:smooth_stone",
        pads: Iterable[tuple[tuple[int, int, int, int], str]] = (),
    ) -> None:
        engine = Engine()
        ground = blocks.parse_state(floor)
        for x in range(low[0], high[0] + 1):
            for z in range(low[1], high[1] + 1):
                engine.level.blocks[(x, 0, z)] = ground
        for (x0, z0, x1, z1), block in pads:
            state = blocks.parse_state(block)
            for x in range(min(x0, x1), max(x0, x1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    engine.level.blocks[(x, 0, z)] = state
        self.doc = Document(engine=engine)
        self.origin: Pos = (0, 0, 0)
        #: Blocks set after settling (``set_later``), as world positions.
        self._later: list[tuple[Pos, str, dict[str, Any] | None]] = []

    # ------------------------------------------------------------------ positions
    def at(self, pos: Pos) -> Pos:
        """The world position of ``pos`` relative to the origin."""
        return (self.origin[0] + pos[0], self.origin[1] + pos[1], self.origin[2] + pos[2])

    # ------------------------------------------------------------------ blocks
    def place(self, pos: Pos, block: Block, request: PlaceRequest = ON_FLOOR) -> None:
        """Place like a player clicking with ``request``."""
        self.doc.place(self.at(pos), block, request)

    def use(self, pos: Pos, times: int = 1) -> None:
        for _ in range(times):
            self.doc.use(self.at(pos))

    def solid(self, pos: Pos, block: Block = blocks.STONE) -> None:
        self.doc.setblock(self.at(pos), block.default_state)

    def set(self, pos: Pos, state: str, nbt: dict[str, Any] | None = None) -> None:
        """``/setblock`` with a state in command syntax and optional block-entity data."""
        self.doc.setblock(self.at(pos), blocks.parse_state(state), nbt)

    def set_later(self, pos: Pos, state: str, nbt: dict[str, Any] | None = None) -> None:
        """Like ``set``, but only after ``settle``: the block's change happens when the
        world is run (items start moving, a composter's timer starts), not while
        settling."""
        self._later.append((self.at(pos), state, nbt))

    def source(self, pos: Pos, kind: str, strength: int, request: PlaceRequest = LOOK_WEST) -> None:
        """A signal source (barrel, lectern, cake, composter, hopper, chest)."""
        self.doc.place_source(self.at(pos), kind, strength, request)

    def sign(self, pos: Pos, *lines: str, facing: Direction | None = None) -> None:
        """A sign with up to four lines on its front: standing on the block below and
        facing north (towards the usual camera), or on a wall when ``facing`` is given
        (the side its text faces; the block behind it holds it)."""
        if facing is None:
            state = "minecraft:oak_sign[rotation=8]"
        else:
            state = f"minecraft:oak_wall_sign[facing={facing.name.lower()}]"
        self.set(pos, state)
        self.doc.set_sign_text(self.at(pos), "front", list(lines)[:4])

    # ------------------------------------------------------------------ annotations
    def group(self, name: str, low: Pos, high: Pos, ports: list[Port]) -> None:
        """A group with ports (relative positions); ports are marked as input/output."""
        moved = [Port(p.name, self.at(p.pos), p.role) for p in ports]
        region = Region.from_corners(self.at(low), self.at(high))
        self.doc.groups.add(Group(name, region, moved))
        for port in moved:
            self.doc.assign_section(port.pos, "input" if port.role == "input" else "output")

    def mark(self, section: str, *positions: Pos) -> None:
        for pos in positions:
            self.doc.assign_section(self.at(pos), section)

    def settle(self, ticks: int = 4) -> None:
        """Run a few ticks, so components placed one after another reach their states,
        and make the result the build (tick 0); then set the ``set_later`` blocks. The
        undo history is dropped."""
        self.doc.run_ticks(ticks)
        self.doc.set_tick_zero()
        for pos, state, nbt in self._later:
            self.doc.setblock(pos, blocks.parse_state(state), nbt)
        self._later.clear()
        self.doc._undo.clear()


def inputs(*ports: tuple[str, Pos]) -> list[Port]:
    return [Port(name, pos, "input") for name, pos in ports]


def outputs(*ports: tuple[str, Pos]) -> list[Port]:
    return [Port(name, pos, "output") for name, pos in ports]
