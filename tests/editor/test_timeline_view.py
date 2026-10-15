"""Timeline view data: scrubbing by tick, edit markers, monitors (no display needed)."""

from __future__ import annotations

from pathlib import Path

from redsim.core.direction import Direction
from redsim.editor.document import Document
from redsim.editor.placement import PlaceRequest
from redsim.world import blocks

UP = PlaceRequest(clicked_face=Direction.UP, yaw=0.0, pitch=90.0)


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


def test_editing_after_a_rewind_keeps_the_later_edits() -> None:
    doc = lamp_circuit()
    doc.run_ticks(3)
    doc.setblock((0, 1, 0), blocks.REDSTONE_BLOCK.default_state)  # keyframe at tick 3
    doc.run_ticks(5)
    doc.seek_tick(1)
    doc.setblock((5, 1, 5), blocks.STONE.default_state)  # an edit before it
    assert doc.tick == 1 and doc.end_tick == 8
    assert sorted(doc.edit_ticks.values()) == [1, 3]
    assert max(doc.tick_steps) == 8
    assert doc.samples[(1, 1, 0)][8] == 15  # the lamp still lights from the kept edit
    assert doc.state_at((5, 1, 5)).is_(blocks.STONE)
    assert doc.undo() and sorted(doc.edit_ticks.values()) == [3]


def test_building_at_tick_0_keeps_the_recorded_edits() -> None:
    doc = lamp_circuit()
    doc.run_ticks(2)
    doc.setblock((0, 1, 0), blocks.REDSTONE_BLOCK.default_state)
    doc.run_ticks(4)
    assert doc.jump("start")
    doc.place_many(
        [(3, 1, x) for x in range(3)],
        blocks.STONE,
        UP,
    )
    assert doc.tick == 0 and doc.end_tick == 6
    assert sorted(doc.edit_ticks.values()) == [2]
    assert doc.seek_tick(6) and doc.state_at((0, 1, 0)).is_(blocks.REDSTONE_BLOCK)
    assert doc.state_at((3, 1, 2)).is_(blocks.STONE)
    assert doc.undo() and doc.state_at((3, 1, 2)).is_air  # one undo step for the line


def test_a_later_edit_that_no_longer_fits_is_dropped() -> None:
    doc = lamp_circuit()
    doc.run_ticks(2)
    doc.place((0, 1, 0), blocks.REDSTONE_BLOCK, UP)
    doc.run_ticks(2)
    doc.seek_tick(1)
    doc.place((0, 1, 0), blocks.STONE, UP)  # the later placement's cell is now taken
    assert sorted(doc.edit_ticks.values()) == [1]
    assert "could not be applied" in doc.notice
    assert doc.end_tick == 4


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
    # Saved after running: the file keeps the build and reopens at tick 4 (ADR-027).
    assert again.tick == 4 and again.end_tick == 4 and again.engine.game_time == 4
    assert again.jump("start") and again.tick == 0 and again.engine.game_time == 0
    doc.run_ticks(3)
    doc.set_tick_zero()
    assert doc.tick == 0 and doc.end_tick == 0 and doc.engine.game_time == 0
    assert "game time 0 → 1" in doc.engine.peek_next_step()


def test_set_tick_zero_after_letting_the_circuit_settle() -> None:
    """Owner workflow: add a redstone block, run a few ticks so it updates the circuit,
    then make that the build. Edits recorded later move along."""
    doc = Document.new_flat()
    doc.setblock(
        (1, 1, 0),
        blocks.REPEATER.default_state.with_(
            blocks.REPEATER.properties[0], blocks.REPEATER.properties[0].values[2]
        ),
    )  # facing
    doc.setblock((2, 1, 0), blocks.REDSTONE_LAMP.default_state)
    doc.run_ticks(2)
    doc.setblock((0, 1, 0), blocks.REDSTONE_BLOCK.default_state)  # recorded at tick 2
    doc.merge_edits(doc.edit_batches()[0].indices, tick=0)  # moved into the build
    assert doc.tick == 2  # the view stays where it was
    doc.run_ticks(5)
    doc.setblock((4, 1, 4), blocks.STONE.default_state)  # recorded at tick 7
    doc.run_ticks(3)
    doc.seek_tick(4)
    lit = doc.state_at((2, 1, 0)).get(blocks.REDSTONE_LAMP.properties[0])
    doc.set_tick_zero()
    assert doc.tick == 0 and doc.history.at_base
    assert doc.state_at((2, 1, 0)).get(blocks.REDSTONE_LAMP.properties[0]) == lit
    assert [b.tick for b in doc.edit_batches()] == [3]  # tick 7 → tick 3
    assert doc.end_tick == 6  # recorded to tick 10 → 6
    assert doc.undo() and doc.tick == 4 and [b.tick for b in doc.edit_batches()] == [7]


def test_a_world_saved_after_running_keeps_its_build(tmp_path: Path) -> None:
    """ADR-027: before, the state at the playhead silently became the new build."""
    lit = blocks.REDSTONE_LAMP.properties[0]
    doc = lamp_circuit()
    doc.setblock((0, 1, 0), blocks.REDSTONE_BLOCK.default_state)  # the lamp lights at once
    doc.setblock((0, 1, 0), blocks.AIR.default_state)  # and goes off 4 ticks later
    assert doc.state_at((1, 1, 0)).get(lit)
    doc.run_ticks(6)
    doc.save(tmp_path / "w.redsim.json")
    again = Document.open(tmp_path / "w.redsim.json")
    assert again.tick == 6 and not again.state_at((1, 1, 0)).get(lit)
    assert again.seek_tick(0) and again.state_at((1, 1, 0)).get(lit)  # the build


def test_deferred_edits_rerun_once_and_undo_one_by_one() -> None:
    doc = lamp_circuit()
    doc.run_ticks(2)
    doc.setblock((0, 1, 0), blocks.REDSTONE_BLOCK.default_state)  # recorded at tick 2
    doc.run_ticks(4)
    doc.seek_tick(0)
    with doc.deferred():
        doc.setblock((5, 1, 5), blocks.STONE.default_state)
        doc.setblock((6, 1, 5), blocks.STONE.default_state)
        assert doc.end_tick == 0  # the future waits
    assert doc.end_tick == 6 and sorted(doc.edit_ticks.values()) == [2]
    assert doc.undo() and doc.state_at((6, 1, 5)).is_air
    assert doc.state_at((5, 1, 5)).is_(blocks.STONE) and sorted(doc.edit_ticks.values()) == [2]
    assert doc.undo() and doc.state_at((5, 1, 5)).is_air and doc.end_tick == 6
