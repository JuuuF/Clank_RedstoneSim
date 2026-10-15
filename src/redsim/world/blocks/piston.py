"""Pistons: base, head, moving piston (B36) with its block entity, and the structure resolver.

Source (relative to ``data/minecraft_src/client-src/net/minecraft/world/level/block/piston/``):

* ``PistonBaseBlock.java``: ``setPlacedBy`` L64, ``neighborChanged`` L71, ``onPlace`` L80,
  ``getStateForPlacement`` L89, ``checkIfExtend`` L93, ``getNeighborSignal`` L116,
  ``triggerEvent`` L139, ``isPushable`` L213, ``moveBlocks`` L257.
* ``PistonStructureResolver.java``: ``resolve`` L37, ``canStickToEachOther`` L68,
  ``addBlockLine`` L76, ``reorderListAtCollision`` L164, ``addBranchingBlocks`` L177.
* ``PistonMovingBlockEntity.java``: ``finalTick`` L259, ``tick`` L291, ``getCollisionShape``.
* ``MovingPistonBlock.java`` (``destroy`` L68, ``useWithoutItem`` L77) and
  ``PistonHeadBlock.java`` (``isFittingBase`` L57, ``affectNeighborsAfterRemoval`` L75,
  ``updateShape`` L83, ``canSurvive`` L99, ``neighborChanged`` L105).

Entity pushing is out of scope. See doc/mechanics/pistons.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import ALL, Direction
from redsim.core.javahash import JavaHashMap
from redsim.core.pos import Pos, above, java_hash, offset
from redsim.sim import trace as tr
from redsim.world import ids
from redsim.world.block import (
    Block,
    BlockState,
    Conductor,
    PlacementContext,
    PushReaction,
    UpdateFlags,
)
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.properties import EXTENDED, FACING, PISTON_TYPE, SHORT
from redsim.world.shape import EMPTY, FULL_BLOCK, Shape, facing_box

if TYPE_CHECKING:
    from redsim.sim.level import Level

TRIGGER_EXTEND = 0
TRIGGER_CONTRACT = 1
TRIGGER_DROP = 2
MAX_PUSH_DEPTH = 12


def piston_facing(state: BlockState) -> Direction:
    value: Direction = state.get(FACING)
    return value


def _is_piston_base(state: BlockState) -> bool:
    return state.block.id in (ids.PISTON, ids.STICKY_PISTON)


# ============================================================================ base
class PistonBaseBlock(Block):
    properties = (FACING, EXTENDED)

    def __init__(self, sticky: bool) -> None:
        super().__init__(
            ids.STICKY_PISTON if sticky else ids.PISTON,
            push_reaction=PushReaction.IMMOVEABLE,
            conductor=Conductor.NEVER,
            destroy_speed=1.5,
        )
        self.is_sticky = sticky
        self.register_default_state(
            self.default_state.with_(FACING, Direction.NORTH).with_(EXTENDED, False)
        )

    def get_shape(self, state: BlockState) -> Shape:
        if state.get(EXTENDED):
            return facing_box(piston_facing(state), 16, 4, 16)
        return FULL_BLOCK

    # --- placement and updates -------------------------------------------------------
    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.default_state.with_(FACING, piston_facing(ctx.requested)).with_(EXTENDED, False)

    def set_placed_by(self, level: Level, pos: Pos, state: BlockState) -> None:
        self.check_if_extend(level, pos, state)

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        self.check_if_extend(level, pos, state)

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        if not old_state.is_(state.block) and level.get_block_entity(pos) is None:
            self.check_if_extend(level, pos, state)

    def check_if_extend(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``checkIfExtend`` L93."""
        direction = piston_facing(state)
        extend = self.get_neighbor_signal(level, pos, direction)
        if extend and not state.get(EXTENDED):
            if PistonStructureResolver(level, pos, direction, True).resolve():
                if level.trace.enabled:  # for "why did this change?" (not game logic)
                    self._trace_power(level, pos, direction)
                level.block_event(pos, self, TRIGGER_EXTEND, direction.data3d)
        elif not extend and state.get(EXTENDED):
            pushed_pos = offset(pos, direction, 2)
            pushed = level.get_block_state(pushed_pos)
            event = TRIGGER_CONTRACT
            if pushed.block.id == ids.MOVING_PISTON and piston_facing(pushed) is direction:
                entity = level.get_block_entity(pushed_pos)
                if (
                    isinstance(entity, PistonMovingBlockEntity)
                    and entity.extending
                    and (
                        entity.progress_o < 0.5  # getProgress(0.0F) == progressO
                        or level.game_time == entity.last_ticked
                        or level.handling_tick
                    )
                ):
                    event = TRIGGER_DROP
            level.block_event(pos, self, event, direction.data3d)

    def get_neighbor_signal(self, level: Level, pos: Pos, push_direction: Direction) -> bool:
        """``getNeighborSignal`` L116, including quasi-connectivity."""
        for direction in ALL:
            if direction is not push_direction and level.has_signal(
                offset(pos, direction), direction
            ):
                return True
        if level.has_signal(pos, Direction.DOWN):
            return True
        up = above(pos)
        for direction in ALL:
            if direction is not Direction.DOWN and level.has_signal(
                offset(up, direction), direction
            ):
                return True
        return False

    def signal_neighbor(
        self, level: Level, pos: Pos, push_direction: Direction
    ) -> tuple[Pos, Direction, bool] | None:
        """The neighbor that makes ``get_neighbor_signal`` true (same order): its position,
        the direction asked, and whether it is reached through the block above the piston
        (quasi-connectivity). Not game logic: for the "why?" trace."""
        for direction in ALL:
            neighbor = offset(pos, direction)
            if direction is not push_direction and level.has_signal(neighbor, direction):
                return neighbor, direction, False
        if level.has_signal(pos, Direction.DOWN):
            return pos, Direction.DOWN, False
        up = above(pos)
        for direction in ALL:
            neighbor = offset(up, direction)
            if direction is not Direction.DOWN and level.has_signal(neighbor, direction):
                return neighbor, direction, True
        return None

    def _trace_power(self, level: Level, pos: Pos, push_direction: Direction) -> None:
        """A trace note of where the power that extends the piston comes from: the block
        giving the signal and, for a powered block, what powers it."""
        found = self.signal_neighbor(level, pos, push_direction)
        if found is None:
            return
        via, direction, quasi = found
        via_state = level.get_block_state(via)
        sources: list[tuple[Pos, str]] = []
        asking = offset(via, direction.opposite)  # the piston, or the block above it
        if level.forced_power and asking in level.forced_power:
            sources.append((asking, "sequence power"))
        elif via_state.get_signal(level, via, direction) <= 0 and via_state.is_redstone_conductor(
            level, via
        ):
            for side in ALL:
                emitter = offset(via, side)
                if level.get_direct_signal(emitter, side) > 0:
                    sources.append((emitter, level.get_block_state(emitter).block.id))
        level.trace.emit(
            tr.NOTE,
            pos,
            kind="piston_power",
            via=via,
            via_block=via_state.block.id,
            quasi=quasi,
            sources=sources,
        )

    # --- block events --------------------------------------------------------------------
    def trigger_event(self, state: BlockState, level: Level, pos: Pos, b0: int, b1: int) -> bool:
        """``triggerEvent`` L139."""
        from redsim.world import blocks

        direction = piston_facing(state)
        extended_state = state.with_(EXTENDED, True)
        extend = self.get_neighbor_signal(level, pos, direction)
        if extend and b0 in (TRIGGER_CONTRACT, TRIGGER_DROP):
            level.set_block(pos, extended_state, UpdateFlags.CLIENTS)
            return False
        if not extend and b0 == TRIGGER_EXTEND:
            return False

        if b0 == TRIGGER_EXTEND:
            if not self.move_blocks(level, pos, direction, True):
                return False
            level.set_block(pos, extended_state, 67)
        elif b0 in (TRIGGER_CONTRACT, TRIGGER_DROP):
            head_entity = level.get_block_entity(offset(pos, direction))
            if isinstance(head_entity, PistonMovingBlockEntity):
                head_entity.final_tick(level)
            moving_state = blocks.MOVING_PISTON.default_state.with_(FACING, direction).with_(
                PISTON_TYPE, "sticky" if self.is_sticky else "normal"
            )
            level.set_block(pos, moving_state, 276)
            level.set_block_entity(
                PistonMovingBlockEntity(
                    pos,
                    moving_state,
                    self.default_state.with_(FACING, Direction.from_data3d(b1 & 7)),
                    direction,
                    extending=False,
                    is_source=True,
                )
            )
            level.update_neighbors_at(pos, moving_state.block)
            moving_state.update_neighbour_shapes(level, pos, UpdateFlags.CLIENTS)
            if self.is_sticky:
                two_pos = offset(pos, direction, 2)
                moving = level.get_block_state(two_pos)
                piston_piece = False
                if moving.block.id == ids.MOVING_PISTON:
                    entity = level.get_block_entity(two_pos)
                    if (
                        isinstance(entity, PistonMovingBlockEntity)
                        and entity.direction is direction
                        and entity.extending
                    ):
                        entity.final_tick(level)
                        piston_piece = True
                if not piston_piece:
                    if (
                        b0 != TRIGGER_CONTRACT
                        or moving.is_air
                        or not is_pushable(
                            moving, level, two_pos, direction.opposite, False, direction
                        )
                        or (
                            moving.get_piston_push_reaction() is not PushReaction.PUSH_PULL
                            and not _is_piston_base(moving)
                        )
                    ):
                        level.remove_block(offset(pos, direction), False)
                    else:
                        self.move_blocks(level, pos, direction, False)
            else:
                level.remove_block(offset(pos, direction), False)
        return True

    def move_blocks(
        self, level: Level, piston_pos: Pos, direction: Direction, extending: bool
    ) -> bool:
        """``moveBlocks`` L257."""
        from redsim.world import blocks

        arm_pos = offset(piston_pos, direction)
        if not extending and level.get_block_state(arm_pos).block.id == ids.PISTON_HEAD:
            level.set_block(arm_pos, level.air, 276)
        resolver = PistonStructureResolver(level, piston_pos, direction, extending)
        if not resolver.resolve():
            return False

        delete_after_move: JavaHashMap[Pos, BlockState] = JavaHashMap(java_hash)
        to_push = resolver.to_push
        to_push_shapes: list[BlockState] = []
        for pos in to_push:
            state = level.get_block_state(pos)
            to_push_shapes.append(state)
            delete_after_move.put(pos, state)
        to_destroy = resolver.to_destroy
        to_update: list[BlockState] = []
        push_direction = direction if extending else direction.opposite

        for pos in reversed(to_destroy):
            state = level.get_block_state(pos)
            level.set_block(pos, level.air, 18)  # dropResources is not simulated
            to_update.append(state)

        moving_piston = blocks.MOVING_PISTON
        for index in range(len(to_push) - 1, -1, -1):
            source = to_push[index]
            moved = level.get_block_state(source)
            destination = offset(source, push_direction)
            delete_after_move.remove(destination)
            actual = moving_piston.default_state.with_(FACING, direction)
            level.set_block(destination, actual, 324)
            level.set_block_entity(
                PistonMovingBlockEntity(
                    destination, actual, to_push_shapes[index], direction, extending, False
                )
            )
            to_update.append(moved)

        if extending:
            piston_type = "sticky" if self.is_sticky else "normal"
            head = blocks.PISTON_HEAD.default_state.with_(FACING, direction).with_(
                PISTON_TYPE, piston_type
            )
            moving = moving_piston.default_state.with_(FACING, direction).with_(
                PISTON_TYPE, piston_type
            )
            delete_after_move.remove(arm_pos)
            level.set_block(arm_pos, moving, 324)
            level.set_block_entity(
                PistonMovingBlockEntity(arm_pos, moving, head, direction, True, True)
            )

        air = level.air
        for pos in list(delete_after_move.keys()):
            level.set_block(pos, air, 82)
        for pos, old_state in list(delete_after_move.items()):
            old_state.update_indirect_neighbour_shapes(level, pos, UpdateFlags.CLIENTS)
            air.update_neighbour_shapes(level, pos, UpdateFlags.CLIENTS)
            air.update_indirect_neighbour_shapes(level, pos, UpdateFlags.CLIENTS)

        update_index = 0
        for pos in reversed(to_destroy):
            state = to_update[update_index]
            update_index += 1
            state.affect_neighbors_after_removal(level, pos, False)
            state.update_indirect_neighbour_shapes(level, pos, UpdateFlags.CLIENTS)
            level.update_neighbors_at(pos, state.block)
        for index in range(len(to_push) - 1, -1, -1):
            level.update_neighbors_at(to_push[index], to_update[update_index].block)
            update_index += 1
        if extending:
            level.update_neighbors_at(arm_pos, blocks.PISTON_HEAD)
        return True


