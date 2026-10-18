"""Entities: falling blocks (``FallingBlockEntity``), with the game's movement code.

Ported from the decompiled 26.3 source:

* ``Entity.move`` (L736): collision against block collision shapes (``collide`` L1177,
  ``collideWithShapes`` L1284 with ``Shapes.collide`` / ``VoxelShape.collideX`` L251, the
  axis order of ``Direction.axisStepOrder``), the collision flags and ``onGround``, the
  supporting block (``checkSupportingBlock`` L710, ``CollisionGetter.findSupportingBlock``),
  bouncing (``restituteMovementAfterCollisions``: slime blocks), the block speed factor
  (honey, soul sand), piston limits (``limitPistonMovement``);
* ``Entity.applyEffectsFromBlocks`` / ``checkInsideBlocks`` (L985, L1320) with
  ``BlockGetter.forEachBlockIntersectedBetween``: ``stepOn`` (slime) and ``entityInside``
  (pressure plates, honey sliding);
* ``BlockCollisions`` (which blocks collide: the cursor's border cells only for large
  shapes and moving pistons);
* ``FallingBlockEntity.fall`` and ``tick``: gravity 0.04, drag 0.98, landing, placing the
  block, discarding it after 600 ticks;
* ``PistonMovingBlockEntity.moveCollidedEntities`` / ``moveStuckEntities`` (pistons push
  entities, slime launches them, honey carries them) and the moving block's collision
  shape with ``NOCLIP``.

Java's float constants (sizes, drag, offsets) are rounded to float32 exactly as Java widens
them (``f32``). Falling blocks are the only entities; they tick in the entity phase in the
order they were created (``Level.entities``, like ``EntityTickList``).

Not as in the game (each one is also marked where it happens with "Not as in the game";
every difference of the simulator is listed in doc/differences.md):

1. **Items.** A falling block that cannot land disappears; the game drops it as an item
   unless the game rule ``entity_drops`` is false, which is what the simulator does. If
   placing the block fails, the entity stays, as with ``entity_drops`` false.
2. **Fall distance.** ``checkFallDamage`` is not run: falling blocks keep no fall distance
   and ``Block.fallOn`` is never called. In the game this only hurts mobs and decides the
   anvil's random damage: an anvil that fell more than one block rolls its own random
   (5 % + 5 % per block) to become chipped or damaged (or break). The simulator's anvil
   always lands unchanged.
3. **Collision shapes** come from the simulator's 16³ voxel shapes, split into boxes
   (``local_boxes``). Fences, walls and closed fence gates are raised to their 1.5-block
   collision. The piston head's arm where it reaches into the base is left out (no entity
   fits there). Blocks the simulator does not model (foreign blocks) collide as a full
   cube if they are one and **not at all otherwise**: falling blocks pass through unmodeled
   beds, snow layers, … where the game lands them on top. (Scaffolding asks who collides:
   its own ``entity_collision_boxes``.)
   ``VoxelShape.collide`` runs on a grid made from those boxes; the game's shapes can have
   a finer grid, which changes results only for an entity that already overlaps a block.
4. **Other entities.** No entity collisions (boats, shulkers), no world border.
5. **Fluids and slowing blocks.** Water is not simulated. Falling blocks pass water blocks
   of an opened world like air, as in the game (they are not pushed by water). Concrete
   powder hardens where it touches water blocks or waterlogged blocks (``_is_water``), but
   the game's extra ray cast for powder falling faster than one block per tick (water it
   passed between two positions) is not ported. Cobwebs, berry bushes, powder snow
   (``stuckSpeedMultiplier``), fire and rain are not modeled (their blocks are foreign).
6. **Replaceable blocks** follow the game's ``replaceable`` flag; foreign blocks with a
   ``canBeReplaced`` of their own (snow layers, …) use the flag too.
"""

from __future__ import annotations

import math
import struct
from bisect import bisect_right
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

from redsim.core.direction import Axis, Direction
from redsim.core.pos import Pos

if TYPE_CHECKING:
    from redsim.sim.level import Level
    from redsim.world.block import BlockState

Vec = tuple[float, float, float]
#: ``AABB``: (minX, minY, minZ, maxX, maxY, maxZ).
Box = tuple[float, float, float, float, float, float]
ZERO: Vec = (0.0, 0.0, 0.0)


def f32(value: float) -> float:
    """A Java ``float`` widened to ``double``."""
    return float(struct.unpack("f", struct.pack("f", value))[0])


#: ``EntityTypes.FALLING_BLOCK.sized(0.98F, 0.98F)``; ``EntityDimensions.makeBoundingBox``
#: uses ``width / 2.0F`` and ``height`` as floats.
HALF_WIDTH = f32(f32(0.98) / 2.0)
HEIGHT = f32(0.98)
AIR_DRAG = f32(0.98)  # Entity.getAirDrag
GRAVITY = 0.04  # FallingBlockEntity.getDefaultGravity
EPSILON = 1.0e-7
ON_POS_LEGACY = f32(0.2)  # getOnPosLegacy
BELOW_MOVEMENT = f32(0.500001)  # getBlockPosBelowThatAffectsMyMovement
ON_POS = f32(1.0e-5)  # getOnPos
PISTON_LIMIT = 0.51  # applyPistonMovementRestriction
DEFLATE = f32(1.0e-5)  # checkInsideBlocks: the box at the target, deflated
MOVED_FAR = 0.9999900000002526**2


def make_box(a: Vec, b: Vec) -> Box:
    """``new AABB(...)``: corners in any order."""
    return (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]),
            max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))  # fmt: skip


def normalized(box: Box) -> Box:
    return make_box((box[0], box[1], box[2]), (box[3], box[4], box[5]))


def box_at(position: Vec) -> Box:
    x, y, z = position
    return (x - HALF_WIDTH, y, z - HALF_WIDTH, x + HALF_WIDTH, y + HEIGHT, z + HALF_WIDTH)


def intersects(a: Box, b: Box) -> bool:
    """``AABB.intersects``: overlapping with positive volume."""
    return (
        a[0] < b[3] and a[3] > b[0] and a[1] < b[4] and a[4] > b[1] and a[2] < b[5] and a[5] > b[2]
    )


def moved(box: Box, dx: float, dy: float, dz: float) -> Box:
    return (box[0] + dx, box[1] + dy, box[2] + dz, box[3] + dx, box[4] + dy, box[5] + dz)


def inflate(box: Box, dx: float, dy: float, dz: float) -> Box:
    return normalized(
        (box[0] - dx, box[1] - dy, box[2] - dz, box[3] + dx, box[4] + dy, box[5] + dz)
    )


