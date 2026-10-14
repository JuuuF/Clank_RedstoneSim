"""The game's ordinary blocks from the generated table (``world/blocks/catalog.py``):
settings from ``Blocks.java``, shapes, placement and the behavior next to redstone."""

from __future__ import annotations

from redsim.core.direction import Direction
from redsim.editor.document import Document
from redsim.editor.placement import PlaceRequest
from redsim.world import blocks
from redsim.world.block import PushReaction
from redsim.world.blocks.catalog import AXIS, DISTANCE, STAIRS_SHAPE
from redsim.world.properties import POWERED
from redsim.world.rotation import mirror_state, rotate_state

P = blocks.parse_state


def up(yaw: float = 0.0) -> PlaceRequest:
    return PlaceRequest(Direction.UP, yaw, 30.0)


def test_hundreds_of_blocks_are_simulated() -> None:
    assert len(blocks.REGISTRY) > 600
    for block_id in (
        "quartz_block", "white_concrete", "red_terracotta", "oak_log", "quartz_pillar",
        "oak_stairs", "oak_slab", "oak_leaves", "white_carpet", "white_stained_glass",
        "copper_block", "waxed_oxidized_cut_copper", "deepslate_diamond_ore",
        "poplar_button", "poplar_pressure_plate", "poplar_sign", "white_glazed_terracotta",
    ):  # fmt: skip
        assert f"minecraft:{block_id}" in blocks.REGISTRY, block_id


def test_settings_come_from_the_game() -> None:
    level = Document.new_flat().level
    pos = (0, 1, 0)

    def conducts(text: str) -> bool:
        return P(text).is_redstone_conductor(level, pos)

    assert conducts("quartz_block") and conducts("white_wool") and conducts("oak_log")
    assert not conducts("white_stained_glass") and not conducts("oak_leaves")
    assert not conducts("sea_lantern")  # isRedstoneConductor(Blocks::never)
    assert not conducts("oak_stairs") and not conducts("oak_slab")  # not full blocks
    assert conducts("oak_slab[type=double]")
    assert blocks.get("white_glazed_terracotta").push_reaction is PushReaction.PUSH
    assert blocks.get("oak_leaves").push_reaction is PushReaction.POPPED
    assert blocks.get("crying_obsidian").push_reaction is PushReaction.IMMOVEABLE


def test_pillars_take_the_clicked_axis_and_turn() -> None:
    doc = Document.new_flat()
    doc.place((0, 1, 0), blocks.get("oak_log"), PlaceRequest(Direction.EAST, 0.0, 0.0))
    state = doc.state_at((0, 1, 0))
    assert state.get(AXIS) == "x"
    assert rotate_state(state, 1).get(AXIS) == "z"
    assert rotate_state(state, 2).get(AXIS) == "x"


def test_stairs_form_corners_like_the_game() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("oak_stairs[facing=north]"))
    # Behind it (north), a stair facing east: StairBlock.getStairsShape → outer_right.
    doc.setblock((0, 1, -1), P("oak_stairs[facing=east]"))
    assert doc.state_at((0, 1, 0)).get(STAIRS_SHAPE) == "outer_right"
    # In front (south), a stair facing west makes an inner corner instead.
    doc.setblock((5, 1, 0), P("oak_stairs[facing=north]"))
    doc.setblock((5, 1, 1), P("oak_stairs[facing=west]"))
    assert doc.state_at((5, 1, 0)).get(STAIRS_SHAPE) == "inner_left"
    # Upside-down stairs give a full top face (dust stays on them).
    top = P("oak_stairs[half=top]")
    assert top.get_block_support_shape().is_face_sturdy(Direction.UP)
    assert not P("oak_stairs").get_block_support_shape().is_face_sturdy(Direction.UP)


def test_stairs_mirror_like_the_game() -> None:
    inner = P("oak_stairs[facing=north,shape=inner_left]")
    left_right = mirror_state(inner, "z")
    assert left_right.get(STAIRS_SHAPE) == "inner_right"
    assert repr(left_right).startswith("minecraft:oak_stairs[facing=south")
    side = P("oak_stairs[facing=east,shape=inner_left]")
    assert mirror_state(side, "x").get(STAIRS_SHAPE) == "inner_left"  # FRONT_BACK quirk


def test_leaves_follow_their_log_a_tick_later_and_observers_see_it() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("oak_log"))
    doc.place((1, 1, 0), blocks.get("oak_leaves"), up())
    assert doc.state_at((1, 1, 0)).get(DISTANCE) == 1
    doc.setblock((2, 1, 0), P("observer[facing=west]"))  # watches the leaves
    doc.run_ticks(4)
    doc.setblock((0, 1, 0), P("air"))  # the log goes: distance 7 a tick later
    assert doc.state_at((1, 1, 0)).get(DISTANCE) == 1
    fired = False
    for _ in range(4):
        doc.run_ticks(1)
        fired = fired or bool(doc.state_at((2, 1, 0)).get(POWERED))
    assert doc.state_at((1, 1, 0)).get(DISTANCE) == 7
    assert fired


def test_carpets_break_without_a_block_below() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("stone"))
    doc.place((0, 2, 0), blocks.get("white_carpet"), up())
    assert doc.state_at((0, 2, 0)).is_(blocks.get("white_carpet"))
    doc.setblock((0, 1, 0), P("air"))
    assert doc.state_at((0, 2, 0)).is_air


def test_facing_blocks_face_the_player() -> None:
    doc = Document.new_flat()
    doc.place((0, 1, 0), blocks.get("white_glazed_terracotta"), up(yaw=0.0))  # looks south
    assert repr(doc.state_at((0, 1, 0))) == "minecraft:white_glazed_terracotta[facing=north]"
