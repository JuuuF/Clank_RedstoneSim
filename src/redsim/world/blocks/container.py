"""Barrel: a container whose fill level is a comparator signal.

Sources (relative to ``data/minecraft_src/client-src/net/minecraft/``):

* ``world/level/block/BarrelBlock.java``: ``FACING``/``OPEN``, placement facing L91
  (nearest looking direction, reversed), ``hasAnalogOutputSignal``/``getAnalogOutputSignal``
  L66-73, ``affectNeighborsAfterRemoval`` L49 (``Containers.updateNeighboursAfterDestroy``:
  ``updateNeighbourForOutputSignal``).
* ``world/inventory/AbstractContainerMenu.java`` ``getRedstoneSignalFromContainer`` L766:
  the sum of ``count / maxStackSize`` over all slots, divided by the slot count, in
  32-bit float, then ``Mth.lerpDiscrete(f, 0, 15)`` (``util/Mth.java`` L545).
* ``world/Container.java`` L34-40: a slot holds at most ``min(99, item max stack size)``;
  every item's max stack size is in ``world/items_data.py`` (generated from the game's
  data generator by ``tools/extract_item_table.py``).
* ``world/level/block/entity/BaseContainerBlockEntity.java`` ``setItem`` L126: store,
  ``limitSize``, ``setChanged`` (``BlockEntity.setChanged`` L198:
  ``updateNeighbourForOutputSignal``); ``removeItem`` L111: split, ``setChanged`` if
  something was taken. ``ContainerBlockEntity`` ports this base; hoppers override both
  without ``setChanged`` (``hopper.py``).

Barrels have a block entity, so pistons cannot move them (``PistonBaseBlock.isPushable``).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

import numpy as np

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.world import ids
from redsim.world.block import Block, BlockState, PlacementContext
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.items_data import ITEM_MAX_STACK
from redsim.world.properties import FACING, OPEN

if TYPE_CHECKING:
    from redsim.sim.level import Level

#: ``Container.getMaxStackSize()`` default.
CONTAINER_MAX_STACK = 99
Stack = tuple[str, int]  # item id, count


def empty_slots(size: int) -> list[Stack | None]:
    return [None] * size


class Slots(Protocol):
    """A container's slots: a list, or two lists joined (a double chest)."""

    def __len__(self) -> int: ...
    def __getitem__(self, slot: int) -> Stack | None: ...
    def __setitem__(self, slot: int, stack: Stack | None) -> None: ...
    def __iter__(self) -> Iterator[Stack | None]: ...


def item_max_stack(item_id: str) -> int:
    """The item's ``minecraft:max_stack_size`` (``items_data``, generated from the game)."""
    return ITEM_MAX_STACK.get(item_id, 64)


def slot_limit(item_id: str) -> int:
    """``Container.getMaxStackSize(ItemStack)``."""
    return min(CONTAINER_MAX_STACK, item_max_stack(item_id))


def lerp_discrete(alpha: np.float32, p0: int, p1: int) -> int:
    """``Mth.lerpDiscrete`` with Java float arithmetic."""
    delta = p1 - p0
    return p0 + math.floor(np.float32(alpha * np.float32(delta - 1))) + (1 if alpha > 0 else 0)


def container_signal(stacks: Iterable[Stack | None], size: int) -> int:
    """``AbstractContainerMenu.getRedstoneSignalFromContainer`` (32-bit float, as in Java)."""
    total = np.float32(0.0)
    for stack in stacks:
        if stack is not None and stack[1] > 0:
            total = np.float32(total + np.float32(np.float32(stack[1]) / slot_limit(stack[0])))
    total = np.float32(total / np.float32(size))
    return lerp_discrete(total, 0, 15)


