"""The game's ordinary blocks, registered from the generated table ``catalog_data``
(``tools/extract_block_table.py``, from the decompiled ``Blocks.java``; owner, 2026-10-14:
"include as many blocks as possible").

Each block gets its game settings (destroy time, push reaction, redstone-conductor rule,
see-through) and, by its Java class, its shape, properties and the behavior that matters
next to redstone:

* full cubes without logic of their own (``Block``, ores, copper, glass, ice, sponge, …);
* ``RotatedPillarBlock`` (logs, pillars: ``axis`` from the clicked face), blocks facing
  away from the player (glazed terracotta, carved pumpkins, the loom), snowy blocks,
  copper grates (``waterlogged``), huge mushroom blocks (sides hidden against each other);
* slabs and stairs (``StairBlock``: shape, corner shapes from the neighbors, mirroring);
* leaves (``LeavesBlock``: their ``distance`` follows neighbors a tick later, so observers
  see it change; they do not decay, random ticks are not simulated);
* carpets (break without a block below).

Blocks with mechanics of their own that are not modeled yet (falling blocks, doors,
fences, TNT, …) stay foreign blocks: drawn and saved, inert in the simulation.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import numpy as np

from redsim.core.direction import ALL, Axis, Direction
from redsim.core.pos import Pos, offset
from redsim.world.block import Block, BlockState, Conductor, PlacementContext, PushReaction
from redsim.world.blocks.catalog_data import BLOCKS, LEAF_DECAY_KEEPERS
from redsim.world.blocks.simple import SimpleBlock, SlabBlock
from redsim.world.properties import (
    HORIZONTAL_FACING,
    SNOWY,
    WATERLOGGED,
    Property,
    boolean,
    integer,
)
from redsim.world.shape import EMPTY, N, Shape, box

if TYPE_CHECKING:
    from redsim.sim.level import Level

AXIS = Property("axis", ("x", "y", "z"))
HALF = Property("half", ("top", "bottom"))
STAIRS_SHAPE = Property(
    "shape", ("straight", "inner_left", "inner_right", "outer_left", "outer_right")
)
DISTANCE = integer("distance", 1, 7)
PERSISTENT = boolean("persistent")
#: ``HugeMushroomBlock``: one property per side (``PipeBlock.PROPERTY_BY_DIRECTION``).
MUSHROOM_SIDES = {d: boolean(d.serialized) for d in ALL}

_FROM_YAW = (Direction.SOUTH, Direction.WEST, Direction.NORTH, Direction.EAST)


def horizontal_direction(yaw: float) -> Direction:
    """``Entity.getDirection`` (the player's horizontal facing)."""
    return _FROM_YAW[math.floor(yaw / 90.0 + 0.5) & 3]


def _conductor(rule: str) -> Conductor:
    return {"never": Conductor.NEVER, "always": Conductor.ALWAYS}.get(rule, Conductor.DEFAULT)


def shape_boxes(shape: Shape) -> list[tuple[tuple[int, int, int], tuple[int, int, int]]]:
    """Pixel boxes of a shape for drawing without the game's textures: the whole block,
    the filled eighths (slabs, stairs), or the bounding box."""
    if shape.is_full_block():
        return [((0, 0, 0), (N, N, N))]
    if shape.is_empty():
        return []
    grid = shape.grid
    half = N // 2
    boxes = []
    for x in (0, half):
        for y in (0, half):
            for z in (0, half):
                part = grid[x : x + half, y : y + half, z : z + half]
                if part.all():
                    boxes.append(((x, y, z), (x + half, y + half, z + half)))
                elif part.any():
                    x0, y0, z0, x1, y1, z1 = shape.bounds()
                    return [((x0, y0, z0), (x1, y1, z1))]
    return boxes


class CatalogBlock(SimpleBlock):
    """A block from the game's table: its settings, a fixed shape, no logic."""

    def __init__(self, block_id: str, spec: tuple[Any, ...], shape: Shape | None = None) -> None:
        kind, destroy, push, conductor, flags, color = spec
        self.kind = kind
        self.map_color = int(color)
        self.see_through = bool(flags & 2)  # noOcclusion: neighbors stay drawn
        super().__init__(
            block_id,
            shape=shape,
            destroy_speed=float(destroy),
            push_reaction=PushReaction[push],
            conductor=_conductor(conductor),
        )

    def pixel_boxes(self, state: BlockState) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
        return shape_boxes(self.get_shape(state))  # type: ignore[return-value]

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        """The state a player placing this block would get (``getStateForPlacement``):
        ``request`` has the clicked face and the player's yaw and pitch."""
        return self.get_state_for_placement(PlacementContext(level, pos, self.default_state))


class PillarBlock(CatalogBlock):
    """``RotatedPillarBlock``: ``axis`` is the clicked face's axis; quarter turns swap x and
    z (``rotate``)."""

    properties = (AXIS,)

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(self.default_state.with_(AXIS, "y"))

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        return self.default_state.with_(AXIS, request.clicked_face.axis.value)


class FacingBlock(CatalogBlock):
    """``HorizontalDirectionalBlock`` placed facing the player (glazed terracotta, carved
    pumpkins, the loom)."""

    properties = (HORIZONTAL_FACING,)

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH))

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        facing = horizontal_direction(request.yaw).opposite
        return self.default_state.with_(HORIZONTAL_FACING, facing)


