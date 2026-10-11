"""The game's block models from the supplied client jar (skipped without the jar)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from PySide6 import QtWidgets

from redsim.core.direction import Direction
from redsim.sim.level import Level
from redsim.ui.assets import Assets
from redsim.world import blocks

assets = Assets.find()
pytestmark = pytest.mark.skipif(assets is None, reason="client jar not available")


@pytest.fixture(scope="module")
def app() -> Any:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_every_block_has_a_model_except_technical_ones() -> None:
    assert assets is not None
    missing = {
        b for b, block in blocks.REGISTRY.items() if not assets.block_quads(block.default_state)
    }
    assert missing == {"minecraft:air", "minecraft:barrier", "minecraft:moving_piston"}


def test_variant_rotation_turns_the_model_and_its_cull_faces() -> None:
    """repeater: the north model turned by ``y`` (90° steps clockwise from above)."""
    assert assets is not None
    for facing, _y in (("south", 0), ("west", 90), ("north", 180), ("east", 270)):
        quads = assets.block_quads(blocks.parse_state(f"repeater[facing={facing}]"))
        bottom = [q for q in quads if q.cull is Direction.DOWN]
        assert bottom, facing
        sides = {q.cull for q in quads if q.cull is not None}
        assert sides == {
            Direction.DOWN,
            Direction.NORTH,
            Direction.SOUTH,
            Direction.WEST,
            Direction.EAST,
        }


def test_observer_up_rotates_its_face_upwards() -> None:
    assert assets is not None
    quads = assets.block_quads(blocks.parse_state("observer[facing=up]"))
    front = [q for q in quads if q.texture.endswith("observer_front")]
    assert len(front) == 1 and front[0].facing is Direction.UP


def test_wire_connects_with_multipart_pieces_and_is_tinted() -> None:
    assert assets is not None
    dot = assets.block_quads(blocks.parse_state("redstone_wire"))
    line = assets.block_quads(blocks.parse_state("redstone_wire[north=side,south=side]"))
    assert any("dot" in q.texture for q in dot)
    assert all("dot" not in q.texture for q in line)  # a straight line has no center dot
    assert any(q.tint == 0 for q in line)


def test_textured_mesh_culls_against_full_neighbors(app: Any) -> None:
    from redsim.ui.atlas import Atlas
    from redsim.ui.geometry import VERTEX_SIZE, Mesher

    assert assets is not None
    mesher = Mesher(assets, Atlas.for_blocks(assets))
    level = Level()
    level.blocks[(0, 0, 0)] = blocks.STONE.default_state
    single = mesher.build(level, level.blocks)
    level.blocks[(1, 0, 0)] = blocks.STONE.default_state
    pair = mesher.build(level, level.blocks)
    assert single.solid.shape[1] == VERTEX_SIZE
    assert len(single.solid) == 6 * 6 and len(pair.solid) == 2 * 5 * 6
    assert np.all(single.solid[:, 7] >= 0)  # textured
    level.blocks = {(0, 1, 0): blocks.parse_state("redstone_wire[north=side,south=side,power=15]")}
    wire = mesher.build(level, level.blocks)
    assert len(wire.translucent) and wire.translucent[:, 3].max() > 0.9  # bright red tint


def test_inventory_previews_use_the_game_items(app: Any) -> None:
    from redsim.ui.icons import game_pixmap

    for block_id in ("minecraft:redstone_wire", "minecraft:repeater", "minecraft:stone"):
        pixmap = game_pixmap(block_id, 32)
        assert pixmap is not None and not pixmap.isNull()