class ContainerBlockEntity(BlockEntity):
    """``BaseContainerBlockEntity``: a fixed number of item slots.

    Stacks are immutable ``(item id, count)`` tuples; ``None`` is an empty slot. Methods
    that notify comparators do so where the game calls ``setChanged``.
    """

    SIZE: ClassVar[int] = 0
    NAME: ClassVar[str] = "container"

    def __init__(self, pos: Pos, state: BlockState) -> None:
        super().__init__(pos, state)
        #: The slots (a list; a double chest joins two lists, ``chest._Halves``).
        self.items: Slots = empty_slots(self.SIZE)

    def signal(self) -> int:
        return container_signal(self.items, self.SIZE)

    def is_empty(self) -> bool:
        return all(stack is None for stack in self.items)

    def set_item(self, level: Level, slot: int, stack: Stack | None) -> None:
        """``BaseContainerBlockEntity.setItem`` (L126): store, limit the count, ``setChanged``."""
        self.store(slot, stack)
        set_changed(self, level)

    def remove_item(self, level: Level, slot: int, count: int) -> Stack | None:
        """``BaseContainerBlockEntity.removeItem`` (L111): ``ContainerHelper.removeItem``
        (split the slot's stack), then ``setChanged`` if something was taken."""
        taken = self.split(slot, count)
        if taken is not None:
            set_changed(self, level)
        return taken

    def store(self, slot: int, stack: Stack | None) -> None:
        """Write a slot without side effects (``ItemStack.limitSize`` applied)."""
        if stack is not None and stack[1] > 0:
            stack = (stack[0], min(stack[1], slot_limit(stack[0])))
        else:
            stack = None
        self.items[slot] = stack

    def split(self, slot: int, count: int) -> Stack | None:
        """``ContainerHelper.removeItem``: ``ItemStack.split`` on the slot, no side effects."""
        stack = self.items[slot]
        if stack is None or count <= 0:
            return None
        taken = min(count, stack[1])
        self.items[slot] = (stack[0], stack[1] - taken) if stack[1] > taken else None
        return (stack[0], taken)

    def clone(self) -> BlockEntity:
        other = super().clone()
        assert isinstance(other, ContainerBlockEntity)
        other.items = list(self.items)
        return other

    def to_json(self) -> dict[str, Any]:
        """Same layout as the game's NBT (``ContainerHelper.saveAllItems``)."""
        return {
            "Items": [
                {"Slot": slot, "id": stack[0], "count": stack[1]}
                for slot, stack in enumerate(self.items)
                if stack is not None
            ]
        }

    def load_json(self, data: dict[str, Any]) -> None:
        self.items = empty_slots(self.SIZE)
        for entry in data.get("Items", []):
            slot = int(entry["Slot"])
            if 0 <= slot < self.SIZE and int(entry.get("count", 1)) > 0:
                self.items[slot] = (str(entry["id"]), int(entry.get("count", 1)))

    def contents(self) -> str:
        """``slot:id*count`` for every filled slot (the harness compares this with the game)."""
        return " ".join(
            f"{slot}:{stack[0]}*{stack[1]}"
            for slot, stack in enumerate(self.items)
            if stack is not None
        )

    def describe(self) -> str:
        filled = sum(1 for stack in self.items if stack is not None)
        total = sum(stack[1] for stack in self.items if stack is not None)
        return f"{self.NAME}: {total} items in {filled} slots, signal {self.signal()}"


class BarrelBlockEntity(ContainerBlockEntity):
    type_id = "barrel"
    valid_blocks = frozenset({ids.BARREL})
    SIZE = 27
    NAME = "barrel"


def set_changed(entity: BlockEntity, level: Level) -> None:
    """``BlockEntity.setChanged`` (L198): comparators around it re-read the value. A
    double chest (``CompoundContainer.setChanged``) notifies both halves."""
    parts = getattr(entity, "parts", None)
    if parts is not None:
        for part in parts:
            set_changed(part, level)
        return
    state = level.get_block_state(entity.pos)
    if not state.is_air:
        level.update_neighbour_for_output_signal(entity.pos, state.block)


class BarrelBlock(Block):
    properties = (FACING, OPEN)
    has_block_entity = True

    def __init__(self) -> None:
        super().__init__(ids.BARREL, destroy_speed=2.5)
        self.register_default_state(
            self.default_state.with_(FACING, Direction.NORTH).with_(OPEN, False)
        )

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return BarrelBlockEntity(pos, state)

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.default_state.with_(FACING, ctx.requested.get(FACING))

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        entity = level.get_block_entity(pos)
        return entity.signal() if isinstance(entity, BarrelBlockEntity) else 0

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        level.update_neighbour_for_output_signal(pos, self)


# Registered here, not with a class decorator (classes stay compilable by mypyc).
register_block_entity(BarrelBlockEntity)
