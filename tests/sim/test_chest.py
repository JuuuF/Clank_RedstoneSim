"""Chests: double chests as one container, blocking, hoppers and comparators."""

from __future__ import annotations

from redsim.core.direction import Direction
from redsim.world.blocks.chest import CHEST_TYPE, ChestBlockEntity, chest_container
from tests.sim.bench import Bench


def test_two_chests_join_and_split() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "chest[facing=north]")
    b.place((2, 1, 0), "chest[facing=north]")  # placed beside a single chest: joins it
    assert {b.get((1, 1, 0), CHEST_TYPE), b.get((2, 1, 0), CHEST_TYPE)} == {"left", "right"}
    b.break_block((2, 1, 0))
    assert b.get((1, 1, 0), CHEST_TYPE) == "single"


def test_comparator_reads_the_double_chest_and_zero_when_blocked() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "chest[facing=north]")
    b.place((2, 1, 0), "chest[facing=north]")
    first = b.level.get_block_entity((2, 1, 0))
    assert isinstance(first, ChestBlockEntity)
    for slot in range(27):
        first.set_item(b.level, slot, ("minecraft:stone", 64))  # one half full
    state = b.state((1, 1, 0))
    double = chest_container(b.level, (1, 1, 0), state, ignore_blocked=False)
    assert double is not None and double.SIZE == 54
    signal = state.get_analog_output_signal(b.level, (1, 1, 0), Direction.SOUTH)
    assert signal == double.signal() == 8  # half of 54 slots full
    b.setblock((2, 2, 0), "stone")  # a conductor on the other half: blocked
    assert state.get_analog_output_signal(b.level, (1, 1, 0), Direction.SOUTH) == 0


def test_hopper_fills_a_blocked_double_chest() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "chest[facing=north]")
    b.place((2, 1, 0), "chest[facing=north]")
    b.setblock((1, 2, 0), "stone")  # blocked: hoppers do not care
    b.setblock((1, 3, 0), "hopper[facing=down]")  # above the stone: not connected
    b.setblock((0, 1, 0), "hopper[facing=east]")
    hopper = b.level.get_block_entity((0, 1, 0))
    hopper.set_item(b.level, 0, ("minecraft:stone", 2))  # type: ignore[union-attr]
    b.tick(9)
    state = b.state((1, 1, 0))
    double = chest_container(b.level, (1, 1, 0), state, ignore_blocked=True)
    assert double is not None
    assert sum(s[1] for s in double.items if s is not None) == 2
