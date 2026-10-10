"""Redstone wire (dust) with the default (non-experimental) evaluator.

Source (relative to ``data/minecraft_src/client-src/net/minecraft/world/level/``):

* ``block/RedstoneWireBlock.java``: ``getConnectionState`` L117, ``getMissingConnections``
  L149, ``updateShape`` L163, ``updateIndirectNeighbourShapes`` L204, ``getConnectingSide``
  L229/L233, ``canSurviveOn`` L260, ``getBlockSignal`` L278, ``checkCornerChangeAt`` L285,
  ``onPlace`` L296, ``affectNeighborsAfterRemoval`` L309, ``updateNeighborsOfNeighboringWires``
  L320, ``neighborChanged`` L336, ``getDirectSignal`` L356, ``getSignal`` L361,
  ``useWithoutItem`` L482, ``updatesOnShapeChange`` L503.
* ``redstone/DefaultRedstoneWireEvaluator.java`` ``updatePowerStrength`` L18 and
  ``redstone/RedstoneWireEvaluator.java`` ``getIncomingWireSignal`` L29.

The update burst iterates a ``HashSet<BlockPos>`` (Java iteration order, see
``redsim.core.javahash``). Trapdoors (which can carry wire connections upward) are not in
the block set yet. See doc/mechanics/redstone-wire.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.direction import ALL, HORIZONTAL, VERTICAL, Direction
from redsim.core.javahash import JavaHashSet
from redsim.core.pos import Pos, above, below, java_hash, offset
from redsim.world import ids
from redsim.world.block import Block, BlockState, PlacementContext, PushReaction
from redsim.world.properties import (
    EAST_REDSTONE,
    NORTH_REDSTONE,
    POWER,
    SOUTH_REDSTONE,
    WEST_REDSTONE,
    Property,
)
from redsim.world.shape import EMPTY, Shape

if TYPE_CHECKING:
    from redsim.sim.level import Level

PROPERTY_BY_DIRECTION: dict[Direction, Property] = {
    Direction.NORTH: NORTH_REDSTONE,
    Direction.EAST: EAST_REDSTONE,
    Direction.SOUTH: SOUTH_REDSTONE,
    Direction.WEST: WEST_REDSTONE,
}
NONE, SIDE, UP = "none", "side", "up"


def is_connected(side: str) -> bool:
    """``RedstoneSide.isConnected``."""
    return side != NONE


def is_cross(state: BlockState) -> bool:
    return all(is_connected(state.get(p)) for p in PROPERTY_BY_DIRECTION.values())


def is_dot(state: BlockState) -> bool:
    return not any(is_connected(state.get(p)) for p in PROPERTY_BY_DIRECTION.values())


class RedstoneWireBlock(Block):
    properties = (NORTH_REDSTONE, EAST_REDSTONE, SOUTH_REDSTONE, WEST_REDSTONE, POWER)

    def __init__(self) -> None:
        super().__init__(
            ids.REDSTONE_WIRE,
            has_collision=False,
            push_reaction=PushReaction.POPPED,
            destroy_speed=0.0,
        )
        default = self.default_state
        for prop in PROPERTY_BY_DIRECTION.values():
            default = default.with_(prop, NONE)
        self.register_default_state(default.with_(POWER, 0))
        cross = self.default_state
        for prop in PROPERTY_BY_DIRECTION.values():
            cross = cross.with_(prop, SIDE)
        self.cross_state = cross
        #: ``shouldSignal``: false while a wire computes its own input (getBlockSignal).
        self.should_signal = True

    def get_shape(self, state: BlockState) -> Shape:
        return EMPTY  # no collision; the visual shape is irrelevant to the simulation

    # --- placement and connections ----------------------------------------------------
    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.get_connection_state(ctx.level, self.cross_state, ctx.pos)

    def get_connection_state(self, level: Level, state: BlockState, pos: Pos) -> BlockState:
        was_dot = is_dot(state)
        state = self.get_missing_connections(
            level, self.default_state.with_(POWER, state.get(POWER)), pos
        )
        if was_dot and is_dot(state):
            return state
        north = is_connected(state.get(NORTH_REDSTONE))
        south = is_connected(state.get(SOUTH_REDSTONE))
        east = is_connected(state.get(EAST_REDSTONE))
        west = is_connected(state.get(WEST_REDSTONE))
        north_south_empty = not north and not south
        east_west_empty = not east and not west
        if not west and north_south_empty:
            state = state.with_(WEST_REDSTONE, SIDE)
        if not east and north_south_empty:
            state = state.with_(EAST_REDSTONE, SIDE)
        if not north and east_west_empty:
            state = state.with_(NORTH_REDSTONE, SIDE)
        if not south and east_west_empty:
            state = state.with_(SOUTH_REDSTONE, SIDE)
        return state

    def get_missing_connections(self, level: Level, state: BlockState, pos: Pos) -> BlockState:
        # The game passes ``pos`` (not ``pos.above()``) to isRedstoneConductor (L150).
        can_connect_up = not level.get_block_state(above(pos)).is_redstone_conductor(level, pos)
        for direction in HORIZONTAL:
            prop = PROPERTY_BY_DIRECTION[direction]
            if not is_connected(state.get(prop)):
                side = self.get_connecting_side(level, pos, direction, can_connect_up)
                state = state.with_(prop, side)
        return state

    def get_connecting_side(
        self, level: Level, pos: Pos, direction: Direction, can_connect_up: bool | None = None
    ) -> str:
        if can_connect_up is None:
            can_connect_up = not level.get_block_state(above(pos)).is_redstone_conductor(level, pos)
        relative_pos = offset(pos, direction)
        relative = level.get_block_state(relative_pos)
        if can_connect_up:
            placeable_above = self.can_survive_on(level, relative_pos, relative)
            if placeable_above and should_connect_to_pos(level, above(relative_pos)):
                if relative.is_face_sturdy(level, relative_pos, direction.opposite):
                    return UP
                return SIDE
        if not relative.should_redstone_wire_connect_to(level, relative_pos, direction) and (
            relative.is_redstone_conductor(level, relative_pos)
            or not should_connect_to_pos(level, below(relative_pos))
        ):
            return NONE
        return SIDE

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction is Direction.DOWN:
            return state if self.can_survive_on(level, neighbor_pos, neighbor) else level.air
        if direction is Direction.UP:
            return self.get_connection_state(level, state, pos)
        prop = PROPERTY_BY_DIRECTION[direction]
        side = self.get_connecting_side(level, pos, direction)
        if is_connected(side) == is_connected(state.get(prop)) and not is_cross(state):
            return state.with_(prop, side)
        return self.get_connection_state(
            level, self.cross_state.with_(POWER, state.get(POWER)).with_(prop, side), pos
        )

    def update_indirect_neighbour_shapes(
        self, state: BlockState, level: Level, pos: Pos, flags: int, limit: int
    ) -> None:
        for direction in HORIZONTAL:
            side = state.get(PROPERTY_BY_DIRECTION[direction])
            side_pos = offset(pos, direction)
            if side != NONE and not level.get_block_state(side_pos).is_(self):
                for diagonal in (below(side_pos), above(side_pos)):
                    if level.get_block_state(diagonal).is_(self):
                        neighbor_pos = offset(diagonal, direction.opposite)
                        level.neighbor_shape_changed(
                            direction.opposite,
                            diagonal,
                            neighbor_pos,
                            level.get_block_state(neighbor_pos),
                            flags,
                            limit,
                        )

    # --- support ------------------------------------------------------------------------
    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        support = below(pos)
        return self.can_survive_on(level, support, level.get_block_state(support))

    def can_survive_on(self, level: Level, pos: Pos, state: BlockState) -> bool:
        return state.is_face_sturdy(level, pos, Direction.UP) or state.block.id == ids.HOPPER

    # --- power --------------------------------------------------------------------------
    def update_power_strength(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``DefaultRedstoneWireEvaluator.updatePowerStrength`` (L18)."""
        target = self.calculate_target_strength(level, pos)
        if state.get(POWER) != target:
            if level.get_block_state(pos) is state:
                level.set_block(pos, state.with_(POWER, target), 2)
            to_update: JavaHashSet[Pos] = JavaHashSet(java_hash)
            to_update.add(pos)
            for direction in ALL:
                to_update.add(offset(pos, direction))
            for update_pos in to_update:
                level.update_neighbors_at(update_pos, self)

    def calculate_target_strength(self, level: Level, pos: Pos) -> int:
        block_signal = self.get_block_signal(level, pos)
        if block_signal == 15:
            return block_signal
        return max(block_signal, self.get_incoming_wire_signal(level, pos))

    def get_block_signal(self, level: Level, pos: Pos) -> int:
        """``getBlockSignal`` L278: best neighbor signal with every wire muted."""
        self.should_signal = False
        signal = level.get_best_neighbor_signal(pos)
        self.should_signal = True
        return signal

    def get_incoming_wire_signal(self, level: Level, pos: Pos) -> int:
        """``RedstoneWireEvaluator.getIncomingWireSignal`` (L29)."""
        wire_signal = 0
        above_pos = above(pos)
        above_is_conductor = level.get_block_state(above_pos).is_redstone_conductor(
            level, above_pos
        )
        for direction in HORIZONTAL:
            neighbor_pos = offset(pos, direction)
            neighbor = level.get_block_state(neighbor_pos)
            wire_signal = max(wire_signal, self._wire_signal(neighbor))
            if neighbor.is_redstone_conductor(level, neighbor_pos):
                if not above_is_conductor:
                    wire_signal = max(
                        wire_signal, self._wire_signal(level.get_block_state(above(neighbor_pos)))
                    )
            else:
                wire_signal = max(
                    wire_signal, self._wire_signal(level.get_block_state(below(neighbor_pos)))
                )
        return max(0, wire_signal - 1)

    def _wire_signal(self, state: BlockState) -> int:
        return int(state.get(POWER)) if state.is_(self) else 0

    # --- update hooks -------------------------------------------------------------------
    def check_corner_change_at(self, level: Level, pos: Pos) -> None:
        if level.get_block_state(pos).is_(self):
            level.update_neighbors_at(pos, self)
            for direction in ALL:
                level.update_neighbors_at(offset(pos, direction), self)

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        if not old_state.is_(self):
            self.update_power_strength(level, pos, state)
            for direction in VERTICAL:
                level.update_neighbors_at(offset(pos, direction), self)
            self.update_neighbors_of_neighboring_wires(level, pos)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        if not moved_by_piston:
            for direction in ALL:
                level.update_neighbors_at(offset(pos, direction), self)
            self.update_power_strength(level, pos, state)
            self.update_neighbors_of_neighboring_wires(level, pos)

    def update_neighbors_of_neighboring_wires(self, level: Level, pos: Pos) -> None:
        for direction in HORIZONTAL:
            self.check_corner_change_at(level, offset(pos, direction))
        for direction in HORIZONTAL:
            target = offset(pos, direction)
            if level.get_block_state(target).is_redstone_conductor(level, target):
                self.check_corner_change_at(level, above(target))
            else:
                self.check_corner_change_at(level, below(target))

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        if state.can_survive(level, pos):
            self.update_power_strength(level, pos, state)
        else:
            level.remove_block(pos, False)  # dropResources is not simulated

    # --- signals ------------------------------------------------------------------------
    def is_signal_source(self, state: BlockState) -> bool:
        return self.should_signal

    def should_redstone_wire_connect_to(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction | None
    ) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return int(state.get(POWER))

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return state.get_signal(level, pos, direction) if self.should_signal else 0

    def get_signal(self, state: BlockState, level: Level, pos: Pos, direction: Direction) -> int:
        if not self.should_signal or direction is Direction.DOWN:
            return 0
        power = int(state.get(POWER))
        if power == 0:
            return 0
        if direction is not Direction.UP:
            connections = self.get_connection_state(level, state, pos)
            if not is_connected(connections.get(PROPERTY_BY_DIRECTION[direction.opposite])):
                return 0
        return power

    # --- interaction --------------------------------------------------------------------
    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """Toggle dot ↔ cross when the wire has no forced connections (L482)."""
        if is_cross(state) or is_dot(state):
            new_state = self.default_state if is_cross(state) else self.cross_state
            new_state = new_state.with_(POWER, state.get(POWER))
            new_state = self.get_connection_state(level, new_state, pos)
            if new_state is not state:
                level.set_block_and_update(pos, new_state)
                self.updates_on_shape_change(level, pos, state, new_state)
                return True
        return False

    def updates_on_shape_change(
        self, level: Level, pos: Pos, old_state: BlockState, new_state: BlockState
    ) -> None:
        for direction in HORIZONTAL:
            relative = offset(pos, direction)
            prop = PROPERTY_BY_DIRECTION[direction]
            if is_connected(old_state.get(prop)) != is_connected(
                new_state.get(prop)
            ) and level.get_block_state(relative).is_redstone_conductor(level, relative):
                level.update_neighbors_at_except_from_facing(
                    relative, new_state.block, direction.opposite
                )


def should_connect_to_pos(level: Level, pos: Pos) -> bool:
    """``shouldConnectTo(level, pos)``: with a null direction."""
    return level.get_block_state(pos).should_redstone_wire_connect_to(level, pos, None)
