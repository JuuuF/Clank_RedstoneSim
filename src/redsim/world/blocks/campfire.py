"""Campfires: ``CampfireBlock.java`` and ``CampfireBlockEntity.java`` (campfire, soul
campfire).

* State: ``lit`` (default true), ``signal_fire`` (a hay bale right below), ``waterlogged``,
  ``facing`` (the player's facing when placed). ``signal_fire`` follows the block below
  through shape updates (``updateShape``), so an observer sees a hay bale come and go.
* Shape ``Block.column(16, 0, 7)``, the same for collision: not a conductor, nothing is
  sturdy on top; falling blocks land in its cell and break.
* A block entity with four food slots, so pistons never move a campfire. While lit its
  ticker cooks: each food's progress grows by one per tick and the food leaves when it
  reaches its cooking time (the game drops the result as an item; items are not
  simulated); while unlit progress cools by 2 per tick. Any change calls ``setChanged``
  (comparators next to it are updated). Food is placed by players with items (not in the
  editor) or with ``/setblock`` data (``Items``, ``CookingTimes``, ``CookingTotalTimes``).

Not as in the game (also marked where it happens; all differences: doc/differences.md):

* cooked food leaves the campfire but is not dropped as an item (items are not simulated);
* a waterlogged campfire schedules no water tick, so its water never flows;
* not modeled at all: light, smoke, hurting mobs standing in it, lighting and dousing with
  items (flint and steel, fire charges, shovels, splash water), burning arrows lighting
  it, beehives calmed by its smoke.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos, below
from redsim.world.block import BlockState
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.blocks.catalog import CatalogBlock, horizontal_direction
from redsim.world.blocks.catalog_data import BLOCKS
from redsim.world.properties import HORIZONTAL_FACING, LIT, WATERLOGGED, boolean
from redsim.world.shape import box

if TYPE_CHECKING:
    from redsim.sim.level import Level

SIGNAL_FIRE = boolean("signal_fire")
CAMPFIRE_IDS = ("minecraft:campfire", "minecraft:soul_campfire")
SHAPE = box(0, 0, 0, 16, 7, 16)  # Block.column(16, 0, 7)
SLOTS = 4


class CampfireBlock(CatalogBlock):
    properties = (LIT, SIGNAL_FIRE, WATERLOGGED, HORIZONTAL_FACING)
    has_block_entity = True
    has_ticker = True

    def __init__(self, block_id: str, spec: tuple[Any, ...] | None = None) -> None:
        super().__init__(block_id, spec if spec is not None else BLOCKS[block_id], shape=SHAPE)
        self.register_default_state(
            self.default_state.with_(LIT, True)
            .with_(SIGNAL_FIRE, False)
            .with_(WATERLOGGED, False)
            .with_(HORIZONTAL_FACING, Direction.NORTH)
        )

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return CampfireBlockEntity(pos, state)

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        """``getStateForPlacement``: unlit and waterlogged in water, a signal fire on hay,
        facing the way the player looks."""
        from redsim.sim.entities import _is_water

        water = _is_water(level.get_block_state(pos))
        return (
            self.default_state.with_(WATERLOGGED, water)
            .with_(SIGNAL_FIRE, _is_smoke_source(level.get_block_state(below(pos))))
            .with_(LIT, not water)
            .with_(HORIZONTAL_FACING, horizontal_direction(request.yaw))
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
        """``updateShape``: ``signal_fire`` follows the block below."""
        # Not as in the game: a waterlogged campfire also schedules a water tick here
        # (water is not simulated, so its water never flows).
        if direction is Direction.DOWN:
            return state.with_(SIGNAL_FIRE, _is_smoke_source(neighbor))
        return state


def _is_smoke_source(state: BlockState) -> bool:
    return state.block.id == "minecraft:hay_block"


class CampfireBlockEntity(BlockEntity):
    type_id = "campfire"
    valid_blocks = frozenset(CAMPFIRE_IDS)

    def __init__(self, pos: Pos, state: BlockState) -> None:
        super().__init__(pos, state)
        self.items: list[tuple[str, int] | None] = [None] * SLOTS
        self.cooking_progress = [0] * SLOTS  # CookingTimes
        self.cooking_time = [0] * SLOTS  # CookingTotalTimes

    def clone(self) -> BlockEntity:
        other = super().clone()
        assert isinstance(other, CampfireBlockEntity)
        other.items = list(self.items)
        other.cooking_progress = list(self.cooking_progress)
        other.cooking_time = list(self.cooking_time)
        return other

    def tick(self, level: Level, pos: Pos, state: BlockState) -> None:
        """The ticker of ``getTicker``: ``cookTick`` while lit, ``cooldownTick`` while not
        (the game swaps the ticker when ``lit`` changes)."""
        changed = False
        if state.get(LIT):
            for slot in range(SLOTS):
                if self.items[slot] is not None:
                    changed = True
                    self.cooking_progress[slot] += 1
                    if self.cooking_progress[slot] >= self.cooking_time[slot]:
                        # Not as in the game: the game drops the cooked result as an
                        # item entity here (Containers.dropItemStack); no items here.
                        self.items[slot] = None
        else:
            for slot in range(SLOTS):
                if self.cooking_progress[slot] > 0:
                    changed = True
                    self.cooking_progress[slot] = min(
                        max(self.cooking_progress[slot] - 2, 0), self.cooking_time[slot]
                    )
        if changed:  # BlockEntity.setChanged(level, pos, state)
            level.update_neighbour_for_output_signal(pos, state.block)

    def to_json(self) -> dict[str, Any]:
        return {
            "Items": [
                {"Slot": slot, "id": stack[0], "count": stack[1]}
                for slot, stack in enumerate(self.items)
                if stack is not None
            ],
            "CookingTimes": list(self.cooking_progress),
            "CookingTotalTimes": list(self.cooking_time),
        }

    def load_json(self, data: dict[str, Any]) -> None:
        self.items = [None] * SLOTS
        for entry in data.get("Items", []):
            slot = int(entry["Slot"])
            if 0 <= slot < SLOTS and int(entry.get("count", 1)) > 0:
                self.items[slot] = (str(entry["id"]), int(entry.get("count", 1)))
        # loadAdditional: a given array is copied over the current one (System.arraycopy,
        # the rest stays); a missing one is filled with zeros.
        for key, target in (("CookingTimes", self.cooking_progress),
                            ("CookingTotalTimes", self.cooking_time)):  # fmt: skip
            values = data.get(key)
            if values is None:
                target[:] = [0] * SLOTS
            else:
                for i, value in enumerate(list(values)[:SLOTS]):
                    target[i] = int(value)

    def contents(self) -> str:
        """``slot:id*count`` for every filled slot (as ``ContainerBlockEntity.contents``)."""
        return " ".join(
            f"{slot}:{stack[0]}*{stack[1]}" for slot, stack in enumerate(self.items) if stack
        )


# Registered here, not with a class decorator (classes stay compilable by mypyc).
register_block_entity(CampfireBlockEntity)
