"""Dispenser and dropper: ``net/minecraft/world/level/block/DispenserBlock.java`` and
``DropperBlock.java``, with ``DispenserBlockEntity`` (9 slots).

Both trigger on a rising signal at themselves or the block above (quasi-connectivity,
``neighborChanged`` L77): ``triggered`` is set at once (flags 2) and a 4-tick scheduled
tick dispenses. A random non-empty slot is chosen (``getRandomSlot``: reservoir sampling
with the level's random source). With one filled slot this is exact; with several the
game itself is random, and the simulation draws from its own random source, seeded with
the game time and position so a replay gives the same choice.

The dropper moves one item into the container in front (``HopperBlockEntity.addItem``),
else drops it. Dropped items (and anything a dispenser shoots, places or uses) are item
entities or effects the simulation does not model: the item just leaves the container.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from redsim.core.direction import Direction
from redsim.core.pos import Pos, above, offset
from redsim.world.block import Block, BlockState, PlacementContext, UpdateFlags
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.blocks.container import ContainerBlockEntity
from redsim.world.properties import FACING, boolean

if TYPE_CHECKING:
    from redsim.sim.level import Level

TRIGGERED = boolean("triggered")
TRIGGER_DURATION = 4  # DispenserBlock.TRIGGER_DURATION

DISPENSER = "minecraft:dispenser"
DROPPER = "minecraft:dropper"


class DispenserBlockEntity(ContainerBlockEntity):
    type_id = "dispenser"
    valid_blocks = frozenset({DISPENSER})
    SIZE = 9
    NAME = "dispenser"

    def random_slot(self, level: Level) -> int:
        """``getRandomSlot`` L34: reservoir sampling over the non-empty slots."""
        rng = random.Random(
            (level.game_time * 31 + self.pos[0]) * 961 + self.pos[1] * 31 + self.pos[2]
        )
        chosen, odds = -1, 1
        for slot, stack in enumerate(self.items):
            if stack is not None:
                if rng.randrange(odds) == 0:
                    chosen = slot
                odds += 1
        return chosen


class DropperBlockEntity(DispenserBlockEntity):
    type_id = "dropper"
    valid_blocks = frozenset({DROPPER})
    NAME = "dropper"


class DispenserBlock(Block):
    properties = (FACING, TRIGGERED)
    has_block_entity = True

    def __init__(self, block_id: str = DISPENSER) -> None:
        super().__init__(block_id, destroy_speed=3.5)
        self.register_default_state(
            self.default_state.with_(FACING, Direction.NORTH).with_(TRIGGERED, False)
        )

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return DispenserBlockEntity(pos, state)

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement`` L101: facing the player (``getNearestLookingDirection
        ().getOpposite()``, chosen by the editor's placement)."""
        return self.default_state.with_(FACING, ctx.requested.get(FACING))

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        """``neighborChanged`` L77: powered at itself or the block above."""
        should_trigger = level.has_neighbor_signal(pos) or level.has_neighbor_signal(above(pos))
        is_triggered = state.get(TRIGGERED)
        if should_trigger and not is_triggered:
            level.schedule_tick(pos, self, TRIGGER_DURATION)
            level.set_block(pos, state.with_(TRIGGERED, True), UpdateFlags.CLIENTS)
        elif not should_trigger and is_triggered:
            level.set_block(pos, state.with_(TRIGGERED, False), UpdateFlags.CLIENTS)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``tick`` L91."""
        self.dispense_from(level, state, pos)

    def dispense_from(self, level: Level, state: BlockState, pos: Pos) -> None:
        """``dispenseFrom`` L37. Every item uses the default behavior here: one item
        leaves the dispenser (shot, dropped, placed or used in the game)."""
        entity = level.get_block_entity(pos)
        if not isinstance(entity, DispenserBlockEntity):
            return
        slot = entity.random_slot(level)
        if slot >= 0:
            entity.set_item(level, slot, _less(entity.items[slot]))  # setItem: setChanged

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        """``getAnalogOutputSignal`` L126: the container's fill level."""
        entity = level.get_block_entity(pos)
        return entity.signal() if isinstance(entity, ContainerBlockEntity) else 0

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        """``affectNeighborsAfterRemoval`` L106 (``Containers.updateNeighboursAfterDestroy``)."""
        level.update_neighbour_for_output_signal(pos, self)


class DropperBlock(DispenserBlock):
    def __init__(self) -> None:
        super().__init__(DROPPER)

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return DropperBlockEntity(pos, state)

    def dispense_from(self, level: Level, state: BlockState, pos: Pos) -> None:
        """``DropperBlock.dispenseFrom`` L23: one item into the container in front
        (``addItem``), else it is dropped."""
        from redsim.world.blocks.hopper import add_item, container_at

        entity = level.get_block_entity(pos)
        if not isinstance(entity, DispenserBlockEntity):
            return
        slot = entity.random_slot(level)
        if slot < 0:
            return
        stack = entity.items[slot]
        assert stack is not None
        facing = level.get_block_state(pos).get(FACING)
        target = container_at(level, offset(pos, facing))
        if target is not None and add_item(level, entity, target, (stack[0], 1)) is not None:
            entity.set_item(level, slot, stack)  # nothing moved (setItem still notifies)
            return
        entity.set_item(level, slot, _less(stack))  # moved, or dropped as an item entity


def _less(stack: tuple[str, int] | None) -> tuple[str, int] | None:
    """The stack with one item fewer (``ItemStack.shrink(1)``)."""
    if stack is None or stack[1] <= 1:
        return None
    return (stack[0], stack[1] - 1)


# Registered here, not with a class decorator (classes stay compilable by mypyc).
register_block_entity(DispenserBlockEntity)
register_block_entity(DropperBlockEntity)
