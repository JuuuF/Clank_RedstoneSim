"""Enchanting tables: in redstone builds a 12-pixel block that pistons cannot move.

Sources (relative to ``data/minecraft_src/server-src/net/minecraft/world/level/block/``):

* ``EnchantingTableBlock.java``: ``SHAPE = Block.column(16, 0, 12)`` (also its collision
  and support shape: the bottom face is sturdy, the top and sides are not); a block entity
  (so pistons cannot move it), whose ticker runs only on the client (the book animation);
  using it opens the enchanting menu (no change to the world).
* ``entity/EnchantingTableBlockEntity.java``: saves only a custom name (kept as data here).
* ``Blocks.java``: not a conductor (``isRedstoneConductor`` default: not a full block).
"""

from __future__ import annotations

from typing import Any

from redsim.core.pos import Pos
from redsim.world.block import BlockState
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.blocks.catalog import CatalogBlock
from redsim.world.shape import column

SHAPE = column(16, 0, 12)


class EnchantingTableBlockEntity(BlockEntity):
    """``EnchantingTableBlockEntity``: only its ``CustomName``, kept as saved."""

    type_id = "enchanting_table"
    valid_blocks = frozenset({"minecraft:enchanting_table"})

    def __init__(self, pos: Pos, state: BlockState) -> None:
        super().__init__(pos, state)
        self.data: dict[str, Any] = {}

    def clone(self) -> BlockEntity:
        other = super().clone()
        assert isinstance(other, EnchantingTableBlockEntity)
        other.data = dict(self.data)
        return other

    def to_json(self) -> dict[str, Any]:
        return dict(self.data)

    def load_json(self, data: dict[str, Any]) -> None:
        self.data = {key: data[key] for key in ("CustomName",) if key in data}


class EnchantingTableBlock(CatalogBlock):
    """``EnchantingTableBlock``."""

    has_block_entity = True

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec, shape=SHAPE)

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return EnchantingTableBlockEntity(pos, state)


# Registered here, not with a class decorator (classes stay compilable by mypyc).
register_block_entity(EnchantingTableBlockEntity)
