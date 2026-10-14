"""Signs: placement like a player's, popping without support, blocking pistons, text as
history edits, saving, rotating and older documents."""

from __future__ import annotations

from pathlib import Path

from redsim.core.direction import Direction
from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.editor.placement import PlaceRequest, placement_state
from redsim.mcworld.importer import sign_texts
from redsim.world import blocks
from redsim.world.blocks.sign import ROTATION, SignBlockEntity
from redsim.world.properties import HORIZONTAL_FACING
from redsim.world.rotation import mirror_state, rotate_state

P = blocks.parse_state


def text(doc: Document, pos: tuple[int, int, int], side: str = "front") -> list[str]:
    entity = doc.level.get_block_entity(pos, create=False)
    assert isinstance(entity, SignBlockEntity)
    return entity.lines(side)


def test_placed_like_a_player() -> None:
    doc = Document.new_flat()
    # Looking down at the floor: a standing sign whose text faces the player.
    standing = placement_state(
        blocks.OAK_SIGN, PlaceRequest(Direction.UP, 0.0, 45.0), doc.level, (0, 1, 0)
    )
    assert standing is not None and standing.block is blocks.OAK_SIGN
    assert standing.get(ROTATION) == 8  # looking south: the text faces north, at the player
    turned = placement_state(
        blocks.OAK_SIGN, PlaceRequest(Direction.UP, 90.0, 45.0), doc.level, (0, 1, 0)
    )
    assert turned is not None and turned.get(ROTATION) == 12
    # Clicking the south face of a wall: a wall sign facing south.
    doc.setblock((0, 1, 0), P("stone"))
    wall = placement_state(
        blocks.OAK_SIGN, PlaceRequest(Direction.SOUTH, 0.0, 0.0), doc.level, (0, 1, 1)
    )
    assert wall is not None and wall.block is blocks.OAK_WALL_SIGN
    assert wall.get(HORIZONTAL_FACING) is Direction.SOUTH
    # In the air with nothing around: nowhere to hang it.
    assert (
        placement_state(
            blocks.OAK_SIGN, PlaceRequest(Direction.UP, 0.0, 45.0), doc.level, (5, 5, 5)
        )
        is None
    )


def test_signs_pop_without_support_and_block_pistons() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("stone"))
    doc.setblock((0, 2, 0), P("oak_sign"))
    doc.setblock((0, 1, 1), P("oak_wall_sign[facing=south]"))
    doc.setblock((3, 1, 0), P("piston[facing=east]"))
    doc.setblock((4, 1, 0), P("oak_sign"))
    doc.run_ticks(1)
    doc.setblock((2, 1, 0), P("redstone_block"))
    doc.break_block((0, 1, 0))
    assert doc.state_at((0, 2, 0)).is_air and doc.state_at((0, 1, 1)).is_air
    doc.run_ticks(3)
    assert doc.state_at((3, 1, 0)) == P("piston[facing=east,extended=false]")  # stopped
    assert doc.state_at((4, 1, 0)).block is blocks.OAK_SIGN


def test_text_is_an_edit_that_undoes_replays_and_saves(tmp_path: Path) -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("oak_sign"))
    doc.run_ticks(2)
    doc.set_sign_text((0, 1, 0), "front", ["Clock", "every 4 ticks"])
    doc.set_sign_text((0, 1, 0), "back", ["", "back side"])
    assert text(doc, (0, 1, 0)) == ["Clock", "every 4 ticks", "", ""]
    doc.run_ticks(2)
    doc.seek_tick(1)
    assert text(doc, (0, 1, 0)) == ["", "", "", ""]  # before it was written
    doc.seek_tick(4)
    assert text(doc, (0, 1, 0), "back") == ["", "back side", "", ""]
    doc.save(tmp_path / "signs.redsim.json")
    loaded = Document.open(tmp_path / "signs.redsim.json")
    assert text(loaded, (0, 1, 0)) == ["Clock", "every 4 ticks", "", ""]
    doc.undo()
    assert text(doc, (0, 1, 0), "back") == ["", "", "", ""]


def test_saved_world_data_is_kept_unless_edited() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("oak_sign"))
    entity = doc.level.get_block_entity((0, 1, 0))
    assert isinstance(entity, SignBlockEntity)
    styled = {"text": "Hi", "color": "red", "bold": True}
    entity.load_json(
        {"front_text": {"messages": [styled, "", "", ""], "color": "blue"}, "is_waxed": True}
    )
    assert entity.front == ["Hi", "", "", ""]
    saved = entity.to_json()
    assert saved["front_text"]["messages"][0] == styled  # unchanged: formatting kept
    assert saved["front_text"]["color"] == "blue" and saved["is_waxed"] is True
    entity.front = ["Bye", "", "", ""]
    assert entity.to_json()["front_text"]["messages"] == ["Bye", "", "", ""]
    entity.load_json({"Text1": '{"text":"old"}', "Text2": "plain"})  # before 1.20
    assert entity.front[:2] == ["old", "plain"]


def test_turning_and_mirroring_follow_the_game() -> None:
    sign = P("oak_sign[rotation=1]")
    assert rotate_state(sign, 1).get(ROTATION) == 5
    assert rotate_state(sign, 3).get(ROTATION) == 13
    assert mirror_state(sign, "x").get(ROTATION) == 15  # Mirror.FRONT_BACK
    assert mirror_state(sign, "z").get(ROTATION) == 7  # Mirror.LEFT_RIGHT
    wall = P("oak_wall_sign[facing=east]")
    assert rotate_state(wall, 1).get(HORIZONTAL_FACING) is Direction.SOUTH


def test_selections_carry_the_text() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("oak_sign"))
    doc.set_sign_text((0, 1, 0), "front", ["moved"])
    doc.clone_region(Region((0, 1, 0), (0, 1, 0)), (2, 0, 0), "move")
    assert text(doc, (2, 1, 0))[0] == "moved"


def test_old_documents_move_their_sign_text_into_the_signs(tmp_path: Path) -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("oak_sign"))
    del doc.level.block_entities[(0, 1, 0)]  # saved while signs were foreign blocks
    doc.extra["signs"] = {"0,1,0": ["from", "a world"], "9,9,9": ["hanging"]}
    doc.save(tmp_path / "old.redsim.json")
    loaded = Document.open(tmp_path / "old.redsim.json")
    assert text(loaded, (0, 1, 0))[:2] == ["from", "a world"]
    assert loaded.extra["signs"] == {"9,9,9": ["hanging"]}


def test_worlds_keep_only_foreign_sign_text_as_data() -> None:
    entities = {
        (0, 0, 0): {"front_text": {"messages": ['"A"', '""', '""', '""']}},
        (1, 0, 0): {"front_text": {"messages": ["B", "", "", ""]}},
    }
    texts = {(0, 0, 0): "minecraft:oak_sign[rotation=0]", (1, 0, 0): "minecraft:oak_hanging_sign"}
    assert sign_texts(entities, texts) == {"1,0,0": ["B", "", "", ""]}
