"""Several selections at once: moved, copied, turned and flipped together (one undo
step, no block updates, pending ticks along), and copied into one clipboard."""

from __future__ import annotations

from redsim.core.direction import Direction
from redsim.editor.clipboard import Region, bounding_box
from redsim.editor.document import Document
from redsim.world import blocks
from redsim.world.properties import HORIZONTAL_FACING
from redsim.world.rotation import default_pivot2

P = blocks.parse_state
A = Region((0, 1, 0), (1, 1, 0))  # two cells
B = Region((3, 1, 0), (3, 1, 0))  # one cell, two blocks east of A


def document() -> Document:
    doc = Document.new_flat()
    with doc.batch():
        doc.setblock((0, 1, 0), P("redstone_block"))
        doc.setblock((1, 1, 0), P("repeater[facing=east]"))
        doc.setblock((2, 1, 0), P("glass"))  # between the boxes: never touched
        doc.setblock((3, 1, 0), P("observer[facing=north]"))
    return doc


def name(doc: Document, pos: tuple[int, int, int]) -> str:
    return repr(doc.state_at(pos))


def test_boxes_move_together_even_onto_each_other() -> None:
    doc = document()
    before = {p: name(doc, p) for p in [(0, 1, 0), (1, 1, 0), (3, 1, 0)]}
    # Shift east by 2: A lands on (2..3), where B was; B goes to 5.
    moved = doc.transform_regions([A, B], offset=(2, 0, 0))
    assert moved == [Region((2, 1, 0), (3, 1, 0)), Region((5, 1, 0), (5, 1, 0))]
    assert name(doc, (2, 1, 0)) == before[(0, 1, 0)]
    assert name(doc, (3, 1, 0)) == before[(1, 1, 0)]
    assert name(doc, (5, 1, 0)) == before[(3, 1, 0)]
    assert doc.state_at((0, 1, 0)).is_air and doc.state_at((1, 1, 0)).is_air
    doc.undo()
    assert {p: name(doc, p) for p in before} == before
    assert name(doc, (2, 1, 0)) == "minecraft:glass"


def test_copy_keeps_the_sources_and_the_cells_between() -> None:
    doc = document()
    copied = doc.transform_regions([A, B], offset=(0, 0, 3), copy=True)
    assert copied == [Region((0, 1, 3), (1, 1, 3)), Region((3, 1, 3), (3, 1, 3))]
    for x in (0, 1, 3):
        assert name(doc, (x, 1, 3)) == name(doc, (x, 1, 0))
    assert doc.state_at((2, 1, 3)).is_air  # not in a box: not copied
    assert name(doc, (2, 1, 0)) == "minecraft:glass"


def test_turning_four_times_returns_to_the_start() -> None:
    doc = document()
    start = {p: repr(s) for p, s in doc.level.blocks.items()}
    regions = [A, B]
    pivot = default_pivot2(*bounding_box(regions))  # kept, as the window does
    for _ in range(4):
        regions = doc.transform_regions(regions, quarter_turns=1, pivot2=pivot)
    assert regions == [A, B]
    # The glass between the boxes was overwritten on the way (turned boxes land on it, as
    # a single turned box lands on its neighbors); everything in the boxes is back.
    now = {p: repr(s) for p, s in doc.level.blocks.items()}
    assert {p: v for p, v in now.items() if p != (2, 1, 0)} == {
        p: v for p, v in start.items() if p != (2, 1, 0)
    }


def test_turning_and_flipping_turn_the_blocks_too() -> None:
    doc = document()
    turned = doc.transform_regions([A, B], quarter_turns=1)
    # The repeater faced east; a clockwise quarter turn makes it face south.
    repeater = next(p for p, s in doc.level.blocks.items() if s.block.id.endswith("repeater"))
    assert doc.state_at(repeater).get(HORIZONTAL_FACING) is Direction.SOUTH
    assert any(r.contains(repeater) for r in turned)
    doc.undo()
    flipped = doc.transform_regions([A, B], mirror="x")
    # Mirrored within the box around both (x 0..3): A goes to 2..3, B to 0.
    assert flipped == [Region((2, 1, 0), (3, 1, 0)), Region((0, 1, 0), (0, 1, 0))]
    assert doc.state_at((2, 1, 0)).get(HORIZONTAL_FACING) is Direction.WEST
    assert doc.state_at((3, 1, 0)).block is blocks.REDSTONE_BLOCK


def test_pending_ticks_move_with_their_blocks() -> None:
    doc = Document.new_flat()
    with doc.batch():
        doc.setblock((0, 1, 0), P("repeater[facing=east,delay=4]"))
        doc.setblock((1, 1, 0), P("redstone_block"))  # its input (facing east: from the east)
    doc.run_ticks(1)  # the repeater has a pending tick now
    assert any(t.pos == (0, 1, 0) for t in doc.level.block_ticks.pending())
    doc.transform_regions(
        [Region((0, 1, 0), (0, 1, 0)), Region((4, 1, 0), (4, 1, 0))], offset=(0, 0, 5)
    )
    pending = {t.pos for t in doc.level.block_ticks.pending()}
    assert (0, 1, 5) in pending and (0, 1, 0) not in pending


def test_several_boxes_copy_into_one_clipboard() -> None:
    doc = document()
    prefab = doc.copy([A, B])
    assert prefab.size == (4, 1, 1)
    assert sorted(e[0] for e in prefab.blocks) == [0, 1, 3]  # the glass between is left out
    doc.paste((0, 1, 5))
    assert name(doc, (3, 1, 5)) == name(doc, (3, 1, 0))
    assert doc.state_at((2, 1, 5)).is_air


def test_replay_and_saving_keep_the_transform(tmp_path) -> None:  # type: ignore[no-untyped-def]
    doc = document()
    doc.run_ticks(2)
    doc.transform_regions([A, B], quarter_turns=1, offset=(0, 0, 2))
    after = {p: repr(s) for p, s in doc.level.blocks.items()}
    doc.save(tmp_path / "multi.redsim.json")
    loaded = Document.open(tmp_path / "multi.redsim.json")
    loaded.seek_tick(doc.tick)
    assert {p: repr(s) for p, s in loaded.level.blocks.items()} == after