class SnowyBlock(CatalogBlock):
    """``SnowyBlock`` (podzol, mycelium): ``snowy`` (no snow is simulated)."""

    properties = (SNOWY,)

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(self.default_state.with_(SNOWY, False))


class WaterloggedBlock(CatalogBlock):
    """A full cube that can hold water (copper grates); water is not simulated."""

    properties = (WATERLOGGED,)

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(self.default_state.with_(WATERLOGGED, False))


class HugeMushroomBlock(CatalogBlock):
    """``HugeMushroomBlock``: a side shows the pores (false) where the same block touches."""

    properties = tuple(MUSHROOM_SIDES.values())

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        state = self.default_state
        for prop in MUSHROOM_SIDES.values():
            state = state.with_(prop, True)
        self.register_default_state(state)

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        state = ctx.requested
        for direction, prop in MUSHROOM_SIDES.items():
            touching = ctx.level.get_block_state(offset(ctx.pos, direction)).block is self
            state = state.with_(prop, not touching)
        return state

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if neighbor.block is self:
            return state.with_(MUSHROOM_SIDES[direction], False)
        return state


class CatalogSlab(SlabBlock):
    """``SlabBlock`` of the table (every slab but the smooth stone one, which predates it)."""

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        kind, destroy, push, conductor, flags, color = spec
        super().__init__(block_id, destroy_speed=float(destroy))
        self.kind = kind
        self.map_color = int(color)
        self.see_through = False
        self.push_reaction = PushReaction[push]
        self.conductor = _conductor(conductor)

    def pixel_boxes(self, state: BlockState) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
        return shape_boxes(self.get_shape(state))  # type: ignore[return-value]

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        """``SlabBlock.getStateForPlacement``: the top half when placed against a block's
        bottom face (the editor has no hit point inside a side face: bottom there)."""
        top = request.clicked_face is Direction.DOWN
        return self.default_state.with_(SLAB_TYPE_PROPERTY, "top" if top else "bottom")


SLAB_TYPE_PROPERTY = SlabBlock.properties[0]


def _rotated_cw(grid: np.ndarray) -> np.ndarray:
    """A quarter turn clockwise seen from above (north → east), as the game's
    ``OctahedralGroup.BLOCK_ROT_Y_90``: (x, z) → (15 − z, x)."""
    return np.flip(np.transpose(grid, (2, 1, 0)), axis=0)


def _stair_shapes() -> dict[tuple[str, bool, Direction], Shape]:
    """``StairBlock`` shapes: (outer/straight/inner, bottom, facing) → shape."""
    outer = box(0, 0, 0, 16, 8, 16).grid | box(0, 8, 0, 8, 16, 8).grid
    straight = outer | _rotated_cw(outer)
    inner = straight | _rotated_cw(straight)
    out = {}
    for name, north in (("outer", outer), ("straight", straight), ("inner", inner)):
        for bottom in (True, False):
            grid = north if bottom else np.flip(north, axis=1)
            for direction in (Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST):
                out[(name, bottom, direction)] = Shape(np.ascontiguousarray(grid))
                grid = _rotated_cw(grid)
    return out


