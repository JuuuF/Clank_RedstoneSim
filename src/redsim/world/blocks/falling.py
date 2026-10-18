"""Gravity blocks: ``FallingBlock.java`` and its subclasses ``ColoredFallingBlock`` /
``SandBlock`` (sand, red sand, gravel), ``ConcretePowderBlock`` (16 colors),
``AnvilBlock`` (anvil, chipped, damaged) and ``DragonEggBlock``.

A gravity block schedules a tick 2 game ticks (the dragon egg: 5) after it is placed and
after every shape update (``onPlace``, ``updateShape``). The tick turns it into a falling
block entity (``sim/entities.py``) when the block below is free (``isFree``: air, fire,
liquids, replaceable blocks): the block becomes air and the entity falls with gravity
until it lands, where it places the block again (``FallingBlockEntity.tick``).

Concrete powder hardens into concrete where it touches water (``touchesLiquid``, also on
landing): water blocks of an opened world and waterlogged blocks count. Suspicious sand
and gravel (``BrushableBlock``: loot and brushing) and pointed dripstone stay foreign
blocks.

Not as in the game (also marked where it happens; all differences: doc/differences.md):

* the anvil's damage on landing: in the game an anvil that fell more than one block may
  become chipped or damaged (or break), decided by the falling entity's own random; the
  simulator's anvil always lands unchanged (``AnvilBlock.falling``,
  ``sim/entities.py`` item 2). The anvil's menu does nothing in the simulator either;
* the dragon egg's teleport when a player uses it: the game picks a random spot; the
  editor's "use" on a dragon egg is refused with a message (``DragonEggBlock``). Breaking
  it in the editor is creative breaking, which removes it as in the game (the teleport on
  hitting it happens in survival only);
* a block that cannot land disappears instead of dropping as an item
  (``sim/entities.py`` item 1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import ALL, Direction
from redsim.core.pos import Pos, below, offset
from redsim.world.block import BlockState, PlacementContext
from redsim.world.blocks.catalog import CatalogBlock, horizontal_direction
from redsim.world.blocks.catalog_data import BLOCKS
from redsim.world.properties import HORIZONTAL_FACING
from redsim.world.shape import Shape, box, column

if TYPE_CHECKING:
    from redsim.sim.entities import FallingBlockEntity
    from redsim.sim.level import Level

#: ``BlockTags.FIRE`` and the liquid blocks (``BlockStateBase.liquid``).
FIRE_OR_LIQUID = frozenset(
    {"minecraft:fire", "minecraft:soul_fire", "minecraft:water", "minecraft:lava"}
)


def is_free(state: BlockState) -> bool:
    """``FallingBlock.isFree``: air, fire, a liquid or a replaceable block (the game's
    ``replaceable`` flag, as ``BlockStateBase.canBeReplaced()`` reads it)."""
    from redsim.world.blocks.openable import can_be_replaced

    return state.is_air or state.block.id in FIRE_OR_LIQUID or can_be_replaced(state)


def fall(level: Level, pos: Pos, state: BlockState) -> FallingBlockEntity:
    """``FallingBlockEntity.fall``: the entity (not waterlogged) at the block's bottom
    center, the block becomes air (in the game its fluid: water for a waterlogged block;
    water is not simulated), then the entity joins."""
    from redsim.sim.entities import FallingBlockEntity
    from redsim.world.properties import WATERLOGGED

    if state.has(WATERLOGGED):
        state = state.with_(WATERLOGGED, False)
    entity = FallingBlockEntity(level.new_entity_id(), state, (pos[0] + 0.5, float(pos[1]),
                                                               pos[2] + 0.5))  # fmt: skip
    level.set_block_and_update(pos, level.air)
    level.add_entity(entity)
    return entity


def on_land(level: Level, pos: Pos, state: BlockState, replaced: BlockState) -> None:
    """``Fallable.onLand`` of the landed block."""
    hook = getattr(state.block, "on_land", None)
    if hook is not None:
        hook(level, pos, state, replaced)


class FallingBlock(CatalogBlock):
    """``FallingBlock``: falls when the block below is free (``tick``)."""

    delay_after_place = 2  # getDelayAfterPlace

    def __init__(self, block_id: str, spec: tuple[Any, ...] | None = None,
                 shape: Shape | None = None) -> None:  # fmt: skip
        super().__init__(block_id, spec if spec is not None else BLOCKS[block_id], shape=shape)

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        level.schedule_tick(pos, self, self.delay_after_place)

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        level.schedule_tick(pos, self, self.delay_after_place)
        return state

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        if is_free(level.get_block_state(below(pos))) and pos[1] >= level.min_y:
            entity = fall(level, pos, state)
            self.falling(entity)

    def falling(self, entity: FallingBlockEntity) -> None:
        return None


class ColoredFallingBlock(FallingBlock):
    """``ColoredFallingBlock`` and ``SandBlock``: sand, red sand, gravel."""


def _is_water(state: BlockState) -> bool:
    from redsim.sim.entities import _is_water as water

    return water(state)


def touches_liquid(level: Level, pos: Pos) -> bool:
    """``ConcretePowderBlock.touchesLiquid``, with its moving test position: the down
    check looks at the previous position (the block itself first)."""
    test = pos
    for direction in ALL:
        state = level.get_block_state(test)
        if direction is not Direction.DOWN or _is_water(state):
            test = offset(pos, direction)
            state = level.get_block_state(test)
            if _is_water(state) and not state.is_face_sturdy(level, pos, direction.opposite):
                return True
    return False


class ConcretePowderBlock(FallingBlock):
    """``ConcretePowderBlock``: hardens into its concrete next to water."""

    def __init__(self, block_id: str, spec: tuple[Any, ...] | None = None) -> None:
        super().__init__(block_id, spec)
        self.concrete_id = block_id.removesuffix("_powder")

    def _concrete(self) -> BlockState:
        from redsim.world import blocks

        return blocks.get(self.concrete_id).default_state

    def _should_solidify(self, level: Level, pos: Pos, replaced: BlockState) -> bool:
        return _is_water(replaced) or touches_liquid(level, pos)

    def on_land(self, level: Level, pos: Pos, state: BlockState, replaced: BlockState) -> None:
        if self._should_solidify(level, pos, replaced):
            level.set_block_and_update(pos, self._concrete())

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        return self.get_state_for_placement(PlacementContext(level, pos, self.default_state))

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement``: concrete right away when placed into or next to
        water."""
        if self._should_solidify(ctx.level, ctx.pos, ctx.level.get_block_state(ctx.pos)):
            return self._concrete()
        return ctx.requested

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if touches_liquid(level, pos):
            return self._concrete()
        return super().update_shape(state, level, pos, direction, neighbor_pos, neighbor)


