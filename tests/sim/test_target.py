"""Target block: dust connects to it; projectile hits power it (game: EXP-037)."""

from __future__ import annotations

from redsim.editor.document import Document
from redsim.world import blocks
from redsim.world.blocks.target import hit_strength
from redsim.world.properties import POWER


def test_hit_strength_from_the_distance_to_the_center() -> None:
    assert hit_strength(0.0) == 15
    assert hit_strength(0.25) == 8  # ceil(7.5)
    assert hit_strength(0.5) == 1  # the edge still gives 1


def test_an_arrow_powers_the_target_for_20_ticks_after_landing() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 1), blocks.REDSTONE_WIRE.default_state)
    doc.setblock((0, 1, 0), blocks.TARGET.default_state)  # the dust bends towards it
    assert doc.state_at((0, 1, 1)).get(blocks.REDSTONE_WIRE.properties[0]) == "side"  # north
    doc.projectile_hit((0, 1, 0), 15, arrow=True)
    assert doc.state_at((0, 1, 0)).get(POWER) == 0  # lands during the next tick
    doc.run_ticks(1)
    assert doc.state_at((0, 1, 0)).get(POWER) == 15
    assert doc.state_at((0, 1, 1)).get(POWER) == 15
    doc.run_ticks(19)
    assert doc.state_at((0, 1, 0)).get(POWER) == 15
    doc.run_ticks(1)
    assert doc.state_at((0, 1, 0)).get(POWER) == 0