class StairBlock(CatalogBlock):
    """``StairBlock``: facing, half, shape (corners from the stairs behind and in front),
    waterlogged."""

    properties = (HORIZONTAL_FACING, HALF, STAIRS_SHAPE, WATERLOGGED)
    _shapes: dict[tuple[str, bool, Direction], Shape] | None = None

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH)
            .with_(HALF, "bottom")
            .with_(STAIRS_SHAPE, "straight")
            .with_(WATERLOGGED, False)
        )

    def get_shape(self, state: BlockState) -> Shape:
        if StairBlock._shapes is None:
            StairBlock._shapes = _stair_shapes()
        bottom = state.get(HALF) == "bottom"
        facing = state.get(HORIZONTAL_FACING)
        kind = state.get(STAIRS_SHAPE)
        group = "straight" if kind == "straight" else kind.split("_")[0]
        if kind == "inner_left":
            facing = facing.counter_clockwise()
        elif kind == "outer_right":
            facing = facing.clockwise()
        return StairBlock._shapes[(group, bottom, facing)]

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        """``getStateForPlacement``: facing the way the player looks; the top half against a
        block's bottom face (no hit point inside side faces in the editor: bottom)."""
        state = self.default_state.with_(
            HORIZONTAL_FACING, horizontal_direction(request.yaw)
        ).with_(HALF, "top" if request.clicked_face is Direction.DOWN else "bottom")
        return state.with_(STAIRS_SHAPE, stairs_shape(state, level, pos))

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return ctx.requested.with_(STAIRS_SHAPE, stairs_shape(ctx.requested, ctx.level, ctx.pos))

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction.axis.is_horizontal:
            return state.with_(STAIRS_SHAPE, stairs_shape(state, level, pos))
        return state

    def mirrored(self, state: BlockState, axis: str) -> BlockState | None:
        """``StairBlock.mirror`` (with its FRONT_BACK quirk: inner corners keep their side).
        ``axis="z"`` is ``LEFT_RIGHT``, ``"x"`` is ``FRONT_BACK``; None: the default."""
        facing = state.get(HORIZONTAL_FACING)
        shape = state.get(STAIRS_SHAPE)
        turned = state.with_(HORIZONTAL_FACING, facing.opposite)
        if axis == "z" and facing.axis is Axis.Z:
            swap = {"outer_left": "outer_right", "outer_right": "outer_left",
                    "inner_left": "inner_right", "inner_right": "inner_left"}  # fmt: skip
            return turned.with_(STAIRS_SHAPE, swap.get(shape, shape))
        if axis == "x" and facing.axis is Axis.X:
            swap = {"outer_left": "outer_right", "outer_right": "outer_left"}
            return turned.with_(STAIRS_SHAPE, swap.get(shape, shape))
        return None


def _is_stairs(state: BlockState) -> bool:
    return isinstance(state.block, StairBlock)


def stairs_shape(state: BlockState, level: Level, pos: Pos) -> str:
    """``StairBlock.getStairsShape``."""
    facing = state.get(HORIZONTAL_FACING)
    half = state.get(HALF)
    behind = level.get_block_state(offset(pos, facing))
    if _is_stairs(behind) and behind.get(HALF) == half:
        behind_facing = behind.get(HORIZONTAL_FACING)
        if behind_facing.axis is not facing.axis and _can_take_shape(
            state, level, pos, behind_facing.opposite
        ):
            return "outer_left" if behind_facing is facing.counter_clockwise() else "outer_right"
    front = level.get_block_state(offset(pos, facing.opposite))
    if _is_stairs(front) and front.get(HALF) == half:
        front_facing = front.get(HORIZONTAL_FACING)
        if front_facing.axis is not facing.axis and _can_take_shape(
            state, level, pos, front_facing
        ):
            return "inner_left" if front_facing is facing.counter_clockwise() else "inner_right"
    return "straight"


def _can_take_shape(state: BlockState, level: Level, pos: Pos, side: Direction) -> bool:
    neighbor = level.get_block_state(offset(pos, side))
    return (
        not _is_stairs(neighbor)
        or neighbor.get(HORIZONTAL_FACING) is not state.get(HORIZONTAL_FACING)
        or neighbor.get(HALF) != state.get(HALF)
    )


