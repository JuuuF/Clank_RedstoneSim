"""Copper bulb: a T flip-flop on rising signals (CopperBulbBlock.java)."""

from __future__ import annotations

from redsim.core.direction import Direction
from redsim.world.properties import LIT, POWERED
from tests.sim.bench import Bench


def test_each_rising_signal_toggles_lit() -> None:
    b = Bench()
    b.place((1, 1, 0), "copper_bulb")
    b.place((0, 1, 0), "lever[face=floor,facing=north]")
    b.use((0, 1, 0))
    assert b.get((1, 1, 0), LIT) is True and b.get((1, 1, 0), POWERED) is True
    b.use((0, 1, 0))  # falling: stays lit
    assert b.get((1, 1, 0), LIT) is True and b.get((1, 1, 0), POWERED) is False
    b.use((0, 1, 0))  # rising again: off
    assert b.get((1, 1, 0), LIT) is False


def test_placing_next_to_power_lights_it_and_comparator_reads_15() -> None:
    b = Bench()
    b.place((0, 1, 0), "redstone_block")
    b.place((1, 1, 0), "oxidized_copper_bulb")  # every stage works the same
    assert b.get((1, 1, 0), LIT) is True
    level = b.level
    state = level.get_block_state((1, 1, 0))
    assert state.get_analog_output_signal(level, (1, 1, 0), Direction.EAST) == 15
    assert not state.is_redstone_conductor(level, (1, 1, 0))
