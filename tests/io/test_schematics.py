"""Schematic files: Litematica, Sponge (WorldEdit) and structure files, read and written."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document import Document
from redsim.io.schematics import read_schematic, write_schematic
from redsim.mcworld import nbt
from redsim.world import blocks

P = blocks.parse_state


def build() -> tuple[Document, Region]:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("repeater[facing=east,delay=3]"))
    doc.setblock((1, 1, 0), P("redstone_wire"))
    doc.setblock((2, 1, 0), P("sticky_piston[facing=up]"))
    doc.setblock((0, 1, 2), P("chest[facing=south]"))
    doc.set_container_slot((0, 1, 2), 3, "minecraft:redstone", 17)
    doc.setblock((1, 1, 2), P("oak_sign[rotation=4]"))
    doc.set_sign_text((1, 1, 2), "front", ["schematic"])
    doc.setblock((2, 2, 2), P("minecraft:oak_stairs[facing=north,half=bottom]"))  # foreign
    return doc, Region((0, 1, 0), (2, 2, 2))


def entries(prefab: Prefab) -> dict[tuple[int, int, int], tuple[str, Any]]:
    return {(dx, dy, dz): (text, data) for dx, dy, dz, text, data in prefab.blocks}


@pytest.mark.parametrize("suffix", [".litematic", ".schem", ".nbt"])
def test_round_trip(suffix: str, tmp_path: Path) -> None:
    doc, region = build()
    prefab = doc.copy(region)
    path = tmp_path / f"circuit{suffix}"
    write_schematic(path, prefab)
    loaded = read_schematic(path)
    assert loaded.name == "circuit" and loaded.size == prefab.size == (3, 2, 3)
    want, got = entries(prefab), entries(loaded)
    assert {p: t for p, (t, _) in got.items()} == {p: t for p, (t, _) in want.items()}
    chest = got[(0, 0, 2)][1]
    assert chest["Items"] == [{"Slot": 3, "id": "minecraft:redstone", "count": 17}]
    assert got[(1, 0, 2)][1]["front_text"]["messages"][0] == "schematic"
    # Pasted, it behaves like the original.
    doc.paste((10, 1, 0), loaded)
    assert repr(doc.state_at((12, 2, 2))) == repr(doc.state_at((2, 2, 2)))
    entity = doc.level.get_block_entity((11, 1, 2))
    assert entity is not None and entity.describe() == "sign: schematic"


def test_left_out_cells_stay_out(tmp_path: Path) -> None:
    doc, _ = build()
    sparse = doc.copy([Region((0, 1, 0), (0, 1, 0)), Region((2, 1, 0), (2, 1, 0))])
    write_schematic(tmp_path / "sparse.nbt", sparse)
    assert sorted(entries(read_schematic(tmp_path / "sparse.nbt"))) == [(0, 0, 0), (2, 0, 0)]
    write_schematic(tmp_path / "sparse.schem", sparse)  # no voids in Sponge files: air
    middle = entries(read_schematic(tmp_path / "sparse.schem"))[(1, 0, 0)]
    assert middle[0] == "minecraft:air"


def test_litematica_regions_with_negative_sizes_and_wide_palettes(tmp_path: Path) -> None:
    # Two regions, one given from its far corner (negative size), and a palette needing
    # 5 bits, so values span two longs.
    texts = ["minecraft:air"] + [f"minecraft:{c}_wool" for c in (
        "white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
        "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black")]  # fmt: skip
    values = [i % len(texts) for i in range(4 * 2 * 3)]
    bits = 5
    words = [0] * ((len(values) * bits + 63) // 64)
    for i, value in enumerate(values):
        word, offset = divmod(i * bits, 64)
        words[word] |= (value << offset) & (2**64 - 1)
        if offset + bits > 64:
            words[word + 1] |= value >> (64 - offset)
    region = {
        "Position": {"x": nbt.Int(3), "y": nbt.Int(1), "z": nbt.Int(2)},
        "Size": {"x": nbt.Int(-4), "y": nbt.Int(2), "z": nbt.Int(-3)},
        "BlockStatePalette": nbt.NbtList([{"Name": t} for t in texts], nbt.COMPOUND),
        "BlockStates": nbt.NbtArray(
            [w - 2**64 if w >= 2**63 else w for w in words], nbt.LONG_ARRAY
        ),
        "TileEntities": nbt.NbtList([], nbt.COMPOUND),
    }
    other = {
        "Position": {"x": nbt.Int(10), "y": nbt.Int(1), "z": nbt.Int(0)},
        "Size": {"x": nbt.Int(1), "y": nbt.Int(1), "z": nbt.Int(1)},
        "BlockStatePalette": nbt.NbtList(
            [{"Name": "minecraft:air"}, {"Name": "minecraft:stone"}], nbt.COMPOUND
        ),
        "BlockStates": nbt.NbtArray([1], nbt.LONG_ARRAY),
    }
    root = {"Version": nbt.Int(6), "Regions": {"a": region, "b": other}}
    path = tmp_path / "two.litematic"
    import gzip

    path.write_bytes(gzip.compress(nbt.dumps(root)))
    prefab = read_schematic(path)
    assert prefab.size == (11, 2, 3)  # x 0..10, y 1..2, z 0..2
    got = entries(prefab)
    # Region a spans x 0..3, z 0..2 (from its far corner); index i → x, z, y as Litematica.
    for i, value in enumerate(values):
        x, z, y = i % 4, (i // 4) % 3, i // 12
        assert got[(x, y, z)][0] == texts[value]
    assert got[(10, 0, 0)][0] == "minecraft:stone"


def test_sponge_version_2_files_are_read(tmp_path: Path) -> None:
    palette = {
        "minecraft:air": nbt.Int(0),
        "minecraft:lever[face=floor,facing=east,powered=false,waterlogged=false]": nbt.Int(1),
    }
    data = [1, 0, 0, 1]  # 2×1×2: x + z·width
    root = {
        "Version": nbt.Int(2),
        "Width": nbt.Short(2),
        "Height": nbt.Short(1),
        "Length": nbt.Short(2),
        "Palette": palette,
        "BlockData": nbt.NbtArray(data, nbt.BYTE_ARRAY),
    }
    import gzip

    path = tmp_path / "old.schem"
    path.write_bytes(gzip.compress(nbt.dumps(root, "Schematic")))
    got = entries(read_schematic(path))
    assert got[(0, 0, 0)][0] == "minecraft:lever[face=floor,facing=east,powered=false]"
    assert got[(1, 0, 1)][0] == got[(0, 0, 0)][0] and got[(1, 0, 0)][0] == "minecraft:air"


def test_unknown_files_are_refused(tmp_path: Path) -> None:
    import gzip

    path = tmp_path / "level.dat"
    path.write_bytes(gzip.compress(nbt.dumps({"Data": {}})))
    with pytest.raises(ValueError):
        read_schematic(path)
    with pytest.raises(ValueError):
        write_schematic(tmp_path / "x.txt", Prefab("x", (1, 1, 1), []))
