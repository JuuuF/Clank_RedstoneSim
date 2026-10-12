"""Streaming a Minecraft world chunk by chunk: which blocks enter the document."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from redsim.editor.document import Document
from redsim.mcworld.chunk import unpack_indices
from redsim.mcworld.importer import SaveInfo, block_states
from redsim.mcworld.stream import WorldStream, unpack_array
from redsim.world import blocks

INFO = SaveInfo(Path("."), "t", 0, None, None, (0.0, 0.0), (0, 0, 0), 0)
STONE = "minecraft:stone"
LEVER = "minecraft:lever[face=floor,facing=north,powered=false]"
PISTON = "minecraft:piston[extended=false,facing=up]"


def pack(index: list[int], palette_size: int) -> list[int]:
    """Section ``data`` longs (signed, like NBT) for palette indices in [y, z, x] order."""
    bits = max(4, (palette_size - 1).bit_length())
    per_long = 64 // bits
    longs = []
    for start in range(0, 4096, per_long):
        value = 0
        for i, v in enumerate(index[start : start + per_long]):
            value |= v << (i * bits)
        longs.append(value - (1 << 64) if value >= 1 << 63 else value)
    return longs


def section(y: int, blocks_at: dict[tuple[int, int, int], str], fill: str = "air") -> Any:
    """A section NBT: ``fill`` everywhere except ``blocks_at`` (local x, y, z → text)."""
    palette = [f"minecraft:{fill}" if ":" not in fill else fill]
    index = [0] * 4096
    for (x, by, z), text in blocks_at.items():
        text = text if ":" in text else f"minecraft:{text}"
        if text not in palette:
            palette.append(text)
        index[by * 256 + z * 16 + x] = palette.index(text)
    entries = [_entry(t) for t in palette]
    if len(palette) == 1:
        return {"Y": y, "block_states": {"palette": entries}}
    return {"Y": y, "block_states": {"palette": entries, "data": pack(index, len(palette))}}


def _entry(text: str) -> dict[str, Any]:
    name, _, rest = text.partition("[")
    props = dict(p.split("=") for p in rest.rstrip("]").split(",") if p)
    return {"Name": name, "Properties": props} if props else {"Name": name}


def ground(*extra: Any) -> dict[str, Any]:
    """A chunk of solid stone from y 0 to 15 (section 0), plus extra sections."""
    return {"sections": [section(0, {}, STONE), *extra]}


def test_unpacking_matches_the_plain_reader() -> None:
    rng = random.Random(3)
    for size in (2, 5, 17, 300):
        index = [rng.randrange(size) for _ in range(4096)]
        data = pack(index, size)
        assert unpack_array(data, size).reshape(-1).tolist() == unpack_indices(data, size)
        assert unpack_indices(data, size) == index


def test_buried_terrain_is_left_out_but_kept_near_builds() -> None:
    stream = WorldStream(INFO)
    loaded: dict[Any, str] = {}
    for cx in (-1, 0, 1):
        for cz in (-1, 0, 1):
            inside = {(8, 8, 8): "redstone_block"} if (cx, cz) == (0, 0) else {}
            chunk = {"sections": [section(0, inside, STONE), section(1, {})]}
            loaded.update(stream.add_chunk(cx, cz, chunk).blocks)
    assert loaded[(8, 8, 8)] == "minecraft:redstone_block"  # a build, buried or not
    assert loaded[(3, 15, 3)] == STONE  # the exposed top layer
    assert loaded[(3, 0, 3)] == STONE  # the bottom: air below (no section -1)
    assert (3, 10, 3) not in loaded  # buried and far from builds
    assert (7, 7, 7) in loaded and (6, 8, 8) not in loaded  # touching the build only
    assert stream.skipped() == 9 * 4096 - len(loaded)  # every block is shown or skipped


def test_the_edge_of_the_loaded_area_waits_for_its_neighbor() -> None:
    stream = WorldStream(INFO)
    first = stream.add_chunk(0, 0, ground()).blocks
    assert (15, 15, 3) in first  # the top shows
    assert (15, 8, 3) not in first  # the east side: unknown yet, so not exposed
    assert (0, 8, 3) not in first
    second = stream.add_chunk(1, 0, {"sections": [section(0, {(0, 8, 3): "air"}, STONE)]})
    assert (15, 8, 3) in second.blocks  # now it faces a cave in the next chunk
    assert (15, 9, 3) not in second.blocks


def test_load_order_does_not_matter() -> None:
    chunks = {
        (cx, cz): ground(section(1, {(cx + 5, 2, 3): LEVER}) if cx == 1 else section(1, {}))
        for cx in range(3)
        for cz in range(2)
    }
    chunks[(2, 1)] = ground(section(1, {(4, 0, 4): PISTON}))
    results = []
    for seed in range(4):
        order = list(chunks)
        random.Random(seed).shuffle(order)
        stream = WorldStream(INFO)
        got: dict[Any, str] = {}
        for key in order:
            got.update(stream.add_chunk(*key, chunks[key]).blocks)
        results.append(got)
    assert all(result == results[0] for result in results)


def test_terrain_in_piston_reach_appears_even_in_chunks_loaded_before() -> None:
    stream = WorldStream(INFO)
    first = stream.add_chunk(0, 0, ground()).blocks
    assert (10, 5, 10) not in first
    second = stream.add_chunk(1, 0, ground(section(1, {(0, 0, 10): PISTON}))).blocks
    assert second[(16, 16, 10)] == PISTON
    assert second[(10, 5, 10)] == STONE  # buried, but within 13 blocks of the piston
    assert (1, 5, 1) not in second and (1, 5, 1) not in first  # out of reach


def test_world_blocks_join_every_stored_level() -> None:
    doc = Document.new_flat()
    stone = blocks.STONE.default_state
    doc.setblock((0, 1, 0), stone)  # an undo step: its base is stored
    doc.run_ticks(3)
    states = block_states({(100, 1, 100): STONE, (0, 0, 0): "minecraft:dirt"})
    doc.add_world_blocks(states, {})
    levels = [doc.level, *(k.level for k in doc.history.keyframes.values())]
    levels += [s.base.level for s in doc._undo]
    assert all(level.blocks.get((100, 1, 100)) is stone for level in levels)
    assert doc.level.blocks[(0, 0, 0)].is_(blocks.SMOOTH_STONE)  # kept, not replaced
    doc.seek_tick(0)
    assert doc.state_at((100, 1, 100)) is stone  # a restored keyframe has it


def test_a_section_of_one_non_terrain_block_is_kept_whole() -> None:
    stream = WorldStream(INFO)
    got = stream.add_chunk(0, 0, {"sections": [section(0, {}, "glass")]}).blocks
    assert len(got) == 4096 and set(got.values()) == {"minecraft:glass"}
