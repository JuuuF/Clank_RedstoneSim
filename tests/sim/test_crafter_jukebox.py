"""Crafters, jukeboxes and detector rails (game-checked: EXP-067)."""

from __future__ import annotations

from redsim.sim.engine import Action
from redsim.world import blocks
from redsim.world.blocks.crafter import ORIENTATION, TRIGGERED, CrafterBlockEntity
from redsim.world.blocks.jukebox import HAS_RECORD, JukeboxBlockEntity
from redsim.world.properties import LIT, POWERED
from redsim.world.rotation import mirror_state, rotate_state
from tests.sim.bench import Bench


def test_power_triggers_a_crafter_and_an_observer_sees_it() -> None:
    b = Bench()
    b.setblock((2, 1, 1), "crafter[orientation=north_up]")
    b.setblock((3, 1, 1), "observer[facing=west]")
    b.setblock((4, 1, 1), "redstone_lamp")
    b.tick(4)  # the observer's own /setblock pulse is over
    b.setblock((1, 1, 1), "redstone_block")
    assert b.get((2, 1, 1), TRIGGERED) is True
    entity = b.level.get_block_entity((2, 1, 1))
    assert isinstance(entity, CrafterBlockEntity) and entity.triggered == 1
    b.tick(2)
    assert b.get((3, 1, 1), POWERED) is True and b.get((4, 1, 1), LIT) is True
    b.tick(4)  # the craft attempt finds no recipe: nothing else happens
    assert b.get((2, 1, 1), TRIGGERED) is True
    b.setblock((1, 1, 1), "air")
    assert b.get((2, 1, 1), TRIGGERED) is False


def test_a_comparator_counts_filled_and_disabled_crafter_slots() -> None:
    b = Bench()
    nbt = {
        "Items": [{"Slot": 0, "id": "minecraft:dirt", "count": 1}],
        "disabled_slots": [0, 3, 5],  # slot 0 holds an item: it cannot be disabled
    }
    b.engine.apply(Action("setblock", (2, 1, 3), "crafter", payload={"nbt": nbt}))
    b.setblock((2, 1, 4), "comparator[facing=north]")
    b.tick(2)
    entity = b.level.get_block_entity((2, 1, 3))
    assert isinstance(entity, CrafterBlockEntity) and entity.get_redstone_signal() == 3
    b.engine.apply(
        Action(
            "container_item", (2, 1, 3), payload={"slot": 3, "item": "minecraft:dirt", "count": 1}
        )
    )
    assert entity.disabled[3] is False and entity.get_redstone_signal() == 3


def test_crafter_orientation_turns_and_mirrors() -> None:
    state = blocks.parse_state("crafter[orientation=up_north]")
    assert rotate_state(state, 1).get(ORIENTATION) == "up_east"
    assert (
        mirror_state(blocks.parse_state("crafter[orientation=east_up]"), "x").get(ORIENTATION)
        == "west_up"
    )


def test_a_jukebox_plays_a_disc_and_stops_at_the_end_of_the_song() -> None:
    b = Bench()
    b.setblock((2, 1, 7), "jukebox")
    b.place((1, 1, 7), "redstone_wire")
    assert b.state((1, 1, 7)).properties_dict()["east"] == "side"  # a signal source
    b.engine.apply(
        Action(
            "container_item",
            (2, 1, 7),
            payload={"slot": 0, "item": "minecraft:music_disc_11", "count": 1},
        )
    )
    assert b.get((2, 1, 7), HAS_RECORD) is True
    assert b.get((1, 1, 7), blocks.REDSTONE_WIRE.properties[-1]) == 15
    entity = b.level.get_block_entity((2, 1, 7))
    assert isinstance(entity, JukeboxBlockEntity) and entity.comparator_output() == 11
    entity.ticks_since_song_started = 71 * 20 + 19  # 11 is 71 seconds, plus 20 ticks
    b.tick()
    assert entity.is_playing()
    b.tick()
    assert not entity.is_playing() and b.get((1, 1, 7), blocks.REDSTONE_WIRE.properties[-1]) == 0
    assert entity.comparator_output() == 11  # the disc is still in it
    b.use((2, 1, 7))  # ejected (the item is not simulated)
    assert b.get((2, 1, 7), HAS_RECORD) is False and entity.comparator_output() == 0


def test_detector_rails_connect_wire_and_stay_unpowered_without_minecarts() -> None:
    b = Bench()
    b.place((2, 1, 11), "detector_rail")
    b.place((1, 1, 11), "redstone_wire")
    assert b.state((1, 1, 11)).properties_dict()["east"] == "side"
    b.setblock((2, 1, 12), "detector_rail[powered=true]")
    assert b.get((2, 1, 12), POWERED) is False  # checkPressed in onPlace: no minecart
    b.place((3, 1, 11), "rail")
    assert b.state((2, 1, 11)).properties_dict()["shape"] in ("east_west", "north_south")


def test_enchanting_tables_hold_still_and_sand_breaks_on_them() -> None:
    from redsim.core.direction import Direction
    from redsim.world.properties import EXTENDED

    b = Bench()
    b.setblock((2, 1, 3), "enchanting_table")
    b.setblock((1, 1, 3), "piston[facing=east]")
    b.setblock((0, 1, 3), "redstone_block")
    b.tick(3)
    assert b.get((1, 1, 3), EXTENDED) is False  # a block entity: immovable
    table = b.state((2, 1, 3))
    assert not table.is_redstone_conductor(b.level, (2, 1, 3))
    assert table.is_face_sturdy(b.level, (2, 1, 3), Direction.DOWN)
    assert not table.is_face_sturdy(b.level, (2, 1, 3), Direction.UP)
    b.setblock((2, 4, 3), "sand")
    b.tick(30)
    assert not b.level.entities and b.state((2, 2, 3)).is_air  # landed in the table's cell
