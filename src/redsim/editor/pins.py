"""Pinned block values: parts of a block's inspector (a property, its contents, the signal
it gives or receives) shown as a small live tag at the block in the view, so they stay in
sight while the simulation runs. Annotations only; saved in ``Document.extra["pins"]``
("x,y,z" → the pinned keys).

Keys: ``prop:<name>`` (a block-state property), ``contents`` (a container's items),
``signal`` (what the block gives: comparator output, source strength, wire power; or the
strongest signal it receives).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.pos import Pos
from redsim.editor import sources
from redsim.world.blocks.container import ContainerBlockEntity
from redsim.world.properties import POWER

if TYPE_CHECKING:
    from redsim.editor.document import Document

PINS_KEY = "pins"


def _key(pos: Pos) -> str:
    return f"{pos[0]},{pos[1]},{pos[2]}"


def pins(document: Document) -> dict[Pos, list[str]]:
    """Every pinned block and its pinned keys, in the order they were pinned."""
    raw = document.extra.get(PINS_KEY)
    out: dict[Pos, list[str]] = {}
    if not isinstance(raw, dict):
        return out
    for key, values in raw.items():
        try:
            x, y, z = (int(v) for v in str(key).split(","))
        except ValueError:
            continue
        if isinstance(values, list) and values:
            out[(x, y, z)] = [str(v) for v in values]
    return out


def pinned(document: Document, pos: Pos) -> list[str]:
    return pins(document).get(pos, [])


def set_pin(document: Document, pos: Pos, key: str, on: bool) -> None:
    """Pin (``on``) or unpin one value of the block at ``pos``."""
    raw = document.extra.get(PINS_KEY)
    table: dict[str, list[str]] = dict(raw) if isinstance(raw, dict) else {}
    keys = [k for k in table.get(_key(pos), []) if k != key]
    if on:
        keys.append(key)
    if keys:
        table[_key(pos)] = keys
    else:
        table.pop(_key(pos), None)
    if table:
        document.extra[PINS_KEY] = table
    else:
        document.extra.pop(PINS_KEY, None)
    document.dirty = True
    document.revision += 1


def clear_pins(document: Document) -> None:
    if document.extra.pop(PINS_KEY, None) is not None:
        document.dirty = True
        document.revision += 1


def choices(document: Document, pos: Pos) -> list[tuple[str, str]]:
    """What can be pinned for the block at ``pos``: (key, label)."""
    level = document.level
    state = level.get_block_state(pos)
    if state.is_air:
        return []
    out = [(f"prop:{prop.name}", prop.name) for prop in state.block.properties]
    if isinstance(level.get_block_entity(pos, create=False), ContainerBlockEntity):
        out.append(("contents", "contents"))
    out.append(("signal", "signal"))
    return out


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    name = getattr(value, "name", None)
    return str(name).lower() if name is not None else str(value)


def signal_text(document: Document, pos: Pos) -> str:
    level = document.level
    state = level.get_block_state(pos)
    entity = level.get_block_entity(pos, create=False)
    output = getattr(entity, "output", None)
    if state.block.id == "minecraft:comparator" and isinstance(output, int):
        return f"output {output}"
    strength = sources.strength_at(level, pos)
    if strength is not None:
        return f"strength {strength}"
    if state.block.id == "minecraft:redstone_wire":
        return f"power {state.get(POWER)}"
    return f"receives {level.get_best_neighbor_signal(pos)}"


def lines(document: Document, pos: Pos, keys: list[str]) -> list[str]:
    """The tag's text lines for the pinned ``keys`` (keys that no longer apply, e.g. after
    the block changed, are skipped)."""
    level = document.level
    state = level.get_block_state(pos)
    by_name = {prop.name: prop for prop in state.block.properties}
    out = []
    for key in keys:
        if key.startswith("prop:"):
            prop = by_name.get(key[5:])
            if prop is not None:
                out.append(f"{prop.name} {_value(state.get(prop))}")
        elif key == "contents":
            entity = level.get_block_entity(pos, create=False)
            if isinstance(entity, ContainerBlockEntity):
                filled = [stack for stack in entity.items if stack is not None]
                total = sum(count for _, count in filled)
                out.append(f"{total} items · {len(filled)}/{entity.SIZE} slots")
        elif key == "signal":
            out.append(signal_text(document, pos))
    return out
