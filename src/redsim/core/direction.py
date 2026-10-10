"""Directions and axes with Java Edition ordering.

Port of ``net/minecraft/core/Direction.java``. Member order matters: ``Direction.values()``
in Java is DOWN, UP, NORTH, SOUTH, WEST, EAST (L33-38), and several update loops iterate it.
"""

from __future__ import annotations

from enum import Enum


class Axis(Enum):
    X = "x"
    Y = "y"
    Z = "z"

    @property
    def is_horizontal(self) -> bool:
        return self is not Axis.Y


class Direction(Enum):
    """The six block faces. ``value`` is the Java ordinal, which equals the 3D data value."""

    DOWN = 0
    UP = 1
    NORTH = 2
    SOUTH = 3
    WEST = 4
    EAST = 5

    # Filled in after class creation (Enum members cannot be set in the class body).
    step: tuple[int, int, int]
    axis: Axis
    opposite: Direction
    serialized: str

    @property
    def ordinal(self) -> int:
        return self.value

    @property
    def data3d(self) -> int:
        """``Direction.get3DDataValue`` (used as piston block-event parameter)."""
        return self.value

    @property
    def is_horizontal(self) -> bool:
        return self.axis is not Axis.Y

    @property
    def is_positive(self) -> bool:
        return sum(self.step) > 0

    def clockwise(self) -> Direction:
        """``Direction.getClockWise()`` around the Y axis (horizontal directions only)."""
        return _CLOCKWISE[self]

    def counter_clockwise(self) -> Direction:
        """``Direction.getCounterClockWise()`` around the Y axis (horizontal only)."""
        return _COUNTER_CLOCKWISE[self]

    @staticmethod
    def from_data3d(value: int) -> Direction:
        """``Direction.from3DDataValue`` (wraps with ``abs(value % 6)``)."""
        return ALL[abs(value % 6)]

    @staticmethod
    def by_name(name: str) -> Direction:
        return _BY_NAME[name]

    def __repr__(self) -> str:
        return f"Direction.{self.name}"


_STEPS = {
    Direction.DOWN: (0, -1, 0),
    Direction.UP: (0, 1, 0),
    Direction.NORTH: (0, 0, -1),
    Direction.SOUTH: (0, 0, 1),
    Direction.WEST: (-1, 0, 0),
    Direction.EAST: (1, 0, 0),
}
_AXES = {
    Direction.DOWN: Axis.Y,
    Direction.UP: Axis.Y,
    Direction.NORTH: Axis.Z,
    Direction.SOUTH: Axis.Z,
    Direction.WEST: Axis.X,
    Direction.EAST: Axis.X,
}
_OPPOSITES = {
    Direction.DOWN: Direction.UP,
    Direction.UP: Direction.DOWN,
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.WEST: Direction.EAST,
    Direction.EAST: Direction.WEST,
}
for _d in Direction:
    _d.step = _STEPS[_d]
    _d.axis = _AXES[_d]
    _d.opposite = _OPPOSITES[_d]
    _d.serialized = _d.name.lower()

_CLOCKWISE = {
    Direction.NORTH: Direction.EAST,
    Direction.EAST: Direction.SOUTH,
    Direction.SOUTH: Direction.WEST,
    Direction.WEST: Direction.NORTH,
}
_COUNTER_CLOCKWISE = {v: k for k, v in _CLOCKWISE.items()}
_BY_NAME = {d.serialized: d for d in Direction}

#: ``Direction.values()``: DOWN, UP, NORTH, SOUTH, WEST, EAST.
ALL: tuple[Direction, ...] = tuple(Direction)
#: ``Direction.Plane.HORIZONTAL`` (Direction.java L540): NORTH, EAST, SOUTH, WEST.
HORIZONTAL: tuple[Direction, ...] = (
    Direction.NORTH,
    Direction.EAST,
    Direction.SOUTH,
    Direction.WEST,
)
#: ``Direction.Plane.VERTICAL``: UP, DOWN.
VERTICAL: tuple[Direction, ...] = (Direction.UP, Direction.DOWN)
#: ``NeighborUpdater.UPDATE_ORDER`` (NeighborUpdater.java L18): W, E, D, U, N, S.
NEIGHBOR_UPDATE_ORDER: tuple[Direction, ...] = (
    Direction.WEST,
    Direction.EAST,
    Direction.DOWN,
    Direction.UP,
    Direction.NORTH,
    Direction.SOUTH,
)
#: ``BlockBehaviour.UPDATE_SHAPE_ORDER`` (BlockBehaviour.java L85): W, E, N, S, D, U.
SHAPE_UPDATE_ORDER: tuple[Direction, ...] = (
    Direction.WEST,
    Direction.EAST,
    Direction.NORTH,
    Direction.SOUTH,
    Direction.DOWN,
    Direction.UP,
)
