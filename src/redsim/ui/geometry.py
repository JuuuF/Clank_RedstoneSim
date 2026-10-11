"""Mesh building and picking from the world model (pure Python + numpy, no Qt).

The renderer only reads world state; it never writes it.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from redsim.core.direction import ALL, Direction
from redsim.core.pos import Pos
from redsim.sim.level import Level
from redsim.ui.style import Box, Color, block_boxes, moving_boxes
from redsim.world import blocks
from redsim.world.block import BlockState
from redsim.world.blocks.piston import PistonMovingBlockEntity
from redsim.world.properties import EXTENDED, FACING, PISTON_TYPE

FloatArray = npt.NDArray[np.float32]

#: Face shading (fake lighting): top brightest, bottom darkest.
SHADE = {
    Direction.UP: 1.0,
    Direction.DOWN: 0.55,
    Direction.NORTH: 0.82,
    Direction.SOUTH: 0.82,
    Direction.WEST: 0.68,
    Direction.EAST: 0.68,
}


def _face_quads(lo: np.ndarray, hi: np.ndarray, direction: Direction) -> np.ndarray:
    """The four corners of one face of an axis-aligned box, counter-clockwise from outside."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    corners = {
        Direction.UP: [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)],
        Direction.DOWN: [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        Direction.NORTH: [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)],
        Direction.SOUTH: [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        Direction.WEST: [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)],
        Direction.EAST: [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
    }[direction]
    return np.array(corners, dtype=np.float32)


@dataclass
class Mesh:
    opaque: FloatArray  # (n, 7): x, y, z, r, g, b, a
    translucent: FloatArray
    #: Contains moving pistons, whose look changes every tick without a block change.
    animated: bool = False

    @property
    def vertex_count(self) -> int:
        return len(self.opaque) + len(self.translucent)


def is_full_opaque(boxes: list[Box]) -> bool:
    return (
        len(boxes) == 1
        and not boxes[0].translucent
        and boxes[0].lo == (0, 0, 0)
        and boxes[0].hi == (16, 16, 16)
    )


def boxes_at(level: Level, pos: Pos) -> list[Box]:
    """Visual boxes of the block at ``pos``; moving pistons show what they move."""
    state = level.get_block_state(pos)
    if state.block.id != "minecraft:moving_piston":
        return block_boxes(state)
    entity = level.get_block_entity(pos, create=False)
    if not isinstance(entity, PistonMovingBlockEntity):
        return []
    progress = entity.extended_progress(entity.progress)
    moved = entity.moved_state
    if entity.is_source and not entity.extending:
        # A retracting piston base: the extended base stays, its head slides back in.
        piston_type = "sticky" if moved.block.id == "minecraft:sticky_piston" else "normal"
        head = blocks.PISTON_HEAD.default_state.with_(FACING, entity.direction).with_(
            PISTON_TYPE, piston_type
        )
        base = block_boxes(moved.with_(EXTENDED, True))
        return base + moving_boxes(head, entity.direction, progress)
    return moving_boxes(moved, entity.direction, progress)


def build_mesh(level: Level) -> Mesh:
    """Mesh of the whole world in one piece (tests and tools; the viewport uses chunks)."""
    return Mesher().build(level, level.blocks)


#: Mesh chunks are 2**CHUNK_SHIFT blocks on each edge. The game meshes 16³ sections; a
#: smaller chunk keeps one rebuild cheap for this Python mesher.
CHUNK_SHIFT = 3

ChunkKey = tuple[int, int, int]


def chunk_of(pos: Pos) -> ChunkKey:
    return (pos[0] >> CHUNK_SHIFT, pos[1] >> CHUNK_SHIFT, pos[2] >> CHUNK_SHIFT)


_STEPS = tuple(direction.step for direction in ALL)
_EMPTY = np.zeros((0, 7), dtype=np.float32)


@dataclass(frozen=True)
class _Model:
    """Face template ids of one block state, per direction (in ``ALL`` order)."""

    full_opaque: bool
    opaque: tuple[tuple[int, ...], ...]
    translucent: tuple[tuple[int, ...], ...]
    opaque_all: tuple[int, ...]
    has_translucent: bool