def expand_towards(box: Box, d: Vec) -> Box:
    """``AABB.expandTowards``."""
    lo, hi = list(box[:3]), list(box[3:])
    for i in range(3):
        if d[i] < 0.0:
            lo[i] += d[i]
        elif d[i] > 0.0:
            hi[i] += d[i]
    return (lo[0], lo[1], lo[2], hi[0], hi[1], hi[2])


def length_sqr(v: Vec) -> float:
    return v[0] * v[0] + v[1] * v[1] + v[2] * v[2]


def add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def with_axis(v: Vec, axis: int, value: float) -> Vec:
    out = list(v)
    out[axis] = value
    return (out[0], out[1], out[2])


def floor(value: float) -> int:
    return math.floor(value)


def block_containing(position: Vec) -> Pos:
    return (floor(position[0]), floor(position[1]), floor(position[2]))


def axis_step_order(movement: Vec) -> tuple[int, int, int]:
    """``Direction.axisStepOrder``: Y first, then the larger horizontal axis."""
    return (1, 2, 0) if abs(movement[0]) < abs(movement[2]) else (1, 0, 2)


def mth_equal(a: float, b: float) -> bool:
    return abs(b - a) < ON_POS  # Mth.equal: 1.0E-5F


# =========================================================================== shapes
class CollisionShape:
    """A block's collision ``VoxelShape`` at its position: grid lines from its boxes,
    cells full where a box covers them (``VoxelShape.collide`` runs on that grid).

    Not as in the game: the game's shapes keep their own grids (``CubeVoxelShape`` at a
    1/2…1/8 resolution, merged grids of ``Shapes.or``), which can have more lines than
    the box edges used here. ``collide`` gives the same result either way unless the
    entity already overlaps the shape (doc item 3)."""

    __slots__ = ("boxes", "coords", "full")

    def __init__(self, boxes: list[Box]) -> None:
        self.boxes = boxes
        self.coords = [sorted({b[i] for b in boxes} | {b[i + 3] for b in boxes}) for i in range(3)]
        full: set[tuple[int, int, int]] = set()
        for b in boxes:
            ranges = [
                range(self.coords[i].index(b[i]), self.coords[i].index(b[i + 3])) for i in range(3)
            ]
            for x in ranges[0]:
                for y in ranges[1]:
                    for z in ranges[2]:
                        full.add((x, y, z))
        self.full = full

    def is_empty(self) -> bool:
        return not self.full

    def bounds(self) -> Box:
        return (
            self.coords[0][0], self.coords[1][0], self.coords[2][0],
            self.coords[0][-1], self.coords[1][-1], self.coords[2][-1],
        )  # fmt: skip

    def intersects(self, box: Box) -> bool:
        """``Shapes.joinIsNotEmpty(shape, Shapes.create(box), AND)``."""
        return any(intersects(b, box) for b in self.boxes)

    def _find(self, axis: int, coord: float) -> int:
        """``VoxelShape.findIndex``: the cell holding ``coord`` (-1 below, size above)."""
        return bisect_right(self.coords[axis], coord) - 1

    def collide(self, a: int, moving: Box, distance: float) -> float:
        """``VoxelShape.collide`` → ``collideX`` (L251) along axis ``a``."""
        if not self.full:
            return distance
        if abs(distance) < EPSILON:
            return 0.0
        b, c = (a + 1) % 3, (a + 2) % 3
        max_a, min_a = moving[a + 3], moving[a]
        a_min = self._find(a, min_a + EPSILON)
        a_max = self._find(a, max_a - EPSILON)
        b_min = max(0, self._find(b, moving[b] + EPSILON))
        b_max = min(len(self.coords[b]) - 1, self._find(b, moving[b + 3] - EPSILON) + 1)
        c_min = max(0, self._find(c, moving[c] + EPSILON))
        c_max = min(len(self.coords[c]) - 1, self._find(c, moving[c + 3] - EPSILON) + 1)
        a_size = len(self.coords[a]) - 1

        def full(ai: int, bi: int, ci: int) -> bool:
            cell = [0, 0, 0]
            cell[a], cell[b], cell[c] = ai, bi, ci
            return (cell[0], cell[1], cell[2]) in self.full

        if distance > 0.0:
            for ai in range(a_max + 1, a_size):
                for bi in range(b_min, b_max):
                    for ci in range(c_min, c_max):
                        if full(ai, bi, ci):
                            new_distance = self.coords[a][ai] - max_a
                            if new_distance >= -EPSILON:
                                distance = min(distance, new_distance)
                            return distance
        elif distance < 0.0:
            for ai in range(a_min - 1, -1, -1):
                for bi in range(b_min, b_max):
                    for ci in range(c_min, c_max):
                        if full(ai, bi, ci):
                            new_distance = self.coords[a][ai + 1] - min_a
                            if new_distance <= EPSILON:
                                distance = max(distance, new_distance)
                            return distance
        return distance


_LOCAL_BOXES: dict[Any, tuple[Box, ...]] = {}


def local_boxes(state: BlockState) -> tuple[Box, ...]:
    """A block state's collision shape as boxes in block units (cached). Fences, walls
    and closed fence gates reach 1.5 blocks up (their 24-pixel collision shapes).

    Not as in the game (doc item 3): the shapes come from the simulator's voxel shapes,
    which end at the block's cell. The piston head's arm loses the part that reaches into
    the base (no entity fits there). Foreign blocks (``ForeignBlock``, not modeled) give
    a full cube or nothing: a non-full foreign block (bed, cauldron, snow layer, …) has
    no collision here, so falling blocks fall through it."""
    found = _LOCAL_BOXES.get(state)
    if found is not None:
        return found
    from redsim.world.blocks.catalog import shape_boxes

    tall = getattr(state.block, "collision_height", 16)
    out = []
    for (x0, y0, z0), (x1, y1, z1) in shape_boxes(state.get_collision_shape()):
        top = tall if y1 == 16 else y1
        out.append((x0 / 16.0, y0 / 16.0, z0 / 16.0, x1 / 16.0, top / 16.0, z1 / 16.0))
    result = tuple(out)
    _LOCAL_BOXES[state] = result
    return result


def has_large_collision_shape(state: BlockState) -> bool:
    """``BlockStateBase.hasLargeCollisionShape`` (moving pistons: no cache, so true)."""
    from redsim.world import blocks

    if state.is_(blocks.MOVING_PISTON) or state.block.dynamic_shape:  # no shape cache
        return True
    return any(b[0] < 0 or b[1] < 0 or b[2] < 0 or b[3] > 1 or b[4] > 1 or b[5] > 1
               for b in local_boxes(state))  # fmt: skip


