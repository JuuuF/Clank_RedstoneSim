"""Hopper: moves one item at a time between containers; redstone power locks it.

Sources (relative to ``data/minecraft_src/client-src/net/minecraft/``):

* ``world/level/block/HopperBlock.java``: ``FACING`` (``FACING_HOPPER``: down or
  horizontal) and ``ENABLED``; placement L77 (the clicked face, reversed; up becomes down);
  ``checkPoweredState`` L118 from ``onPlace`` (a different block was there) and
  ``neighborChanged``: ``ENABLED = !hasNeighborSignal`` with flags 2; removal updates
  comparators (``Containers.updateNeighboursAfterDestroy``); analog output = the container
  fill level. Shapes L46-70.
* ``world/level/block/entity/HopperBlockEntity.java``: 5 slots, ``TransferCooldown``
  (-1 when new), ``tickedGameTime``.

  * ``pushItemsTick`` L97 (every game tick, block-entity phase): cooldown − 1, remember the
    game time; at cooldown ≤ 0 set it to 0 and ``tryMoveItems``.
  * ``tryMoveItems`` L106: only when enabled and not on cooldown: push one item
    (``ejectItems``) if not empty, then pull one (``suckInItems``) if not full; if either
    moved, cooldown 8 and ``setChanged`` (comparators update).
  * ``ejectItems`` L143: into the container in front (``getAttachedContainer``), unless all
    its slots are full; the first slot whose item fits is used.
  * ``suckInItems`` L218: from the container above, the first slot whose item fits. (Item
    entities above are not simulated.)
  * ``tryMoveInItem`` L314: an empty slot takes the stack (``setItem``), a matching stack
    grows; when an **empty** hopper receives an item, its cooldown becomes 8, or 7 if the
    sending hopper has not ticked later in this game tick than the receiver
    (``tickedGameTime``), so chained hoppers move one item per 8 ticks regardless of their
    ticker order.
  * ``setItem`` L80 and ``removeItem`` L74 do **not** call ``setChanged`` (unlike other
    containers), so ``/item replace`` on a hopper does not update comparators.

Containers are block entities extending ``ContainerBlockEntity`` (barrels, hoppers, chests,
dispensers, droppers); a full composter above gives its bone meal (``_take_compost``);
there are no container entities in scope. Pistons cannot move hoppers (block
entity). Dust can sit on top of a hopper (``RedstoneWireBlock.canSurviveOn``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos, offset
from redsim.world import ids
from redsim.world.block import Block, BlockState, PlacementContext
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.blocks.container import (
    ContainerBlockEntity,
    Stack,
    item_max_stack,
    set_changed,
)
from redsim.world.properties import ENABLED, FACING_HOPPER
from redsim.world.shape import Shape, box, column

if TYPE_CHECKING:
    from redsim.sim.level import Level

#: ``HopperBlockEntity.MOVE_ITEM_SPEED``: ticks between two moves.
MOVE_ITEM_SPEED = 8


def _shapes() -> dict[Direction, Shape]:
    """``HopperBlock.makeShapes``: bowl (minus its inside), funnel, and the spout rotated to
    ``FACING`` around (8, 6, 8) and clipped to the block."""
    bowl = Shape(box(0, 10, 0, 16, 16, 16).grid & ~column(12, 11, 16).grid)
    body = bowl | column(8, 4, 10)
    spouts = {
        Direction.DOWN: box(6, 0, 6, 10, 6, 10),
        Direction.NORTH: box(6, 4, 0, 10, 8, 8),
        Direction.SOUTH: box(6, 4, 8, 10, 8, 16),
        Direction.WEST: box(0, 4, 6, 8, 8, 10),
        Direction.EAST: box(8, 4, 6, 16, 8, 10),
    }
    return {facing: body | spout for facing, spout in spouts.items()}


SHAPES = _shapes()


class HopperBlockEntity(ContainerBlockEntity):
    type_id = "hopper"
    valid_blocks = frozenset({ids.HOPPER})
    SIZE = 5
    NAME = "hopper"

    def __init__(self, pos: Pos, state: BlockState) -> None:
        super().__init__(pos, state)
        self.cooldown_time = -1
        self.ticked_game_time = 0

    @property
    def facing(self) -> Direction:
        """The cached ``facing`` (``setBlockState`` keeps it in step with the block state)."""
        facing: Direction = self.block_state.get(FACING_HOPPER)
        return facing

    # HopperBlockEntity.setItem/removeItem: no setChanged.
    def set_item(self, level: Level, slot: int, stack: Stack | None) -> None:
        self.store(slot, stack)

    def remove_item(self, level: Level, slot: int, count: int) -> Stack | None:
        return self.split(slot, count)

    def is_on_cooldown(self) -> bool:
        return self.cooldown_time > 0

    def is_on_custom_cooldown(self) -> bool:
        return self.cooldown_time > MOVE_ITEM_SPEED

    def inventory_full(self) -> bool:
        return all(
            stack is not None and stack[1] == item_max_stack(stack[0]) for stack in self.items
        )

    def tick(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``pushItemsTick``."""
        self.cooldown_time -= 1
        self.ticked_game_time = level.game_time
        if not self.is_on_cooldown():
            self.cooldown_time = 0
            try_move_items(level, pos, state, self)

    def to_json(self) -> dict[str, Any]:
        data = super().to_json()
        data["TransferCooldown"] = self.cooldown_time
        return data

    def load_json(self, data: dict[str, Any]) -> None:
        super().load_json(data)
        self.cooldown_time = int(data.get("TransferCooldown", -1))

    def shift_time(self, delta: int) -> None:
        self.ticked_game_time += delta

    def runtime_json(self) -> dict[str, Any]:
        return {"ticked_game_time": self.ticked_game_time}

    def load_runtime_json(self, data: dict[str, Any]) -> None:
        self.ticked_game_time = int(data.get("ticked_game_time", 0))

    def describe(self) -> str:
        return f"{super().describe()}, cooldown {self.cooldown_time}"


