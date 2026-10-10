"""Direction ordering must match Java's enum and update-order constants."""

from __future__ import annotations

from redsim.core.direction import (
    ALL,
    HORIZONTAL,
    NEIGHBOR_UPDATE_ORDER,
    SHAPE_UPDATE_ORDER,
    VERTICAL,
    Direction,
)
from redsim.core.pos import offset


def test_values_order_matches_java_ordinals() -> None:
    assert [d.name for d in ALL] == ["DOWN", "UP", "NORTH", "SOUTH", "WEST", "EAST"]
    assert [d.data3d for d in ALL] == [0, 1, 2, 3, 4, 5]


def test_planes_and_update_orders() -> None:
    d = Direction
    assert HORIZONTAL == (d.NORTH, d.EAST, d.SOUTH, d.WEST)
    assert VERTICAL == (d.UP, d.DOWN)
    assert NEIGHBOR_UPDATE_ORDER == (d.WEST, d.EAST, d.DOWN, d.UP, d.NORTH, d.SOUTH)
    assert SHAPE_UPDATE_ORDER == (d.WEST, d.EAST, d.NORTH, d.SOUTH, d.DOWN, d.UP)


def test_geometry() -> None:
    assert offset((0, 0, 0), Direction.NORTH) == (0, 0, -1)
    assert offset((0, 0, 0), Direction.EAST, 2) == (2, 0, 0)
    assert Direction.NORTH.clockwise() is Direction.EAST
    assert Direction.WEST.clockwise() is Direction.NORTH
    assert Direction.NORTH.counter_clockwise() is Direction.WEST
    for direction in ALL:
        assert direction.opposite.opposite is direction
        assert Direction.from_data3d(direction.data3d) is direction
