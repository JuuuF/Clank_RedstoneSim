"""Lectern: a comparator source driven by the open page of its book, and a page-turn pulse.

Sources (relative to ``data/minecraft_src/client-src/net/minecraft/``):

* ``world/level/block/LecternBlock.java``: shapes L47 (collision: a 2-px slab plus an 8-px
  post up to 14 px), placement L74 (``getHorizontalDirection().getOpposite()``),
  ``signalPageChange`` L148 (``POWERED`` on, tick in 2), ``changePowered``/``updateBelow``
  L154-162 (``setBlockAndUpdate``, then neighbor updates around the block below), ``tick``
  L165 (``POWERED`` off), ``affectNeighborsAfterRemoval`` L170, ``ownSignal`` L182 (15 when
  powered), ``getDirectSignal`` L187 (15 upwards, i.e. into the block below),
  ``getAnalogOutputSignal`` L197 (0 without ``HAS_BOOK``).
* ``world/level/block/entity/LecternBlockEntity.java``: ``setPage`` L159 (clamp; on a change
  ``setChanged`` and ``signalPageChange``), ``getRedstoneSignal`` L172
  (``floor(page / (pageCount - 1.0F) * 14.0F) + 1`` in 32-bit float), ``loadAdditional``
  L196 (``Page`` clamped with ``Mth.clamp``, which yields -1 for a book without pages).

The outline shape's slanted top is not modeled (voxel shapes are whole pixels); support and
collision use the exact collision shape. Lecterns have a block entity, so pistons cannot
move them.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import numpy as np

from redsim.core.direction import Direction
from redsim.core.pos import Pos, below
from redsim.world import ids
from redsim.world.block import Block, BlockState, PlacementContext
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.blocks.container import set_changed
from redsim.world.properties import HAS_BOOK, HORIZONTAL_FACING, POWERED
from redsim.world.shape import Shape, column

if TYPE_CHECKING:
    from redsim.sim.level import Level

PAGE_CHANGE_IMPULSE_TICKS = 2
WRITABLE_BOOK = "minecraft:writable_book"
_COLLISION = column(16, 0, 2) | column(8, 2, 14)


def java_clamp(value: int, low: int, high: int) -> int:
    """``Mth.clamp(int, int, int)``: ``min(max(value, low), high)`` (high wins if low > high)."""
    return min(max(value, low), high)


def page_signal(page: int, page_count: int, has_book: bool) -> int:
    """``LecternBlockEntity.getRedstoneSignal`` with Java float arithmetic."""
    if page_count > 1:
        progress = np.float32(np.float32(page) / np.float32(page_count - 1.0))
    else:
        progress = np.float32(1.0)
    return math.floor(np.float32(progress * np.float32(14.0))) + (1 if has_book else 0)


@register_block_entity
class LecternBlockEntity(BlockEntity):
    type_id = "lectern"
    valid_blocks = frozenset({ids.LECTERN})

    def __init__(self, pos: Pos, state: BlockState) -> None:
        super().__init__(pos, state)
        self.book: str | None = None  # item id of the book on the lectern
        self.page_count = 0
        self.page = 0

    def has_book(self) -> bool:
        return self.book is not None

    def signal(self) -> int:
        return page_signal(self.page, self.page_count, self.has_book())

    def set_page(self, level: Level, page: int) -> bool:
        """``setPage`` (a player turning the page): returns whether the page changed."""
        new_page = java_clamp(page, 0, self.page_count - 1)
        if new_page == self.page:
            return False
        self.page = new_page
        set_changed(self, level)
        signal_page_change(level, self.pos, level.get_block_state(self.pos))
        return True

    def to_json(self) -> dict[str, Any]:
        """Like the game's NBT (``Book``, ``Page``); the book's pages are counted only."""
        if self.book is None:
            return {}
        book = {"id": self.book, "count": 1, "pages": self.page_count}
        return {"Book": book, "Page": self.page}

    def load_json(self, data: dict[str, Any]) -> None:
        book = data.get("Book")
        self.book = str(book["id"]) if book else None
        self.page_count = int(book.get("pages", 0)) if book else 0
        self.page = java_clamp(int(data.get("Page", 0)), 0, self.page_count - 1)

    def describe(self) -> str:
        if self.book is None:
            return "lectern: no book"
        return f"lectern: page {self.page + 1} of {self.page_count}, signal {self.signal()}"


def signal_page_change(level: Level, pos: Pos, state: BlockState) -> None:
    """``LecternBlock.signalPageChange``."""
    change_powered(level, pos, state, True)
    level.schedule_tick(pos, state.block, PAGE_CHANGE_IMPULSE_TICKS)


def change_powered(level: Level, pos: Pos, state: BlockState, powered: bool) -> None:
    level.set_block_and_update(pos, state.with_(POWERED, powered))
    update_below(level, pos, state)


def update_below(level: Level, pos: Pos, state: BlockState) -> None:
    level.update_neighbors_at(below(pos), state.block)


class LecternBlock(Block):
    properties = (HORIZONTAL_FACING, POWERED, HAS_BOOK)
    has_block_entity = True

    def __init__(self) -> None:
        super().__init__(ids.LECTERN, destroy_speed=2.5)
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH)
            .with_(POWERED, False)
            .with_(HAS_BOOK, False)
        )

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return LecternBlockEntity(pos, state)

    def get_shape(self, state: BlockState) -> Shape:
        return _COLLISION

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        facing = ctx.requested.get(HORIZONTAL_FACING)
        return self.default_state.with_(HORIZONTAL_FACING, facing).with_(HAS_BOOK, False)

    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return 15 if state.get(POWERED) else 0

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return 15 if direction is Direction.UP and state.get(POWERED) else 0

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        entity = level.get_block_entity(pos)
        if state.get(HAS_BOOK) and isinstance(entity, LecternBlockEntity):
            return entity.signal()
        return 0

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        change_powered(level, pos, state, False)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        if state.get(POWERED):
            update_below(level, pos, state)
