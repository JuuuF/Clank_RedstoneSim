"""Chunk sections → block states (``PalettedContainer`` storage) and back.

A section is 16×16×16 blocks: a palette of block states and, unless the palette has one
entry, packed indices in longs (``SimpleBitStorage``: max(4, bits) bits each, values do
not span longs; index order y, z, x). Palette entries are ``{"Name", "Properties"}`` in
older versions; 26.x writes bare id strings, ``{"": id}`` or ``{"id", "properties"}``.
All are read.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

Pos = tuple[int, int, int]


def palette_entry(entry: Any) -> tuple[str, dict[str, str]]:
    """(block id, properties) of a palette entry, whichever version wrote it: a bare id
    string, ``{"": id}``, ``{"id", "properties"}`` or ``{"Name", "Properties"}``."""
    if isinstance(entry, str):
        return entry, {}
    if "" in entry:
        return str(entry[""]), {}
    name = entry.get("id", entry.get("Name", "minecraft:air"))
    props = entry.get("properties", entry.get("Properties", {})) or {}
    return str(name), {str(k): str(v) for k, v in props.items()}


def state_text(block_id: str, props: dict[str, str]) -> str:
    """``minecraft:lever[face=wall,…]``, the text ``blocks.parse_state`` reads."""
    if not props:
        return block_id
    return f"{block_id}[{','.join(f'{k}={v}' for k, v in props.items())}]"


def unpack_indices(data: list[int], palette_size: int, count: int = 4096) -> list[int]:
    """The ``count`` palette indices packed in ``data`` (signed Java longs)."""
    bits = max(4, (palette_size - 1).bit_length())
    per_long = 64 // bits
    mask = (1 << bits) - 1
    out: list[int] = []
    for value in data:
        value &= 0xFFFFFFFFFFFFFFFF
        for _ in range(per_long):
            out.append(value & mask)
            value >>= bits
            if len(out) == count:
                return out
    return out


def pack_indices(indices: list[int], palette_size: int) -> list[int]:
    """The inverse of ``unpack_indices``: signed Java longs."""
    bits = max(4, (palette_size - 1).bit_length())
    per_long = 64 // bits
    longs = []
    for start in range(0, len(indices), per_long):
        value = 0
        for offset, index in enumerate(indices[start : start + per_long]):
            value |= index << (offset * bits)
        longs.append(value - (1 << 64) if value >= 1 << 63 else value)
    return longs


def section_blocks(
    section: dict[str, Any], chunk_x: int, chunk_z: int
) -> Iterator[tuple[Pos, str]]:
    """(world position, state text) of every non-air block in a section."""
    states = section.get("block_states")
    if not states:
        return
    palette = [state_text(*palette_entry(e)) for e in states.get("palette", [])]
    if not palette:
        return
    base_x, base_y, base_z = chunk_x * 16, int(section["Y"]) * 16, chunk_z * 16
    if len(palette) == 1:
        if palette[0] in AIR:
            return
        for i in range(4096):
            yield (base_x + (i & 15), base_y + (i >> 8), base_z + ((i >> 4) & 15)), palette[0]
        return
    indices = unpack_indices(list(states.get("data", [])), len(palette))
    for i, index in enumerate(indices):
        text = palette[index]
        if text not in AIR:
            yield (base_x + (i & 15), base_y + (i >> 8), base_z + ((i >> 4) & 15)), text


AIR = frozenset({"minecraft:air", "minecraft:cave_air", "minecraft:void_air"})
