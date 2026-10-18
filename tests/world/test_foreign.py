"""Blocks the simulator does not model (foreign blocks) take the game's piston and conductor
settings from the block table: a block with a block entity is never moved by pistons
(owner's "simulation_bug" world, EXP-050)."""

from __future__ import annotations

import pytest

from redsim.editor.document import Document
from redsim.world import blocks
from redsim.world.block import Conductor, PushReaction
from redsim.world.blocks.foreign import ForeignBlock
from redsim.world.properties import EXTENDED

P = blocks.parse_state


def test_block_entities_are_immovable_and_settings_come_from_the_game() -> None:
    # (The owner's worlds had furnaces, jukeboxes, enchanting tables: all simulated since.)
    beehive = P("beehive").block
    assert isinstance(beehive, ForeignBlock)
    assert beehive.push_reaction is PushReaction.IMMOVEABLE  # it has a block entity
    assert P("beacon").block.conductor is Conductor.NEVER  # isRedstoneConductor(never)
    assert P("white_bed[part=foot]").block.push_reaction is PushReaction.POPPED
    assert P("end_portal_frame").block.destroy_speed == -1.0


@pytest.mark.parametrize("block", ["furnace[facing=north,lit=false]", "beehive"])
def test_slime_leaves_a_block_entity_behind(block: str) -> None:
    """A sticky piston pushes a slime block that touches a furnace (simulated) or a
    beehive (foreign): the slime moves, the other block stays (``isPushable`` is
    false for block entities; pulled blocks that are not pushable are left out of the
    structure)."""
    doc = Document.new_flat()  # in the air, so the slime does not drag the floor along
    doc.setblock((0, 4, 0), P("sticky_piston[facing=east]"))
    doc.setblock((1, 4, 0), P("slime_block"))
    doc.setblock((1, 4, 1), P(block))
    doc.run_ticks(2)
    doc.setblock((-1, 4, 0), P("redstone_block"))  # powers the piston
    doc.run_ticks(4)
    assert doc.state_at((0, 4, 0)).get(EXTENDED)
    assert doc.state_at((2, 4, 0)).is_(blocks.SLIME_BLOCK)  # moved one block east
    assert repr(doc.state_at((1, 4, 1))) == f"minecraft:{block}"  # stayed
    assert doc.state_at((2, 4, 1)).is_air
