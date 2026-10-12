"""Binary NBT, region files and chunk sections of Minecraft Java saves."""

from __future__ import annotations

from pathlib import Path

import pytest

from redsim.mcworld import nbt
from redsim.mcworld.chunk import pack_indices, palette_entry, section_blocks, unpack_indices

SAVE = Path(__file__).resolve().parents[2] / "data" / "minecraft_saves" / "Redstone"


def test_nbt_round_trips_types_and_empty_lists() -> None:
    root = {
        "b": nbt.Byte(-3),
        "s": nbt.Short(300),
        "i": nbt.Int(-70000),
        "l": nbt.Long(-(2**40)),
        "f": nbt.Float(0.5),
        "d": nbt.Double(-1.25),
        "text": "Grüße \u0000 \U0001f600",  # modified UTF-8: NUL and a surrogate pair
        "list": nbt.NbtList([nbt.Int(1), nbt.Int(2)], nbt.INT),
        "empty": nbt.NbtList([], nbt.COMPOUND),
        "longs": nbt.NbtArray([1, -1, 2**62], nbt.LONG_ARRAY),
        "nested": {"x": nbt.Byte(1)},
    }
    data = nbt.dumps(root, "root")
    name, back = nbt.loads(data)
    assert name == "root" and back == root
    assert back["empty"].element == nbt.COMPOUND and type(back["s"]) is nbt.Short
    assert nbt.dumps(back, name) == data
    assert b"\xc0\x80" in data  # NUL as Java writes it


def test_packed_indices_round_trip() -> None:
    for size in (2, 16, 17, 300):
        indices = [(i * 7) % size for i in range(4096)]
        assert unpack_indices(pack_indices(indices, size), size) == indices


def test_palette_entries_of_every_version() -> None:
    assert palette_entry("minecraft:air") == ("minecraft:air", {})
    assert palette_entry({"": "minecraft:stone"}) == ("minecraft:stone", {})
    entry = {"id": "minecraft:lever", "properties": {"powered": "true"}}
    assert palette_entry(entry) == ("minecraft:lever", {"powered": "true"})
    old = {"Name": "minecraft:lever", "Properties": {"powered": "false"}}
    assert palette_entry(old) == ("minecraft:lever", {"powered": "false"})


def test_one_block_palette_fills_the_section() -> None:
    section = {"Y": nbt.Byte(-1), "block_states": {"palette": ["minecraft:stone"]}}
    blocks = list(section_blocks(section, 2, 3))
    assert len(blocks) == 4096 and blocks[0] == ((32, -16, 48), "minecraft:stone")


@pytest.mark.skipif(not SAVE.exists(), reason="the example save is not supplied")
def test_example_save_reads() -> None:
    from redsim.mcworld.region import RegionFile

    raw = nbt.decompress((SAVE / "level.dat").read_bytes())
    name, root = nbt.loads(raw)
    assert root["Data"]["LevelName"] == "Redstone"
    assert nbt.dumps(root, name) == raw  # byte-exact
    region = RegionFile(SAVE / "dimensions/minecraft/overworld/region/r.0.0.mca")
    chunk = region.read_chunk(0, 0)
    assert chunk is not None and chunk["Status"] == "minecraft:full"
