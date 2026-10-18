"""Lightning rods (all four oxidation stages, waxed or not): a rod that gives a 15 signal for
8 ticks when lightning strikes it.

Sources (relative to ``data/minecraft_src/server-src/net/minecraft/world/level/block/``):

* ``LightningRodBlock.java``: ``facing`` = the clicked face (``getStateForPlacement``),
  ``onLightningStrike`` (powered, the neighbors of the block behind it updated, unpowered
  by a tick 8 later), ``ownSignal`` 15 while powered, ``getDirectSignal`` (strong power only
  into the block it stands on or hangs from), ``onPlace`` (a powered rod arriving as a new
  block schedules that tick if none is pending), ``affectNeighborsAfterRemoval``, always a
  signal source (so redstone wire connects to it from every side).
* ``RodBlock.java``: the shape, a 4×4 rod along ``facing``'s axis; ``rotate`` / ``mirror``.
* ``WeatheringLightningRodBlock.java``: oxidation by random ticks (not simulated, and off on
  the test server: ``random_tick_speed 0``); every stage works the same.
* ``Blocks.java``: strength 3, ``forceSolidOn``, ``noOcclusion``, pushed and pulled by
  pistons; not a conductor (the shape is not a full block).
* ``entity/LightningBolt.java``: in its first tick a bolt powers the rod in the block it is
  in or just below (``powerLightningRod``), then a struck oxidized rod becomes
  ``lightning_rod`` again (``clearCopperOnLightningStrike``).

Lightning (weather) is not simulated. The editor's stand-in is a lightning strike on a rod
(``Level.lightning_strikes``, the ``strike`` command), which acts in the next tick's entity
phase like a bolt summoned on top of the rod. Not as in the game (doc/differences.md): the
bolt's fire (none on peaceful, the test server's difficulty), its damage to mobs and its
random walk that cleans copper blocks next to the rod are left out, and water is not
simulated (``waterlogged`` stays inert).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import Axis, Direction
from redsim.core.pos import Pos, offset
from redsim.world.block import BlockState, PlacementContext
from redsim.world.blocks.catalog import CatalogBlock
from redsim.world.properties import FACING, POWERED, WATERLOGGED
from redsim.world.shape import Shape, box

if TYPE_CHECKING:
    from redsim.sim.level import Level

#: ``LightningRodBlock.ACTIVATION_TICKS``.
ACTIVATION_TICKS = 8
#: ``RodBlock.SHAPES`` (``Shapes.rotateAllAxis(Block.cube(4, 4, 16))``).
SHAPES = {
    Axis.X: box(0, 6, 6, 16, 10, 10),
    Axis.Y: box(6, 0, 6, 10, 16, 10),
    Axis.Z: box(6, 6, 0, 10, 10, 16),
}
STAGES = ("", "exposed_", "weathered_", "oxidized_")
#: Every lightning rod id; the unwaxed ones weather and are cleaned by lightning.
ROD_IDS = tuple(
    f"minecraft:{wax}{stage}lightning_rod" for wax in ("", "waxed_") for stage in STAGES
)


class LightningRodBlock(CatalogBlock):
    """``LightningRodBlock`` (and ``WeatheringLightningRodBlock``)."""

    properties = (FACING, POWERED, WATERLOGGED)
    force_solid = True  # Properties.forceSolidOn

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.weathering = not block_id.startswith("minecraft:waxed_")
        self.register_default_state(
            self.default_state.with_(FACING, Direction.UP)
            .with_(WATERLOGGED, False)
            .with_(POWERED, False)
        )

    def get_shape(self, state: BlockState) -> Shape:
        direction: Direction = state.get(FACING)
        return SHAPES[direction.axis]

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement``: the given ``facing``, unpowered; no water (not
        simulated)."""
        return self.default_state.with_(FACING, ctx.requested.get(FACING))

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        """``facing`` = the clicked face."""
        return self.default_state.with_(FACING, request.clicked_face)

    # --- signals ------------------------------------------------------------------------
    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return 15 if state.get(POWERED) else 0

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        """Strong power only into the block behind it (the one it was placed against)."""
        return 15 if state.get(POWERED) and state.get(FACING) is direction else 0

    def update_neighbours(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``updateNeighbours``: the neighbors of the block behind the rod (not its own)."""
        direction: Direction = state.get(FACING)
        level.update_neighbors_at(offset(pos, direction.opposite), self)

    # --- lightning and ticks ------------------------------------------------------------
    def on_lightning_strike(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``onLightningStrike`` (the spark particles: ``levelEvent`` 3002, no effect)."""
        level.set_block_and_update(pos, state.with_(POWERED, True))
        self.update_neighbours(state, level, pos)
        level.schedule_tick(pos, self, ACTIVATION_TICKS)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        level.set_block_and_update(pos, state.with_(POWERED, False))
        self.update_neighbours(state, level, pos)

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        if (
            not state.is_(old_state.block)
            and state.get(POWERED)
            and not level.has_scheduled_tick(pos, self)
        ):
            level.schedule_tick(pos, self, ACTIVATION_TICKS)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        if state.get(POWERED):
            self.update_neighbours(state, level, pos)


def strike(level: Level, pos: Pos) -> bool:
    """A lightning bolt's first tick at the rod at ``pos`` (``LightningBolt.tick``):
    ``powerLightningRod``, then ``clearCopperOnLightningStrike`` for the struck block (an
    oxidized rod becomes ``lightning_rod``, keeping its state). False: no rod there.

    Not as in the game: the random walk that then cleans copper blocks next to the struck
    one (``randomWalkCleaningCopper``, the level's random) is left out; it changes nothing
    when no other copper block touches the rod."""
    state = level.get_block_state(pos)
    if not isinstance(state.block, LightningRodBlock):
        return False
    state.block.on_lightning_strike(state, level, pos)
    struck = level.get_block_state(pos)
    if isinstance(struck.block, LightningRodBlock) and struck.block.weathering:
        from redsim.world import blocks

        first = blocks.get("minecraft:lightning_rod")
        if struck.block is not first:  # WeatheringCopper.getFirst: the state carries over
            cleaned = first.default_state
            for prop in first.properties:
                cleaned = cleaned.with_(prop, struck.get(prop))
            level.set_block_and_update(pos, cleaned)
    return True
