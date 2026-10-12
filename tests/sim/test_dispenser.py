"""Dispensers and droppers (DispenserBlock.java, DropperBlock.java)."""

from __future__ import annotations

from redsim.world.blocks.dispenser import TRIGGERED, DispenserBlockEntity
from redsim.world.blocks.hopper import HopperBlockEntity
from tests.sim.bench import Bench


def _fill(b: Bench, pos: tuple[int, int, int], stacks: dict[int, tuple[str, int]]) -> None:
    entity = b.level.get_block_entity(pos)
    assert isinstance(entity, DispenserBlockEntity)
    for slot, stack in stacks.items():
        entity.set_item(b.level, slot, stack)


def test_dropper_moves_one_item_per_rising_edge_after_4_ticks() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "dropper[facing=east]")
    b.setblock((2, 1, 0), "hopper[facing=down]")
    _fill(b, (1, 1, 0), {4: ("minecraft:stone", 3)})
    b.setblock((0, 1, 0), "redstone_block")
    assert b.get((1, 1, 0), TRIGGERED) is True
    b.tick(3)
    hopper = b.level.get_block_entity((2, 1, 0))
    assert isinstance(hopper, HopperBlockEntity) and hopper.is_empty()
    b.tick(1)  # the scheduled tick (4) dispenses
    assert hopper.items[0] == ("minecraft:stone", 1)
    b.tick(10)  # still powered: nothing more
    entity = b.level.get_block_entity((1, 1, 0))
    assert isinstance(entity, DispenserBlockEntity) and entity.items[4] == ("minecraft:stone", 2)


def test_quasi_connectivity_and_dropping_without_a_container() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "dispenser[facing=up]")
    _fill(b, (1, 1, 0), {0: ("minecraft:stone", 1)})
    b.setblock((1, 3, 0), "redstone_block")  # powers the block above the dispenser
    b.setblock((1, 2, 0), "stone")
    b.setblock((0, 1, 0), "stone")  # any neighbor update now lets it notice
    assert b.get((1, 1, 0), TRIGGERED) is True
    b.tick(4)
    entity = b.level.get_block_entity((1, 1, 0))
    assert isinstance(entity, DispenserBlockEntity) and entity.is_empty()  # dispensed


def test_random_slot_is_repeatable() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "dropper[facing=east]")
    _fill(b, (1, 1, 0), {0: ("minecraft:stone", 1), 5: ("minecraft:dirt", 1)})
    entity = b.level.get_block_entity((1, 1, 0))
    assert isinstance(entity, DispenserBlockEntity)
    assert entity.random_slot(b.level) == entity.random_slot(b.level) in (0, 5)
