"""Render style, mesh building and picking (no display needed)."""

from __future__ import annotations

import random

import numpy as np

from redsim.core.direction import Direction
from redsim.sim.level import Level
from redsim.ui.geometry import VERTEX_SIZE, ChunkedMesh, Mesh, build_mesh, chunk_of, pick
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


def test_repeater_delay_torch_matches_the_game_model() -> None:
    # repeater_<n>tick.json (facing=south, unrotated): fixed torch z 2..4 at the output end,
    # delay torch z 6..8 for delay 1 up to z 12..14 for delay 4 (towards the input).
    for delay in range(1, 5):
        state = blocks.parse_state(f"repeater[facing=south,delay={delay}]")
        torches = sorted(b.lo[2] for b in block_boxes(state) if b.lo[1] == 2 and b.hi[1] == 7)
        assert torches == [2, 6 + 2 * (delay - 1)]


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
    assert len(mesh.opaque) == 0 and len(mesh.solid) == 0 and len(mesh.translucent) == 36
    assert np.all(mesh.translucent[:, 6] < 1.0)


def _faces(meshes: list[Mesh]) -> tuple[list[bytes], list[bytes]]:
    def rows(arrays: list[np.ndarray]) -> list[bytes]:
        joined = np.vstack(arrays) if arrays else np.zeros((0, VERTEX_SIZE), np.float32)
        return sorted(face.tobytes() for face in np.round(joined.reshape(-1, 6, VERTEX_SIZE), 4))

    opaque = [m.opaque for m in meshes] + [m.solid for m in meshes]
    return rows(opaque), rows([m.translucent for m in meshes])


def test_chunks_rebuild_only_where_blocks_changed() -> None:
    level = Level()
    level.blocks[(0, 0, 0)] = blocks.STONE.default_state
    level.blocks[(40, 0, 0)] = blocks.STONE.default_state
    chunks = ChunkedMesh()
    assert chunk_of((40, 0, 0)) in chunks.update(level)
    assert chunks.update(level) == set()  # nothing changed
    level.add_blocks({(1, 0, 0): blocks.STONE.default_state})
    dirty = chunks.update(level)
    assert chunk_of((0, 0, 0)) in dirty and chunk_of((40, 0, 0)) not in dirty
    level.set_block((40, 0, 0), level.air, 2)
    chunks.update(level)
    assert chunk_of((40, 0, 0)) not in chunks.chunks


def test_chunks_notice_blocks_written_without_set_block() -> None:
    level = Level()
    level.blocks[(0, 0, 0)] = blocks.STONE.default_state
    chunks = ChunkedMesh()
    chunks.update(level)
    level.blocks[(40, 0, 0)] = blocks.STONE.default_state  # not reported as touched
    assert chunk_of((40, 0, 0)) in chunks.update(level)


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


def test_full_cubes_go_to_the_solid_buffer_components_stay_opaque() -> None:
    level = Level()
    level.blocks[(0, 0, 0)] = blocks.STONE.default_state
    level.blocks[(0, 1, 0)] = blocks.REDSTONE_WIRE.cross_state
    mesh = build_mesh(level)
    assert len(mesh.solid) == 36 and len(mesh.opaque) > 0


def test_xray_keeps_full_cube_components_opaque() -> None:
    level = Level()
    level.blocks[(0, 0, 0)] = blocks.REDSTONE_LAMP.default_state
    mesh = build_mesh(level)
    assert len(mesh.solid) == 0 and len(mesh.opaque) == 36


def test_blocks_beside_a_pressure_plate_keep_their_face() -> None:
    """Thin blocks (pressure plates, chests) do not hide their neighbor's faces."""
    level = Level()
    level.blocks[(0, 0, 0)] = blocks.STONE.default_state
    alone = build_mesh(level).vertex_count
    for beside in ("stone_pressure_plate", "light_weighted_pressure_plate", "chest"):
        level.blocks[(1, 0, 0)] = blocks.parse_state(beside)
        both = build_mesh(level).vertex_count
        level.blocks.pop((1, 0, 0))
        plate = Level()
        plate.blocks[(1, 0, 0)] = blocks.parse_state(beside)
        assert both == alone + build_mesh(plate).vertex_count, beside


def test_every_block_has_a_shape() -> None:
    """No block falls back to the magenta placeholder cube."""
    from redsim.ui.style import UNKNOWN

    for block in blocks.REGISTRY.values():
        for state in (block.default_state,):
            assert all(box.color != UNKNOWN for box in block_boxes(state)), block.id
