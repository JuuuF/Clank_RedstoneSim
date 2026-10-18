"""Furnaces (furnace, blast furnace, smoker): containers of three slots whose fill level is
a comparator signal.

Sources (relative to ``data/minecraft_src/server-src/net/minecraft/world/``):

* ``level/block/AbstractFurnaceBlock.java``: ``FACING`` (horizontal) and ``LIT`` (default
  north, unlit); placement faces the player (``getHorizontalDirection().getOpposite()``,
  unlit); ``hasAnalogOutputSignal``, ``getAnalogOutputSignal`` =
  ``AbstractContainerMenu.getRedstoneSignalFromBlockEntity`` (``container.py``);
  ``affectNeighborsAfterRemoval``: ``Containers.updateNeighboursAfterDestroy``
  (comparators update). ``FurnaceBlock``, ``BlastFurnaceBlock`` and ``SmokerBlock`` differ
  only in their recipes and menus.
* ``level/block/entity/AbstractFurnaceBlockEntity.java``: slots 0 (ingredient), 1 (fuel),
  2 (result) (``getContainerSize`` 3, ``getMaxStackSize`` the ``Container`` default 99);
  NBT ``Items``, ``cooking_time_spent``, ``cooking_total_time``, ``lit_time_remaining``,
  ``lit_total_time``, ``speed_multiplier``, ``RecipesUsed`` (``loadAdditional`` /
  ``saveAdditional`` L124-147; the timers are kept as they are and saved back).
* ``Blocks.java``: strength 3.5, a full block that conducts; a block entity, so pistons
  never move them.

Not as in the game (doc/differences.md; also marked where it happens):

* furnaces do not tick: they never burn fuel or cook (``serverTick``: that needs the
  game's recipes and fuel values), so ``lit`` stays as it is and the contents only change
  by the editor, ``/item`` or ``/setblock``. A furnace without an ingredient, or with an
  ingredient but neither fuel nor fire, does nothing in the game either;
* hoppers and droppers do not put items into furnaces or take them out
  (``WorldlyContainer``: the face decides the slot, and only fuel goes into slot 1);
  ``hopper.container_at`` leaves furnaces out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.world.block import BlockState, PlacementContext
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.blocks.catalog import FacingBlock
from redsim.world.blocks.container import ContainerBlockEntity
from redsim.world.properties import HORIZONTAL_FACING, LIT

if TYPE_CHECKING:
    from redsim.sim.level import Level

#: ``AbstractFurnaceBlockEntity.saveAdditional`` keys besides ``Items``.
TIMER_KEYS = (
    "cooking_time_spent",
    "cooking_total_time",
    "lit_time_remaining",
    "lit_total_time",
    "speed_multiplier",
    "RecipesUsed",
)


class FurnaceBlockEntity(ContainerBlockEntity):
    """``FurnaceBlockEntity``: three slots; the cooking timers are carried, not run."""

    type_id = "furnace"
    valid_blocks = frozenset({"minecraft:furnace"})
    SIZE = 3
    NAME = "furnace"

    def __init__(self, pos: Pos, state: BlockState) -> None:
        super().__init__(pos, state)
        #: The other NBT of ``saveAdditional`` as loaded (``TIMER_KEYS``).
        self.timers: dict[str, Any] = {}

    def clone(self) -> BlockEntity:
        other = super().clone()
        assert isinstance(other, FurnaceBlockEntity)
        other.timers = dict(self.timers)
        return other

    def to_json(self) -> dict[str, Any]:
        return {**self.timers, **super().to_json()}

    def load_json(self, data: dict[str, Any]) -> None:
        super().load_json(data)
        self.timers = {key: data[key] for key in TIMER_KEYS if key in data}


class BlastFurnaceBlockEntity(FurnaceBlockEntity):
    type_id = "blast_furnace"
    valid_blocks = frozenset({"minecraft:blast_furnace"})
    NAME = "blast furnace"


class SmokerBlockEntity(FurnaceBlockEntity):
    type_id = "smoker"
    valid_blocks = frozenset({"minecraft:smoker"})
    NAME = "smoker"


_ENTITIES: dict[str, type[FurnaceBlockEntity]] = {
    "minecraft:furnace": FurnaceBlockEntity,
    "minecraft:blast_furnace": BlastFurnaceBlockEntity,
    "minecraft:smoker": SmokerBlockEntity,
}


class FurnaceBlock(FacingBlock):
    """``AbstractFurnaceBlock`` (furnace, blast furnace, smoker)."""

    properties = (HORIZONTAL_FACING, LIT)
    has_block_entity = True

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(self.default_state.with_(LIT, False))
        self._entity = _ENTITIES[block_id]

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return self._entity(pos, state)

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement``: the given facing, unlit."""
        return self.default_state.with_(HORIZONTAL_FACING, ctx.requested.get(HORIZONTAL_FACING))

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        entity = level.get_block_entity(pos)
        return entity.signal() if isinstance(entity, FurnaceBlockEntity) else 0

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        level.update_neighbour_for_output_signal(pos, self)


def is_furnace(entity: BlockEntity | None) -> bool:
    return isinstance(entity, FurnaceBlockEntity)


# Registered here, not with a class decorator (classes stay compilable by mypyc).
register_block_entity(FurnaceBlockEntity)
register_block_entity(BlastFurnaceBlockEntity)
register_block_entity(SmokerBlockEntity)
