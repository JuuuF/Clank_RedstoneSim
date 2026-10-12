"""Display names of blocks as the game shows them ("Redstone Dust", "Block of Redstone"),
from the client jar's ``lang/en_us.json`` (``assets.Assets``); title case without it."""

from __future__ import annotations

import json
from functools import lru_cache

from redsim.ui.assets import Assets

#: Blocks shown under their item's name (the inventory gives the item).
ITEM_NAMES = {
    "minecraft:redstone_wire": "item.minecraft.redstone",
    "minecraft:redstone_wall_torch": "block.minecraft.redstone_torch",
}


@lru_cache(maxsize=1)
def _lang() -> dict[str, str]:
    assets = Assets.find()
    data = assets.file_bytes("assets/minecraft/lang/en_us.json") if assets else None
    return json.loads(data) if data else {}


@lru_cache(maxsize=512)
def block_name(block_id: str) -> str:
    namespace, name = block_id.split(":", 1) if ":" in block_id else ("minecraft", block_id)
    key = ITEM_NAMES.get(block_id, f"block.{namespace}.{name}")
    found = _lang().get(key)
    if found:
        return found
    return " ".join(word.capitalize() for word in name.split("_"))


@lru_cache(maxsize=256)
def item_name(item_id: str) -> str:
    """An item's name as the game shows it ("Redstone Dust", "Ender Pearl")."""
    namespace, name = item_id.split(":", 1) if ":" in item_id else ("minecraft", item_id)
    lang = _lang()
    found = lang.get(f"item.{namespace}.{name}") or lang.get(f"block.{namespace}.{name}")
    return found or " ".join(word.capitalize() for word in name.split("_"))
