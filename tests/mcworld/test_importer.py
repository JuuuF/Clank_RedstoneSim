"""Opening Minecraft worlds: foreign blocks, terrain pruning, the example save."""

from __future__ import annotations

from pathlib import Path

import pytest

from redsim.editor.document import Document
from redsim.mcworld.importer import ImportedArea, SaveInfo, _state, prune_terrain
from redsim.world import blocks

SAVE = Path(__file__).resolve().parents[2] / "data" / "minecraft_saves" / "Redstone"


def test_foreign_blocks_keep_their_state_and_survive_saving(tmp_path: Path) -> None:
    text = "minecraft:note_block[instrument=harp,note=3,powered=false]"
    state = blocks.parse_state(text)
    assert repr(state) == text and blocks.parse_state(repr(state)) is state
    sign = blocks.parse_state("minecraft:oak_sign[rotation=4,waterlogged=false]")
    assert not sign.block.full  # signs are not full cubes: not solid, not conducting
    doc = Document.new_flat()
    doc.level.blocks[(0, 1, 0)] = state
    doc.save(tmp_path / "foreign.redsim.json")
    assert Document.open(tmp_path / "foreign.redsim.json").state_at((0, 1, 0)) is state


def test_known_blocks_drop_properties_the_simulator_lacks() -> None:
    state = _state("minecraft:lever[face=wall,facing=east,powered=true,waterlogged=false]")
    assert state.is_(blocks.LEVER) and "waterlogged" not in repr(state)


def test_buried_terrain_is_left_out_but_kept_near_builds() -> None:
    info = SaveInfo(Path("."), "t", 0, None, None, (0.0, 0.0), (0, 0, 0), 0)
    area = ImportedArea(info, (0, 0), 1)
    for x in range(16):
        for z in range(16):
            for y in range(0, 4):
                area.blocks[(x, y, z)] = "minecraft:stone"
    area.blocks[(8, 4, 8)] = "minecraft:lever[face=floor,facing=north,powered=false]"
    prune_terrain(area)
    assert (3, 3, 3) in area.blocks  # the exposed top layer
    assert (3, 1, 3) not in area.blocks  # buried and far from the lever
    assert (8, 3, 8) in area.blocks and (7, 2, 8) not in area.blocks
    assert (8, 2, 8) not in area.blocks or (8, 3, 8) in area.blocks


@pytest.mark.skipif(not SAVE.exists(), reason="the example save is not supplied")
def test_example_world_opens_around_the_player() -> None:
    from redsim.mcworld.importer import open_world

    opened = open_world(SAVE, radius=2)
    level = opened.document.level
    assert opened.area.chunks > 0 and opened.area.skipped_terrain > 0
    assert any(state.is_(blocks.REDSTONE_WIRE) for state in level.blocks.values())
    assert "minecraft:quartz_stairs" in opened.foreign  # not simulated: kept as text
    assert any(state.is_(blocks.NOTE_BLOCK) for state in level.blocks.values())  # simulated
    assert opened.document.extra["minecraft_world"]["name"] == "Redstone"
    opened.document.run_ticks(5)  # it simulates