def is_pushable(
    state: BlockState,
    level: Level,
    pos: Pos,
    direction: Direction,
    allow_destroyable: bool,
    connection_direction: Direction,
) -> bool:
    """``PistonBaseBlock.isPushable`` L213."""
    if pos[1] < level.min_y or pos[1] > level.max_y or not level.is_within_world_border(pos):
        return False
    if state.is_air:
        return True
    if direction is Direction.DOWN and pos[1] == level.min_y:
        return False
    if direction is Direction.UP and pos[1] == level.max_y:
        return False
    if not _is_piston_base(state):
        if state.get_destroy_speed() == -1.0:
            return False
        reaction = state.get_piston_push_reaction()
        if reaction is PushReaction.IMMOVEABLE:
            return False
        if reaction is PushReaction.POPPED:
            return allow_destroyable
        if reaction is PushReaction.PUSH:
            return direction is connection_direction
    elif state.get(EXTENDED):
        return False
    return not state.has_block_entity


# ============================================================================ resolver
def _is_sticky(state: BlockState) -> bool:
    return state.block.id in (ids.SLIME_BLOCK, ids.HONEY_BLOCK)


def _can_stick_to_each_other(state1: BlockState, state2: BlockState) -> bool:
    if state1.block.id == ids.HONEY_BLOCK and state2.block.id == ids.SLIME_BLOCK:
        return False
    if state1.block.id == ids.SLIME_BLOCK and state2.block.id == ids.HONEY_BLOCK:
        return False
    return _is_sticky(state1) or _is_sticky(state2)


