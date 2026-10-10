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
from redsim.core.pos import Pos, offset
from redsim.sim.level import Level
from redsim.ui.style import Box, Color, block_boxes, moving_boxes
from redsim.world import blocks
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
    states = level.blocks
    models: dict[Pos, list[Box]] = {pos: boxes_at(level, pos) for pos in states}
    full_opaque = {pos for pos, boxes in models.items() if is_full_opaque(boxes)}
    opaque: list[np.ndarray] = []
    translucent: list[np.ndarray] = []
    for pos, boxes in models.items():
        origin = np.array(pos, dtype=np.float32)
        cull = pos in full_opaque
        for box in boxes:
            lo = origin + np.array(box.lo, dtype=np.float32) / 16.0
            hi = origin + np.array(box.hi, dtype=np.float32) / 16.0
            target = translucent if box.translucent else opaque
            color = box.color
            if cull and (pos[0] + pos[1] + pos[2]) % 2:
                # Checkerboard tint on full cubes, for depth perception (presentation only).
                color = (color[0] * 0.93, color[1] * 0.93, color[2] * 0.93, color[3])
            for direction in ALL:
                if cull and offset(pos, direction) in full_opaque:
                    continue
                if box.translucent and states.get(offset(pos, direction)) is states[pos]:
                    continue  # no inner faces between identical glass/slime blocks
                target.append(_triangles(lo, hi, direction, color))
    return Mesh(_stack(opaque), _stack(translucent))


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