class Mesher:
    """Builds meshes from block states, vectorized over faces.

    Every distinct face (box, direction, color) becomes one *template*: its 6 vertices in
    block-local coordinates. A block state maps to the template ids of its faces, cached, so
    building a mesh is a lookup per block followed by one numpy gather and offset.
    """

    def __init__(self) -> None:
        self._template_ids: dict[tuple[object, ...], int] = {}
        self._template_rows: list[np.ndarray] = []
        self._templates = np.zeros((0, 6, 7), dtype=np.float32)
        self._models: dict[tuple[BlockState, bool], _Model] = {}
        self._full: dict[BlockState, bool] = {}

    def _is_full(self, state: BlockState) -> bool:
        full = self._full.get(state)
        if full is None:
            full = state.block is not blocks.MOVING_PISTON and is_full_opaque(block_boxes(state))
            self._full[state] = full
        return full

    def _template(self, box: Box, direction: Direction, color: Color) -> int:
        key = (box.lo, box.hi, direction, color)
        index = self._template_ids.get(key)
        if index is None:
            lo = np.array(box.lo, dtype=np.float32) / 16.0
            hi = np.array(box.hi, dtype=np.float32) / 16.0
            index = len(self._template_rows)
            self._template_rows.append(_triangles(lo, hi, direction, color))
            self._template_ids[key] = index
        return index

    def _model(self, state: BlockState, tinted: bool) -> _Model:
        boxes = block_boxes(state)
        opaque: list[list[int]] = [[] for _ in ALL]
        translucent: list[list[int]] = [[] for _ in ALL]
        for box in boxes:
            color = box.color
            if tinted:
                # Checkerboard tint on full cubes, for depth perception (presentation only).
                color = (color[0] * 0.93, color[1] * 0.93, color[2] * 0.93, color[3])
            target = translucent if box.translucent else opaque
            for index, direction in enumerate(ALL):
                target[index].append(self._template(box, direction, color))
        model = _Model(
            full_opaque=self._is_full(state),
            opaque=tuple(tuple(ids) for ids in opaque),
            translucent=tuple(tuple(ids) for ids in translucent),
            opaque_all=tuple(i for ids in opaque for i in ids),
            has_translucent=any(translucent),
        )
        self._models[(state, tinted)] = model
        return model

    def build(self, level: Level, positions: Iterable[Pos]) -> Mesh:
        """Mesh of the blocks at ``positions`` (faces against full neighbors are culled)."""
        states = level.blocks
        models = self._models
        is_full = self._is_full
        o_ids: list[int] = []
        o_pos: list[Pos] = []
        o_counts: list[int] = []
        t_ids: list[int] = []
        t_pos: list[Pos] = []
        t_counts: list[int] = []
        dynamic: list[Pos] = []
        for pos in positions:
            state = states.get(pos)
            if state is None:
                continue
            if state.block is blocks.MOVING_PISTON:
                dynamic.append(pos)
                continue
            x, y, z = pos
            full = is_full(state)
            tinted = full and bool((x + y + z) & 1)
            model = models.get((state, tinted)) or self._model(state, tinted)
            if full:
                before = len(o_ids)
                for index, (dx, dy, dz) in enumerate(_STEPS):
                    neighbor = states.get((x + dx, y + dy, z + dz))
                    if neighbor is None or not is_full(neighbor):
                        o_ids.extend(model.opaque[index])
                if len(o_ids) > before:
                    o_pos.append(pos)
                    o_counts.append(len(o_ids) - before)
            elif model.opaque_all:
                o_ids.extend(model.opaque_all)
                o_pos.append(pos)
                o_counts.append(len(model.opaque_all))
            if model.has_translucent:
                before = len(t_ids)
                for index, (dx, dy, dz) in enumerate(_STEPS):
                    if states.get((x + dx, y + dy, z + dz)) is not state:
                        t_ids.extend(model.translucent[index])  # no faces between equal blocks
                if len(t_ids) > before:
                    t_pos.append(pos)
                    t_counts.append(len(t_ids) - before)
        if len(self._templates) != len(self._template_rows):
            self._templates = np.stack(self._template_rows)
        opaque = [self._assemble(o_ids, o_pos, o_counts)]
        translucent = [self._assemble(t_ids, t_pos, t_counts)]
        for pos in dynamic:
            # Moved blocks are never culled against (their look changes every tick), but keep
            # the checkerboard tint so a block does not flicker when it comes to rest.
            moving = boxes_at(level, pos)
            tinted = is_full_opaque(moving) and bool(sum(pos) & 1)
            origin = np.array(pos, dtype=np.float32)
            for box in moving:
                lo = origin + np.array(box.lo, dtype=np.float32) / 16.0
                hi = origin + np.array(box.hi, dtype=np.float32) / 16.0
                color = box.color
                if tinted:
                    color = (color[0] * 0.93, color[1] * 0.93, color[2] * 0.93, color[3])
                target = translucent if box.translucent else opaque
                for direction in ALL:
                    target.append(_triangles(lo, hi, direction, color))
        return Mesh(_stack(opaque), _stack(translucent), animated=bool(dynamic))

    def _assemble(self, ids: list[int], positions: list[Pos], counts: list[int]) -> FloatArray:
        if not ids:
            return _EMPTY
        vertices = self._templates[np.asarray(ids, dtype=np.intp)]  # (faces, 6, 7), a copy
        offsets = np.repeat(np.asarray(positions, dtype=np.float32), counts, axis=0)
        vertices[:, :, :3] += offsets[:, None, :]
        return vertices.reshape(-1, 7)


