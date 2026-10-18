"""Rails: plain rails (shape connections) and powered/activator rails (power along the line).

Sources (``data/minecraft_src/client-src/net/minecraft/world/level/block/``):

* ``BaseRailBlock.java``: shapes (flat 2 px, slope 8 px; no collision), ``canSurvive`` (a
  rigid top face below), ``onPlace`` → ``updateState`` (``updateDir`` with
  ``RailState.place``; straight rails then run their own ``neighborChanged``),
  ``neighborChanged`` (removal when unsupported, else the subclass's ``updateState``),
  ``affectNeighborsAfterRemoval``, placement shape by the horizontal look direction,
  ``rotate``/``mirror`` tables.
* ``RailState.java``: connections, ``place`` (choose the shape from neighboring rails that
  can still connect, then let them connect back), ``connectTo``, ``removeSoftConnections``,
  ``countPotentialConnections``.
* ``RailBlock.java``: a plain rail re-runs ``updateDir`` when a signal source updates it and
  it has three potential connections (a T junction switches with power).
* ``PoweredRailBlock.java`` (powered and activator rails): powered when it has a neighbor
  signal or a powered rail of the same kind within 8 rails along the line
  (``findPoweredRailSignal``/``isSameRailWithPower``); a change updates the block below
  (and above for slopes).

* ``DetectorRailBlock.java``: a straight rail that is a signal source (so wire connects
  to it), powered while a minecart is on it (``checkPressed``, rechecked every 20 ticks),
  with a comparator output from the minecart's contents. Minecarts are not simulated, so a
  detector rail stays unpowered (as in the game without minecarts); every ``checkPressed``
  (placing it, an entity inside, a pending recheck) still updates comparators around it.

Not as in the game: waterlogging is not simulated (always false here), and minecarts do not
exist, so detector rails never detect one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.direction import HORIZONTAL, Direction
from redsim.core.pos import Pos, above, below, offset
from redsim.world.block import Block, BlockState, PlacementContext
from redsim.world.properties import POWERED, Property, boolean
from redsim.world.shape import Shape, SupportType, column

if TYPE_CHECKING:
    from redsim.sim.level import Level

NS, EW = "north_south", "east_west"
A_EAST, A_WEST, A_NORTH, A_SOUTH = (
    "ascending_east",
    "ascending_west",
    "ascending_north",
    "ascending_south",
)
SE, SW, NW, NE = "south_east", "south_west", "north_west", "north_east"
#: ``BlockStateProperties.RAIL_SHAPE`` / ``RAIL_SHAPE_STRAIGHT`` (enum order of RailShape).
RAIL_SHAPE = Property("shape", (NS, EW, A_EAST, A_WEST, A_NORTH, A_SOUTH, SE, SW, NW, NE))
RAIL_SHAPE_STRAIGHT = Property("shape", (NS, EW, A_EAST, A_WEST, A_NORTH, A_SOUTH))
WATERLOGGED = boolean("waterlogged")
SLOPES = frozenset({A_EAST, A_WEST, A_NORTH, A_SOUTH})
_FLAT = column(16, 0, 2)
_SLOPE = column(16, 0, 8)

#: ``BaseRailBlock.rotate`` (clockwise 90°) and ``mirror``.
ROTATE_CW = {
    NS: EW, EW: NS, A_EAST: A_SOUTH, A_WEST: A_NORTH, A_NORTH: A_EAST, A_SOUTH: A_WEST,
    SE: SW, SW: NW, NW: NE, NE: SE,
}  # fmt: skip
MIRROR = {
    "z": {A_NORTH: A_SOUTH, A_SOUTH: A_NORTH, SE: NE, SW: NW, NW: SW, NE: SE},  # LEFT_RIGHT
    "x": {A_EAST: A_WEST, A_WEST: A_EAST, SE: SW, SW: SE, NW: NE, NE: NW},  # FRONT_BACK
}


def is_rail(state: BlockState) -> bool:
    return isinstance(state.block, BaseRailBlock)


def can_support_rigid_block(level: Level, pos: Pos) -> bool:
    return level.get_block_state(pos).is_face_sturdy(level, pos, Direction.UP, SupportType.RIGID)


class BaseRailBlock(Block):
    is_rail = True
    is_straight = False
    shape_property: Property = RAIL_SHAPE

    def __init__(self, block_id: str) -> None:
        super().__init__(block_id, has_collision=False, destroy_speed=0.7)

    def get_shape(self, state: BlockState) -> Shape:
        return _SLOPE if state.get(self.shape_property) in SLOPES else _FLAT

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        return can_support_rigid_block(level, below(pos))

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.default_state.with_(self.shape_property, ctx.requested.get(self.shape_property))

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        if old_state.block is not state.block:
            self.update_state_first(state, level, pos, moved_by_piston)

    def update_state_first(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> BlockState:
        """``BaseRailBlock.updateState(state, level, pos, movedByPiston)``."""
        state = self.update_dir(level, pos, state, True)
        if self.is_straight:
            level.neighbor_changed_full(state, pos, self, moved_by_piston)
        return state

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        if level.get_block_state(pos).block is not self:
            return
        if self.should_be_removed(pos, level, state.get(self.shape_property)):
            level.remove_block(pos, moved_by_piston)  # Not as in the game: no item drops
        else:
            self.update_state(state, level, pos, source)

    @staticmethod
    def should_be_removed(pos: Pos, level: Level, shape: str) -> bool:
        if not can_support_rigid_block(level, below(pos)):
            return True
        side = {A_EAST: Direction.EAST, A_WEST: Direction.WEST}.get(shape) or {
            A_NORTH: Direction.NORTH,
            A_SOUTH: Direction.SOUTH,
        }.get(shape)
        return side is not None and not can_support_rigid_block(level, offset(pos, side))

    def update_state(self, state: BlockState, level: Level, pos: Pos, source: Block) -> None:
        """``updateState(state, level, pos, block)``: subclasses react to updates."""
        return None

    def update_dir(self, level: Level, pos: Pos, state: BlockState, first: bool) -> BlockState:
        current = state.get(self.shape_property)
        rail = RailState(level, pos, state)
        return rail.place(level.has_neighbor_signal(pos), first, current).state

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        if moved_by_piston:
            return
        if state.get(self.shape_property) in SLOPES:
            level.update_neighbors_at(above(pos), self)
        if self.is_straight:
            level.update_neighbors_at(pos, self)
            level.update_neighbors_at(below(pos), self)


class RailBlock(BaseRailBlock):
    properties = (RAIL_SHAPE, WATERLOGGED)
    shape_property = RAIL_SHAPE

    def __init__(self) -> None:
        super().__init__("minecraft:rail")
        self.register_default_state(
            self.default_state.with_(RAIL_SHAPE, NS).with_(WATERLOGGED, False)
        )

    def update_state(self, state: BlockState, level: Level, pos: Pos, source: Block) -> None:
        if source.default_state.is_signal_source() and (
            RailState(level, pos, state).count_potential_connections() == 3
        ):
            self.update_dir(level, pos, state, False)


class PoweredRailBlock(BaseRailBlock):
    """Powered rail and activator rail (``PoweredRailBlock`` in the game for both)."""

    properties = (RAIL_SHAPE_STRAIGHT, POWERED, WATERLOGGED)
    shape_property = RAIL_SHAPE_STRAIGHT
    is_straight = True

    def __init__(self, block_id: str) -> None:
        super().__init__(block_id)
        self.register_default_state(
            self.default_state.with_(RAIL_SHAPE_STRAIGHT, NS)
            .with_(POWERED, False)
            .with_(WATERLOGGED, False)
        )

    def find_powered_rail_signal(
        self, level: Level, pos: Pos, state: BlockState, forward: bool, depth: int
    ) -> bool:
        if depth >= 8:
            return False
        x, y, z = pos
        check_below = True
        shape = state.get(RAIL_SHAPE_STRAIGHT)
        if shape == NS:
            z += 1 if forward else -1
        elif shape == EW:
            x += -1 if forward else 1
        elif shape == A_EAST:
            if forward:
                x -= 1
            else:
                x, y, check_below = x + 1, y + 1, False
            shape = EW
        elif shape == A_WEST:
            if forward:
                x, y, check_below = x - 1, y + 1, False
            else:
                x += 1
            shape = EW
        elif shape == A_NORTH:
            if forward:
                z += 1
            else:
                z, y, check_below = z - 1, y + 1, False
            shape = NS
        elif shape == A_SOUTH:
            if forward:
                z, y, check_below = z + 1, y + 1, False
            else:
                z -= 1
            shape = NS
        if self.is_same_rail_with_power(level, (x, y, z), forward, depth, shape):
            return True
        return check_below and self.is_same_rail_with_power(
            level, (x, y - 1, z), forward, depth, shape
        )

    def is_same_rail_with_power(
        self, level: Level, pos: Pos, forward: bool, depth: int, direction: str
    ) -> bool:
        state = level.get_block_state(pos)
        if state.block is not self:
            return False
        shape = state.get(RAIL_SHAPE_STRAIGHT)
        if direction == EW and shape in (NS, A_NORTH, A_SOUTH):
            return False
        if direction == NS and shape in (EW, A_EAST, A_WEST):
            return False
        if not state.get(POWERED):
            return False
        if level.has_neighbor_signal(pos):
            return True
        return self.find_powered_rail_signal(level, pos, state, forward, depth + 1)

    def update_state(self, state: BlockState, level: Level, pos: Pos, source: Block) -> None:
        powered = state.get(POWERED)
        should_power = (
            level.has_neighbor_signal(pos)
            or self.find_powered_rail_signal(level, pos, state, True, 0)
            or self.find_powered_rail_signal(level, pos, state, False, 0)
        )
        if should_power != powered:
            level.set_block_and_update(pos, state.with_(POWERED, should_power))
            level.update_neighbors_at(below(pos), self)
            if state.get(RAIL_SHAPE_STRAIGHT) in SLOPES:
                level.update_neighbors_at(above(pos), self)


class DetectorRailBlock(BaseRailBlock):
    """``DetectorRailBlock`` without minecarts (none are simulated)."""

    properties = (RAIL_SHAPE_STRAIGHT, POWERED, WATERLOGGED)
    shape_property = RAIL_SHAPE_STRAIGHT
    is_straight = True
    #: ``PRESSED_CHECK_PERIOD``.
    pressed_check_period = 20

    def __init__(self) -> None:
        super().__init__("minecraft:detector_rail")
        self.register_default_state(
            self.default_state.with_(POWERED, False)
            .with_(RAIL_SHAPE_STRAIGHT, NS)
            .with_(WATERLOGGED, False)
        )

    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return 15 if state.get(POWERED) else 0

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return 15 if state.get(POWERED) and direction is Direction.UP else 0

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        """The minecart's command block or contents while powered: no minecarts, 0."""
        return 0

    def entity_inside_entity(
        self, state: BlockState, level: Level, pos: Pos, entity: object
    ) -> None:
        """``entityInside`` (a falling block passing through it)."""
        if not state.get(POWERED):
            self.check_pressed(level, pos, state)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        if state.get(POWERED):
            self.check_pressed(level, pos, state)

    def check_pressed(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``checkPressed``: pressed while a minecart is in its search box. Not as in the
        game: there are no minecarts, so it is never pressed (a powered one, put by
        ``/setblock``, turns off at its next check)."""
        if not self.can_survive(state, level, pos) or level.get_block_state(pos).block is not self:
            return
        was_pressed = bool(state.get(POWERED))
        should_be_pressed = False
        if was_pressed and not should_be_pressed:
            new_state = state.with_(POWERED, False)
            level.set_block_and_update(pos, new_state)
            self.update_power_to_connected(level, pos, new_state)
            level.update_neighbors_at(pos, self)
            level.update_neighbors_at(below(pos), self)
        level.update_neighbour_for_output_signal(pos, self)

    def update_power_to_connected(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``updatePowerToConnected``: the rails it connects to get a neighbor update."""
        for connection in RailState(level, pos, state).connections:
            neighbor = level.get_block_state(connection)
            level.neighbor_changed_full(neighbor, connection, neighbor.block, False)

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        if old_state.block is not state.block:
            updated = self.update_state_first(state, level, pos, moved_by_piston)
            self.check_pressed(level, pos, updated)


class RailState:
    """``RailState``: a rail's connections and the shape logic shared by all rails."""

    def __init__(self, level: Level, pos: Pos, state: BlockState) -> None:
        self.level = level
        self.pos = pos
        self.state = state
        block = state.block
        assert isinstance(block, BaseRailBlock)
        self.block = block
        self.is_straight = block.is_straight
        self.connections: list[Pos] = []
        self.update_connections(state.get(block.shape_property))

    def update_connections(self, shape: str) -> None:
        x, y, z = self.pos
        north, south, west, east = (x, y, z - 1), (x, y, z + 1), (x - 1, y, z), (x + 1, y, z)
        self.connections = {
            NS: [north, south],
            EW: [west, east],
            A_EAST: [west, above(east)],
            A_WEST: [above(west), east],
            A_NORTH: [above(north), south],
            A_SOUTH: [north, above(south)],
            SE: [east, south],
            SW: [west, south],
            NW: [west, north],
            NE: [east, north],
        }[shape]

    def remove_soft_connections(self) -> None:
        i = 0
        while i < len(self.connections):
            rail = self.get_rail(self.connections[i])
            if rail is not None and rail.connects_to(self):
                self.connections[i] = rail.pos
                i += 1
            else:
                del self.connections[i]

    def has_rail(self, pos: Pos) -> bool:
        level = self.level
        return (
            is_rail(level.get_block_state(pos))
            or is_rail(level.get_block_state(above(pos)))
            or is_rail(level.get_block_state(below(pos)))
        )

    def get_rail(self, pos: Pos) -> RailState | None:
        for test in (pos, above(pos), below(pos)):
            state = self.level.get_block_state(test)
            if is_rail(state):
                return RailState(self.level, test, state)
        return None

    def connects_to(self, rail: RailState) -> bool:
        return self.has_connection(rail.pos)

    def has_connection(self, rail_pos: Pos) -> bool:
        return any(c[0] == rail_pos[0] and c[2] == rail_pos[2] for c in self.connections)

    def count_potential_connections(self) -> int:
        return sum(1 for d in HORIZONTAL if self.has_rail(offset(self.pos, d)))

    def can_connect_to(self, rail: RailState) -> bool:
        return self.connects_to(rail) or len(self.connections) != 2

    def connect_to(self, rail: RailState) -> None:
        self.connections.append(rail.pos)
        x, y, z = self.pos
        north, south, west, east = (x, y, z - 1), (x, y, z + 1), (x - 1, y, z), (x + 1, y, z)
        n, s = self.has_connection(north), self.has_connection(south)
        w, e = self.has_connection(west), self.has_connection(east)
        shape = None
        if n or s:
            shape = NS
        if w or e:
            shape = EW
        if not self.is_straight:
            if s and e and not n and not w:
                shape = SE
            if s and w and not n and not e:
                shape = SW
            if n and w and not s and not e:
                shape = NW
            if n and e and not s and not w:
                shape = NE
        shape = self._ascend(shape, north, south, west, east)
        if shape is None:
            shape = NS
        self.state = self.state.with_(self.block.shape_property, shape)
        self.level.set_block_and_update(self.pos, self.state)

    def _ascend(
        self, shape: str | None, north: Pos, south: Pos, west: Pos, east: Pos
    ) -> str | None:
        level = self.level
        if shape == NS:
            if is_rail(level.get_block_state(above(north))):
                shape = A_NORTH
            if is_rail(level.get_block_state(above(south))):
                shape = A_SOUTH
        if shape == EW:
            if is_rail(level.get_block_state(above(east))):
                shape = A_EAST
            if is_rail(level.get_block_state(above(west))):
                shape = A_WEST
        return shape

    def has_neighbor_rail(self, rail_pos: Pos) -> bool:
        neighbor = self.get_rail(rail_pos)
        if neighbor is None:
            return False
        neighbor.remove_soft_connections()
        return neighbor.can_connect_to(self)

    def place(self, has_signal: bool, first: bool, default_shape: str) -> RailState:
        x, y, z = self.pos
        north, south, west, east = (x, y, z - 1), (x, y, z + 1), (x - 1, y, z), (x + 1, y, z)
        n = self.has_neighbor_rail(north)
        s = self.has_neighbor_rail(south)
        w = self.has_neighbor_rail(west)
        e = self.has_neighbor_rail(east)
        shape: str | None = None
        north_or_south, west_or_east = n or s, w or e
        if north_or_south and not west_or_east:
            shape = NS
        if west_or_east and not north_or_south:
            shape = EW
        south_east, south_west = s and e, s and w
        north_east, north_west = n and e, n and w
        if not self.is_straight:
            if south_east and not n and not w:
                shape = SE
            if south_west and not n and not e:
                shape = SW
            if north_west and not s and not e:
                shape = NW
            if north_east and not s and not w:
                shape = NE
        if shape is None:
            if north_or_south and west_or_east:
                shape = default_shape
            elif north_or_south:
                shape = NS
            elif west_or_east:
                shape = EW
            if not self.is_straight:
                if has_signal:
                    for flag, value in ((south_east, SE), (south_west, SW), (north_east, NE)):
                        if flag:
                            shape = value
                    if north_west:
                        shape = NW
                else:
                    for flag, value in ((north_west, NW), (north_east, NE), (south_west, SW)):
                        if flag:
                            shape = value
                    if south_east:
                        shape = SE
        shape = self._ascend(shape, north, south, west, east)
        if shape is None:
            shape = default_shape
        self.update_connections(shape)
        self.state = self.state.with_(self.block.shape_property, shape)
        if first or self.level.get_block_state(self.pos) is not self.state:
            self.level.set_block_and_update(self.pos, self.state)
            for connection in list(self.connections):
                neighbor = self.get_rail(connection)
                if neighbor is not None:
                    neighbor.remove_soft_connections()
                    if neighbor.can_connect_to(self):
                        neighbor.connect_to(self)
        return self
