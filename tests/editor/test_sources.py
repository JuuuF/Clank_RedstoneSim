"""Signal sources backed by real blocks: placement, swapping, strengths."""

from __future__ import annotations

import pytest

from redsim.core.direction import Direction
from redsim.editor import sources
from redsim.editor.document import Document
from redsim.editor.placement import PlaceRequest
from redsim.world import blocks
from redsim.world.properties import FACING, POWERED

LOOK_DOWN_SOUTH = PlaceRequest(Direction.UP, 0.0, 60.0)


@pytest.mark.parametrize("kind", ["barrel", "lectern"])
@pytest.mark.parametrize("strength", [0, 1, 7, 8, 14, 15])
def test_placed_source_reads_the_chosen_strength(kind: str, strength: int) -> None:
    doc = Document.new_flat()
    doc.place_source((0, 1, 0), kind, strength, LOOK_DOWN_SOUTH)
    assert sources.strength_at(doc.level, (0, 1, 0)) == strength


def test_barrel_fill_uses_the_fewest_items() -> None:
    assert [sources.barrel_total(s) for s in (0, 1, 2, 15)] == [0, 1, 124, 1728]


def test_barrel_faces_like_a_player_would_place_it() -> None:
    doc = Document.new_flat()
    doc.place_source((0, 1, 0), "barrel", 3, LOOK_DOWN_SOUTH)  # looking down: faces up
    assert doc.state_at((0, 1, 0)).get(FACING) is Direction.UP


def test_swapping_keeps_strength_and_cake_rounds_to_even() -> None:
    doc = Document.new_flat()
    doc.place_source((0, 1, 0), "barrel", 9, LOOK_DOWN_SOUTH)
    doc.set_source((0, 1, 0), "lectern", 9)
    assert doc.state_at((0, 1, 0)).is_(blocks.LECTERN)
    assert sources.strength_at(doc.level, (0, 1, 0)) == 9
    doc.set_source((0, 1, 0), "cake", 9)
    assert sources.strength_at(doc.level, (0, 1, 0)) == 8  # nearest even (lower on ties)
    assert "using 8" in doc.notice
    doc.set_source((0, 1, 0), "barrel", 12)
    assert sources.strength_at(doc.level, (0, 1, 0)) == 12
    doc.undo()  # each change is one undo step
    assert doc.state_at((0, 1, 0)).is_(blocks.CAKE)


def test_turning_a_page_changes_the_signal_and_pulses() -> None:
    doc = Document.new_flat()
    doc.place_source((0, 1, 0), "lectern", 4, LOOK_DOWN_SOUTH)
    doc.turn_page((0, 1, 0), 10)
    assert sources.strength_at(doc.level, (0, 1, 0)) == 11
    assert doc.state_at((0, 1, 0)).get(POWERED) is True
    doc.run_ticks(2)
    assert doc.state_at((0, 1, 0)).get(POWERED) is False