#: ``PistonMovingBlockEntity.NOCLIP``: while a piston moves entities in this direction, its
#: own moving blocks do not collide with them.
_noclip: list[Direction | None] = [None]


def block_shape(
    level: Level, pos: Pos, state: BlockState, entity_bottom: float | None = None
) -> CollisionShape | None:
    """``state.getCollisionShape(level, pos, context).move(pos)`` (None: empty). The
    context is an entity whose feet are at ``entity_bottom``, or a player placing a block
    (None); only scaffolding asks (``entity_collision_boxes``)."""
    from redsim.world import blocks

    x, y, z = pos
    own = getattr(state.block, "entity_collision_boxes", None)
    if state.is_(blocks.MOVING_PISTON):
        boxes = moving_piston_boxes(level, pos)
    elif own is not None:
        boxes = list(own(state, pos, entity_bottom))
    else:
        boxes = list(local_boxes(state))
    if not boxes:
        return None
    return CollisionShape([(b[0] + x, b[1] + y, b[2] + z, b[3] + x, b[4] + y, b[5] + z)
                           for b in boxes])  # fmt: skip


def moving_piston_boxes(level: Level, pos: Pos) -> list[Box]:
    """``PistonMovingBlockEntity.getCollisionShape`` L347 in block units (the moved
    block reaches out of its cell)."""
    from redsim.world import blocks
    from redsim.world.blocks.piston import (
        EXTENDED,
        FACING,
        SHORT,
        PistonBaseBlock,
        PistonMovingBlockEntity,
    )

    entity = level.get_block_entity(pos)
    if not isinstance(entity, PistonMovingBlockEntity):
        return []
    head: list[Box] = []
    if (
        not entity.extending
        and entity.is_source
        and isinstance(entity.moved_state.block, PistonBaseBlock)
    ):
        head = list(local_boxes(entity.moved_state.with_(EXTENDED, True)))
    movement = entity.direction if entity.extending else entity.direction.opposite
    if entity.progress < 1.0 and _noclip[0] is movement:
        return head
    if entity.is_source:
        short = entity.extending != ((1.0 - entity.progress) < 0.25)
        state = blocks.PISTON_HEAD.default_state.with_(FACING, entity.direction).with_(SHORT, short)
    else:
        state = entity.moved_state
    extended = f32(entity.extended_progress(entity.progress))
    sx, sy, sz = entity.direction.step
    dx, dy, dz = sx * extended, sy * extended, sz * extended
    return head + [moved(b, dx, dy, dz) for b in local_boxes(state)]