class PistonStructureResolver:
    """Port of ``PistonStructureResolver`` (list semantics kept, including ``indexOf``)."""

    def __init__(
        self, level: Level, piston_pos: Pos, direction: Direction, extending: bool
    ) -> None:
        self.level = level
        self.piston_pos = piston_pos
        self.piston_direction = direction
        self.extending = extending
        if extending:
            self.push_direction = direction
            self.start_pos = offset(piston_pos, direction)
        else:
            self.push_direction = direction.opposite
            self.start_pos = offset(piston_pos, direction, 2)
        self.to_push: list[Pos] = []
        self.to_destroy: list[Pos] = []

    def resolve(self) -> bool:
        self.to_push.clear()
        self.to_destroy.clear()
        next_state = self.level.get_block_state(self.start_pos)
        if not is_pushable(
            next_state,
            self.level,
            self.start_pos,
            self.push_direction,
            False,
            self.piston_direction,
        ):
            if self.extending and next_state.get_piston_push_reaction() is PushReaction.POPPED:
                self.to_destroy.append(self.start_pos)
                return True
            return False
        if not self.add_block_line(self.start_pos, self.push_direction):
            return False
        i = 0
        while i < len(self.to_push):
            pos = self.to_push[i]
            if _is_sticky(self.level.get_block_state(pos)) and not self.add_branching_blocks(pos):
                return False
            i += 1
        return True

    def add_block_line(self, start: Pos, direction: Direction) -> bool:
        level = self.level
        next_state = level.get_block_state(start)
        if next_state.is_air:
            return True
        if not is_pushable(next_state, level, start, self.push_direction, False, direction):
            return True
        if start == self.piston_pos:
            return True
        if start in self.to_push:
            return True
        block_count = 1
        if block_count + len(self.to_push) > MAX_PUSH_DEPTH:
            return False
        while _is_sticky(next_state):
            pos = offset(start, self.push_direction.opposite, block_count)
            previous = next_state
            next_state = level.get_block_state(pos)
            if (
                next_state.is_air
                or not _can_stick_to_each_other(previous, next_state)
                or not is_pushable(
                    next_state, level, pos, self.push_direction, False, self.push_direction.opposite
                )
                or pos == self.piston_pos
            ):
                break
            block_count += 1
            if block_count + len(self.to_push) > MAX_PUSH_DEPTH:
                return False
        blocks_added = 0
        for i in range(block_count - 1, -1, -1):
            self.to_push.append(offset(start, self.push_direction.opposite, i))
            blocks_added += 1
        i = 1
        while True:
            pos = offset(start, self.push_direction, i)
            collision = self.to_push.index(pos) if pos in self.to_push else -1
            if collision > -1:
                self.reorder_list_at_collision(blocks_added, collision)
                for j in range(collision + blocks_added + 1):
                    block_pos = self.to_push[j]
                    if _is_sticky(
                        level.get_block_state(block_pos)
                    ) and not self.add_branching_blocks(block_pos):
                        return False
                return True
            next_state = level.get_block_state(pos)
            if next_state.is_air:
                return True
            if (
                not is_pushable(
                    next_state, level, pos, self.push_direction, True, self.push_direction
                )
                or pos == self.piston_pos
            ):
                return False
            if next_state.get_piston_push_reaction() is PushReaction.POPPED:
                self.to_destroy.append(pos)
                return True
            if len(self.to_push) >= MAX_PUSH_DEPTH:
                return False
            self.to_push.append(pos)
            blocks_added += 1
            i += 1

    def reorder_list_at_collision(self, blocks_added: int, collision: int) -> None:
        head = self.to_push[:collision]
        last_line = self.to_push[len(self.to_push) - blocks_added :]
        collision_to_line = self.to_push[collision : len(self.to_push) - blocks_added]
        self.to_push = head + last_line + collision_to_line

    def add_branching_blocks(self, from_pos: Pos) -> bool:
        from_state = self.level.get_block_state(from_pos)
        for direction in ALL:
            if direction.axis is not self.push_direction.axis:
                neighbour_pos = offset(from_pos, direction)
                neighbour = self.level.get_block_state(neighbour_pos)
                if _can_stick_to_each_other(neighbour, from_state) and not self.add_block_line(
                    neighbour_pos, direction
                ):
                    return False
        return True