class LeavesBlock(CatalogBlock):
    """``LeavesBlock``: ``distance`` to the nearest log (``PREVENTS_NEARBY_LEAF_DECAY``),
    set a tick after a neighbor changes (``updateShape`` schedules, ``tick`` sets it with
    updates); no support on any face. Decay (random ticks) is not simulated."""

    properties = (DISTANCE, PERSISTENT, WATERLOGGED)

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(
            self.default_state.with_(DISTANCE, 7).with_(PERSISTENT, False).with_(WATERLOGGED, False)
        )

    def get_block_support_shape(self, state: BlockState) -> Shape:
        return EMPTY

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        return update_distance(self.default_state.with_(PERSISTENT, True), level, pos)

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        from_neighbor = distance_at(neighbor) + 1
        if from_neighbor != 1 or state.get(DISTANCE) != from_neighbor:
            level.schedule_tick(pos, self, 1)
        return state

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        level.set_block_and_update(pos, update_distance(state, level, pos))


def distance_at(state: BlockState) -> int:
    """``LeavesBlock.getDistanceAt``."""
    if state.block.id in LEAF_DECAY_KEEPERS:
        return 0
    if isinstance(state.block, LeavesBlock):
        return int(state.get(DISTANCE))
    return 7


def update_distance(state: BlockState, level: Level, pos: Pos) -> BlockState:
    """``LeavesBlock.updateDistance`` (directions in ``Direction.values()`` order)."""
    distance = 7
    for direction in ALL:
        distance = min(distance, distance_at(level.get_block_state(offset(pos, direction))) + 1)
        if distance == 1:
            break
    return state.with_(DISTANCE, distance)


class CarpetBlock(CatalogBlock):
    """``CarpetBlock``: one pixel high; breaks when the block below is air."""

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec, shape=box(0, 0, 0, 16, 1, 16))

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        return not level.get_block_state(offset(pos, Direction.DOWN)).is_air

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        return state if self.can_survive(state, level, pos) else level.air


#: Java class → how the simulator builds the block.
FULL_CUBES = frozenset({
    "Block", "DropExperienceBlock", "WeatheringCopperFullBlock", "TransparentBlock",
    "StainedGlassBlock", "TintedGlassBlock", "HalfTransparentBlock", "SpongeBlock",
    "WetSpongeBlock", "MagmaBlock", "AmethystBlock", "BuddingAmethystBlock",
    "CryingObsidianBlock", "NetherrackBlock", "InfestedBlock", "RootedDirtBlock",
    "NyliumBlock", "SculkBlock", "CraftingTableBlock", "SmithingTableBlock",
    "CartographyTableBlock", "PumpkinBlock", "BonemealableFeaturePlacerBlock", "IceBlock",
})  # fmt: skip
FACTORIES: dict[str, Callable[[str, tuple[Any, ...]], Block]] = {
    **{kind: CatalogBlock for kind in FULL_CUBES},
    "RotatedPillarBlock": PillarBlock,
    "HayBlock": PillarBlock,
    "InfestedRotatedPillarBlock": PillarBlock,
    "GlazedTerracottaBlock": FacingBlock,
    "CarvedPumpkinBlock": FacingBlock,
    "LoomBlock": FacingBlock,
    "SnowyBlock": SnowyBlock,
    "MyceliumBlock": SnowyBlock,
    "WeatheringCopperGrateBlock": WaterloggedBlock,
    "HugeMushroomBlock": HugeMushroomBlock,
    "SlabBlock": CatalogSlab,
    "WeatheringCopperSlabBlock": CatalogSlab,
    "StairBlock": StairBlock,
    "WeatheringCopperStairBlock": StairBlock,
    "LeavesBlock": LeavesBlock,
    "TintedParticleLeavesBlock": LeavesBlock,
    "UntintedParticleLeavesBlock": LeavesBlock,
    "MangroveLeavesBlock": LeavesBlock,
    "WoolCarpetBlock": CarpetBlock,
    "CarpetBlock": CarpetBlock,
}


def catalog_blocks(known: set[str]) -> list[Block]:
    """Blocks of the table the simulator can model, except the ``known`` ids."""
    out = []
    for block_id, spec in BLOCKS.items():
        factory = FACTORIES.get(spec[0])
        if factory is None or block_id in known or spec[4] & 1:  # no collision: not ours
            continue
        out.append(factory(block_id, spec))
    return out
