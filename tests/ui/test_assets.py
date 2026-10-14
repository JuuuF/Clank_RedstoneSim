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


def test_flat_dust_is_extruded_pixel_by_pixel() -> None:
    from redsim.ui.assets import Assets
    from redsim.world import blocks

    assets = Assets.find()
    if assets is None:
        pytest.skip("no client jar")
    quads = list(assets.block_quads(blocks.REDSTONE_WIRE.default_state))
    # Side faces are the vertical quads (the dust model shades every face as "up").
    sides = [q for q in quads if len({round(c[1], 5) for c in q.corners}) > 1]
    assert sides, "the 1-pixel dust has side faces"
    for quad in sides:  # each side face is one pixel wide and shows one texel
        xs = {round(c[0] * 16, 4) for c in quad.corners}
        zs = {round(c[2] * 16, 4) for c in quad.corners}
        assert max(xs) - min(xs) <= 1 and max(zs) - min(zs) <= 1
        us = {round(u * 16, 4) for u, _ in quad.uvs}
        assert max(us) - min(us) == 1


def test_moved_blocks_are_drawn_at_their_progress(app: Any) -> None:
    """A block pushed east, half way: it spans x 1.5–2.5 (``PistonHeadRenderer``), and
    between ticks it is drawn between its last two positions (the partial tick)."""
    from redsim.editor.document import Document
    from redsim.ui.atlas import Atlas
    from redsim.ui.geometry import Mesher

    assert assets is not None
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), blocks.parse_state("sticky_piston[facing=east]"))
    doc.setblock((1, 1, 0), blocks.parse_state("stone"))
    doc.run_ticks(1)
    doc.setblock((-1, 1, 0), blocks.parse_state("redstone_block"))
    for _ in range(3):
        doc.step()
    mesher = Mesher(assets, Atlas.for_blocks(assets, []))

    def span(partial: float) -> tuple[float, float]:
        mesher.partial_tick = partial
        mesh = mesher.build(doc.level, [(2, 1, 0)])
        rows = np.vstack([mesh.solid, mesh.opaque, mesh.translucent])
        return float(rows[:, 0].min()), float(rows[:, 0].max())

    assert span(1.0) == (1.5, 2.5)
    assert span(0.0) == (1.0, 2.0)  # the tick before: still at the start


def test_chest_textures_keep_their_pixels(app: Any) -> None:
    """Entity textures (64×64) are not squeezed into a 16×16 tile; double-chest halves
    use their own textures, with the outline on the outer side (``ChestModel``)."""
    from redsim.ui.atlas import Atlas

    assert assets is not None
    atlas = Atlas.for_blocks(assets)
    for name in ("normal", "normal_left", "normal_right", "trapped"):
        assert atlas.tile(f"minecraft:entity/chest/{name}").shape[:2] == (64, 64)
    assert atlas.tile("minecraft:block/stone").shape[:2] == (16, 16)
    left = assets.block_quads(blocks.parse_state("chest[facing=south,type=left]"))
    assert {q.texture for q in left} == {"minecraft:entity/chest/normal_left"}
    top = next(q for q in left if q.facing.name == "UP" and q.corners[0][1] > 0.8)
    # The lid top's outline (texture column 43) lies at the half's outer (east) edge.
    east = max(range(4), key=lambda i: top.corners[i][0])
    assert round(top.uvs[east][0] * 64) == 44
