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
    assert sorted(doc.edit_ticks.values()) == [0, 3, 5]
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
