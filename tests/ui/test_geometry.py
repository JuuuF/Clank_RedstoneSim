"""Render style, mesh building and picking (no display needed)."""

from __future__ import annotations

import numpy as np

from redsim.core.direction import Direction
from redsim.sim.level import Level
from redsim.ui.geometry import build_mesh, pick
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
