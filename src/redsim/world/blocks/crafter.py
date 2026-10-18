"""Crafters: a 3×3 container that crafts when powered. In redstone builds they matter as a
block whose state (``triggered``) changes when power reaches it, which observers see, and as
a comparator source (filled or disabled slots).

Sources (relative to ``data/minecraft_src/server-src/net/minecraft/world/level/block/``):

* ``CrafterBlock.java``: ``orientation`` (``FrontAndTop``), ``triggered``, ``crafting``;
  ``neighborChanged`` (rising power: ``triggered`` with flags 2, so shape updates but no
  neighbor updates, and a craft attempt 4 ticks later; falling power: untriggered),
  ``tick`` → ``dispenseFrom``, ``getStateForPlacement``, ``setPlacedBy``, comparator
  output, ``affectNeighborsAfterRemoval``, ``rotate``/``mirror``.
* ``entity/CrafterBlockEntity.java``: nine slots, disabled slots and ``triggered``
  (``containerData``), ``crafting_ticks_remaining`` (the ticker turns ``crafting`` off),
  ``getRedstoneSignal`` (slots that hold an item or are disabled), ``setItem`` (enables a
  disabled slot), saved keys.
* ``Blocks.java``: a full block (it conducts), a block entity (pistons cannot move it).

Not as in the game (doc/differences.md): crafting recipes are not simulated, so a craft
attempt always fails, as in the game with an empty grid or one that matches no recipe (the
game then only plays a sound); a crafter holding a recipe would craft, push the result out
and use up one of each ingredient there. Hoppers and droppers leave crafters alone (in the
game they fill the slots one item at a time, evenly).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.world.block import Block, BlockState, PlacementContext
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.blocks.catalog import CatalogBlock
from redsim.world.blocks.container import ContainerBlockEntity, set_changed
from redsim.world.properties import Property, boolean

if TYPE_CHECKING:
    from redsim.sim.level import Level

TRIGGERED = boolean("triggered")
CRAFTING = boolean("crafting")
#: ``FrontAndTop`` in enum order: (name, front, top).
FRONT_AND_TOP = (
    ("down_east", Direction.DOWN, Direction.EAST),
    ("down_north", Direction.DOWN, Direction.NORTH),
    ("down_south", Direction.DOWN, Direction.SOUTH),
    ("down_west", Direction.DOWN, Direction.WEST),
    ("up_east", Direction.UP, Direction.EAST),
    ("up_north", Direction.UP, Direction.NORTH),
    ("up_south", Direction.UP, Direction.SOUTH),
    ("up_west", Direction.UP, Direction.WEST),
    ("west_up", Direction.WEST, Direction.UP),
    ("east_up", Direction.EAST, Direction.UP),
    ("north_up", Direction.NORTH, Direction.UP),
    ("south_up", Direction.SOUTH, Direction.UP),
)
ORIENTATION = Property("orientation", tuple(name for name, _, _ in FRONT_AND_TOP))
_BY_NAME = {name: (front, top) for name, front, top in FRONT_AND_TOP}
_BY_PAIR = {(front, top): name for name, front, top in FRONT_AND_TOP}
#: ``CRAFTING_TICK_DELAY``.
CRAFTING_TICK_DELAY = 4
SIZE = 9


def front_and_top(front: Direction, top: Direction) -> str:
    """``FrontAndTop.fromFrontAndTop``."""
    return _BY_PAIR[(front, top)]


class CrafterBlockEntity(ContainerBlockEntity):
    """``CrafterBlockEntity``."""

    type_id = "crafter"
    valid_blocks = frozenset({"minecraft:crafter"})
    SIZE = SIZE
    NAME = "crafter"

    def __init__(self, pos: Pos, state: BlockState) -> None:
        super().__init__(pos, state)
        self.disabled = [False] * SIZE
        self.triggered = 0
        self.crafting_ticks_remaining = 0

    def clone(self) -> BlockEntity:
        other = super().clone()
        assert isinstance(other, CrafterBlockEntity)
        other.disabled = list(self.disabled)
        return other

    def get_redstone_signal(self) -> int:
        """``getRedstoneSignal``: slots holding an item or disabled."""
        return sum(1 for slot in range(SIZE) if self.items[slot] is not None or self.disabled[slot])

    def signal(self) -> int:
        return self.get_redstone_signal()

    def slot_can_be_disabled(self, slot: int) -> bool:
        return 0 <= slot < SIZE and self.items[slot] is None

    def set_slot_state(self, level: Level | None, slot: int, enabled: bool) -> None:
        """``setSlotState`` (a player clicking a slot in its menu)."""
        if self.slot_can_be_disabled(slot):
            self.disabled[slot] = not enabled
            if level is not None:
                set_changed(self, level)

    def set_item(self, level: Level, slot: int, stack: tuple[str, int] | None) -> None:
        """``setItem``: a disabled slot is enabled first (only while it is empty)."""
        if 0 <= slot < SIZE and self.disabled[slot]:
            self.set_slot_state(level, slot, True)
        super().set_item(level, slot, stack)

    def tick(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``serverTick``: after a craft, ``crafting`` turns off 6 ticks later."""
        remaining = self.crafting_ticks_remaining - 1
        if remaining >= 0:
            self.crafting_ticks_remaining = remaining
            if remaining == 0:
                level.set_block_and_update(pos, state.with_(CRAFTING, False))

    def to_json(self) -> dict[str, Any]:
        return {
            "crafting_ticks_remaining": self.crafting_ticks_remaining,
            **super().to_json(),
            "disabled_slots": [slot for slot in range(SIZE) if self.disabled[slot]],
            "triggered": self.triggered,
        }

    def load_json(self, data: dict[str, Any]) -> None:
        super().load_json(data)
        self.crafting_ticks_remaining = int(data.get("crafting_ticks_remaining", 0))
        self.disabled = [False] * SIZE
        for slot in data.get("disabled_slots", []):
            if self.slot_can_be_disabled(int(slot)):
                self.disabled[int(slot)] = True
        self.triggered = int(data.get("triggered", 0))

    def describe(self) -> str:
        disabled = sum(self.disabled)
        extra = f", {disabled} disabled" if disabled else ""
        return f"{super().describe()}{extra}"


