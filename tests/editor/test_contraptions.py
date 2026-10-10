"""Regions, clipboard, prefabs and groups (milestone 7)."""

from __future__ import annotations

from pathlib import Path

from redsim.core.direction import Direction
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document import Document
from redsim.editor.groups import Group, Port, port_reading
from redsim.editor.placement import PlaceRequest
from redsim.world import blocks
from redsim.world.properties import HORIZONTAL_FACING, LIT, POWERED
from redsim.world.rotation import rotate_offset, rotate_state


def lever_lamp(doc: Document, x: int) -> None:
    up = PlaceRequest(Direction.UP, yaw=0, pitch=60)
    doc.place((x, 1, 0), blocks.LEVER, up)
    doc.place((x + 1, 1, 0), blocks.REDSTONE_LAMP, up)


def test_region_order_matches_clone_and_fill() -> None:
    region = Region.from_corners((1, 0, 1), (0, 1, 0))
    assert region.size == (2, 2, 2)
    assert region.positions()[:3] == [(0, 0, 0), (1, 0, 0), (0, 1, 0)]


def test_rotation_of_positions_and_states() -> None:
    assert rotate_offset((1, 0, 0), 1) == (0, 0, 1)  # BlockPos.rotate(CLOCKWISE_90)
    repeater = blocks.parse_state("repeater[facing=north]")
    assert rotate_state(repeater, 1).get(HORIZONTAL_FACING) is Direction.EAST
    wire = blocks.parse_state("redstone_wire[north=side,east=none,south=up,west=none]")
    turned = rotate_state(wire, 1)
    assert repr(turned).startswith(
        "minecraft:redstone_wire[north=none,east=side,south=none,west=up"
    )


def test_copy_paste_makes_a_working_copy() -> None:
    doc = Document.new_flat()
    lever_lamp(doc, 0)
    doc.copy(Region.from_corners((0, 1, 0), (1, 1, 0)))
    doc.paste((0, 1, 4))
    assert doc.state_at((0, 1, 4)).is_(blocks.LEVER)
    doc.use((0, 1, 4))
    assert doc.state_at((1, 1, 4)).get(LIT) is True
    assert doc.state_at((1, 1, 0)).get(LIT) is False  # the original is independent


def test_rotated_paste_turns_components() -> None:
    doc = Document.new_flat()
    doc.place((0, 1, 0), blocks.REPEATER, PlaceRequest(Direction.UP, yaw=270, pitch=60))
    doc.copy(Region.from_corners((0, 1, 0), (0, 1, 0)))
    before = doc.state_at((0, 1, 0)).get(HORIZONTAL_FACING)
    doc.rotate_clipboard(1)
    doc.paste((5, 1, 5))
    assert doc.state_at((5, 1, 5)).get(HORIZONTAL_FACING) is before.clockwise()


def test_fill_with_air_deletes_and_updates() -> None:
    doc = Document.new_flat()
    lever_lamp(doc, 0)
    doc.use((0, 1, 0))
    assert doc.state_at((1, 1, 0)).get(LIT) is True
    doc.fill(Region.from_corners((0, 1, 0), (0, 1, 0)), blocks.AIR.default_state)
    doc.run_tick()
    for _ in range(4):
        doc.run_tick()
    assert doc.state_at((0, 1, 0)).is_air
    assert doc.state_at((1, 1, 0)).get(LIT) is False  # lamp noticed the lever's removal


def test_paste_is_undoable_and_replays() -> None:
    doc = Document.new_flat()
    lever_lamp(doc, 0)
    doc.copy(Region.from_corners((0, 1, 0), (1, 1, 0)))
    doc.paste((0, 1, 4))
    assert doc.undo()
    assert doc.state_at((0, 1, 4)).is_air
    assert doc.redo()
    assert doc.state_at((0, 1, 4)).is_(blocks.LEVER)


def test_prefabs_and_groups_survive_save(tmp_path: Path) -> None:
    doc = Document.new_flat()
    lever_lamp(doc, 0)
    region = Region.from_corners((0, 1, 0), (1, 1, 0))
    doc.save_prefab("lamp switch", region)
    doc.groups.add(
        Group("switch", region, [Port("in", (0, 1, 0), "input"), Port("out", (1, 1, 0), "output")])
    )
    path = tmp_path / "world.redsim.json"
    doc.save(path)
    opened = Document.open(path)
    assert opened.prefabs["lamp switch"].non_air_count == 2
    group = opened.groups.groups["switch"]
    assert [p.name for p in group.ports] == ["in", "out"]
    assert port_reading(opened.level, group.ports[0]) == "lever off"
    opened.paste((0, 1, 6), opened.prefabs["lamp switch"])
    assert opened.state_at((1, 1, 6)).is_(blocks.REDSTONE_LAMP)
    assert Prefab.from_json(opened.prefabs["lamp switch"].to_json()).size == (2, 1, 1)
    assert not opened.state_at((0, 1, 6)).get(POWERED)
