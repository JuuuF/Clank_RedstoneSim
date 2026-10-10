"""Render style, mesh building and picking (no display needed)."""

from __future__ import annotations

import random

import numpy as np

from redsim.core.direction import Direction
from redsim.sim.level import Level
from redsim.ui.geometry import ChunkedMesh, Mesh, build_mesh, chunk_of, pick
from redsim.ui.style import block_boxes, wire_color
from redsim.world import blocks


def test_wire_color_matches_game_formula() -> None:
    assert wire_color(0)[:3] == (0.3, 0.0, 0.0)
    r, g, b, _ = wire_color(15)
    assert (round(r, 3), round(g, 3), round(b, 3)) == (1.0, 0.2, 0.0)


def test_wall_lever_sits_against_its_attached_block() -> None:
    # Lever facing east: attached block to the west, so the model hugs x = 0.
    state = blocks.parse_state("lever[face=wall,facing=east]")
    boxes = block_boxes(state)
    assert min(b.lo[0] for b in boxes) == 0
    wall_torch = block_boxes(blocks.parse_state("redstone_wall_torch[facing=east]"))
    assert min(b.lo[0] for b in wall_torch) <= 1


def test_mesh_culls_hidden_faces_between_full_cubes() -> None:
    level = Level()
    level.blocks[(0, 0, 0)] = blocks.STONE.default_state
    single = build_mesh(level).vertex_count
    level.blocks[(1, 0, 0)] = blocks.STONE.default_state
    pair = build_mesh(level).vertex_count
    assert single == 6 * 6
    assert pair == 10 * 6  # the shared faces are not drawn


def test_pick_hits_face_and_thin_components() -> None:
    level = Level()
    level.blocks[(0, 0, 0)] = blocks.STONE.default_state
    hit = pick(level, (0.5, 5.0, 0.5), (0, -1, 0))
    assert hit is not None and hit.pos == (0, 0, 0) and hit.face is Direction.UP
    level.blocks[(0, 1, 0)] = blocks.REDSTONE_WIRE.cross_state
    hit = pick(level, (0.5, 5.0, 0.5), (0, -1, 0))
    assert hit is not None and hit.pos == (0, 1, 0)
    # A ray passing just above the 1-pixel wire hits the stone behind it instead.
    hit = pick(level, (-3.0, 1.2, 0.5), (1, 0, 0))
    assert hit is None or hit.pos != (0, 1, 0)


def test_pick_misses_into_empty_space() -> None:
    assert pick(Level(), (0, 10, 0), (0, 1, 0)) is None


def test_translucent_blocks_go_to_their_own_buffer() -> None:
    level = Level()
    level.blocks[(0, 0, 0)] = blocks.GLASS.default_state
    mesh = build_mesh(level)
    assert len(mesh.opaque) == 0 and len(mesh.translucent) == 36
    assert np.all(mesh.translucent[:, 6] < 1.0)


def _faces(meshes: list[Mesh]) -> tuple[list[bytes], list[bytes]]:
    def rows(arrays: list[np.ndarray]) -> list[bytes]:
        joined = np.vstack(arrays) if arrays else np.zeros((0, 7), np.float32)
        return sorted(face.tobytes() for face in np.round(joined.reshape(-1, 6, 7), 4))

    return rows([m.opaque for m in meshes]), rows([m.translucent for m in meshes])


def test_chunks_rebuild_only_where_blocks_changed() -> None:
    level = Level()
    level.blocks[(0, 0, 0)] = blocks.STONE.default_state
    level.blocks[(40, 0, 0)] = blocks.STONE.default_state
    chunks = ChunkedMesh()
    assert chunk_of((40, 0, 0)) in chunks.update(level)
    assert chunks.update(level) == set()  # nothing changed
    level.blocks[(1, 0, 0)] = blocks.STONE.default_state
    dirty = chunks.update(level)
    assert chunk_of((0, 0, 0)) in dirty and chunk_of((40, 0, 0)) not in dirty
    del level.blocks[(40, 0, 0)]
    chunks.update(level)
    assert chunk_of((40, 0, 0)) not in chunks.chunks


def test_faces_are_culled_across_chunk_borders() -> None:
    level = Level()
    level.blocks[(7, 0, 0)] = blocks.STONE.default_state  # last block of chunk 0
    chunks = ChunkedMesh()
    chunks.update(level)
    assert chunks.chunks[chunk_of((7, 0, 0))].vertex_count == 36
    level.blocks[(8, 0, 0)] = blocks.STONE.default_state  # first block of chunk 1
    chunks.update(level)
    assert chunk_of((7, 0, 0)) != chunk_of((8, 0, 0))
    assert chunks.chunks[chunk_of((7, 0, 0))].vertex_count == 30  # east face now hidden


def test_incremental_chunks_equal_a_full_rebuild() -> None:
    rng = random.Random(7)
    pool = [
        blocks.STONE.default_state,
        blocks.GLASS.default_state,
        blocks.SLIME_BLOCK.default_state,
        blocks.REDSTONE_WIRE.cross_state,
        blocks.parse_state("repeater[delay=2,facing=east]"),
    ]
    level = Level()
    chunks = ChunkedMesh()
    for _ in range(12):
        for _ in range(60):
            pos = (rng.randrange(-10, 10), rng.randrange(0, 6), rng.randrange(-10, 10))
            if rng.random() < 0.3:
                level.blocks.pop(pos, None)
            else:
                level.blocks[pos] = rng.choice(pool)
        chunks.update(level)
        assert _faces(list(chunks.chunks.values())) == _faces([build_mesh(level)])
