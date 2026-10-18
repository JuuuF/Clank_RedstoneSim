"""Lightning rods and the editor's lightning strike (game-checked: EXP-066)."""

from __future__ import annotations

import pytest

from redsim.core.direction import Direction
from redsim.editor.placement import PlaceRequest, placement_state
from redsim.sim.engine import Action
from redsim.world import blocks
from redsim.world.blocks.lightning_rod import ROD_IDS
from redsim.world.properties import FACING, LIT, POWERED
from tests.sim.bench import Bench


def _strike(b: Bench, pos: tuple[int, int, int]) -> None:
    b.engine.apply(Action("lightning_strike", pos))


def test_a_struck_rod_gives_15_for_8_ticks_and_strongly_powers_its_block() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "stone")
    b.place((1, 2, 0), "lightning_rod[facing=up]")
    b.place((2, 1, 0), "redstone_lamp")
    b.setblock((1, 1, 1), "stone")
    b.place((1, 2, 1), "redstone_wire")
    assert b.state((1, 2, 1)).properties_dict()["north"] == "side"  # wire connects to it
    _strike(b, (1, 2, 0))
    assert b.get((1, 2, 0), POWERED) is False  # the bolt strikes in the next tick
    b.tick()
    assert b.get((1, 2, 0), POWERED) is True and b.get((2, 1, 0), LIT) is True
    assert b.level.get_direct_signal_to((1, 1, 0)) == 15
    assert b.get((1, 2, 1), blocks.REDSTONE_WIRE.properties[-1]) == 15
    b.tick(7)
    assert b.get((1, 2, 0), POWERED) is True
    b.tick()
    assert b.get((1, 2, 0), POWERED) is False


@pytest.mark.parametrize(
    ("rod", "after"),
    [
        ("oxidized_lightning_rod", "minecraft:lightning_rod"),
        ("exposed_lightning_rod", "minecraft:lightning_rod"),
        ("waxed_weathered_lightning_rod", "minecraft:waxed_weathered_lightning_rod"),
    ],
)
def test_lightning_cleans_an_unwaxed_rod(rod: str, after: str) -> None:
    b = Bench()
    b.place((3, 1, 3), f"{rod}[facing=up]")
    _strike(b, (3, 1, 3))
    b.tick()
    state = b.state((3, 1, 3))
    assert state.block.id == after and state.get(POWERED) is True
    b.tick(8)
    assert b.get((3, 1, 3), POWERED) is False


def test_a_struck_rod_moved_by_a_piston_stays_powered_for_8_new_ticks() -> None:
    b = Bench()
    b.place((4, 1, 0), "lightning_rod[facing=up]")
    b.place((3, 1, 0), "piston[facing=east]")
    _strike(b, (4, 1, 0))
    b.tick(3)
    b.setblock((2, 1, 0), "redstone_block")
    b.tick(3)  # the piston moves it in 2 ticks
    assert b.state((5, 1, 0)).is_(blocks.get("lightning_rod"))
    assert b.get((5, 1, 0), POWERED) is True
    b.tick(7)
    assert b.get((5, 1, 0), POWERED) is True
    b.tick(1)
    assert b.get((5, 1, 0), POWERED) is False


def test_rods_face_the_clicked_face_and_need_no_support() -> None:
    b = Bench()
    request = PlaceRequest(clicked_face=Direction.EAST, yaw=90.0, pitch=0.0)
    state = placement_state(blocks.get("lightning_rod"), request, b.level, (5, 5, 5))
    assert state is not None and state.get(FACING) is Direction.EAST
    b.place((5, 5, 5), "lightning_rod[facing=down]")  # in the air: rods need no support
    rod = b.state((5, 5, 5))
    assert not rod.is_redstone_conductor(b.level, (5, 5, 5)) and rod.is_solid()
    assert len(ROD_IDS) == 8 and all(i in blocks.REGISTRY for i in ROD_IDS)