# ============================================================================ head
class PistonHeadBlock(Block):
    properties = (FACING, PISTON_TYPE, SHORT)

    def __init__(self) -> None:
        super().__init__(ids.PISTON_HEAD, push_reaction=PushReaction.IMMOVEABLE, destroy_speed=1.5)
        self.register_default_state(
            self.default_state.with_(FACING, Direction.NORTH)
            .with_(PISTON_TYPE, "normal")
            .with_(SHORT, False)
        )

    def get_shape(self, state: BlockState) -> Shape:
        facing = piston_facing(state)
        return facing_box(facing, 16, 0, 4) | facing_box(facing, 4, 4, 16)

    def is_fitting_base(self, arm: BlockState, base: BlockState) -> bool:
        base_id = ids.PISTON if arm.get(PISTON_TYPE) == "normal" else ids.STICKY_PISTON
        return (
            base.block.id == base_id
            and base.get(EXTENDED)
            and piston_facing(base) is piston_facing(arm)
        )

    def player_will_destroy(self, level: Level, pos: Pos, state: BlockState) -> BlockState:
        # Creative players (the editor) prevent drops: the base is destroyed directly.
        base_pos = offset(pos, piston_facing(state).opposite)
        if self.is_fitting_base(state, level.get_block_state(base_pos)):
            level.destroy_block(base_pos, False)
        return state

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        base_pos = offset(pos, piston_facing(state).opposite)
        if self.is_fitting_base(state, level.get_block_state(base_pos)):
            level.destroy_block(base_pos, True)

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction.opposite is piston_facing(state) and not state.can_survive(level, pos):
            return level.air
        return state

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        base = level.get_block_state(offset(pos, piston_facing(state).opposite))
        return self.is_fitting_base(state, base) or (
            base.block.id == ids.MOVING_PISTON and piston_facing(base) is piston_facing(state)
        )

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        if state.can_survive(level, pos):
            level.neighbor_changed(offset(pos, piston_facing(state).opposite), source)


