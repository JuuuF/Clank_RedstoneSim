"""Opening Minecraft worlds: foreign blocks, the example save."""

from __future__ import annotations

from pathlib import Path

import pytest

from redsim.editor.document import Document
from redsim.mcworld.importer import state_from_text as _state
from redsim.world import blocks

SAVE = Path(__file__).resolve().parents[2] / "data" / "minecraft_saves" / "Redstone"


def test_foreign_blocks_keep_their_state_and_survive_saving(tmp_path: Path) -> None:
    text = "minecraft:note_block[instrument=harp,note=3,powered=false]"
    state = blocks.parse_state(text)
    assert repr(state) == text and blocks.parse_state(repr(state)) is state
    sign = blocks.parse_state("minecraft:oak_hanging_sign[attached=false,rotation=4]")
    assert not sign.block.full  # hanging signs are not full cubes: not solid, not conducting
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


def test_sign_text_is_read_from_every_message_form() -> None:
    from redsim.mcworld.importer import sign_texts

    entities = {
        (1, 2, 3): {"front_text": {"messages": ['"Hello"', '{"text":"a","extra":["b"]}', "", "x"]}},
        (4, 5, 6): {"front_text": {"messages": ["", "", "", ""]}},  # empty: not kept
    }
    # Hanging signs are kept as foreign blocks: their text is document data. (Standing and
    # wall signs read the same forms into their block entity: tests/sim/test_signs.py.)
    texts = {(1, 2, 3): "minecraft:oak_hanging_sign", (4, 5, 6): "minecraft:oak_hanging_sign"}
    assert sign_texts(entities, texts) == {"1,2,3": ["Hello", "ab", "", "x"]}


@pytest.mark.skipif(not SAVE.exists(), reason="the example save is not supplied")
def test_an_opened_world_saves_back_into_a_copy(tmp_path: Path) -> None:
    from redsim.mcworld.importer import open_world, read_save
    from redsim.mcworld.writer import save_world_copy

    opened = open_world(SAVE, radius=2)
    doc = opened.document
    assert opened.info.player_pos is not None
    x, y, z = (int(v) for v in opened.info.player_pos)
    doc.setblock((x, y + 3, z), blocks.REDSTONE_BLOCK.default_state)
    wire = next(p for p, s in doc.level.blocks.items() if s.is_(blocks.REDSTONE_WIRE))
    doc.break_block(wire)
    report = save_world_copy(doc, tmp_path / "copy")
    assert report.blocks >= 2 and report.outside == 0
    copy = open_world(tmp_path / "copy", radius=2).document.level
    assert copy.blocks.get((x, y + 3, z)) is blocks.REDSTONE_BLOCK.default_state
    assert wire not in copy.blocks
    assert all(copy.blocks.get(p) is s for p, s in doc.level.blocks.items())
    assert read_save(tmp_path / "copy").name == "copy"
    with pytest.raises(ValueError):  # never over an existing folder
        save_world_copy(doc, tmp_path / "copy")


@pytest.mark.skipif(not SAVE.exists(), reason="the example save is not supplied")
def test_pending_ticks_go_into_the_copy(tmp_path: Path) -> None:
    from redsim.mcworld.importer import open_world
    from redsim.mcworld.writer import save_world_copy

    opened = open_world(SAVE, radius=2)
    doc = opened.document
    assert opened.info.player_pos is not None
    x, y, z = (int(v) for v in opened.info.player_pos)
    doc.setblock((x, y + 2, z), blocks.STONE.default_state)  # something to stand on
    doc.setblock((x, y + 3, z), blocks.parse_state("repeater[facing=east,delay=4]"))
    doc.setblock((x + 1, y + 3, z), blocks.REDSTONE_BLOCK.default_state)  # its input
    pending = [t for t in doc.level.block_ticks.pending() if t.pos == (x, y + 3, z)]
    assert pending
    save_world_copy(doc, tmp_path / "ticks")
    copy = open_world(tmp_path / "ticks", radius=2).document.level
    again = [t for t in copy.block_ticks.pending() if t.pos == (x, y + 3, z)]
    assert [(t.block_id, t.trigger_tick - copy.game_time) for t in again] == [
        (t.block_id, t.trigger_tick - doc.level.game_time) for t in pending
    ]


@pytest.mark.skipif(not SAVE.exists(), reason="the example save is not supplied")
def test_a_saved_world_document_reconnects_to_its_save(tmp_path: Path) -> None:
    from redsim.editor.document import Document
    from redsim.mcworld.importer import attach_world, open_world, stream_chunks

    opened = open_world(SAVE, radius=2)
    doc = opened.document
    wire = next(p for p, s in doc.level.blocks.items() if s.is_(blocks.REDSTONE_WIRE))
    doc.break_block(wire)
    held = set(opened.stream.loaded)
    doc.save(tmp_path / "world.redsim.json")
    reopened = Document.open(tmp_path / "world.redsim.json")
    stream = attach_world(reopened)
    assert stream is not None and set(stream.reload) == held
    center = next(iter(held))
    while stream.reload:  # its own chunks are read again, adding nothing
        assert stream_chunks(reopened, center, 2, 10.0) == 0
    assert wire not in reopened.level.blocks  # the removed wire stays removed
    before = len(reopened.level.blocks)
    assert stream_chunks(reopened, center, 4, 10.0) > 0  # further chunks stream in
    assert len(reopened.level.blocks) > before


@pytest.mark.skipif(not SAVE.exists(), reason="the example save is not supplied")
def test_the_builds_of_the_example_save_are_found() -> None:
    from redsim.mcworld.importer import read_save
    from redsim.mcworld.index import scan_builds

    builds = scan_builds(read_save(SAVE).regions)
    assert builds and builds[0].redstone >= builds[-1].redstone
    first = builds[0]
    assert all(first.low[i] <= first.high[i] for i in range(3))
    assert any(block_id.endswith("piston") for block_id, _ in first.top_parts())


def test_build_blocks_and_redstone_parts() -> None:
    from redsim.mcworld.index import is_build_block, is_redstone

    assert not is_build_block("minecraft:stone") and not is_build_block("minecraft:oak_leaves")
    assert not is_build_block("minecraft:short_grass") and not is_build_block("minecraft:air")
    assert is_build_block("minecraft:glass") and is_build_block("minecraft:repeater")
    assert is_redstone("minecraft:sticky_piston") and not is_redstone("minecraft:glass")