# --- item transfer (HopperBlockEntity statics) ---------------------------------------------
def try_move_items(level: Level, pos: Pos, state: BlockState, hopper: HopperBlockEntity) -> bool:
    if hopper.is_on_cooldown() or not state.get(ENABLED):
        return False
    changed = False
    if not hopper.is_empty():
        changed = eject_items(level, pos, hopper)
    if not hopper.inventory_full():
        changed = suck_in_items(level, hopper) or changed
    if changed:
        hopper.cooldown_time = MOVE_ITEM_SPEED
        if not state.is_air:  # static BlockEntity.setChanged(level, pos, state)
            level.update_neighbour_for_output_signal(pos, state.block)
        return True
    return False


def container_at(level: Level, pos: Pos) -> ContainerBlockEntity | None:
    """``getContainerAt`` → ``getBlockContainer`` L378: a block entity that is a container;
    a chest gives its double chest (even when blocked)."""
    state = level.get_block_state(pos)
    if not state.has_block_entity:
        return None
    from redsim.world.blocks.chest import ChestBlock, chest_container

    if isinstance(state.block, ChestBlock):
        return chest_container(level, pos, state, ignore_blocked=True)
    entity = level.get_block_entity(pos)
    return entity if isinstance(entity, ContainerBlockEntity) else None


def is_full_container(container: ContainerBlockEntity) -> bool:
    return all(
        stack is not None and stack[1] >= item_max_stack(stack[0]) for stack in container.items
    )


def eject_items(level: Level, pos: Pos, hopper: HopperBlockEntity) -> bool:
    container = container_at(level, offset(pos, hopper.facing))
    if container is None or is_full_container(container):
        return False
    for slot in range(hopper.SIZE):
        stack = hopper.items[slot]
        if stack is not None:
            moving = hopper.remove_item(level, slot, 1)
            assert moving is not None
            if add_item(level, hopper, container, moving) is None:
                set_changed(container, level)
                return True
            hopper.items[slot] = stack  # setCount(originalCount) (+ the hopper's setItem)
    return False


def suck_in_items(level: Level, hopper: HopperBlockEntity) -> bool:
    above = offset(hopper.pos, Direction.UP)
    container = container_at(level, above)
    if container is None:
        return _take_compost(level, hopper, above)  # (item entities are not simulated)
    for slot in range(container.SIZE):
        if _try_take_in_item_from_slot(level, hopper, container, slot):
            return True
    return False


