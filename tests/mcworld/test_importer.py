"""Opening Minecraft worlds: foreign blocks, the example save."""

from __future__ import annotations

from pathlib import Path

import pytest

from redsim.editor.document import Document
from redsim.mcworld.importer import _state
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


@pytest.mark.skipif(not SAVE.exists(), reason="the example save is not supplied")
def test_example_world_opens_around_the_player() -> None:
    from redsim.mcworld.importer import open_world

    opened = open_world(SAVE, radius=2)
    level = opened.document.level
    assert len(opened.stream.loaded) > 0 and opened.stream.skipped() > 0
    assert any(state.is_(blocks.REDSTONE_WIRE) for state in level.blocks.values())
    assert "minecraft:quartz_stairs" in opened.foreign  # not simulated: kept as text
    assert any(state.is_(blocks.NOTE_BLOCK) for state in level.blocks.values())  # simulated
    assert opened.document.extra["minecraft_world"]["name"] == "Redstone"
    opened.document.run_ticks(5)  # it simulates
    before = len(level.blocks)
    from redsim.mcworld.importer import player_chunk, stream_chunks

    assert stream_chunks(opened.document, player_chunk(opened.info), 3, 10.0) > 0
    assert len(opened.document.level.blocks) > before  # more chunks streamed in
