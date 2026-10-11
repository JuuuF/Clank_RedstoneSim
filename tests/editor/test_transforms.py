"""Rotating, mirroring and stacking selections in place (editor tools, no block updates)."""

from __future__ import annotations

from redsim.core.direction import Direction
from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.world import blocks
from redsim.world.properties import EAST_REDSTONE, HORIZONTAL_FACING, POWERED, WEST_REDSTONE


def doc_with_line() -> Document:
    """A repeater facing east (input east, output west) with a lamp east of it."""
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), blocks.parse_state("repeater[facing=east]"))
    doc.setblock((1, 1, 0), blocks.REDSTONE_LAMP.default_state)
    return doc


def test_rotating_turns_positions_and_states_clockwise() -> None:
    doc = doc_with_line()
    box = doc.transform_region(Region((0, 1, 0), (1, 1, 0)), quarter_turns=1)
    assert box == Region((1, 1, 0), (1, 1, 1))  # 2×1 footprint becomes 1×2 around the pivot
    repeater = doc.state_at((1, 1, 0))
    assert repeater.is_(blocks.REPEATER) and repeater.get(HORIZONTAL_FACING) is Direction.SOUTH
    assert doc.state_at((1, 1, 1)).is_(blocks.REDSTONE_LAMP)  # east of it → south of it
    assert doc.state_at((0, 1, 0)).is_air
    doc.undo()  # one undo step
    assert doc.state_at((0, 1, 0)).get(HORIZONTAL_FACING) is Direction.EAST


def test_mirroring_swaps_sides_and_facings() -> None:
    doc = doc_with_line()
    doc.setblock((0, 1, 1), blocks.parse_state("redstone_wire[east=side,west=none]"))
    box = doc.transform_region(Region((0, 1, 0), (1, 1, 1)), mirror="x")
    assert box == Region((0, 1, 0), (1, 1, 1))
    assert doc.state_at((0, 1, 0)).is_(blocks.REDSTONE_LAMP)
    assert doc.state_at((1, 1, 0)).get(HORIZONTAL_FACING) is Direction.WEST
    wire = doc.state_at((1, 1, 1))
    assert wire.get(WEST_REDSTONE) == "side" and wire.get(EAST_REDSTONE) == "none"


def test_pending_ticks_move_with_their_blocks() -> None:
    doc = Document.new_flat()
    doc.setblock((1, 1, 0), blocks.parse_state("repeater[facing=east,delay=4]"))
    doc.setblock((2, 1, 0), blocks.REDSTONE_BLOCK.default_state)  # schedules the repeater
    doc.run_ticks(1)
    box = doc.transform_region(Region((1, 1, 0), (1, 1, 0)), quarter_turns=2)
    assert box == Region((1, 1, 0), (1, 1, 0))
    pending = [(t.pos, t.block_id) for t in doc.level.block_ticks.pending()]
    assert ((1, 1, 0), "minecraft:repeater") in pending
    doc.run_ticks(8)
    assert doc.state_at((1, 1, 0)).get(POWERED) is True  # the tick still fired


def test_stacking_repeats_the_selection() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), blocks.REDSTONE_LAMP.default_state)
    box = doc.stack_region(Region((0, 1, 0), (0, 1, 0)), (2, 0, 0), 3)
    assert box == Region((0, 1, 0), (6, 1, 0))
    assert [doc.state_at((x, 1, 0)).is_(blocks.REDSTONE_LAMP) for x in range(7)] == [
        True, False, True, False, True, False, True,
    ]  # fmt: skip
    doc.undo()
    assert doc.state_at((2, 1, 0)).is_air


def test_turning_back_and_four_turns_return_to_the_start() -> None:
    from redsim.world.rotation import default_pivot2

    doc = doc_with_line()
    start = Region((0, 1, 0), (1, 1, 0))  # 2 × 1: the center is not on the cell grid
    pivot = default_pivot2(start.low, start.high)
    turned = doc.transform_region(start, 1, pivot2=pivot)
    back = doc.transform_region(turned, 3, pivot2=pivot)
    assert back == start
    assert doc.state_at((0, 1, 0)).get(HORIZONTAL_FACING) is Direction.EAST
    assert doc.state_at((1, 1, 0)).is_(blocks.REDSTONE_LAMP)
    box = start
    for _ in range(4):
        box = doc.transform_region(box, 1, pivot2=pivot)
    assert box == start and doc.state_at((1, 1, 0)).is_(blocks.REDSTONE_LAMP)