#: ``AnvilBlock.SHAPES`` (``Shapes.rotateHorizontalAxis``): base, foot, waist and top; the
#: Z-axis shape, turned for the X axis (all parts are centered, so x and z swap).
_ANVIL_PARTS = ((12, 12, 0, 4), (8, 10, 4, 5), (4, 8, 5, 10), (10, 16, 10, 16))


def _anvil_shape(swap: bool) -> Shape:
    out: Shape | None = None
    for size_x, size_z, y0, y1 in _ANVIL_PARTS:
        if swap:
            size_x, size_z = size_z, size_x
        part = box(8 - size_x / 2, y0, 8 - size_z / 2, 8 + size_x / 2, y1, 8 + size_z / 2)
        out = part if out is None else out | part
    assert out is not None
    return out


ANVIL_SHAPES = {"z": _anvil_shape(False), "x": _anvil_shape(True)}


class AnvilBlock(FallingBlock):
    """``AnvilBlock``: facing the player's clockwise side; hurts entities when falling
    (``setHurtsEntities``)."""

    properties = (HORIZONTAL_FACING,)

    def __init__(self, block_id: str, spec: tuple[Any, ...] | None = None) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH))

    def get_shape(self, state: BlockState) -> Shape:
        return ANVIL_SHAPES[state.get(HORIZONTAL_FACING).axis.value]

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        facing = horizontal_direction(request.yaw).clockwise()
        return self.default_state.with_(HORIZONTAL_FACING, facing)

    def falling(self, entity: FallingBlockEntity) -> None:
        # Not as in the game: in the game this also arms the anvil's random damage on
        # landing (FallingBlockEntity.causeFallDamage: after a fall of more than one block
        # a 5 % + 5 % per block chance to become chipped, then damaged, then to break).
        # The simulator keeps no fall distance and lands the anvil unchanged.
        entity.hurt_entities = True


class DragonEggBlock(FallingBlock):
    """``DragonEggBlock``: falls 5 ticks after an update; ``Block.column(14, 0, 16)``."""

    delay_after_place = 5

    def __init__(self, block_id: str, spec: tuple[Any, ...] | None = None) -> None:
        super().__init__(block_id, spec, shape=column(14, 0, 16))

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """Not as in the game: ``useWithoutItem`` teleports the egg to a random free spot
        up to 15 blocks away (the level's random); that cannot be reproduced, so the
        editor refuses the action instead of guessing a spot."""
        from redsim.sim.engine import ActionError

        raise ActionError("The dragon egg teleports to a random spot in the game; not simulated.")


CONCRETE_POWDERS = tuple(i for i, spec in BLOCKS.items() if spec[0] == "ConcretePowderBlock")