def ghost_mesh(
    states: dict[Pos, BlockState], alpha: float = 0.45, mesher: Mesher | None = None
) -> FloatArray:
    """Translucent preview of loose block states (selection drags, paste preview)."""
    level = Level()
    level.blocks = {pos: state for pos, state in states.items() if not state.is_air}
    mesh = (mesher or Mesher()).build(level, level.blocks)
    rows = np.vstack([mesh.opaque, mesh.translucent])
    rows[:, 6] = np.minimum(rows[:, 6], alpha)
    return rows


class ChunkedMesh:
    """Per-chunk meshes of one world, rebuilt only where something changed.

    Changes are found by diffing the block map against the last one seen, which also covers
    timeline seeks (they swap in a restored level). A changed block dirties its own chunk and
    the chunks of its 6 neighbors (face culling looks across chunk borders). Chunks holding
    moving pistons are rebuilt on every update because their look follows the block
    entity's progress.
    """

    def __init__(self, mesher: Mesher | None = None) -> None:
        self.mesher = mesher if mesher is not None else Mesher()
        self.chunks: dict[ChunkKey, Mesh] = {}
        self._known: dict[Pos, BlockState] = {}
        self._members: dict[ChunkKey, set[Pos]] = {}
        self._animated: set[ChunkKey] = set()

    def reset(self) -> None:
        self.chunks.clear()
        self._known = {}
        self._members.clear()
        self._animated.clear()

    def update(self, level: Level) -> set[ChunkKey]:
        """Bring the chunks up to date; returns the keys whose mesh changed or was removed."""
        current = level.blocks
        changed = {pos for pos, _ in self._known.items() ^ current.items()}
        dirty = set(self._animated)
        if changed:
            members = self._members
            for pos in changed:
                key = chunk_of(pos)
                if pos in current:
                    members.setdefault(key, set()).add(pos)
                else:
                    chunk = members.get(key)
                    if chunk is not None:
                        chunk.discard(pos)
                x, y, z = pos
                dirty.add(key)
                for dx, dy, dz in _STEPS:
                    dirty.add(chunk_of((x + dx, y + dy, z + dz)))
            self._known = dict(current)
        self._animated = set()
        for key in dirty:
            positions = self._members.get(key)
            if not positions:
                self._members.pop(key, None)
                self.chunks.pop(key, None)
                continue
            mesh = self.mesher.build(level, positions)
            self.chunks[key] = mesh
            if mesh.animated:
                self._animated.add(key)
        return dirty


def _triangles(lo: np.ndarray, hi: np.ndarray, direction: Direction, color: Color) -> np.ndarray:
    quad = _face_quads(lo, hi, direction)
    shade = SHADE[direction]
    rgba = np.array([color[0] * shade, color[1] * shade, color[2] * shade, color[3]], np.float32)
    corners = quad[[0, 1, 2, 0, 2, 3]]
    return np.hstack([corners, np.tile(rgba, (6, 1))])


def _stack(parts: list[np.ndarray]) -> FloatArray:
    if not parts:
        return np.zeros((0, 7), dtype=np.float32)
    return np.ascontiguousarray(np.vstack(parts), dtype=np.float32)


def box_lines(
    lo: Iterable[float], hi: Iterable[float], color: Color, grow: float = 0.002
) -> FloatArray:
    """12 edges of a box as GL_LINES vertices (x, y, z, r, g, b, a)."""
    x0, y0, z0 = (v - grow for v in lo)
    x1, y1, z1 = (v + grow for v in hi)
    corners = [
        (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
        (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1),
    ]  # fmt: skip
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
             (0, 4), (1, 5), (2, 6), (3, 7)]  # fmt: skip
    rows = [(*corners[i], *color) for edge in edges for i in edge]
    return np.array(rows, dtype=np.float32)


def solid_box(lo: Iterable[float], hi: Iterable[float], color: Color) -> FloatArray:
    """A shaded, closed box as triangles (x, y, z, r, g, b, a)."""
    a = np.array(list(lo), dtype=np.float32)
    b = np.array(list(hi), dtype=np.float32)
    return np.vstack([_triangles(a, b, direction, color) for direction in ALL])


