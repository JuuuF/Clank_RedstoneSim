"""Timeline lines of a sequence: groups, order, saving."""

from __future__ import annotations

from pathlib import Path

from redsim.editor.document import Document
from redsim.editor.lines import BLOCKS_GROUP, DEFAULT_GROUP, Lines

A, B, C = (0, 1, 0), (0, 1, 1), (0, 1, 2)


def test_lines_follow_the_pulses_and_keep_the_chosen_order() -> None:
    lines = Lines()
    assert lines.sync([A, B, C])
    assert [g.name for g in lines.groups] == [DEFAULT_GROUP]
    assert lines.groups[0].members == [A, B, C]
    lines.move(C, 0, 0)  # dragged to the top
    assert lines.groups[0].members == [C, A, B]
    outputs = lines.add_group("Outputs", [A])
    assert lines.group_of(A) == outputs and lines.groups[0].members == [C, B]
    lines.move(B, outputs, 0)
    assert lines.groups[outputs].members == [B, A]
    assert lines.sync([A, C])  # B lost its pulses: its line goes
    assert lines.groups[outputs].members == [A]
    lines.move_group(outputs, -1)
    assert [g.name for g in lines.groups] == ["Outputs", DEFAULT_GROUP]
    lines.remove_group(0)  # its lines join a neighbor group
    assert lines.groups[0].members == [C, A]


def test_groups_are_saved_with_the_document(tmp_path: Path) -> None:
    doc = Document.new_flat()
    doc.lines.sync([A, B])
    doc.lines.add_group("Inputs", [B])
    doc.lines.groups[1].collapsed = True
    doc.save(tmp_path / "lines.redsim.json")
    loaded = Document.open(tmp_path / "lines.redsim.json")
    assert loaded.lines == doc.lines


def test_every_category_has_its_own_saved_groups(tmp_path: Path) -> None:
    doc = Document.new_flat()
    placed = doc.lines_of("build")
    assert placed is doc.lines_of("build") and doc.lines_of("power") is doc.lines
    placed.sync([A, B], BLOCKS_GROUP, "#55aa55")
    placed.add_group("Clock", [B])
    doc.save(tmp_path / "rows.redsim.json")
    loaded = Document.open(tmp_path / "rows.redsim.json")
    assert loaded.lines_of("build") == placed
    assert [g.name for g in loaded.lines_of("build").groups] == [BLOCKS_GROUP, "Clock"]
    assert loaded.lines_of("build").groups[0].color == "#55aa55"
    assert not loaded.lines_of("remove").groups