# ============================================================================ moving piston
class MovingPistonBlock(Block):
    properties = (FACING, PISTON_TYPE)
    has_block_entity = True
    has_ticker = True
    force_solid = True
    dynamic_shape = True

    def __init__(self) -> None:
        super().__init__(
            ids.MOVING_PISTON,
            push_reaction=PushReaction.IMMOVEABLE,
            conductor=Conductor.NEVER,
            destroy_speed=-1.0,
        )
        self.register_default_state(
            self.default_state.with_(FACING, Direction.NORTH).with_(PISTON_TYPE, "normal")
        )

    def get_shape(self, state: BlockState) -> Shape:
        return EMPTY

    def get_dynamic_support_shape(self, state: BlockState, level: Level, pos: Pos) -> Shape:
        entity = level.get_block_entity(pos)
        if isinstance(entity, PistonMovingBlockEntity):
            return entity.collision_shape(level, pos)
        return EMPTY

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return None  # created explicitly by the piston (MovingPistonBlock.newBlockEntity)

    def destroy(self, level: Level, pos: Pos, state: BlockState) -> None:
        relative = offset(pos, piston_facing(state).opposite)
        base = level.get_block_state(relative)
        if isinstance(base.block, PistonBaseBlock) and base.get(EXTENDED):
            level.remove_block(relative, False)

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        if level.get_block_entity(pos) is None:
            level.remove_block(pos, False)
            return True
        return False


