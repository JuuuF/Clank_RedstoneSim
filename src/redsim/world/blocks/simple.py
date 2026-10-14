"""Blocks without redstone logic of their own, and the redstone block.

Properties come from ``net/minecraft/world/level/block/Blocks.java`` (see
doc/mechanics/block-properties.md for the table and line references).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.compiled import mypyc_attr
from redsim.core.pos import Pos
from redsim.world.block import Block, BlockState, Conductor, PushReaction
from redsim.world.properties import SLAB_TYPE, SNOWY, WATERLOGGED
from redsim.world.shape import EMPTY, Shape, box, column

if TYPE_CHECKING:
    from redsim.sim.level import Level


class AirBlock(Block):
    def __init__(self) -> None:
        super().__init__("minecraft:air", has_collision=False, is_air=True, destroy_speed=0.0)

    def get_shape(self, state: BlockState) -> Shape:
        return EMPTY


@mypyc_attr(allow_interpreted_subclasses=True)  # ForeignBlock, test blocks
class SimpleBlock(Block):
    """A block with a fixed shape and default behavior (stone, glass, obsidian, ...)."""

    def __init__(
        self,
        block_id: str,
        *,
        shape: Shape | None = None,
        collision_shape: Shape | None = None,
        destroy_speed: float = 1.5,
        push_reaction: PushReaction = PushReaction.PUSH_PULL,
        conductor: Conductor = Conductor.DEFAULT,
    ) -> None:
        self._shape = shape
        self._collision_shape = collision_shape
        super().__init__(
            block_id, destroy_speed=destroy_speed, push_reaction=push_reaction, conductor=conductor
        )

    def get_shape(self, state: BlockState) -> Shape:
        return self._shape if self._shape is not None else super().get_shape(state)

    def get_collision_shape(self, state: BlockState) -> Shape:
        if self._collision_shape is not None:
            return self._collision_shape
        return super().get_collision_shape(state)


class HoneyBlock(SimpleBlock):
    """``HoneyBlock``: collision shape ``Block.column(14, 0, 15)`` (HoneyBlock.java L29), so
    it is not a conductor and only its bottom face gives CENTER support."""

    def __init__(self) -> None:
        super().__init__("minecraft:honey_block", collision_shape=column(14, 0, 15))


class SlabBlock(Block):
    """``SlabBlock``: bottom/top half or double; only the double slab is a full block.
    ``waterlogged`` is kept for the game's state text (water is not simulated)."""

    properties = (SLAB_TYPE, WATERLOGGED)

    def __init__(self, block_id: str, destroy_speed: float = 2.0) -> None:
        super().__init__(block_id, destroy_speed=destroy_speed)
        self.register_default_state(
            self.default_state.with_(SLAB_TYPE, "bottom").with_(WATERLOGGED, False)
        )

    def get_shape(self, state: BlockState) -> Shape:
        slab_type = state.get(SLAB_TYPE)
        if slab_type == "double":
            return super().get_shape(state)
        if slab_type == "top":
            return box(0, 8, 0, 16, 16, 16)
        return box(0, 0, 0, 16, 8, 16)


class RedstoneBlock(Block):
    """``PoweredBlock`` (redstone block): signal 15 to every side, no strong power,
    ``isRedstoneConductor(Blocks::never)``."""

    def __init__(self) -> None:
        super().__init__("minecraft:redstone_block", conductor=Conductor.NEVER, destroy_speed=5.0)

    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return 15


def full_cube(block_id: str, destroy_speed: float = 1.5) -> SimpleBlock:
    """A default full cube: conductor, sturdy on all faces, PUSH_PULL."""
    return SimpleBlock(block_id, destroy_speed=destroy_speed)


class GrassBlock(SimpleBlock):
    """``GrassBlock`` as terrain: a full cube with its ``snowy`` state (never set here)."""

    properties = (SNOWY,)

    def __init__(self) -> None:
        super().__init__("minecraft:grass_block", destroy_speed=0.6)
        self.register_default_state(self.default_state.with_(SNOWY, False))


def non_conductor(block_id: str, destroy_speed: float = 0.3) -> SimpleBlock:
    """A full cube with ``isRedstoneConductor(Blocks::never)`` (glass, glowstone)."""
    return SimpleBlock(block_id, conductor=Conductor.NEVER, destroy_speed=destroy_speed)


def immovable(block_id: str, destroy_speed: float = 50.0) -> SimpleBlock:
    """A full cube with ``pushReaction(PushReaction.IMMOVEABLE)`` (obsidian)."""
    return SimpleBlock(block_id, push_reaction=PushReaction.IMMOVEABLE, destroy_speed=destroy_speed)


__all__ = [
    "AirBlock",
    "HoneyBlock",
    "RedstoneBlock",
    "SimpleBlock",
    "SlabBlock",
    "full_cube",
    "immovable",
    "non_conductor",
]
