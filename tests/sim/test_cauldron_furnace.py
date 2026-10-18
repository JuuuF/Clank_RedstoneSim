"""Cauldrons and furnaces as comparator sources (cauldron.py, furnace.py; server scenario
``cauldrons_furnaces``). The 5x5 vault lamp door by Purplers reads a water cauldron that a
piston moves and two furnaces through blocks: with both foreign (inert), its comparators
read 0 and the door broke when it opened."""

from __future__ import annotations

from pathlib import Path

import pytest

from redsim.editor.document import Document
from redsim.world import blocks
from redsim.world.blocks.container import item_max_stack
from redsim.world.blocks.furnace import FurnaceBlockEntity
from redsim.world.blocks.hopper import HopperBlockEntity

P = blocks.parse_state


def _output(doc: Document, pos: tuple[int, int, int]) -> int:
    entity = doc.level.get_block_entity(pos, create=False)
    return int(getattr(entity, "output", 0))


def _reader(doc: Document, source: str, nbt: dict | None = None) -> int:
    """A comparator at (1, 1, 0) reading ``source`` at (0, 1, 0), placed first."""
    doc.setblock((1, 1, 0), P("comparator[facing=west]"))
    doc.setblock((0, 1, 0), P(source), nbt)
    doc.run_ticks(4)
    return _output(doc, (1, 1, 0))


@pytest.mark.parametrize(
    ("source", "signal"),
    [
        ("cauldron", 0),
        ("water_cauldron[level=1]", 1),
        ("water_cauldron[level=2]", 2),
        ("water_cauldron[level=3]", 3),
        ("lava_cauldron", 3),
        ("powder_snow_cauldron[level=2]", 2),
    ],
)
def test_comparators_read_how_full_a_cauldron_is(source: str, signal: int) -> None:
    assert _reader(Document.new_flat(), source) == signal


def test_a_piston_moves_a_cauldron_in_front_of_a_comparator_and_back() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("sticky_piston[facing=east]"))
    doc.setblock((1, 1, 0), P("water_cauldron[level=3]"))
    doc.setblock((2, 1, 1), P("comparator[facing=north]"))  # reads (2, 1, 0)
    doc.run_ticks(2)
    assert _output(doc, (2, 1, 1)) == 0
    doc.setblock((-1, 1, 0), P("redstone_block"))
    doc.run_ticks(6)
    assert doc.state_at((2, 1, 0)) == P("water_cauldron[level=3]")
    assert _output(doc, (2, 1, 1)) == 3
    doc.setblock((-1, 1, 0), P("air"))
    doc.run_ticks(6)
    assert doc.state_at((1, 1, 0)) == P("water_cauldron[level=3]")
    assert _output(doc, (2, 1, 1)) == 0


def test_a_cauldron_does_not_conduct() -> None:
    doc = Document.new_flat()
    doc.setblock((1, 1, 0), P("repeater[facing=west]"))
    doc.setblock((2, 1, 0), P("water_cauldron[level=1]"))
    doc.setblock((3, 1, 0), P("redstone_lamp"))
    doc.setblock((0, 1, 0), P("redstone_block"))
    doc.run_ticks(6)
    assert "powered=true" in repr(doc.state_at((1, 1, 0)))
    assert doc.state_at((3, 1, 0)) == P("redstone_lamp[lit=false]")


def _items(*stacks: tuple[int, str, int]) -> dict:
    return {"Items": [{"Slot": slot, "id": item, "count": count} for slot, item, count in stacks]}


@pytest.mark.parametrize(
    ("source", "nbt", "signal"),
    [
        ("furnace", None, 0),
        ("furnace", _items((0, "minecraft:redstone", 1)), 1),
        ("furnace", _items((1, "minecraft:wooden_shovel", 1)), 5),  # stacks to 1
        ("blast_furnace", _items((0, "minecraft:cobblestone", 64), (2, "minecraft:stone", 7)), 6),
        ("smoker", _items((0, "minecraft:ender_pearl", 8)), 3),  # stacks to 16
    ],
)
def test_comparators_read_a_furnaces_contents(source: str, nbt: dict | None, signal: int) -> None:
    assert _reader(Document.new_flat(), source, nbt) == signal


def test_pistons_cannot_push_furnaces() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("piston[facing=east]"))
    doc.setblock((1, 1, 0), P("smoker"))
    doc.setblock((-1, 1, 0), P("redstone_block"))
    doc.run_ticks(4)
    assert doc.state_at((0, 1, 0)) == P("piston[facing=east,extended=false]")
    assert doc.state_at((1, 1, 0)).block.id == "minecraft:smoker"


def test_hoppers_leave_furnaces_alone() -> None:
    """Not as in the game: a hopper would fill the furnace (doc/differences.md)."""
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("furnace"))
    doc.setblock((0, 2, 0), P("hopper[facing=down]"), _items((0, "minecraft:coal", 2)))
    doc.run_ticks(20)
    hopper = doc.level.get_block_entity((0, 2, 0))
    assert isinstance(hopper, HopperBlockEntity) and hopper.contents() == "0:minecraft:coal*2"
    furnace = doc.level.get_block_entity((0, 1, 0))
    assert isinstance(furnace, FurnaceBlockEntity) and furnace.is_empty()


def test_furnace_data_survives_saving(tmp_path: Path) -> None:
    doc = Document.new_flat()
    nbt = {**_items((1, "minecraft:wooden_shovel", 1)), "cooking_total_time": 200,
           "speed_multiplier": 1.0, "RecipesUsed": {}}  # fmt: skip
    doc.setblock((0, 1, 0), P("furnace[facing=east]"), nbt)
    path = tmp_path / "furnace.redsim.json"
    doc.save(path)
    entity = Document.open(path).level.get_block_entity((0, 1, 0), create=False)
    assert isinstance(entity, FurnaceBlockEntity)
    assert entity.to_json() == nbt


def test_filling_a_furnace_that_has_no_block_entity_yet() -> None:
    """Worlds saved while furnaces were foreign have none: the editor starts from the empty
    data the game creates on first access."""
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("furnace"))
    doc.level.block_entities.pop((0, 1, 0), None)
    doc.set_container_slot((0, 1, 0), 1, "minecraft:wooden_shovel", 1)
    entity = doc.level.get_block_entity((0, 1, 0), create=False)
    assert isinstance(entity, FurnaceBlockEntity) and entity.signal() == 5


@pytest.mark.parametrize(
    ("item", "size"),
    [("minecraft:stone", 64), ("minecraft:wooden_shovel", 1), ("minecraft:iron_sword", 1),
     ("minecraft:ender_pearl", 16), ("minecraft:oak_sign", 16), ("minecraft:potion", 1)],
)  # fmt: skip
def test_item_stack_sizes_come_from_the_game(item: str, size: int) -> None:
    assert item_max_stack(item) == size
