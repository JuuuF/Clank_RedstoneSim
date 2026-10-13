"""Mesh building and picking from the world model (pure Python + numpy, no Qt).

The renderer only reads world state; it never writes it.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from redsim.core.direction import ALL, Direction
from redsim.core.pos import Pos
from redsim.sim.level import Level
from redsim.ui.assets import Assets, Quad
from redsim.ui.style import Box, Color, block_boxes, moving_boxes, wire_color
from redsim.world import blocks
from redsim.world.block import BlockState
from redsim.world.blocks.piston import PistonMovingBlockEntity
from redsim.world.properties import EXTENDED, FACING, PISTON_TYPE, POWER

if TYPE_CHECKING:
    from redsim.ui.atlas import Atlas

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
#: A light color per face on top of the shade (round 8: less plain lighting): sunlit tops a
#: little warm, faces in the shade a little cool, like a sunny day in the game.
LIGHT = {
    Direction.UP: (1.03, 1.0, 0.93),
    Direction.DOWN: (0.94, 0.96, 1.06),
    Direction.NORTH: (0.97, 0.99, 1.04),
    Direction.SOUTH: (0.97, 0.99, 1.04),
    Direction.WEST: (0.95, 0.98, 1.07),
    Direction.EAST: (0.95, 0.98, 1.07),
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
    opaque: FloatArray  # (n, 9): x, y, z, r, g, b, a, u, v; components and partial blocks
    translucent: FloatArray
    #: Contains moving pistons, whose look changes every tick without a block change.
    animated: bool = False
    #: Full opaque cubes (building blocks), kept apart so X-ray can make them see-through.
    solid: FloatArray = field(default_factory=lambda: np.zeros((0, 9), dtype=np.float32))

    @property
    def vertex_count(self) -> int:
        return len(self.opaque) + len(self.translucent) + len(self.solid)


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
#: Corner shading (Minecraft-like smooth lighting without textures): brightness of a face
#: corner by how many of its 3 outer neighbors (two sides, one diagonal) are full blocks.
AO_LEVELS = (1.0, 0.82, 0.68, 0.55)


def _corner_offsets() -> tuple[tuple[tuple[Pos, Pos, Pos], ...], ...]:
    """For each direction (``ALL`` order) and each of its 4 face corners: the offsets of the
    two side neighbors and the diagonal neighbor in the layer outside the face."""
    result = []
    for direction in ALL:
        n = direction.step
        axis = next(i for i in range(3) if n[i] != 0)
        tangents = [i for i in range(3) if i != axis]
        corners = _face_quads(np.zeros(3), np.ones(3), direction)
        per_corner = []
        for corner in corners:
            signs = {a: (1 if corner[a] > 0.5 else -1) for a in tangents}
            side = []
            for a in tangents:
                o = list(n)
                o[a] += signs[a]
                side.append((o[0], o[1], o[2]))
            diagonal = list(n)
            for a in tangents:
                diagonal[a] += signs[a]
            per_corner.append((side[0], side[1], (diagonal[0], diagonal[1], diagonal[2])))
        result.append(tuple(per_corner))
    return tuple(result)


def block_noise(pos: Pos) -> float:
    """A stable ±5 % brightness variation per block (presentation only), instead of the
    checkerboard, so surfaces read like Minecraft blocks."""
    h = (pos[0] * 374761393 + pos[1] * 668265263 + pos[2] * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return 0.95 + 0.1 * (h & 0xFFFF) / 0xFFFF


#: Full cubes that are circuit parts: X-ray keeps them opaque (they go to the opaque buffer).
XRAY_KEEP = frozenset(
    {
        "minecraft:redstone_lamp",
        "minecraft:redstone_block",
        "minecraft:piston",
        "minecraft:sticky_piston",
        "minecraft:barrel",
        "minecraft:slime_block",
    }
)
#: Vertex layout of world meshes: x, y, z, r, g, b, a, u, v (u < 0: untextured).
VERTEX_SIZE = 9
_EMPTY = np.zeros((0, VERTEX_SIZE), dtype=np.float32)


@dataclass(frozen=True)
class _Model:
    """Face template ids of one block state. ``opaque[i]`` for ``i`` < 6 are the faces
    culled by a full neighbor in direction ``ALL[i]``; ``opaque[6]`` are never culled.
    Translucent faces likewise (also culled against the same state)."""

    opaque: tuple[tuple[int, ...], ...]
    translucent: tuple[tuple[int, ...], ...]
    has_translucent: bool


#: Blocks drawn in the translucent pass (with the game's models; boxes say it themselves).
TRANSLUCENT_BLOCKS = frozenset({"minecraft:slime_block", "minecraft:honey_block"})
GRASS_TINT = (0.569, 0.741, 0.349)  # plains grass color (#91BD59)


def tint_color(state: BlockState, index: int) -> tuple[float, float, float]:
    """``BlockColors`` for the in-scope blocks: redstone dust by power, grass green."""
    if index < 0:
        return (1.0, 1.0, 1.0)
    if state.block.id == "minecraft:redstone_wire":
        red, green, blue, _ = wire_color(int(state.get(POWER)))
        return (red, green, blue)
    if state.block.id == "minecraft:grass_block":
        return GRASS_TINT
    return (1.0, 1.0, 1.0)


class Mesher:
    """Builds meshes from block states, vectorized over faces.

    Every distinct face becomes one *template*: its 6 vertices (``x, y, z, r, g, b, a, u,
    v``) in block-local coordinates. A block state maps to the template ids of its faces,
    cached, so building a mesh is a lookup per block followed by one numpy gather and
    offset. With the game's assets (``assets.Assets``) and a texture ``atlas``, faces come
    from the real block models; otherwise from the colored boxes of ``style``.
    """

    def __init__(self, assets: Assets | None = None, atlas: Atlas | None = None) -> None:
        self.assets = assets if atlas is not None else None
        self.atlas = atlas
        self._template_ids: dict[tuple[object, ...], int] = {}
        self._template_rows: list[np.ndarray] = []
        #: Per template: for each of its 6 vertices, the face corner it sits on (corner
        #: shading of full cubes), or None if it is not a whole block face.
        self._template_corners: list[tuple[int, ...] | None] = []
        self._templates = np.zeros((0, 6, VERTEX_SIZE), dtype=np.float32)
        self._models: dict[BlockState, _Model] = {}
        self._full: dict[BlockState, bool] = {}
        #: How far the running simulation is into the next tick (0..1): moving blocks are
        #: drawn between their last two positions, like the game's partial tick.
        self.partial_tick = 1.0  # paused: the state at the end of the tick

    def render_progress(self, entity: PistonMovingBlockEntity) -> float:
        """``getProgress(partialTick)``: between the last and the current progress."""
        old, new = entity.progress_o, entity.progress
        return min(1.0, old + (new - old) * self.partial_tick)

    @property
    def textured(self) -> bool:
        return self.assets is not None

    def _is_full(self, state: BlockState) -> bool:
        full = self._full.get(state)
        if full is None:
            full = (
                state.block is not blocks.MOVING_PISTON
                and getattr(state.block, "full", True)  # a foreign sign's box is a guess
                and is_full_opaque(block_boxes(state))
            )
            self._full[state] = full
        return full

    def _add_template(self, key: tuple[object, ...], rows: np.ndarray) -> int:
        index = self._template_ids.get(key)
        if index is None:
            index = len(self._template_rows)
            self._template_rows.append(rows)
            self._template_corners.append(_corner_indices(rows))
            self._template_ids[key] = index
        return index

    def _box_template(self, box: Box, direction: Direction, color: Color) -> int:
        lo = np.array(box.lo, dtype=np.float32) / 16.0
        hi = np.array(box.hi, dtype=np.float32) / 16.0
        return self._add_template(
            (box.lo, box.hi, direction, color), _pad(_triangles(lo, hi, direction, color))
        )

    def _quad_template(self, quad: Quad, state: BlockState) -> int:
        assert self.atlas is not None
        red, green, blue = tint_color(state, quad.tint)
        shade = SHADE[quad.facing] if quad.shade else 1.0
        lr, lg, lb = LIGHT[quad.facing] if quad.shade else (1.0, 1.0, 1.0)
        color = (red * shade * lr, green * shade * lg, blue * shade * lb, 1.0)
        key = (quad.corners, quad.uvs, quad.texture, color)
        if key in self._template_ids:
            return self._template_ids[key]
        uv = [self.atlas.uv(quad.texture, u, v) for u, v in quad.uvs]
        rows = np.array(
            [(*quad.corners[i], *color, *uv[i]) for i in (0, 1, 2, 0, 2, 3)], dtype=np.float32
        )
        return self._add_template(key, rows)

    def _model(self, state: BlockState) -> _Model:
        opaque: list[list[int]] = [[] for _ in range(7)]
        translucent: list[list[int]] = [[] for _ in range(7)]
        quads = self.assets.block_quads(state) if self.assets is not None else ()
        if quads:
            see_through = state.block.id in TRANSLUCENT_BLOCKS
            for quad in quads:
                slot = 6 if quad.cull is None else ALL.index(quad.cull)
                target = translucent if see_through or quad.translucent else opaque
                target[slot].append(self._quad_template(quad, state))
        else:
            full = self._is_full(state)
            for box in block_boxes(state):
                target = translucent if box.translucent else opaque
                for index, direction in enumerate(ALL):
                    slot = index if full or box.translucent else 6
                    target[slot].append(self._box_template(box, direction, box.color))
        model = _Model(
            opaque=tuple(tuple(ids) for ids in opaque),
            translucent=tuple(tuple(ids) for ids in translucent),
            has_translucent=any(translucent),
        )
        self._models[state] = model
        return model

    def build(self, level: Level, positions: Iterable[Pos]) -> Mesh:
        """Mesh of the blocks at ``positions`` (faces against full neighbors are culled)."""
        states = level.blocks
        models = self._models
        is_full = self._is_full
        o_ids: list[int] = []
        o_pos: list[Pos] = []
        o_counts: list[int] = []
        s_ids: list[int] = []
        s_pos: list[Pos] = []
        s_counts: list[int] = []
        o_shade: list[float] = []  # 6 brightness factors per face (corner shading)
        s_shade: list[float] = []
        t_ids: list[int] = []
        t_pos: list[Pos] = []
        t_counts: list[int] = []
        dynamic: list[Pos] = []
        corners_of = self._template_corners
        for pos in positions:
            state = states.get(pos)
            if state is None:
                continue
            if state.block is blocks.MOVING_PISTON:
                dynamic.append(pos)
                continue
            x, y, z = pos
            full = is_full(state)
            model = models.get(state) or self._model(state)
            keep = not full or state.block.id in XRAY_KEEP
            ids, at, counts = (o_ids, o_pos, o_counts) if keep else (s_ids, s_pos, s_counts)
            shade = o_shade if keep else s_shade
            noise = block_noise(pos) if full else 1.0
            before = len(ids)
            for index, (dx, dy, dz) in enumerate(_STEPS):
                face_ids = model.opaque[index]
                if not face_ids:
                    continue
                neighbor = states.get((x + dx, y + dy, z + dz))
                if neighbor is not None and is_full(neighbor):
                    continue
                ids.extend(face_ids)
                if not full:
                    shade.extend((1.0,) * (6 * len(face_ids)))
                    continue
                levels = []
                for side1, side2, diagonal in CORNERS[index]:
                    a = states.get((x + side1[0], y + side1[1], z + side1[2]))
                    b = states.get((x + side2[0], y + side2[1], z + side2[2]))
                    c = states.get((x + diagonal[0], y + diagonal[1], z + diagonal[2]))
                    a_full = a is not None and is_full(a)
                    b_full = b is not None and is_full(b)
                    c_full = c is not None and is_full(c)
                    occluded = 3 if a_full and b_full else a_full + b_full + c_full
                    levels.append(AO_LEVELS[occluded] * noise)
                for face_id in face_ids:
                    corners = corners_of[face_id]
                    if corners is None:
                        shade.extend((noise,) * 6)
                    else:
                        shade.extend(levels[c] for c in corners)
            if model.opaque[6]:
                ids.extend(model.opaque[6])
                shade.extend((noise,) * (6 * len(model.opaque[6])))
            if len(ids) > before:
                at.append(pos)
                counts.append(len(ids) - before)
            if model.has_translucent:
                before = len(t_ids)
                for index, (dx, dy, dz) in enumerate(_STEPS):
                    neighbor = states.get((x + dx, y + dy, z + dz))
                    if neighbor is not state and (neighbor is None or not is_full(neighbor)):
                        t_ids.extend(model.translucent[index])  # none between equal blocks
                t_ids.extend(model.translucent[6])
                if len(t_ids) > before:
                    t_pos.append(pos)
                    t_counts.append(len(t_ids) - before)
        if len(self._templates) != len(self._template_rows):
            self._templates = np.stack(self._template_rows)
        opaque = [self._assemble(o_ids, o_pos, o_counts, o_shade)]
        translucent = [self._assemble(t_ids, t_pos, t_counts)]
        for pos in dynamic:
            self._moving(level, pos, opaque, translucent)
        solid = self._assemble(s_ids, s_pos, s_counts, s_shade)
        return Mesh(_stack(opaque), _stack(translucent), animated=bool(dynamic), solid=solid)

    def _moving(
        self, level: Level, pos: Pos, opaque: list[np.ndarray], translucent: list[np.ndarray]
    ) -> None:
        """Blocks moved by a piston: drawn at their progress, never culled against."""
        origin = np.array(pos, dtype=np.float32)
        entity = level.get_block_entity(pos, create=False)
        if self.assets is not None and isinstance(entity, PistonMovingBlockEntity):
            # ``PistonHeadRenderer``: offset = step × getExtendedProgress(getProgress(partial)).
            progress = entity.extended_progress(self.render_progress(entity))
            shift = np.array(entity.direction.step, dtype=np.float32) * progress
            pieces = [(entity.moved_state, shift)]
            if entity.is_source and not entity.extending:
                piston = (
                    "sticky"
                    if entity.moved_state.block.id == "minecraft:sticky_piston"
                    else "normal"
                )
                head = blocks.PISTON_HEAD.default_state.with_(FACING, entity.direction).with_(
                    PISTON_TYPE, piston
                )
                pieces = [(entity.moved_state.with_(EXTENDED, True), np.zeros(3, np.float32))]
                pieces.append((head, shift))
            for state, offset in pieces:
                model = self._models.get(state) or self._model(state)
                for group, target in ((model.opaque, opaque), (model.translucent, translucent)):
                    ids = [i for slot in group for i in slot]
                    if ids:
                        rows = np.stack([self._template_rows[i] for i in ids]).reshape(
                            -1, VERTEX_SIZE
                        )
                        rows = rows.copy()
                        rows[:, :3] += origin + offset
                        target.append(rows)
            return
        moving = boxes_at(level, pos)
        noise = block_noise(pos) if is_full_opaque(moving) else 1.0
        for box in moving:
            lo = origin + np.array(box.lo, dtype=np.float32) / 16.0
            hi = origin + np.array(box.hi, dtype=np.float32) / 16.0
            red, green, blue, alpha = box.color
            color = (red * noise, green * noise, blue * noise, alpha)
            target = translucent if box.translucent else opaque
            for direction in ALL:
                target.append(_pad(_triangles(lo, hi, direction, color)))

    def _assemble(
        self,
        ids: list[int],
        positions: list[Pos],
        counts: list[int],
        shade: list[float] | None = None,
    ) -> FloatArray:
        if not ids:
            return _EMPTY
        vertices = self._templates[np.asarray(ids, dtype=np.intp)]  # (faces, 6, 9), a copy
        offsets = np.repeat(np.asarray(positions, dtype=np.float32), counts, axis=0)
        vertices[:, :, :3] += offsets[:, None, :]
        if shade:
            factors = np.asarray(shade, dtype=np.float32).reshape(-1, 6)
            vertices[:, :, 3:6] *= factors[:, :, None]
        return vertices.reshape(-1, VERTEX_SIZE)


def _pad(rows: np.ndarray) -> np.ndarray:
    """Untextured vertices: UV (-1, -1) tells the shader to use the color alone."""
    if rows.shape[1] == VERTEX_SIZE:
        return rows
    uv = np.full((len(rows), 2), -1.0, dtype=np.float32)
    return np.hstack([rows, uv]).astype(np.float32)


_UNIT_FACES = {direction: _face_quads(np.zeros(3), np.ones(3), direction) for direction in ALL}


def _corner_indices(rows: np.ndarray) -> tuple[int, ...] | None:
    """Which corner (``_face_quads`` order) each of a template's 6 vertices sits on, if the
    template is a whole face of the unit cube (corner shading applies)."""
    positions = rows[:, :3]
    for corners in _UNIT_FACES.values():
        found = []
        for vertex in positions:
            match = np.where(np.all(np.abs(corners - vertex) < 1e-4, axis=1))[0]
            if len(match) != 1:
                break
            found.append(int(match[0]))
        else:
            return tuple(found)
    return None


def ghost_mesh(
    states: dict[Pos, BlockState], alpha: float = 0.45, mesher: Mesher | None = None
) -> FloatArray:
    """Translucent preview of loose block states (selection drags, paste preview)."""
    level = Level()
    level.blocks = {pos: state for pos, state in states.items() if not state.is_air}
    mesh = (mesher or Mesher()).build(level, level.blocks)
    rows = np.vstack([mesh.solid, mesh.opaque, mesh.translucent])
    rows[:, 6] = np.minimum(rows[:, 6], alpha)
    return rows


class ChunkedMesh:
    """Per-chunk meshes of one world, rebuilt only where something changed.

    Changes come from the level's touched positions (``Level.take_touched``) while it is
    the same level; a different level (a timeline seek swaps in a restored copy, or a new
    document) is diffed against the block map seen last. A changed block dirties its own chunk and
    the chunks of its 6 neighbors (face culling looks across chunk borders). Chunks holding
    moving pistons are rebuilt on every update because their look follows the block
    entity's progress.
    """

    def __init__(self, mesher: Mesher | None = None) -> None:
        self.mesher = mesher if mesher is not None else Mesher()
        self.chunks: dict[ChunkKey, Mesh] = {}
        self._known: dict[Pos, BlockState] = {}
        self._level: Level | None = None  # the level ``_known`` follows
        self._members: dict[ChunkKey, set[Pos]] = {}
        self._animated: set[ChunkKey] = set()

    def reset(self) -> None:
        self.chunks.clear()
        self._known = {}
        self._level = None
        self._members.clear()
        self._animated.clear()

    def update_animated(self, level: Level) -> set[ChunkKey]:
        """Rebuild only the chunks with moving pistons (between ticks, as the partial tick
        advances); returns their keys."""
        for key in self._animated:
            positions = self._members.get(key)
            if positions:
                self.chunks[key] = self.mesher.build(level, positions)
        return set(self._animated)

    def update(self, level: Level) -> set[ChunkKey]:
        """Bring the chunks up to date; returns the keys whose mesh changed or was removed."""
        current = level.blocks
        known = self._known
        touched = level.take_touched()
        changed: set[Pos] = set()
        if level is self._level:  # the same level: what it reports as touched
            for pos in touched:
                state = current.get(pos)
                if known.get(pos) is not state:
                    changed.add(pos)
                    if state is None:
                        del known[pos]
                    else:
                        known[pos] = state
        if level is not self._level or len(known) != len(current):
            # A restored or new level (or blocks written past ``set_block``): compare all.
            changed |= {pos for pos, _ in known.items() ^ current.items()}
            self._known = dict(current)
            self._level = level
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
    lr, lg, lb = LIGHT[direction]
    rgba = np.array(
        [color[0] * shade * lr, color[1] * shade * lg, color[2] * shade * lb, color[3]], np.float32
    )
    corners = quad[[0, 1, 2, 0, 2, 3]]
    return np.hstack([corners, np.tile(rgba, (6, 1))])


def _stack(parts: list[np.ndarray]) -> FloatArray:
    if not parts:
        return np.zeros((0, 7), dtype=np.float32)
    width = max(part.shape[1] for part in parts)
    if width == VERTEX_SIZE:
        parts = [_pad(part) for part in parts]
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


def ray_box(
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
                hit = ray_box(o, d, lo, hi)
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


CORNERS = _corner_offsets()
