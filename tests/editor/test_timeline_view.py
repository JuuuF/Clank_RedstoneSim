"""Timeline view data: scrubbing by tick, edit markers, monitors (no display needed)."""

from __future__ import annotations

from pathlib import Path

from redsim.editor.document import Document
from redsim.world import blocks


def lamp_circuit() -> Document:
    doc = Document.new_flat()
    doc.setblock((1, 1, 0), blocks.REDSTONE_LAMP.default_state)
    doc.toggle_monitor((1, 1, 0))
    return doc


def test_scrub_markers_and_monitor_samples() -> None:
    doc = lamp_circuit()
    doc.run_ticks(3)
    doc.setblock((0, 1, 0), blocks.REDSTONE_BLOCK.default_state)  # lamp lights at once
    doc.run_ticks(2)
    doc.setblock((0, 1, 0), blocks.AIR.default_state)  # lamp turns off 4 ticks later
    doc.run_ticks(6)
    assert doc.end_tick == 11
    assert sorted(doc.edit_ticks.values()) == [3, 5]  # the tick-0 lamp is part of the build
    samples = doc.samples[(1, 1, 0)]
    assert [samples[t] for t in (2, 3, 8, 9, 10)] == [0, 15, 15, 0, 0]
    assert doc.seek_tick(4) and doc.engine.game_time == 4
    assert doc.state_at((0, 1, 0)).is_(blocks.REDSTONE_BLOCK)
    assert doc.seek_tick(11) and doc.engine.game_time == 11


def test_editing_after_a_rewind_forgets_the_old_future() -> None:
    doc = lamp_circuit()
    doc.run_ticks(5)
    doc.seek_tick(2)
    doc.setblock((0, 1, 0), blocks.REDSTONE_BLOCK.default_state)
    assert doc.end_tick == 2
    assert max(doc.tick_steps) == 2
    assert max(doc.samples[(1, 1, 0)]) == 2


def test_monitors_are_saved(tmp_path: Path) -> None:
    doc = lamp_circuit()
    doc.save(tmp_path / "w.redsim.json")
    again = Document.open(tmp_path / "w.redsim.json")
    assert again.monitors == [(1, 1, 0)]
    assert not again.toggle_monitor((1, 1, 0)) and again.monitors == []


def test_the_build_at_tick_0_is_not_replayed() -> None:
    doc = Document.new_flat()
    for x in range(5):
        doc.setblock((x, 1, 0), blocks.REDSTONE_WIRE.default_state)
    doc.setblock((-1, 1, 0), blocks.REDSTONE_BLOCK.default_state)
    assert doc.history.inputs == {}  # folded into the base
    doc.run_ticks(4)
    assert doc.jump("start") and doc.tick == 0
    assert doc.history.position == doc.history.start  # restored, not re-executed
    assert doc.state_at((4, 1, 0)).get(blocks.REDSTONE_WIRE.properties[-1]) == 11


def test_edits_at_one_tick_replay_together() -> None:
    doc = Document.new_flat()
    doc.run_ticks(5)
    for x in range(3):
        doc.setblock((x, 1, 0), blocks.STONE.default_state)
    doc.run_ticks(5)
    assert [b.tick for b in doc.edit_batches()] == [5]
    assert len(doc.edit_batches()[0].indices) == 3
    doc.seek_tick(4)
    assert all(doc.state_at((x, 1, 0)).is_air for x in range(3))
    doc.run_tick()
    assert doc.tick == 5 and all(doc.state_at((x, 1, 0)).is_(blocks.STONE) for x in range(3))


def test_a_failed_edit_leaves_no_trace_in_the_replay() -> None:
    import pytest

    from redsim.core.direction import Direction
    from redsim.editor.document import EditError
    from redsim.editor.placement import PlaceRequest

    doc = Document.new_flat()
    request = PlaceRequest(Direction.UP, 0.0, 60.0)
    doc.run_ticks(2)
    doc.place((0, 1, 0), blocks.REPEATER, request)
    with pytest.raises(EditError):
        doc.place((0, 1, 0), blocks.STONE, request)  # occupied
    doc.place((1, 1, 0), blocks.REDSTONE_LAMP, request)
    doc.run_ticks(6)
    final = dict(doc.level.blocks)
    doc.jump("start")
    while doc.tick < 8:
        doc.run_tick()  # used to fail: "player actions happen between ticks"
    assert dict(doc.level.blocks) == final


def test_undo_removes_a_timed_edit_from_the_history() -> None:
    doc = lamp_circuit()
    doc.run_ticks(3)
    doc.setblock((0, 1, 0), blocks.REDSTONE_BLOCK.default_state)
    doc.run_ticks(5)
    assert doc.undo()
    assert doc.tick == 3 and doc.end_tick == 8
    assert doc.edit_ticks == {}
    doc.seek_tick(8)
    assert doc.state_at((0, 1, 0)).is_air
    assert doc.redo()
    doc.seek_tick(8)
    assert doc.state_at((0, 1, 0)).is_(blocks.REDSTONE_BLOCK)


def test_undo_at_tick_0_restores_the_build() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), blocks.STONE.default_state)
    doc.setblock((1, 1, 0), blocks.STONE.default_state)
    assert doc.undo() and doc.state_at((1, 1, 0)).is_air
    assert doc.state_at((0, 1, 0)).is_(blocks.STONE)
    assert doc.redo() and doc.state_at((1, 1, 0)).is_(blocks.STONE)


def test_moving_merging_and_baking_edit_batches() -> None:
    doc = lamp_circuit()
    doc.run_ticks(2)
    doc.setblock((0, 1, 0), blocks.REDSTONE_BLOCK.default_state)
    doc.run_ticks(3)
    doc.setblock((3, 1, 0), blocks.STONE.default_state)
    doc.run_ticks(4)
    assert [b.tick for b in doc.edit_batches()] == [2, 5]
    first = doc.edit_batches()[0]
    doc.move_edits(first.indices, +2)
    assert [b.tick for b in doc.edit_batches()] == [4, 5]
    assert doc.samples[(1, 1, 0)][3] == 0 and doc.samples[(1, 1, 0)][4] == 15
    doc.merge_edits([i for b in doc.edit_batches() for i in b.indices])
    assert [b.tick for b in doc.edit_batches()] == [4]
    assert len(doc.edit_batches()[0].indices) == 2
    doc.merge_edits(doc.edit_batches()[0].indices, tick=0)  # into the build
    assert doc.edit_batches() == [] and doc.end_tick == 9
    doc.jump("start")
    assert doc.state_at((0, 1, 0)).is_(blocks.REDSTONE_BLOCK)
    assert doc.undo() and [b.tick for b in doc.edit_batches()] == [4]
    doc.delete_edits(doc.edit_batches()[0].indices)
    assert doc.edit_batches() == []


def test_set_tick_zero_and_relative_ticks(tmp_path: Path) -> None:
    doc = lamp_circuit()
    doc.run_ticks(4)
    doc.save(tmp_path / "w.redsim.json")
    again = Document.open(tmp_path / "w.redsim.json")
    assert again.engine.game_time == 4 and again.tick == 0  # saved at game time 4
    doc.run_ticks(3)
    doc.set_tick_zero()
    assert doc.tick == 0 and doc.end_tick == 0 and doc.engine.game_time == 7
