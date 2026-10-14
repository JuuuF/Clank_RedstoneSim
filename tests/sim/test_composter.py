"""Composters: levels as comparator signals, 7 becoming 8, emptying by a player or a
hopper below; hoppers, chests and composters as signal-source kinds."""

from __future__ import annotations

import pytest

from redsim.editor import sources
from redsim.editor.document import Document
from redsim.world import blocks
from redsim.world.blocks.composter import LEVEL
from redsim.world.blocks.hopper import HopperBlockEntity

P = blocks.parse_state


def test_level_seven_becomes_ready_after_twenty_ticks() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("composter[level=7]"))
    doc.run_ticks(19)
    assert doc.state_at((0, 1, 0)).get(LEVEL) == 7
    doc.run_ticks(1)
    assert doc.state_at((0, 1, 0)).get(LEVEL) == 8


def test_comparators_read_the_level_and_players_empty_a_full_one() -> None:
    doc = Document.new_flat()
    doc.setblock((1, 1, 0), P("comparator[facing=west]"))  # reads the block to its west
    doc.setblock((0, 1, 0), P("composter[level=5]"))  # (placed after: the comparator updates)
    doc.run_ticks(3)
    entity = doc.level.get_block_entity((1, 1, 0))
    assert entity is not None and entity.output == 5  # type: ignore[attr-defined]
    doc.use((0, 1, 0))  # not full: nothing happens
    assert doc.state_at((0, 1, 0)).get(LEVEL) == 5
    doc.setblock((0, 1, 0), P("composter[level=8]"))
    doc.run_ticks(3)
    doc.use((0, 1, 0))
    doc.run_ticks(3)
    assert doc.state_at((0, 1, 0)).get(LEVEL) == 0
    assert entity.output == 0  # type: ignore[attr-defined]


def test_a_hopper_below_takes_the_bone_meal() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("hopper[facing=east]"))
    doc.setblock((0, 2, 0), P("composter[level=8]"))
    doc.run_ticks(2)
    assert doc.state_at((0, 2, 0)).get(LEVEL) == 0
    hopper = doc.level.get_block_entity((0, 1, 0))
    assert isinstance(hopper, HopperBlockEntity)
    assert hopper.items[0] == ("minecraft:bone_meal", 1)


def test_pistons_move_composters() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("piston[facing=east]"))
    doc.setblock((1, 1, 0), P("composter[level=3]"))
    doc.run_ticks(1)
    doc.setblock((-1, 1, 0), P("redstone_block"))
    doc.run_ticks(4)
    assert doc.state_at((2, 1, 0)) == P("composter[level=3]")


@pytest.mark.parametrize("kind", ["hopper", "chest", "composter", "barrel"])
def test_every_strength_of_the_new_source_kinds(kind: str) -> None:
    doc = Document.new_flat()
    for strength in sources.KINDS[kind].strengths:
        doc.setblock((0, 1, 0), blocks.AIR.default_state)
        doc.setblock((0, 1, 0), P("stone"))  # a fresh block each time
        doc.set_source((0, 1, 0), kind, strength)
        assert sources.strength_at(doc.level, (0, 1, 0)) == strength, (kind, strength)