class CrafterBlock(CatalogBlock):
    """``CrafterBlock``."""

    properties = (ORIENTATION, TRIGGERED, CRAFTING)
    has_block_entity = True
    has_ticker = True

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(
            self.default_state.with_(ORIENTATION, "north_up")
            .with_(TRIGGERED, False)
            .with_(CRAFTING, False)
        )

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        entity = CrafterBlockEntity(pos, state)
        entity.triggered = 1 if state.has(TRIGGERED) and state.get(TRIGGERED) else 0
        return entity

    # --- placement ----------------------------------------------------------------------
    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement``: the given orientation, ``triggered`` if powered."""
        return self.default_state.with_(ORIENTATION, ctx.requested.get(ORIENTATION)).with_(
            TRIGGERED, ctx.level.has_neighbor_signal(ctx.pos)
        )

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        """``getStateForPlacement``: the front faces the player; the top is up, or, placed
        looking up or down, the way the player faces."""
        from redsim.editor.placement import horizontal_direction, ordered_by_nearest

        front = ordered_by_nearest(request.yaw, request.pitch)[0].opposite
        facing = horizontal_direction(request.yaw)
        top = (
            facing.opposite
            if front is Direction.DOWN
            else facing
            if front is Direction.UP
            else Direction.UP
        )
        requested = self.default_state.with_(ORIENTATION, front_and_top(front, top))
        return self.get_state_for_placement(PlacementContext(level, pos, requested))

    def set_placed_by(self, level: Level, pos: Pos, state: BlockState) -> None:
        if state.get(TRIGGERED):
            level.schedule_tick(pos, self, CRAFTING_TICK_DELAY)

    # --- redstone -----------------------------------------------------------------------
    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        should_trigger = level.has_neighbor_signal(pos)
        is_triggered = bool(state.get(TRIGGERED))
        entity = level.get_block_entity(pos)
        if should_trigger and not is_triggered:
            level.schedule_tick(pos, self, CRAFTING_TICK_DELAY)
            level.set_block(pos, state.with_(TRIGGERED, True), 2)
            if isinstance(entity, CrafterBlockEntity):
                entity.triggered = 1
        elif not should_trigger and is_triggered:
            level.set_block(pos, state.with_(TRIGGERED, False).with_(CRAFTING, False), 2)
            if isinstance(entity, CrafterBlockEntity):
                entity.triggered = 0

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``dispenseFrom``. Not as in the game: no recipe is ever found (recipes are not
        simulated), so the attempt fails (``levelEvent`` 1050: a sound)."""
        return None

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        entity = level.get_block_entity(pos)
        return entity.get_redstone_signal() if isinstance(entity, CrafterBlockEntity) else 0

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        """``Containers.updateNeighboursAfterDestroy``: comparators around it update."""
        level.update_neighbour_for_output_signal(pos, self)

    # --- turning ------------------------------------------------------------------------
    def rotated(self, state: BlockState, quarter_turns: int) -> BlockState:
        """``rotate``: front and top turn clockwise (seen from above)."""
        front, top = _BY_NAME[state.get(ORIENTATION)]
        for _ in range(quarter_turns % 4):
            front = front.clockwise() if front.is_horizontal else front
            top = top.clockwise() if top.is_horizontal else top
        return state.with_(ORIENTATION, front_and_top(front, top))

    def mirrored(self, state: BlockState, axis: str) -> BlockState:
        """``mirror``: ``"x"`` (FRONT_BACK, ``INVERT_X``) swaps east and west, ``"z"``
        (LEFT_RIGHT, ``INVERT_Z``) north and south, for front and top."""
        flipped = Direction.EAST if axis == "x" else Direction.SOUTH
        front, top = _BY_NAME[state.get(ORIENTATION)]
        if front.axis is flipped.axis:
            front = front.opposite
        if top.axis is flipped.axis:
            top = top.opposite
        return state.with_(ORIENTATION, front_and_top(front, top))


def is_crafter(entity: BlockEntity | None) -> bool:
    return isinstance(entity, CrafterBlockEntity)


# Registered here, not with a class decorator (classes stay compilable by mypyc).
register_block_entity(CrafterBlockEntity)
