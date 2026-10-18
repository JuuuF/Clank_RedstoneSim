"""Tripwire hooks and tripwire (string): a hook on each end of a line of tripwire; an
entity in the wire powers both hooks.

Sources (relative to ``data/minecraft_src/server-src/net/minecraft/world/level/block/``):

* ``TripWireHookBlock.java``: ``canSurvive`` (a sturdy face behind it), ``updateShape``
  (breaks when that block goes), ``getStateForPlacement`` (the nearest horizontal looking
  direction, reversed, that survives), ``setPlacedBy`` and ``tick`` → ``calculateState``
  (scan up to 41 blocks along ``facing`` for the other hook, set both hooks and, when
  ``attached`` changed, every wire between), ``notifyNeighbors`` (the hook and the block it
  hangs on), ``onRemoved``, signals (15; strong power only into its block).
* ``TripWireBlock.java``: connections to wire and to hooks facing it (``updateShape``),
  ``onPlace`` / ``affectNeighborsAfterRemoval`` → ``updateSource`` (the hooks to the south
  and west run ``calculateState``; a removed wire counts as powered), ``entityInside``,
  ``tick`` and ``checkPressed`` (pressed while an entity is in its shape, rechecked every
  10 ticks, released 1 tick after the last check that found none), shears disarm it
  (``playerWillDestroy``).
* ``Blocks.java``: both ``noCollision``, ``pushReaction(POPPED)``, instant to break.

Entities: falling blocks are real entities (``sim/entities.py``) and trigger a wire whose
shape they pass (``getEntityInsideCollisionShape`` is the wire's shape). Mobs and items are
editor *visitors* (``Level.plate_visitors``, the ``plate`` command), as on pressure plates:
any visitor presses the wire (no entity the editor stands in for ignores block triggers).

Not as in the game (doc/differences.md): sounds and the game events of hooks
(``emitState``: click, attach, detach; ``BLOCK_ACTIVATE`` …, heard by sculk sensors) are
left out, they change no block. The attached wire's shape is 1 to 2.5 pixels high; the
whole-pixel shape grid holds 1 to 3 (drawing and picking only: entity checks use the exact
box, the wire has no collision).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos, offset
from redsim.world.block import BlockState, PlacementContext, UpdateFlags
from redsim.world.blocks.connecting import SIDES
from redsim.world.blocks.openable import _GameBlock, box_z, rotate_horizontal
from redsim.world.properties import HORIZONTAL_FACING, POWERED, boolean
from redsim.world.shape import EMPTY, Shape, column

if TYPE_CHECKING:
    from redsim.sim.level import Level

ATTACHED = boolean("attached")
DISARMED = boolean("disarmed")
FACING = HORIZONTAL_FACING
#: ``TripWireHookBlock.WIRE_DIST_MAX``: hooks see wire up to 41 blocks away.
WIRE_DIST_MAX = 42
#: ``RECHECK_PERIOD``: a pressed wire, and a hook after a wire change, recheck after 10.
RECHECK_PERIOD = 10

#: ``TripWireHookBlock.SHAPES``.
HOOK_SHAPES = rotate_horizontal(box_z(6, 0, 10, 10, 16))
#: ``TripWireBlock.SHAPE_ATTACHED`` / ``SHAPE_NOT_ATTACHED`` as exact boxes in block units
#: (entity checks).
Box = tuple[float, float, float, float, float, float]
BOX_ATTACHED: Box = (0.0, 1.0 / 16.0, 0.0, 1.0, 2.5 / 16.0, 1.0)
BOX_NOT_ATTACHED: Box = (0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
#: Not as in the game: the attached shape is 2.5 pixels high, the pixel grid holds 3.
SHAPE_ATTACHED = column(16, 1, 3)
SHAPE_NOT_ATTACHED = column(16, 0, 8)


class TripWireHookBlock(_GameBlock):
    """``TripWireHookBlock``: ``facing`` points from the block it hangs on toward the wire."""

    properties = (FACING, POWERED, ATTACHED)

    def __init__(self) -> None:
        super().__init__("minecraft:tripwire_hook")
        self.has_collision = False
        self.register_default_state(
            self.default_state.with_(FACING, Direction.NORTH)
            .with_(POWERED, False)
            .with_(ATTACHED, False)
        )

    def get_shape(self, state: BlockState) -> Shape:
        return HOOK_SHAPES[state.get(FACING)]

    def get_collision_shape(self, state: BlockState) -> Shape:
        return EMPTY

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``canSurvive``: the block behind has a sturdy face toward the hook."""
        direction: Direction = state.get(FACING)
        relative = offset(pos, direction.opposite)
        return direction.is_horizontal and level.get_block_state(relative).is_face_sturdy(
            level, relative, direction
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
        """``updateShape``: breaks when the block it hangs on no longer holds it."""
        if direction.opposite is state.get(FACING) and not state.can_survive(level, pos):
            return level.air
        return state

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement``: unpowered, unattached, with the given ``facing`` (the
        engine refuses it without support)."""
        return ctx.requested.with_(POWERED, False).with_(ATTACHED, False)

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        """``getStateForPlacement``: the first horizontal one of the nearest looking
        directions, reversed, at which the hook survives."""
        from redsim.editor.placement import nearest_looking_directions

        state = self.default_state
        for direction in nearest_looking_directions(request):
            if direction.is_horizontal:
                state = state.with_(FACING, direction.opposite)
                if state.can_survive(level, pos):
                    return state
        return None

    def set_placed_by(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``setPlacedBy``: a placed hook looks for its wire at once."""
        calculate_state(level, pos, state, False, False, -1, None)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``tick`` (10 ticks after a wire on its line changed)."""
        calculate_state(level, pos, state, False, True, -1, None)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        if not moved_by_piston:
            on_removed(state, level, pos)

    # --- signals ------------------------------------------------------------------------
    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return 15 if state.get(POWERED) else 0

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        """``getDirectSignal``: strong power only into the block it hangs on."""
        return 15 if state.get(POWERED) and state.get(FACING) is direction else 0


def calculate_state(
    level: Level,
    pos: Pos,
    state: BlockState,
    is_being_destroyed: bool,
    can_update: bool,
    wire_source: int,
    wire_source_state: BlockState | None,
) -> None:
    """``TripWireHookBlock.calculateState``: find the hook across the wire, decide
    ``attached`` (an unbroken, armed line to a hook facing back, at least 2 blocks away)
    and ``powered`` (some armed wire on it is powered), set both hooks, and the wires'
    ``attached`` when it changed. ``wire_source``: the distance of the wire that changed
    (its new state ``wire_source_state``), which makes the hook recheck in 10 ticks."""
    if not state.has(FACING):
        return
    direction: Direction = state.get(FACING)
    was_attached = bool(state.get(ATTACHED)) if state.has(ATTACHED) else False
    # (wasPowered only chooses emitState's sound.)
    block = state.block
    attached = not is_being_destroyed
    powered = False
    receiver_pos = 0
    wire_states: list[BlockState | None] = [None] * WIRE_DIST_MAX
    for i in range(1, WIRE_DIST_MAX):
        test_pos = offset(pos, direction, i)
        wire_state = level.get_block_state(test_pos)
        if isinstance(wire_state.block, TripWireHookBlock):
            if wire_state.get(FACING) is direction.opposite:
                receiver_pos = i
            break
        if not isinstance(wire_state.block, TripWireBlock) and i != wire_source:
            wire_states[i] = None
            attached = False
        else:
            if i == wire_source and wire_source_state is not None:
                wire_state = wire_source_state  # MoreObjects.firstNonNull
            wire_armed = not wire_state.get(DISARMED)
            wire_powered = bool(wire_state.get(POWERED))
            powered |= wire_armed and wire_powered
            wire_states[i] = wire_state
            if i == wire_source:
                level.schedule_tick(pos, block, RECHECK_PERIOD)
                attached &= wire_armed
    attached &= receiver_pos > 1
    powered &= attached
    new_state = block.default_state.with_(ATTACHED, attached).with_(POWERED, powered)
    if receiver_pos > 0:
        test_pos = offset(pos, direction, receiver_pos)
        opposite = direction.opposite
        level.set_block_and_update(test_pos, new_state.with_(FACING, opposite))
        notify_neighbors(block, level, test_pos, opposite)
        if not isinstance(level.get_block_state(pos).block, TripWireHookBlock):
            # The hook itself is gone (its update broke it): ``onRemoved`` with the new
            # state, whose ``facing`` is the default (north), as in the game.
            on_removed(new_state, level, pos)
            return
        # (emitState at the other hook: sounds and game events only.)
    # (emitState here: sounds and game events only.)
    if not is_being_destroyed:
        level.set_block_and_update(pos, new_state.with_(FACING, direction))
        if can_update:
            notify_neighbors(block, level, pos, direction)
    if was_attached != attached:
        for i in range(1, receiver_pos):
            test_pos = offset(pos, direction, i)
            wire_data = wire_states[i]
            if wire_data is not None:
                current = level.get_block_state(test_pos)
                if isinstance(current.block, (TripWireBlock, TripWireHookBlock)):
                    level.set_block_and_update(test_pos, wire_data.with_(ATTACHED, attached))


def notify_neighbors(block: Any, level: Level, pos: Pos, direction: Direction) -> None:
    """``TripWireHookBlock.notifyNeighbors``: around the hook and around its block."""
    front = direction.opposite
    level.update_neighbors_at(pos, block)
    level.update_neighbors_at(offset(pos, front), block)


def on_removed(state: BlockState, level: Level, pos: Pos) -> None:
    """``TripWireHookBlock.onRemoved``: detach the line, and update the neighbors if the
    hook was powered."""
    attached = bool(state.get(ATTACHED))
    powered = bool(state.get(POWERED))
    if attached or powered:
        calculate_state(level, pos, state, True, False, -1, None)
    if powered:
        notify_neighbors(state.block, level, pos, state.get(FACING))


class TripWireBlock(_GameBlock):
    """``TripWireBlock`` (placed with string): ``attached`` while it is part of a line
    between two hooks, ``powered`` while an entity is in it, ``disarmed`` once cut with
    shears; the four sides connect to wire and to hooks facing it."""

    properties = (
        POWERED, ATTACHED, DISARMED, SIDES[Direction.NORTH], SIDES[Direction.EAST],
        SIDES[Direction.WEST], SIDES[Direction.SOUTH],
    )  # fmt: skip

    def __init__(self, hook: TripWireHookBlock) -> None:
        super().__init__("minecraft:tripwire")
        self.has_collision = False
        self.hook = hook
        state = self.default_state.with_(POWERED, False).with_(ATTACHED, False)
        state = state.with_(DISARMED, False)
        for prop in SIDES.values():
            state = state.with_(prop, False)
        self.register_default_state(state)

    def get_shape(self, state: BlockState) -> Shape:
        return SHAPE_ATTACHED if state.get(ATTACHED) else SHAPE_NOT_ATTACHED

    def get_collision_shape(self, state: BlockState) -> Shape:
        return EMPTY

    def entity_inside_boxes(self, state: BlockState) -> tuple[Box, ...]:
        """``getEntityInsideCollisionShape`` = the wire's shape, exactly (block units)."""
        return (BOX_ATTACHED if state.get(ATTACHED) else BOX_NOT_ATTACHED,)

    def should_connect_to(self, neighbor: BlockState, direction: Direction) -> bool:
        """``shouldConnectTo``: wire, or a hook facing this way."""
        if neighbor.is_(self.hook):
            return neighbor.get(FACING) is direction.opposite
        return neighbor.is_(self)

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement``: the default state, connected to its neighbors."""
        state = self.default_state
        for direction, prop in SIDES.items():
            neighbor = ctx.level.get_block_state(offset(ctx.pos, direction))
            state = state.with_(prop, self.should_connect_to(neighbor, direction))
        return state

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        return self.get_state_for_placement(PlacementContext(level, pos, self.default_state))

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction.is_horizontal:
            return state.with_(SIDES[direction], self.should_connect_to(neighbor, direction))
        return state

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        if not old_state.is_(self):
            self.update_source(level, pos, state)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        """A removed wire tells its hooks it was powered (so breaking it, or a piston
        popping it, triggers them), unless it was disarmed."""
        if not moved_by_piston:
            self.update_source(level, pos, state.with_(POWERED, True))

    def shear(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``playerWillDestroy`` with shears in the main hand: disarmed first (flags 260:
        no neighbor or shape updates), so the removal does not trigger the hooks."""
        level.set_block(
            pos,
            state.with_(DISARMED, True),
            UpdateFlags.INVISIBLE | UpdateFlags.SKIP_BLOCK_ENTITY_SIDEEFFECTS,
        )

    def update_source(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``updateSource``: the hooks south and west of the wire (facing it) recalculate,
        each over the whole line."""
        for direction in (Direction.SOUTH, Direction.WEST):
            for i in range(1, WIRE_DIST_MAX):
                test_pos = offset(pos, direction, i)
                block = level.get_block_state(test_pos)
                if block.is_(self.hook):
                    if block.get(FACING) is direction.opposite:
                        calculate_state(level, test_pos, block, False, True, i, state)
                    break
                if not block.is_(self):
                    break

    # --- entities -----------------------------------------------------------------------
    def entity_inside(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``entityInside`` of an editor visitor."""
        if not state.get(POWERED) and not level.has_scheduled_tick(pos, self):
            self.check_pressed(level, pos, True)

    def entity_inside_entity(
        self, state: BlockState, level: Level, pos: Pos, entity: object
    ) -> None:
        """``entityInside`` of a simulated entity (a falling block)."""
        self.entity_inside(state, level, pos)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        if level.get_block_state(pos).get(POWERED):
            self.check_pressed(level, pos, self.has_entities(level, pos))

    def has_entities(self, level: Level, pos: Pos) -> bool:
        """``level.getEntities(null, shape.bounds().move(pos))`` holds one that does not
        ignore block triggers: a visitor, or a falling block in the wire's box."""
        mobs, others = level.visitors_at(pos)
        if mobs + others > 0:
            return True
        if not level.entities:
            return False
        from redsim.sim.entities import entities_in

        x0, y0, z0, x1, y1, z1 = self.entity_inside_boxes(level.get_block_state(pos))[0]
        x, y, z = pos
        return bool(entities_in(level, (x + x0, y + y0, z + z0, x + x1, y + y1, z + z1)))

    def check_pressed(self, level: Level, pos: Pos, should_be_pressed: bool) -> None:
        """``checkPressed``: set ``powered`` (and tell the hooks) when it changes; recheck
        in 10 ticks while pressed, once more 1 tick after it was released."""
        state = level.get_block_state(pos)
        was_pressed = bool(state.get(POWERED))
        if should_be_pressed != was_pressed:
            state = state.with_(POWERED, should_be_pressed)
            level.set_block_and_update(pos, state)
            self.update_source(level, pos, state)
        if should_be_pressed:
            level.schedule_tick(pos, self, RECHECK_PERIOD)
        elif was_pressed:
            level.schedule_tick(pos, self, 1)

    def rotated(self, state: BlockState, quarter_turns: int) -> BlockState:
        """``rotate``: each side's value moves to the side turned clockwise."""
        out = state
        for direction, prop in SIDES.items():
            turned = direction
            for _ in range(quarter_turns % 4):
                turned = turned.clockwise()
            out = out.with_(SIDES[turned], state.get(prop))
        return out

    def mirrored(self, state: BlockState, axis: str) -> BlockState:
        """``mirror``: ``"x"`` (FRONT_BACK) swaps east and west, ``"z"`` north and south."""
        a, b = (
            (Direction.EAST, Direction.WEST) if axis == "x" else (Direction.NORTH, Direction.SOUTH)
        )
        return state.with_(SIDES[a], state.get(SIDES[b])).with_(SIDES[b], state.get(SIDES[a]))