class PistonMovingBlockEntity(BlockEntity):
    type_id = "piston"
    valid_blocks = frozenset({ids.MOVING_PISTON})

    def __init__(
        self,
        pos: Pos,
        state: BlockState,
        moved_state: BlockState | None = None,
        direction: Direction = Direction.DOWN,
        extending: bool = False,
        is_source: bool = False,
    ) -> None:
        super().__init__(pos, state)
        from redsim.world import blocks

        self.moved_state = moved_state if moved_state is not None else blocks.AIR.default_state
        self.direction = direction
        self.extending = extending
        self.is_source = is_source
        self.progress = 0.0
        self.progress_o = 0.0
        self.last_ticked = 0

    @property
    def push_direction(self) -> Direction:
        return self.direction if self.extending else self.direction.opposite

    def extended_progress(self, progress: float) -> float:
        return progress - 1.0 if self.extending else 1.0 - progress

    def collision_shape(self, level: Level, pos: Pos) -> Shape:
        """``getCollisionShape`` (without the entity-only NOCLIP case)."""
        from redsim.world import blocks

        head_shape = EMPTY
        if (
            not self.extending
            and self.is_source
            and isinstance(self.moved_state.block, PistonBaseBlock)
        ):
            head_shape = self.moved_state.with_(EXTENDED, True).get_collision_shape()
        if self.is_source:
            short = self.extending != ((1.0 - self.progress) < 0.25)
            state = blocks.PISTON_HEAD.default_state.with_(FACING, self.direction).with_(
                SHORT, short
            )
        else:
            state = self.moved_state
        shift = int(round(self.extended_progress(self.progress) * 16))
        dx, dy, dz = (step * shift for step in self.direction.step)
        return head_shape | state.get_collision_shape().offset(dx, dy, dz)

    def shift_time(self, delta: int) -> None:
        self.last_ticked += delta

    def tick(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``PistonMovingBlockEntity.tick`` L291."""
        self.last_ticked = level.game_time
        self.progress_o = self.progress
        if self.progress_o >= 1.0:
            level.remove_block_entity(pos)
            self.set_removed()
            if level.get_block_state(pos).block.id == ids.MOVING_PISTON:
                new_state = level.update_from_neighbour_shapes(self.moved_state, pos)
                if new_state.is_air:
                    level.set_block(pos, self.moved_state, 340)
                    level.update_or_destroy(self.moved_state, new_state, pos, UpdateFlags.ALL)
                else:
                    level.set_block(pos, new_state, 67)
                    level.neighbor_changed(pos, new_state.block)
        else:
            new_progress = self.progress + 0.5
            if level.entities:
                from redsim.sim.entities import move_collided_entities, move_stuck_entities

                move_collided_entities(level, pos, new_progress, self)
                move_stuck_entities(level, pos, new_progress, self)
            self.progress = min(new_progress, 1.0)

    def final_tick(self, level: Level) -> None:
        """``finalTick`` L259: complete the move immediately."""
        from redsim.world import blocks

        if self.progress_o < 1.0:
            self.progress = 1.0
            self.progress_o = self.progress
            level.remove_block_entity(self.pos)
            self.set_removed()
            if level.get_block_state(self.pos).block.id == ids.MOVING_PISTON:
                if self.is_source:
                    new_state = blocks.AIR.default_state
                else:
                    new_state = level.update_from_neighbour_shapes(self.moved_state, self.pos)
                level.set_block_and_update(self.pos, new_state)
                level.neighbor_changed(self.pos, new_state.block)

    def pre_remove_side_effects(self, level: Level, pos: Pos, state: BlockState) -> None:
        self.final_tick(level)

    def to_json(self) -> dict[str, Any]:
        return {
            "blockState": repr(self.moved_state),
            "facing": self.direction.serialized,
            "progress": self.progress,
            "progressO": self.progress_o,
            "extending": self.extending,
            "source": self.is_source,
            "lastTicked": self.last_ticked,
        }

    def load_json(self, data: dict[str, Any]) -> None:
        from redsim.world import blocks

        self.moved_state = blocks.parse_state(data["blockState"])
        self.direction = Direction.by_name(data["facing"])
        self.progress = float(data["progress"])
        self.progress_o = float(data["progressO"])
        self.extending = bool(data["extending"])
        self.is_source = bool(data["source"])
        self.last_ticked = int(data["lastTicked"])

    def describe(self) -> str:
        kind = "head" if self.is_source else repr(self.moved_state)
        motion = "extending" if self.extending else "retracting"
        return f"moving {kind} {motion} {self.direction.serialized} progress={self.progress}"


# Registered here, not with a class decorator (classes stay compilable by mypyc).
register_block_entity(PistonMovingBlockEntity)
