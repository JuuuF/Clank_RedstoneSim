"""Repeater and comparator unit tests (doc/mechanics/repeater.md, comparator.md).

Game-verified behavior (delays, pulse extension, lock priority race, compare/subtract,
reading through blocks, torch not a side input) lives in the recordings replayed by
test_game_verified.py; these tests cover player paths and update details.
"""

from __future__ import annotations

from redsim.sim import trace as tr
from redsim.world.blocks.comparator import ComparatorBlockEntity
from redsim.world.properties import DELAY, LIT, LOCKED, MODE_COMPARATOR, POWERED
from tests.sim.bench import Bench


def scheduled(b: Bench, start: int, block: str) -> list[tuple[int, str]]:
    return [
        (r.detail["delay"], r.detail["priority"])
        for r in b.level.trace.records[start:]
        if r.kind == tr.SCHEDULE_TICK and r.detail["block"] == block and r.detail["accepted"]
    ]


def test_placed_repeater_with_input_turns_on_after_one_tick() -> None:
    """``DiodeBlock.setPlacedBy`` schedules delay 1 / NORMAL (Q-REP-PLACE-DELAY1)."""
    b = Bench()
    b.place((0, 1, 0), "redstone_block")
    start = len(b.level.trace.records)
    b.place((1, 1, 0), "repeater[facing=west]")
    b.use((1, 1, 0))
    b.use((1, 1, 0))  # delay 3 now; the pending tick keeps its original timing
    assert b.get((1, 1, 0), DELAY) == 3
    assert scheduled(b, start, "repeater")[0] == (1, "NORMAL")
    b.tick(1)
    assert b.get((1, 1, 0), POWERED) is True


def test_repeater_priorities_by_situation() -> None:
    b = Bench()
    b.place((1, 1, 0), "repeater[facing=west]")  # outputs into a lamp
    b.place((2, 1, 0), "redstone_lamp")
    start = len(b.level.trace.records)
    b.place((0, 1, 0), "redstone_block")
    assert scheduled(b, start, "repeater") == [(2, "HIGH")]  # turning on
    b.tick(2)
    start = len(b.level.trace.records)
    b.break_block((0, 1, 0))
    assert scheduled(b, start, "repeater") == [(2, "VERY_HIGH")]  # turning off

    b.place((1, 1, 3), "repeater[facing=west]")  # outputs into another repeater
    b.place((2, 1, 3), "repeater[facing=west]")
    start = len(b.level.trace.records)
    b.place((0, 1, 3), "redstone_block")
    assert scheduled(b, start, "repeater")[0] == (2, "EXTREMELY_HIGH")


def test_wire_and_torches_beside_a_repeater_do_not_lock_it() -> None:
    b = Bench()
    b.place((1, 1, 1), "repeater[facing=west]")
    b.place((1, 1, 2), "redstone_wire")
    b.place((1, 1, 3), "redstone_block")  # wire beside the repeater is powered
    b.place((1, 1, 0), "redstone_torch")  # lit torch on the other side
    assert b.get((1, 1, 1), LOCKED) is False
    b.place((0, 1, 1), "redstone_block")
    b.tick(2)
    assert b.get((1, 1, 1), POWERED) is True


def test_wire_connects_to_repeater_only_along_its_axis() -> None:
    b = Bench()
    b.place((1, 1, 1), "repeater[facing=west]")
    b.place((0, 1, 2), "redstone_wire")  # an isolated wire is a cross; give it a line
    b.place((1, 1, 2), "redstone_wire")
    b.place((2, 1, 1), "redstone_wire")
    side = b.state((1, 1, 2))
    front = b.state((2, 1, 1))
    from redsim.world.properties import NORTH_REDSTONE, WEST_REDSTONE

    assert side.get(NORTH_REDSTONE) == "none"  # no connection into the repeater's side
    assert front.get(WEST_REDSTONE) == "side"


def test_comparator_mode_toggle_refreshes_immediately() -> None:
    b = Bench()
    b.place((0, 1, 1), "redstone_block")
    b.place((1, 1, 1), "comparator[facing=west]")
    b.place((1, 1, 2), "redstone_wire")
    b.place((1, 1, 3), "redstone_wire")
    b.place((1, 1, 4), "redstone_block")  # side wire at power 14
    b.tick(2)
    be = b.level.get_block_entity((1, 1, 1))
    assert isinstance(be, ComparatorBlockEntity) and be.output == 15
    b.use((1, 1, 1))  # to subtract: output changes during the use itself
    assert b.get((1, 1, 1), MODE_COMPARATOR) == "subtract"
    assert be.output == 1


def test_comparator_power_change_updates_front_twice() -> None:
    """``refreshOutputState``: setBlock(…, 2) → onPlace → updateNeighborsInFront, then the
    explicit call (Q-COMP-DOUBLE-FRONT)."""
    b = Bench()
    b.place((1, 1, 0), "comparator[facing=west]")
    b.place((2, 1, 0), "redstone_lamp")
    b.place((0, 1, 0), "redstone_block")
    b.tick(1)
    start = len(b.level.trace.records)
    b.tick(1)  # the comparator turns on in this tick
    lamp_updates = [
        r
        for r in b.level.trace.records[start:]
        if r.kind == tr.NEIGHBOR_UPDATE
        and r.pos == (2, 1, 0)
        and r.detail["source"] == "comparator"
    ]
    assert len(lamp_updates) == 2
    assert b.get((2, 1, 0), LIT) is True
