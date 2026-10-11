"""F3 debug screen text (no display needed)."""

from __future__ import annotations

from redsim.editor.document import Document
from redsim.ui.debug_screen import block_lines, world_lines
from redsim.world import blocks


def test_block_lines_show_state_power_and_ticks() -> None:
    doc = Document.new_flat()
    doc.setblock((1, 1, 0), blocks.parse_state("repeater[facing=east,delay=2]"))
    doc.setblock((2, 1, 0), blocks.REDSTONE_BLOCK.default_state)  # schedules the repeater
    lines = block_lines(doc, (1, 1, 0))
    assert lines[1] == "minecraft:repeater"
    assert "delay: 2" in lines
    # A block of redstone gives weak power only (its direct signal is 0).
    assert any(line.startswith("Receives weak:") and "E15" in line for line in lines)
    assert any(line.startswith("Receives strong:") and "E0" in line for line in lines)
    assert any(line.startswith("Scheduled tick: at 4") for line in lines)
    world = world_lines(doc, "rates", "camera", "normal", None, False)
    assert any("Scheduled ticks: 1 pending" in line for line in world)