def _take_compost(level: Level, hopper: HopperBlockEntity, above: Pos) -> bool:
    """A full composter above gives its bone meal (``ComposterBlock.OutputContainer``):
    if the hopper has room for it, the composter empties (its ``setChanged``)."""
    from redsim.world.blocks.composter import BONE_MEAL, LEVEL, READY, ComposterBlock

    state = level.get_block_state(above)
    if not isinstance(state.block, ComposterBlock) or state.get(LEVEL) != READY:
        return False
    if add_item(level, None, hopper, (BONE_MEAL, 1)) is not None:
        return False
    level.set_block_and_update(above, state.with_(LEVEL, 0))
    return True


def _try_take_in_item_from_slot(
    level: Level, hopper: HopperBlockEntity, container: ContainerBlockEntity, slot: int
) -> bool:
    stack = container.items[slot]
    if stack is None:
        return False
    moving = container.remove_item(level, slot, 1)
    assert moving is not None
    if add_item(level, container, hopper, moving) is None:
        set_changed(container, level)
        return True
    container.items[slot] = stack  # itemStack.setCount(originalCount)
    if stack[1] == 1:
        container.set_item(level, slot, stack)
    return False


def add_item(
    level: Level, source: ContainerBlockEntity | None, container: ContainerBlockEntity, stack: Stack
) -> Stack | None:
    """``addItem``: offer ``stack`` to every slot in order; returns what is left."""
    rest: Stack | None = stack
    for slot in range(container.SIZE):
        if rest is None:
            break
        rest = _try_move_in_item(level, source, container, rest, slot)
    return rest


def _try_move_in_item(
    level: Level,
    source: ContainerBlockEntity | None,
    container: ContainerBlockEntity,
    stack: Stack,
    slot: int,
) -> Stack | None:
    current = container.items[slot]
    was_empty = container.is_empty()
    rest: Stack | None = stack
    success = False
    if current is None:
        container.set_item(level, slot, stack)
        rest, success = None, True
    elif current[0] == stack[0] and current[1] <= item_max_stack(current[0]):  # canMergeItems
        count = min(stack[1], item_max_stack(stack[0]) - current[1])
        rest = (stack[0], stack[1] - count) if stack[1] > count else None
        container.items[slot] = (current[0], current[1] + count)
        success = count > 0
    if success:
        if (
            was_empty
            and isinstance(container, HopperBlockEntity)
            and not container.is_on_custom_cooldown()
        ):
            skip = (
                1
                if isinstance(source, HopperBlockEntity)
                and container.ticked_game_time >= source.ticked_game_time
                else 0
            )
            container.cooldown_time = MOVE_ITEM_SPEED - skip
        set_changed(container, level)
    return rest


class HopperBlock(Block):
    properties = (FACING_HOPPER, ENABLED)
    has_block_entity = True
    has_ticker = True

    def __init__(self) -> None:
        super().__init__(ids.HOPPER, destroy_speed=3.0)
        self.register_default_state(
            self.default_state.with_(FACING_HOPPER, Direction.DOWN).with_(ENABLED, True)
        )

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return HopperBlockEntity(pos, state)

    def get_shape(self, state: BlockState) -> Shape:
        return SHAPES[state.get(FACING_HOPPER)]

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        facing = ctx.requested.get(FACING_HOPPER)
        return self.default_state.with_(FACING_HOPPER, facing).with_(ENABLED, True)

    # --- locking ---------------------------------------------------------------------------
    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        if state.block is not old_state.block:
            self.check_powered_state(level, pos, state)

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        self.check_powered_state(level, pos, state)

    def check_powered_state(self, level: Level, pos: Pos, state: BlockState) -> None:
        should_be_on = not level.has_neighbor_signal(pos)
        if should_be_on != state.get(ENABLED):
            level.set_block(pos, state.with_(ENABLED, should_be_on), 2)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        level.update_neighbour_for_output_signal(pos, self)

    # --- comparator output -----------------------------------------------------------------
    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        entity = level.get_block_entity(pos)
        return entity.signal() if isinstance(entity, ContainerBlockEntity) else 0


__all__ = ["MOVE_ITEM_SPEED", "SHAPES", "HopperBlock", "HopperBlockEntity", "container_at"]


# Registered here, not with a class decorator (classes stay compilable by mypyc).
register_block_entity(HopperBlockEntity)
