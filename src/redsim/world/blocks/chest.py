"""Chests and trapped chests: ``net/minecraft/world/level/block/ChestBlock.java``,
``TrappedChestBlock.java``, ``DoubleBlockCombiner.java`` and ``CompoundContainer.java``.

A chest is a 27-slot container. Two chests side by side, facing the same way, join into
a double chest (``type`` left/right): hoppers, droppers and comparators then see one
54-slot container, the ``right`` half's slots first. A comparator reads 0 from a chest
whose (either) half has a redstone conductor on top (``isChestBlockedAt``: the combiner
gives no container), hoppers ignore that. Players opening chests are not simulated, so a
trapped chest is a signal source of strength 0 (redstone wire still points at it).
Chests never get waterlogged here (no fluids).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos, above, offset
from redsim.world.block import Block, BlockState, PlacementContext
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.blocks.container import ContainerBlockEntity, Stack
from redsim.world.properties import HORIZONTAL_FACING, Property, boolean
from redsim.world.shape import Shape, box, column

if TYPE_CHECKING:
    from redsim.sim.level import Level

CHEST = "minecraft:chest"
TRAPPED_CHEST = "minecraft:trapped_chest"
CHEST_TYPE = Property("type", ("single", "left", "right"))  # ChestType
WATERLOGGED = boolean("waterlogged")

SHAPE = column(14, 0, 14)  # ChestBlock.SHAPE
#: ``HALF_SHAPES``: ``boxZ(14, 0, 14, 0, 15)`` rotated towards the connected half.
HALF_SHAPES = {
    Direction.NORTH: box(1, 0, 0, 15, 14, 15),
    Direction.SOUTH: box(1, 0, 1, 15, 14, 16),
    Direction.WEST: box(0, 0, 1, 15, 14, 15),
    Direction.EAST: box(1, 0, 1, 16, 14, 15),
}


@register_block_entity
class ChestBlockEntity(ContainerBlockEntity):
    type_id = "chest"
    valid_blocks = frozenset({CHEST})
    SIZE = 27
    NAME = "chest"


@register_block_entity
class TrappedChestBlockEntity(ChestBlockEntity):
    type_id = "trapped_chest"
    valid_blocks = frozenset({TRAPPED_CHEST})
    NAME = "trapped chest"


class _Halves:
    """The slots of two containers as one list (``CompoundContainer`` indexing)."""

    def __init__(self, first: list[Stack | None], second: list[Stack | None]) -> None:
        self.first, self.second = first, second

    def __len__(self) -> int:
        return len(self.first) + len(self.second)

    def __getitem__(self, slot: int) -> Stack | None:
        n = len(self.first)
        return self.first[slot] if slot < n else self.second[slot - n]

    def __setitem__(self, slot: int, stack: Stack | None) -> None:
        n = len(self.first)
        if slot < n:
            self.first[slot] = stack
        else:
            self.second[slot - n] = stack

    def __iter__(self) -> Iterator[Stack | None]:
        yield from self.first
        yield from self.second


class CompoundContainer(ContainerBlockEntity):
    """A double chest as one container (``CompoundContainer``): ``first`` (the right half)
    then ``second``. Changes notify comparators at both halves (``setChanged``)."""

    SIZE = 54
    NAME = "double chest"

    def __init__(self, first: ChestBlockEntity, second: ChestBlockEntity) -> None:
        super().__init__(first.pos, first.block_state)
        self.first, self.second = first, second
        self.items = _Halves(first.items, second.items)  # type: ignore[assignment]

    @property
    def parts(self) -> tuple[ChestBlockEntity, ChestBlockEntity]:
        return (self.first, self.second)


def connected_direction(state: BlockState) -> Direction:
    """``getConnectedDirection`` L131: where the other half is."""
    facing: Direction = state.get(HORIZONTAL_FACING)
    return facing.clockwise() if state.get(CHEST_TYPE) == "left" else facing.counter_clockwise()


def is_blocked(level: Level, pos: Pos) -> bool:
    """``isChestBlockedAt`` L263: a redstone conductor on top (cats are not simulated)."""
    top = above(pos)
    return level.get_block_state(top).is_redstone_conductor(level, top)


def chest_container(
    level: Level, pos: Pos, state: BlockState, ignore_blocked: bool
) -> ContainerBlockEntity | None:
    """``ChestBlock.getContainer`` → ``DoubleBlockCombiner.combineWithNeigbour``: the
    chest, the double chest, or None (no entity, or blocked unless ignored)."""
    entity = level.get_block_entity(pos)
    if not isinstance(entity, ChestBlockEntity):
        return None
    if not ignore_blocked and is_blocked(level, pos):
        return None
    kind = state.get(CHEST_TYPE)
    if kind == "single":
        return entity
    neighbor_pos = offset(pos, connected_direction(state))
    neighbor = level.get_block_state(neighbor_pos)
    if (
        neighbor.block is state.block
        and neighbor.get(CHEST_TYPE) not in ("single", kind)
        and neighbor.get(HORIZONTAL_FACING) == state.get(HORIZONTAL_FACING)
    ):
        if not ignore_blocked and is_blocked(level, neighbor_pos):
            return None
        other = level.get_block_entity(neighbor_pos)
        if isinstance(other, ChestBlockEntity):
            # ``getBlockType``: RIGHT is FIRST.
            first, second = (entity, other) if kind == "right" else (other, entity)
            return CompoundContainer(first, second)
    return entity


class ChestBlock(Block):
    properties = (HORIZONTAL_FACING, CHEST_TYPE, WATERLOGGED)
    has_block_entity = True

    def __init__(self, block_id: str = CHEST) -> None:
        super().__init__(block_id, destroy_speed=2.5)
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH)
            .with_(CHEST_TYPE, "single")
            .with_(WATERLOGGED, False)
        )

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return ChestBlockEntity(pos, state)

    def get_shape(self, state: BlockState) -> Shape:
        """``getShape`` L124."""
        if state.get(CHEST_TYPE) == "single":
            return SHAPE
        return HALF_SHAPES[connected_direction(state)]

    def _partner_facing(self, level: Level, pos: Pos, direction: Direction) -> Any:
        """``candidatePartnerFacing`` L176: a single chest of this kind there."""
        state = level.get_block_state(offset(pos, direction))
        if state.block is self and state.get(CHEST_TYPE) == "single":
            return state.get(HORIZONTAL_FACING)
        return None

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement`` L142 without sneaking: facing the player, joining a
        single chest beside it that faces the same way (``getChestType`` L163)."""
        facing: Direction = ctx.requested.get(HORIZONTAL_FACING)
        kind = "single"
        if facing == self._partner_facing(ctx.level, ctx.pos, facing.clockwise()):
            kind = "left"
        elif facing == self._partner_facing(ctx.level, ctx.pos, facing.counter_clockwise()):
            kind = "right"
        return (
            self.default_state.with_(HORIZONTAL_FACING, facing)
            .with_(CHEST_TYPE, kind)
            .with_(WATERLOGGED, False)
        )

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        """``updateShape`` L90: join a half that points here, split when the partner
        goes."""
        if neighbor.block is self and direction.axis is not Direction.UP.axis:
            other = neighbor.get(CHEST_TYPE)
            if (
                state.get(CHEST_TYPE) == "single"
                and other != "single"
                and state.get(HORIZONTAL_FACING) == neighbor.get(HORIZONTAL_FACING)
                and connected_direction(neighbor) == direction.opposite
            ):
                return state.with_(CHEST_TYPE, "left" if other == "right" else "right")
        elif state.get(CHEST_TYPE) != "single" and connected_direction(state) == direction:
            return state.with_(CHEST_TYPE, "single")
        return state

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        """``getAnalogOutputSignal`` L291: 0 while blocked."""
        container = chest_container(level, pos, state, ignore_blocked=False)
        return container.signal() if container is not None else 0

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        """``Containers.updateNeighboursAfterDestroy``."""
        level.update_neighbour_for_output_signal(pos, self)


class TrappedChestBlock(ChestBlock):
    """``TrappedChestBlock``: a signal source; its signal counts the players looking in,
    so it is 0 here."""

    def __init__(self) -> None:
        super().__init__(TRAPPED_CHEST)

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return TrappedChestBlockEntity(pos, state)

    def is_signal_source(self, state: BlockState) -> bool:
        return True
