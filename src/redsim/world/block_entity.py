"""Block entities: per-position state that is not part of the block state.

Port of the relevant parts of ``net/minecraft/world/level/block/entity/BlockEntity.java``.
Concrete block entities live next to their blocks (comparator, moving piston, container).
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from redsim.core.pos import Pos

if TYPE_CHECKING:
    from redsim.sim.level import Level
    from redsim.world.block import BlockState


#: Registered block-entity classes by ``type_id`` (for loading saves).
BLOCK_ENTITY_TYPES: dict[str, type[BlockEntity]] = {}


def register_block_entity(cls: type[BlockEntity]) -> type[BlockEntity]:
    BLOCK_ENTITY_TYPES[cls.type_id] = cls
    return cls


class BlockEntity:
    type_id: str = "block_entity"
    #: Block ids this entity type is valid for (``BlockEntityType.isValid``).
    valid_blocks: frozenset[str] = frozenset()

    def __init__(self, pos: Pos, state: BlockState) -> None:
        self.pos = pos
        self.block_state = state
        self.removed = False

    def set_removed(self) -> None:
        self.removed = True

    def pre_remove_side_effects(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``BlockEntity.preRemoveSideEffects``: called before the block entity is removed
        because its block was replaced (unless flag 256 is set)."""
        return None

    def tick(self, level: Level, pos: Pos, state: BlockState) -> None:
        """The ``BlockEntityTicker``; only called if the block declares ``has_ticker``."""
        return None

    def clone(self) -> BlockEntity:
        """Deep copy for history snapshots."""
        return copy.copy(self)

    def to_json(self) -> dict[str, Any]:
        return {}

    def load_json(self, data: dict[str, Any]) -> None:
        return None

    def describe(self) -> str:
        return self.type_id