def block_collisions(
    level: Level, box: Box, entity_bottom: float
) -> Iterator[tuple[Pos, CollisionShape]]:
    """``BlockCollisions`` (no suffocation filter): the shapes intersecting ``box``, in
    the cursor's order (x fastest, then y, then z), for an entity whose feet are at
    ``entity_bottom`` (``CollisionContext.of(entity)``)."""
    x0, x1 = floor(box[0] - EPSILON) - 1, floor(box[3] + EPSILON) + 1
    y0, y1 = floor(box[1] - EPSILON) - 1, floor(box[4] + EPSILON) + 1
    z0, z1 = floor(box[2] - EPSILON) - 1, floor(box[5] + EPSILON) + 1
    from redsim.world import blocks

    for z in range(z0, z1 + 1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                face = (x in (x0, x1)) + (y in (y0, y1)) + (z in (z0, z1))
                if face == 3:
                    continue
                pos = (x, y, z)
                state = level.get_block_state(pos)
                if state.is_air:
                    continue
                if face == 1 and not has_large_collision_shape(state):
                    continue
                if face == 2 and not state.is_(blocks.MOVING_PISTON):
                    continue
                shape = block_shape(level, pos, state, entity_bottom)
                if shape is not None and shape.intersects(box):
                    yield pos, shape


def collide_with_shapes(movement: Vec, box: Box, shapes: list[CollisionShape]) -> Vec:
    """``Entity.collideWithShapes`` with ``Shapes.collide`` per axis."""
    if not shapes:
        return movement
    resolved: Vec = ZERO
    for axis in axis_step_order(movement):
        amount = movement[axis]
        if amount != 0.0:
            moving = moved(box, *resolved)
            distance = amount
            for shape in shapes:
                if abs(distance) < EPSILON:
                    distance = 0.0
                    break
                distance = shape.collide(axis, moving, distance)
            resolved = with_axis(resolved, axis, distance)
    return resolved


def find_supporting_block(level: Level, position: Vec, box: Box) -> Pos | None:
    """``CollisionGetter.findSupportingBlock``: the colliding block nearest the entity
    (ties: the larger position in ``Vec3i.compareTo``)."""
    best: Pos | None = None
    best_distance = math.inf
    for pos, _ in block_collisions(level, box, position[1]):
        dx = pos[0] + 0.5 - position[0]
        dy = pos[1] + 0.5 - position[1]
        dz = pos[2] + 0.5 - position[2]
        distance = dx * dx + dy * dy + dz * dz
        if distance < best_distance or (
            distance == best_distance and (best is None or _compare(best, pos) < 0)
        ):
            best, best_distance = pos, distance
    return best


def _compare(a: Pos, b: Pos) -> int:
    """``Vec3i.compareTo``: by y, then z, then x."""
    if a[1] == b[1]:
        return a[0] - b[0] if a[2] == b[2] else a[2] - b[2]
    return a[1] - b[1]


# =========================================================================== traversal
def _corners_in_direction(first: Pos, second: Pos, direction: Vec) -> Iterator[Pos]:
    """``BlockPos.betweenCornersInDirection``."""
    lo = [min(first[i], second[i]) for i in range(3)]
    hi = [max(first[i], second[i]) for i in range(3)]
    diff = [hi[i] - lo[i] for i in range(3)]
    start = [lo[i] if direction[i] >= 0.0 else hi[i] for i in range(3)]
    axes = axis_step_order(direction)
    steps = [1 if direction[a] >= 0.0 else -1 for a in axes]
    maxima = [diff[a] for a in axes]
    for i in range(maxima[0] + 1):
        for j in range(maxima[1] + 1):
            for k in range(maxima[2] + 1):
                p = list(start)
                p[axes[0]] += steps[0] * i
                p[axes[1]] += steps[1] * j
                p[axes[2]] += steps[2] * k
                yield (p[0], p[1], p[2])


def _box_corners(box: Box) -> tuple[Pos, Pos]:
    return (
        (floor(box[0]), floor(box[1]), floor(box[2])),
        (floor(box[3]), floor(box[4]), floor(box[5])),
    )


def _furthest_corner(d: Vec) -> tuple[int, int, int]:
    """``BlockGetter.getFurthestCorner``."""
    x_dot, y_dot, z_dot = abs(d[0]), abs(d[1]), abs(d[2])
    xs = 1 if d[0] >= 0.0 else -1
    ys = 1 if d[1] >= 0.0 else -1
    zs = 1 if d[2] >= 0.0 else -1
    if x_dot <= y_dot and x_dot <= z_dot:
        return (-xs, -zs, ys)
    return (zs, -ys, -xs) if y_dot <= z_dot else (-ys, xs, -zs)


def _sign(value: float) -> int:
    return 0 if value == 0.0 else (1 if value > 0.0 else -1)


def _frac(value: float) -> float:
    return value - math.floor(value)


def clip_box(box: Box, start: Vec, end: Vec) -> Vec | None:
    """``AABB.clip``: where the segment enters the box (None: it does not)."""
    scale = [1.0]
    d = sub(end, start)
    hit = False

    def clip_point(da: float, db: float, dc: float, point: float, min_b: float,
                   max_b: float, min_c: float, max_c: float, fa: float, fb: float,
                   fc: float) -> bool:  # fmt: skip
        s = (point - fa) / da
        pb = fb + s * db
        pc = fc + s * dc
        if (0.0 < s < scale[0] and min_b - EPSILON < pb < max_b + EPSILON
                and min_c - EPSILON < pc < max_c + EPSILON):  # fmt: skip
            scale[0] = s
            return True
        return False

    x0, y0, z0, x1, y1, z1 = box
    fx, fy, fz = start
    dx, dy, dz = d
    if dx > EPSILON:
        hit |= clip_point(dx, dy, dz, x0, y0, y1, z0, z1, fx, fy, fz)
    elif dx < -EPSILON:
        hit |= clip_point(dx, dy, dz, x1, y0, y1, z0, z1, fx, fy, fz)
    if dy > EPSILON:
        hit |= clip_point(dy, dz, dx, y0, z0, z1, x0, x1, fy, fz, fx)
    elif dy < -EPSILON:
        hit |= clip_point(dy, dz, dx, y1, z0, z1, x0, x1, fy, fz, fx)
    if dz > EPSILON:
        hit |= clip_point(dz, dx, dy, z0, x0, x1, y0, y1, fz, fx, fy)
    elif dz < -EPSILON:
        hit |= clip_point(dz, dx, dy, z1, x0, x1, y0, y1, fz, fx, fy)
    if not hit:
        return None
    s = scale[0]
    return (fx + s * dx, fy + s * dy, fz + s * dz)


def contains(box: Box, point: Vec) -> bool:
    """``AABB.contains(Vec3)``."""
    return (box[0] <= point[0] < box[3] and box[1] <= point[1] < box[4]
            and box[2] <= point[2] < box[5])  # fmt: skip


def collided_along_vector(box: Box, vector: Vec, parts: list[Box]) -> bool:
    """``AABB.collidedAlongVector``: whether ``box``, moved by ``vector``, touches one of
    ``parts`` (each grown by half the box, so its center's path is tested)."""
    start = ((box[0] + box[3]) * 0.5, (box[1] + box[4]) * 0.5, (box[2] + box[5]) * 0.5)
    end = add(start, vector)
    hx = (box[3] - box[0]) * 0.5 - EPSILON
    hy = (box[4] - box[1]) * 0.5 - EPSILON
    hz = (box[5] - box[2]) * 0.5 - EPSILON
    for part in parts:
        grown = inflate(part, hx, hy, hz)
        if contains(grown, end) or contains(grown, start):
            return True
        if clip_box(grown, start, end) is not None:
            return True
    return False


def for_each_block_between(
    start: Vec, end: Vec, target: Box, visit: Callable[[Pos, int], bool]
) -> bool:
    """``BlockGetter.forEachBlockIntersectedBetween`` (L173)."""
    travel = sub(end, start)
    if length_sqr(travel) < ON_POS * ON_POS:
        lo, hi = _box_corners(target)
        for z in range(lo[2], hi[2] + 1):
            for y in range(lo[1], hi[1] + 1):
                for x in range(lo[0], hi[0] + 1):
                    if not visit((x, y, z), 0):
                        return False
        return True
    visited: set[Pos] = set()
    back = moved(target, -travel[0], -travel[1], -travel[2])
    for pos in _corners_in_direction(*_box_corners(back), travel):
        if not visit(pos, 0):
            return False
        visited.add(pos)
    iterations = _collisions_along_travel(visited, travel, target, visit)
    if iterations < 0:
        return False
    for pos in _corners_in_direction(*_box_corners(target), travel):
        if pos not in visited:
            visited.add(pos)
            if not visit(pos, iterations + 1):
                return False
    return True


def _collisions_along_travel(
    visited: set[Pos], delta: Vec, target: Box, visit: Callable[[Pos, int], bool]
) -> int:
    """``BlockGetter.addCollisionsAlongTravel`` L209."""
    size = (target[3] - target[0], target[4] - target[1], target[5] - target[2])
    corner = _furthest_corner(delta)
    center = tuple(target[i] + 0.5 * (target[i + 3] - target[i]) for i in range(3))
    to_corner = tuple(center[i] + size[i] * 0.5 * corner[i] for i in range(3))
    from_corner = (to_corner[0] - delta[0], to_corner[1] - delta[1], to_corner[2] - delta[2])
    cell = [floor(from_corner[0]), floor(from_corner[1]), floor(from_corner[2])]
    sign = [_sign(delta[0]), _sign(delta[1]), _sign(delta[2])]
    t_delta = [math.inf if sign[i] == 0 else sign[i] / delta[i] for i in range(3)]
    t_delta = [1.7976931348623157e308 if v == math.inf else v for v in t_delta]
    t = [
        t_delta[i] * (1.0 - _frac(from_corner[i]) if sign[i] > 0 else _frac(from_corner[i]))
        for i in range(3)
    ]
    iterations = 0
    while t[0] <= 1.0 or t[1] <= 1.0 or t[2] <= 1.0:
        if t[0] < t[1]:
            if t[0] < t[2]:
                cell[0] += sign[0]
                t[0] += t_delta[0]
            else:
                cell[2] += sign[2]
                t[2] += t_delta[2]
        elif t[1] < t[2]:
            cell[1] += sign[1]
            t[1] += t_delta[1]
        else:
            cell[2] += sign[2]
            t[2] += t_delta[2]
        cell_box = (float(cell[0]), float(cell[1]), float(cell[2]),
                    cell[0] + 1.0, cell[1] + 1.0, cell[2] + 1.0)  # fmt: skip
        hit = clip_box(cell_box, from_corner, to_corner)  # type: ignore[arg-type]
        if hit is None:
            continue
        iterations += 1
        hx = min(max(hit[0], cell[0] + ON_POS), cell[0] + 1.0 - ON_POS)
        hy = min(max(hit[1], cell[1] + ON_POS), cell[1] + 1.0 - ON_POS)
        hz = min(max(hit[2], cell[2] + ON_POS), cell[2] + 1.0 - ON_POS)
        opposite = (
            floor(hx - size[0] * corner[0]),
            floor(hy - size[1] * corner[1]),
            floor(hz - size[2] * corner[2]),
        )
        current = iterations
        for pos in _corners_in_direction((cell[0], cell[1], cell[2]), opposite, delta):
            if pos not in visited:
                visited.add(pos)
                if not visit(pos, current):
                    return -1
    return iterations


# =========================================================================== entity
class FallingBlockEntity:
    """``FallingBlockEntity`` (and the parts of ``Entity`` it uses)."""

    __slots__ = (
        "id", "state", "position", "old", "delta", "time", "drop_item", "cancel_drop",
        "hurt_entities", "on_ground", "horizontal_collision", "vertical_collision",
        "vertical_collision_below", "main_support", "on_ground_no_blocks", "movements",
        "piston_deltas", "piston_deltas_time", "removed", "start_pos",
    )  # fmt: skip

    def __init__(self, entity_id: int, state: BlockState, position: Vec) -> None:
        self.id = entity_id
        self.state = state
        self.position = position
        self.old = position
        self.delta: Vec = ZERO
        self.time = 0
        self.drop_item = True
        self.cancel_drop = False
        self.hurt_entities = False
        self.on_ground = False
        self.horizontal_collision = False
        self.vertical_collision = False
        self.vertical_collision_below = False
        self.main_support: Pos | None = None
        self.on_ground_no_blocks = False
        #: ``movementThisTick``: (from, to, the movement asked for or None).
        self.movements: list[tuple[Vec, Vec, Vec | None]] = []
        self.piston_deltas = [0.0, 0.0, 0.0]
        self.piston_deltas_time = 0
        self.removed = False
        self.start_pos = block_containing(position)

    # ------------------------------------------------------------------ basics
    @property
    def box(self) -> Box:
        return box_at(self.position)

    @property
    def block_position(self) -> Pos:
        return block_containing(self.position)

    def clone(self) -> FallingBlockEntity:
        other = FallingBlockEntity.__new__(FallingBlockEntity)
        for name in FallingBlockEntity.__slots__:
            setattr(other, name, getattr(self, name))
        other.movements = list(self.movements)
        other.piston_deltas = list(self.piston_deltas)
        return other

    def discard(self, level: Level) -> None:
        self.removed = True
        level.entities.pop(self.id, None)

    # ------------------------------------------------------------------ tick
    def tick(self, level: Level) -> None:
        """``tickNonPassenger``: ``commonTick`` then ``FallingBlockEntity.tick``."""
        from redsim.world.blocks.falling import ConcretePowderBlock, is_free, on_land

        self.old = self.position  # setOldPosAndRot
        if self.state.is_air:
            self.discard(level)
            return
        self.time += 1
        self.delta = (self.delta[0], self.delta[1] - GRAVITY, self.delta[2])
        self.move(level, self.delta, piston=False)
        self.apply_effects_from_blocks(level)
        # (handlePortal: portals are not simulated.)
        if not self.removed:
            pos = self.block_position
            block = self.state.block
            is_concrete = isinstance(block, ConcretePowderBlock)
            stuck_in_water = is_concrete and _is_water(level.get_block_state(pos))
            # Not as in the game: for concrete powder moving faster than one block per tick
            # (motion² > 1) the game also ray casts from the old to the new position and
            # stops at water it passed (ClipContext SOURCE_ONLY); not ported (doc item 5).
            if not self.on_ground and not stuck_in_water:
                y = pos[1]
                if (self.time > 100 and (y <= level.min_y or y > level.max_y)) or self.time > 600:
                    # Not as in the game: with entity_drops it drops as an item (doc item 1).
                    self.discard(level)
            else:
                current = level.get_block_state(pos)
                self.delta = (self.delta[0] * 0.7, self.delta[1] * -0.5, self.delta[2] * 0.7)
                from redsim.world import blocks
                from redsim.world.blocks.openable import can_be_replaced

                if not current.is_(blocks.MOVING_PISTON):
                    if self.cancel_drop:
                        self.discard(level)
                    else:
                        may_replace = can_be_replaced(current)
                        below = level.get_block_state((pos[0], pos[1] - 1, pos[2]))
                        would_continue = is_free(below) and (not is_concrete or not stuck_in_water)
                        would_survive = self.state.can_survive(level, pos) and not would_continue
                        if may_replace and would_survive:
                            # (No falling block has block-entity data. Water is not
                            # simulated, so a falling scaffolding never takes up water.)
                            if level.set_block_and_update(pos, self.state):
                                self.discard(level)
                                on_land(level, pos, self.state, current)
                            # Not as in the game: if placing fails, the game discards it
                            # and drops an item when entity_drops is on; the simulator
                            # follows entity_drops false: the entity stays (doc item 1).
                        else:
                            # Not as in the game: with entity_drops it drops as an item
                            # here (doc item 1).
                            self.discard(level)
        self.delta = (self.delta[0] * AIR_DRAG, self.delta[1] * AIR_DRAG, self.delta[2] * AIR_DRAG)

    # ------------------------------------------------------------------ movement
    def move(self, level: Level, delta: Vec, piston: bool) -> None:
        """``Entity.move`` L736 (``MoverType.SELF`` or ``PISTON``)."""
        if piston:
            delta = self._limit_piston_movement(level, delta)
            if delta == ZERO:
                return
        # Not as in the game: stuckSpeedMultiplier (cobwebs, berry bushes, powder snow) is
        # left out: those blocks are foreign (doc item 5).
        movement = self._collide(level, delta)
        movement_length = length_sqr(movement)
        if movement_length > EPSILON or length_sqr(delta) - movement_length < EPSILON:
            # (The game's fall-distance reset by a ray cast belongs to doc item 2.)
            new_position = add(self.position, movement)
            self._add_movement((self.position, new_position, delta))
            self.position = new_position
        x_collision = not mth_equal(delta[0], movement[0])
        z_collision = not mth_equal(delta[2], movement[2])
        self.horizontal_collision = x_collision or z_collision
        moved_vertically = abs(delta[1]) > 0.0
        # isLocalInstanceAuthoritative() is true on the server: always updated.
        self.vertical_collision = delta[1] != movement[1]
        self.vertical_collision_below = self.vertical_collision and delta[1] < 0.0
        self.on_ground = self.vertical_collision_below
        self._check_supporting_block(level, self.on_ground, movement)
        effect_pos = self.on_pos(level, ON_POS_LEGACY)
        effect_state = level.get_block_state(effect_pos)
        # Not as in the game: checkFallDamage (fall distance, Block.fallOn) is not run; in
        # the game it only hurts mobs and rolls the anvil's random damage (doc item 2).
        if (moved_vertically and self.vertical_collision) or self.horizontal_collision:
            self._restitute(effect_state, x_collision, z_collision, movement)
        factor = self._block_speed_factor(level)
        self.delta = (self.delta[0] * factor, self.delta[1], self.delta[2] * factor)

    def _add_movement(self, movement: tuple[Vec, Vec, Vec | None]) -> None:
        if len(self.movements) >= 100:
            first = self.movements.pop(0)
            second = self.movements.pop(0)
            self.movements.insert(0, (first[0], second[1], None))
        self.movements.append(movement)

    def _limit_piston_movement(self, level: Level, vec: Vec) -> Vec:
        """``limitPistonMovement``: at most 0.51 per axis and game tick."""
        if length_sqr(vec) <= EPSILON:
            return vec
        if level.game_time != self.piston_deltas_time:
            self.piston_deltas = [0.0, 0.0, 0.0]
            self.piston_deltas_time = level.game_time
        for axis in (0, 1, 2):
            if vec[axis] != 0.0:
                amount = vec[axis]
                limited = min(max(amount + self.piston_deltas[axis], -PISTON_LIMIT), PISTON_LIMIT)
                amount = limited - self.piston_deltas[axis]
                self.piston_deltas[axis] = limited
                return ZERO if abs(amount) <= ON_POS else with_axis(ZERO, axis, amount)
        return ZERO

    def _collide(self, level: Level, movement: Vec) -> Vec:
        """``Entity.collide`` (no step-up: falling blocks have ``maxUpStep`` 0).

        Not as in the game: no entity colliders and no world border (doc item 4)."""
        if length_sqr(movement) == 0.0:
            return movement
        box = self.box
        swept = expand_towards(box, movement)
        shapes = [shape for _, shape in block_collisions(level, swept, self.position[1])]
        return collide_with_shapes(movement, box, shapes)

    def _check_supporting_block(self, level: Level, on_ground: bool, movement: Vec | None) -> None:
        """``checkSupportingBlock`` L710."""
        if on_ground:
            b = self.box
            test = (b[0], b[1] - 1.0e-6, b[2], b[3], b[1], b[5])
            support = find_supporting_block(level, self.position, test)
            if support is not None or self.on_ground_no_blocks:
                self.main_support = support
            elif movement is not None:
                shifted = moved(test, -movement[0], 0.0, -movement[2])
                support = find_supporting_block(level, self.position, shifted)
                self.main_support = support
            self.on_ground_no_blocks = support is None
        else:
            self.on_ground_no_blocks = False
            self.main_support = None

    def on_pos(self, level: Level, offset: float) -> Pos:
        """``getOnPos(offset)``."""
        x, y, z = self.position
        if self.main_support is not None:
            if not offset > ON_POS:
                return self.main_support
            below = level.get_block_state(self.main_support)
            from redsim.world.blocks.connecting import FenceBlock, WallBlock
            from redsim.world.blocks.openable import FenceGateBlock

            fence = isinstance(below.block, FenceBlock)
            if ((not offset <= 0.5 or not fence) and not isinstance(below.block, WallBlock)
                    and not isinstance(below.block, FenceGateBlock)):  # fmt: skip
                return (self.main_support[0], floor(y - offset), self.main_support[2])
            return self.main_support
        return (floor(x), floor(y - offset), floor(z))

    def _restitute(
        self, effect_state: BlockState, x_collision: bool, z_collision: bool, movement: Vec
    ) -> None:
        """``restituteMovementAfterCollisions``: falling blocks only bounce off slime."""
        restitution = 0.0  # getEntityBounciness
        current = self.delta
        after = current
        if x_collision:
            after = with_axis(after, 0, -current[0] * restitution)
        if z_collision:
            after = with_axis(after, 2, -current[2] * restitution)
        if self.vertical_collision:
            if self.vertical_collision_below:
                suppressed = getattr(effect_state.block, "suppresses_bounce", False)
                # getBlockBounciness: the block's float restitution × 0.8F (not living).
                bounciness = f32(f32(getattr(effect_state.block, "bounce_restitution", 0.0))
                                 * f32(0.8))  # fmt: skip
                restitution = (
                    max(restitution, bounciness)
                    if not (-current[1] <= GRAVITY) and not suppressed
                    else 0.0
                )
            if restitution > 0.0:
                portion = movement[1] / current[1]
                compensation = portion * GRAVITY
                drag = 1.0 + portion * (AIR_DRAG - 1.0)  # Mth.lerp(portion, 1.0, drag)
            else:
                compensation, drag = 0.0, 1.0
            after = with_axis(after, 1, (compensation - current[1]) * drag * restitution)
        self.delta = after

    def _block_speed_factor(self, level: Level) -> float:
        """``getBlockSpeedFactor``: honey and soul sand slow down horizontally."""
        here = level.get_block_state(self.block_position)
        factor = f32(getattr(here.block, "speed_factor", 1.0))
        if here.block.id in ("minecraft:water", "minecraft:bubble_column"):
            return factor
        if factor == 1.0:
            below = level.get_block_state(self.on_pos(level, BELOW_MOVEMENT))
            return f32(getattr(below.block, "speed_factor", 1.0))
        return factor

    # ------------------------------------------------------------------ block effects
    def apply_effects_from_blocks(self, level: Level) -> None:
        """``applyEffectsFromBlocks()`` with this tick's movements."""
        final = list(self.movements)
        self.movements = []
        if not final:
            final.append((self.old, self.position, None))
        elif length_sqr(sub(final[-1][1], self.position)) > f32(9.9999994e-11):
            final.append((final[-1][1], self.position, None))
        self._apply_effects(level, final)

    def apply_effects_between(self, level: Level, start: Vec, end: Vec) -> None:
        """``applyEffectsFromBlocks(from, to)`` (after a piston moved the entity)."""
        self._apply_effects(level, [(start, end, None)])

    def _apply_effects(self, level: Level, movements: list[tuple[Vec, Vec, Vec | None]]) -> None:
        if self.removed:
            return
        # Not as in the game: fire, freezing, rain and the fluids' entityInside are left
        # out (fire, powder snow and water are not simulated; doc item 5).
        if self.on_ground:
            effect_pos = self.on_pos(level, ON_POS_LEGACY)
            effect_state = level.get_block_state(effect_pos)
            step_on = getattr(effect_state.block, "step_on", None)
            if step_on is not None:
                step_on(level, effect_pos, effect_state, self)
        visited: set[Pos] = set()
        for start, end, original in movements:
            pos = start
            delta = sub(end, start)
            budget = 16
            if original is not None and length_sqr(delta) > 0.0:
                for axis in axis_step_order(original):
                    amount = delta[axis]
                    if amount != 0.0:
                        to = with_axis(pos, axis, pos[axis] + amount)
                        budget -= self._check_inside(level, pos, to, visited, budget)
                        pos = to
            else:
                budget -= self._check_inside(level, start, end, visited, 16)
            if budget <= 0:
                self._check_inside(level, end, end, visited, 1)

    def _check_inside(
        self, level: Level, start: Vec, end: Vec, visited: set[Pos], budget: int
    ) -> int:
        """``checkInsideBlocks(from, to, ...)`` L1365: ``entityInside`` of every block the
        box passes. A block counts as inside when its ``getEntityInsideCollisionShape`` is
        a full block (the default) or the box moving from ``start`` to ``end`` touches it
        (``collidedWithShapeMovingFrom``): of the simulated blocks only tripwire has a
        smaller one (``entity_inside_boxes``); cauldrons have one too but do nothing to a
        falling block, and foreign blocks do nothing to entities."""
        target = inflate(box_at(end), -DEFLATE, -DEFLATE, -DEFLATE)
        count = [0]

        def visit(pos: Pos, iteration: int) -> bool:
            if self.removed or iteration >= budget:
                return False
            count[0] = iteration
            state = level.get_block_state(pos)
            if state.is_air:
                return True
            inside_boxes = getattr(state.block, "entity_inside_boxes", None)
            if inside_boxes is not None:
                x, y, z = pos
                parts = [moved(b, x, y, z) for b in inside_boxes(state)]
                if not collided_along_vector(box_at(start), sub(end, start), parts):
                    return True
            if pos in visited:
                return True
            visited.add(pos)
            inside = getattr(state.block, "entity_inside_entity", None)
            if inside is not None:
                inside(state, level, pos, self)
            return True

        for_each_block_between(start, end, target, visit)
        return count[0] + 1

    # ------------------------------------------------------------------ saving
    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "state": repr(self.state),
            "pos": list(self.position),
            "old": list(self.old),
            "motion": list(self.delta),
            "time": self.time,
            "cancel_drop": self.cancel_drop,
            "hurt_entities": self.hurt_entities,
            "on_ground": self.on_ground,
            "collisions": [
                self.horizontal_collision,
                self.vertical_collision,
                self.vertical_collision_below,
            ],  # fmt: skip
            "support": list(self.main_support) if self.main_support is not None else None,
            "on_ground_no_blocks": self.on_ground_no_blocks,
            "piston_deltas": list(self.piston_deltas),
            "piston_deltas_time": self.piston_deltas_time,
            "start": list(self.start_pos),
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> FallingBlockEntity:
        from redsim.world import blocks

        x, y, z = (float(v) for v in data["pos"])
        entity = FallingBlockEntity(int(data["id"]), blocks.parse_state(data["state"]), (x, y, z))
        entity.old = tuple(float(v) for v in data["old"])  # type: ignore[assignment]
        entity.delta = tuple(float(v) for v in data["motion"])  # type: ignore[assignment]
        entity.time = int(data["time"])
        entity.cancel_drop = bool(data["cancel_drop"])
        entity.hurt_entities = bool(data["hurt_entities"])
        entity.on_ground = bool(data["on_ground"])
        h, v, below = (bool(b) for b in data["collisions"])
        entity.horizontal_collision, entity.vertical_collision = h, v
        entity.vertical_collision_below = below
        support = data["support"]
        entity.main_support = None if support is None else (int(support[0]), int(support[1]),
                                                             int(support[2]))  # fmt: skip
        entity.on_ground_no_blocks = bool(data["on_ground_no_blocks"])
        entity.piston_deltas = [float(v) for v in data["piston_deltas"]]
        entity.piston_deltas_time = int(data["piston_deltas_time"])
        sx, sy, sz = (int(v) for v in data["start"])
        entity.start_pos = (sx, sy, sz)
        return entity

    def describe(self) -> str:
        x, y, z = self.position
        return f"falling {repr(self.state)} at {x:.3f} {y:.3f} {z:.3f}"


#: Blocks whose fluid is always water (``getFluidState``: ``LiquidBlock`` water at any
#: level, ``BubbleColumnBlock``, ``KelpBlock``, ``KelpPlantBlock``, ``SeagrassBlock``,
#: ``TallSeagrassBlock``). All are foreign blocks; their water is never simulated.
WATER_BLOCKS = frozenset(
    {
        "minecraft:water", "minecraft:bubble_column", "minecraft:kelp",
        "minecraft:kelp_plant", "minecraft:seagrass", "minecraft:tall_seagrass",
    }
)  # fmt: skip


def _is_water(state: BlockState) -> bool:
    """``getFluidState().is(FluidTags.WATER)``: water blocks and waterlogged blocks
    (simulated or foreign)."""
    if state.block.id in WATER_BLOCKS:
        return True
    extra = getattr(state.block, "extra_properties", {})
    if extra.get("waterlogged") == "true":
        return True
    from redsim.world.properties import WATERLOGGED

    return state.has(WATERLOGGED) and bool(state.get(WATERLOGGED))


def entities_in(level: Level, box: Box) -> list[FallingBlockEntity]:
    """``level.getEntities(null, box)``: entities whose box intersects ``box``."""
    return [e for e in level.entities.values() if not e.removed and intersects(e.box, box)]


# =========================================================================== pistons
def move_collided_entities(level: Level, pos: Pos, new_progress: float, be: Any) -> None:
    """``PistonMovingBlockEntity.moveCollidedEntities`` L118."""
    if not level.entities:
        return
    from redsim.world import blocks
    from redsim.world.blocks.piston import FACING, PISTON_TYPE, SHORT, PistonBaseBlock

    movement = be.direction if be.extending else be.direction.opposite
    delta_progress = f32(new_progress) - f32(be.progress)
    if not be.extending and be.is_source and isinstance(be.moved_state.block, PistonBaseBlock):
        related = (
            blocks.PISTON_HEAD.default_state.with_(SHORT, f32(be.progress) > 0.25)
            .with_(PISTON_TYPE, "sticky" if be.moved_state.is_(blocks.STICKY_PISTON) else "normal")
            .with_(FACING, be.moved_state.get(FACING))
        )
    else:
        related = be.moved_state
    # Not as in the game: the game splits the shape with VoxelShape.toAabbs; these boxes
    # come from local_boxes. For the simulated blocks both give the same outer faces,
    # which are what pushes entities (doc item 3).
    shape_boxes_local = list(local_boxes(related))
    if not shape_boxes_local:
        return
    bounds = CollisionShape(shape_boxes_local).bounds()
    aabb = _by_position_and_progress(pos, bounds, be)
    area = _movement_area(aabb, movement, delta_progress)
    area = (min(area[0], aabb[0]), min(area[1], aabb[1]), min(area[2], aabb[2]),
            max(area[3], aabb[3]), max(area[4], aabb[4]), max(area[5], aabb[5]))  # fmt: skip
    found = entities_in(level, area)
    if not found:
        return
    bounce = be.moved_state.is_(blocks.SLIME_BLOCK)
    for entity in found:
        if bounce:
            dx, dy, dz = entity.delta
            sx, sy, sz = movement.step
            if movement.axis is Axis.X:
                dx = float(sx)
            elif movement.axis is Axis.Y:
                dy = float(sy)
            else:
                dz = float(sz)
            entity.delta = (dx, dy, dz)
        delta = 0.0
        for local in shape_boxes_local:
            moving = _movement_area(_by_position_and_progress(pos, local, be), movement,
                                    delta_progress)  # fmt: skip
            entity_box = entity.box
            if intersects(moving, entity_box):
                delta = max(delta, _movement(moving, movement, entity_box))
                if delta >= delta_progress:
                    break
        if not delta <= 0.0:
            delta = min(delta, delta_progress) + 0.01
            _move_entity_by_piston(level, movement, entity, delta, movement)
            if not be.extending and be.is_source:
                _fix_entity_within_piston_base(level, pos, entity, movement, delta_progress)


def move_stuck_entities(level: Level, pos: Pos, new_progress: float, be: Any) -> None:
    """``moveStuckEntities`` L185: honey carries entities standing on it sideways."""
    from redsim.world import blocks

    if not level.entities or not be.moved_state.is_(blocks.HONEY_BLOCK):
        return
    movement = be.direction if be.extending else be.direction.opposite
    if not movement.axis.is_horizontal:
        return
    top = max((b[4] for b in local_boxes(be.moved_state)), default=0.0)
    aabb = _by_position_and_progress(pos, (0.0, top, 0.0, 1.0, 1.5000010000000001, 1.0), be)
    delta_progress = f32(new_progress) - f32(be.progress)
    for entity in entities_in(level, aabb):
        x, _, z = entity.position
        supported = entity.main_support == pos
        inside = aabb[0] <= x <= aabb[3] and aabb[2] <= z <= aabb[5]
        if entity.on_ground and (supported or inside):
            _move_entity_by_piston(level, movement, entity, delta_progress, movement)


def _by_position_and_progress(pos: Pos, box: Box, be: Any) -> Box:
    current = f32(be.extended_progress(be.progress))
    sx, sy, sz = be.direction.step
    return moved(box, pos[0] + current * sx, pos[1] + current * sy, pos[2] + current * sz)


def _movement_area(aabb: Box, direction: Direction, amount: float) -> Box:
    """``PistonMath.getMovementArea``."""
    delta = amount * (1 if direction.is_positive else -1)
    lo, hi = min(delta, 0.0), max(delta, 0.0)
    x0, y0, z0, x1, y1, z1 = aabb
    if direction is Direction.WEST:
        return normalized((x0 + lo, y0, z0, x0 + hi, y1, z1))
    if direction is Direction.EAST:
        return normalized((x1 + lo, y0, z0, x1 + hi, y1, z1))
    if direction is Direction.DOWN:
        return normalized((x0, y0 + lo, z0, x1, y0 + hi, z1))
    if direction is Direction.NORTH:
        return normalized((x0, y0, z0 + lo, x1, y1, z0 + hi))
    if direction is Direction.SOUTH:
        return normalized((x0, y0, z1 + lo, x1, y1, z1 + hi))
    return normalized((x0, y1 + lo, z0, x1, y1 + hi, z1))  # UP


def _movement(outside_of: Box, direction: Direction, box: Box) -> float:
    """``getMovement``: how far ``box`` must move to leave ``outside_of``."""
    if direction is Direction.EAST:
        return outside_of[3] - box[0]
    if direction is Direction.WEST:
        return box[3] - outside_of[0]
    if direction is Direction.DOWN:
        return box[4] - outside_of[1]
    if direction is Direction.SOUTH:
        return outside_of[5] - box[2]
    if direction is Direction.NORTH:
        return box[5] - outside_of[2]
    return outside_of[4] - box[1]  # UP


def _move_entity_by_piston(
    level: Level, piston_direction: Direction, entity: FallingBlockEntity, delta: float,
    movement: Direction,
) -> None:  # fmt: skip
    """``moveEntityByPiston``."""
    _noclip[0] = piston_direction
    try:
        previous = entity.position
        sx, sy, sz = movement.step
        entity.move(level, (delta * sx, delta * sy, delta * sz), piston=True)
        entity.apply_effects_between(level, previous, entity.position)
        if entity.movements:  # removeLatestMovementRecording
            entity.movements.pop()
    finally:
        _noclip[0] = None


def _fix_entity_within_piston_base(
    level: Level, pos: Pos, entity: FallingBlockEntity, direction: Direction, delta_progress: float
) -> None:
    """``fixEntityWithinPistonBase``."""
    box = entity.box
    cell = (float(pos[0]), float(pos[1]), float(pos[2]), pos[0] + 1.0, pos[1] + 1.0, pos[2] + 1.0)
    if intersects(box, cell):
        opposite = direction.opposite
        delta = _movement(cell, opposite, box) + 0.01
        lo = (max(box[0], cell[0]), max(box[1], cell[1]), max(box[2], cell[2]))
        hi = (min(box[3], cell[3]), min(box[4], cell[4]), min(box[5], cell[5]))
        overlap = make_box(lo, hi)
        delta_intersected = _movement(cell, opposite, overlap) + 0.01
        if abs(delta - delta_intersected) < 0.01:
            delta = min(delta, delta_progress) + 0.01
            _move_entity_by_piston(level, direction, entity, delta, opposite)


def is_unobstructed(level: Level, state: BlockState, pos: Pos) -> bool:
    """``CollisionGetter.isUnobstructed``: no falling block (``blocksBuilding``) inside the
    block's collision shape (players placing blocks: ``CollisionContext.placementContext``)."""
    if not level.entities:
        return True
    shape = block_shape(level, pos, state)
    if shape is None:
        return True
    return not any(shape.intersects(e.box) for e in entities_in(level, shape.bounds()))