def thick_edges(lo: Iterable[float], hi: Iterable[float], color: Color, width: float) -> FloatArray:
    """The 12 edges of a box as thin square prisms (OpenGL core profiles cannot draw wide
    lines)."""
    lo3 = np.array(list(lo), dtype=np.float32)
    hi3 = np.array(list(hi), dtype=np.float32)
    half = width / 2
    parts = []
    for axis in range(3):
        others = [i for i in range(3) if i != axis]
        for u in (lo3[others[0]], hi3[others[0]]):
            for v in (lo3[others[1]], hi3[others[1]]):
                a = np.zeros(3, dtype=np.float32)
                b = np.zeros(3, dtype=np.float32)
                a[axis], b[axis] = lo3[axis] - half, hi3[axis] + half
                a[others[0]], b[others[0]] = u - half, u + half
                a[others[1]], b[others[1]] = v - half, v + half
                parts.append(solid_box(a, b, color))
    return np.vstack(parts)


def block_outline(level: Level, pos: Pos, color: Color) -> FloatArray:
    """Outline of a block's visual boxes (a full cube outline for empty space)."""
    boxes = boxes_at(level, pos)
    if not boxes:
        return box_lines(pos, (pos[0] + 1, pos[1] + 1, pos[2] + 1), color)
    lo = np.min([b.lo for b in boxes], axis=0) / 16.0 + np.array(pos)
    hi = np.max([b.hi for b in boxes], axis=0) / 16.0 + np.array(pos)
    return box_lines(lo, hi, color)


# ---------------------------------------------------------------- picking
@dataclass(frozen=True)
class Hit:
    pos: Pos
    face: Direction  # outward normal of the face that was hit
    distance: float


def _ray_box(
    origin: np.ndarray, direction: np.ndarray, lo: np.ndarray, hi: np.ndarray
) -> tuple[float, int] | None:
    """Slab test; returns (t_enter, axis) of the entry face or None."""
    t_enter, t_exit, axis = -math.inf, math.inf, -1
    for i in range(3):
        if abs(direction[i]) < 1e-12:
            if origin[i] < lo[i] or origin[i] > hi[i]:
                return None
            continue
        t1 = (lo[i] - origin[i]) / direction[i]
        t2 = (hi[i] - origin[i]) / direction[i]
        t_near, t_far = min(t1, t2), max(t1, t2)
        if t_near > t_enter:
            t_enter, axis = t_near, i
        t_exit = min(t_exit, t_far)
        if t_enter > t_exit:
            return None
    if t_exit < 0 or axis < 0:
        return None
    return (max(t_enter, 0.0), axis)


_AXIS_FACES = {
    (0, True): Direction.WEST,
    (0, False): Direction.EAST,
    (1, True): Direction.DOWN,
    (1, False): Direction.UP,
    (2, True): Direction.NORTH,
    (2, False): Direction.SOUTH,
}


def pick(
    level: Level, origin: Iterable[float], direction: Iterable[float], max_distance: float = 96.0
) -> Hit | None:
    """First block whose visual boxes the ray hits (voxel traversal, Amanatides & Woo)."""
    o = np.array(list(origin), dtype=np.float64)
    d = np.array(list(direction), dtype=np.float64)
    norm = float(np.linalg.norm(d))
    if norm == 0:
        return None
    d /= norm
    voxel = [math.floor(v) for v in o]
    step = [1 if v > 0 else -1 for v in d]
    t_max, t_delta = [], []
    for i in range(3):
        if d[i] == 0:
            t_max.append(math.inf)
            t_delta.append(math.inf)
        else:
            boundary = voxel[i] + (1 if d[i] > 0 else 0)
            t_max.append((boundary - o[i]) / d[i])
            t_delta.append(abs(1.0 / d[i]))
    travelled = 0.0
    while travelled <= max_distance:
        pos = (voxel[0], voxel[1], voxel[2])
        state = level.blocks.get(pos)
        if state is not None:
            best: tuple[float, int] | None = None
            for box in boxes_at(level, pos):
                lo = np.array(pos, dtype=np.float64) + np.array(box.lo) / 16.0
                hi = np.array(pos, dtype=np.float64) + np.array(box.hi) / 16.0
                hit = _ray_box(o, d, lo, hi)
                if hit is not None and (best is None or hit[0] < best[0]):
                    best = hit
            if best is not None:
                t, axis = best
                return Hit(pos, _AXIS_FACES[(axis, d[axis] > 0)], t)
        axis = int(np.argmin(t_max))
        travelled = t_max[axis]
        voxel[axis] += step[axis]
        t_max[axis] += t_delta[axis]
    return None
