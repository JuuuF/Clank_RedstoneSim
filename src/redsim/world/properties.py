"""Block-state properties (``net/minecraft/world/level/block/state/properties``).

Values are plain Python objects: ``bool``, ``int``, ``Direction``, or lower-case strings for
the game's serializable enums (``RedstoneSide``, ``AttachFace``, ``ComparatorMode``, …), using
the game's serialized names so save files read like ``/setblock`` arguments.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from redsim.core.direction import HORIZONTAL, Direction


class Property:
    """A named property with an ordered tuple of possible values."""

    def __init__(self, name: str, values: Sequence[Any]) -> None:
        self.name = name
        self.values: tuple[Any, ...] = tuple(values)

    def serialize(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, Direction):
            return value.serialized
        return str(value)

    def parse(self, text: str) -> Any:
        for value in self.values:
            if self.serialize(value) == text:
                return value
        raise ValueError(f"invalid value {text!r} for property {self.name}")

    def next_value(self, value: Any) -> Any:
        """``StateHolder.cycle``: the next value in declaration order, wrapping around."""
        index = self.values.index(value)
        return self.values[(index + 1) % len(self.values)]

    def __repr__(self) -> str:
        return f"Property({self.name})"


def boolean(name: str) -> Property:
    return Property(name, (True, False))


def integer(name: str, minimum: int, maximum: int) -> Property:
    return Property(name, range(minimum, maximum + 1))


# BlockStateProperties (only the ones used by in-scope blocks).
POWERED = boolean("powered")
LIT = boolean("lit")
LOCKED = boolean("locked")
EXTENDED = boolean("extended")
SHORT = boolean("short")
POWER = integer("power", 0, 15)
DELAY = integer("delay", 1, 4)
BITES = integer("bites", 0, 6)
OPEN = boolean("open")
SNOWY = boolean("snowy")
HAS_BOOK = boolean("has_book")
#: ``BlockStateProperties.FACING`` (L53) declares N, E, S, W, U, D (not ordinal order).
FACING = Property("facing", (*HORIZONTAL, Direction.UP, Direction.DOWN))
HORIZONTAL_FACING = Property("facing", HORIZONTAL)  # HorizontalDirectionalBlock: N, E, S, W
ATTACH_FACE = Property("face", ("floor", "wall", "ceiling"))
MODE_COMPARATOR = Property("mode", ("compare", "subtract"))
PISTON_TYPE = Property("type", ("normal", "sticky"))
SLAB_TYPE = Property("type", ("top", "bottom", "double"))
REDSTONE_SIDE_VALUES = ("up", "side", "none")
NORTH_REDSTONE = Property("north", REDSTONE_SIDE_VALUES)
EAST_REDSTONE = Property("east", REDSTONE_SIDE_VALUES)
SOUTH_REDSTONE = Property("south", REDSTONE_SIDE_VALUES)
WEST_REDSTONE = Property("west", REDSTONE_SIDE_VALUES)
