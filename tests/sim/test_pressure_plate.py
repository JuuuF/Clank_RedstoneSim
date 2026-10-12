"""Pressure plates with "visitors" standing on them (entities are not simulated)."""

from __future__ import annotations

from redsim.core.pos import Pos
from redsim.sim.engine import Action
from redsim.world.properties import LIT, POWER, POWERED
from tests.sim.bench import Bench


def _visit(b: Bench, pos: Pos, mobs: int, others: int, ticks: int) -> None:
    b.engine.apply(
        Action("plate_visitors", pos, payload={"mobs": mobs, "others": others, "ticks": ticks})
    )


def test_plate_presses_next_tick_and_releases_20_ticks_after_the_last_visit() -> None:
    b = Bench()
    b.place((1, 1, 0), "oak_pressure_plate")
    b.place((2, 1, 0), "redstone_lamp")
    _visit(b, (1, 1, 0), mobs=1, others=0, ticks=5)
    assert b.get((1, 1, 0), POWERED) is False  # the entity steps on it in the next tick
    b.tick()
    assert b.get((1, 1, 0), POWERED) is True and b.get((2, 1, 0), LIT) is True
    b.tick(19)  # the recheck after 20 ticks finds nobody (gone after 5): released
    assert b.get((1, 1, 0), POWERED) is True
    b.tick()
    assert b.get((1, 1, 0), POWERED) is False


def test_stone_plates_ignore_items_and_weighted_plates_count() -> None:
    b = Bench()
    b.place((1, 1, 0), "stone_pressure_plate")
    b.place((3, 1, 0), "light_weighted_pressure_plate")
    b.place((5, 1, 0), "heavy_weighted_pressure_plate")
    _visit(b, (1, 1, 0), mobs=0, others=3, ticks=40)
    _visit(b, (3, 1, 0), mobs=1, others=6, ticks=40)
    _visit(b, (5, 1, 0), mobs=0, others=11, ticks=40)
    b.tick()
    assert b.get((1, 1, 0), POWERED) is False
    assert b.get((3, 1, 0), POWER) == 7  # ceil(7/15 · 15)
    assert b.get((5, 1, 0), POWER) == 2  # ceil(11/150 · 15) = ceil(1.1)


def test_plate_strongly_powers_the_block_below() -> None:
    b = Bench()
    b.place((1, 1, 0), "oak_pressure_plate")
    _visit(b, (1, 1, 0), mobs=1, others=0, ticks=5)
    b.tick()
    assert b.level.get_direct_signal_to((1, 0, 0)) == 15
