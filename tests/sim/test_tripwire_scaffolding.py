"""Tripwire hooks, tripwire and scaffolding (game-checked: EXP-064, EXP-065)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.sim.engine import Action, ActionError
from redsim.world import blocks
from redsim.world.blocks.scaffolding import BOTTOM, DISTANCE
from redsim.world.blocks.tripwire import ATTACHED, DISARMED, FACING
from redsim.world.properties import LIT, POWERED
from redsim.world.rotation import mirror_state, rotate_state
from tests.sim.bench import Bench

HOOK_A: Pos = (1, 1, 0)


def _line(b: Bench, wires: int = 3) -> Pos:
    """Stone, hook facing east, ``wires`` tripwire, hook facing west, stone (along x)."""
    end = wires + 2
    b.setblock((0, 1, 0), "stone")
    b.setblock((end + 1, 1, 0), "stone")
    b.place(HOOK_A, "tripwire_hook[facing=east]")
    b.place((end, 1, 0), "tripwire_hook[facing=west]")
    for x in range(2, end):
        b.place((x, 1, 0), "tripwire")
    return (end, 1, 0)


def _visit(b: Bench, pos: Pos, ticks: int) -> None:
    payload = {"mobs": 1, "others": 0, "ticks": ticks}
    b.engine.apply(Action("plate_visitors", pos, payload=payload))


def test_a_complete_line_attaches_both_hooks_and_every_wire() -> None:
    b = Bench()
    hook_b = _line(b)
    assert b.get(HOOK_A, ATTACHED) is True and b.get(hook_b, ATTACHED) is True
    assert all(b.get((x, 1, 0), ATTACHED) for x in range(2, 5))
    wire = b.state((3, 1, 0))
    assert wire.get(POWERED) is False and wire.properties_dict()["east"] == "true"


def test_an_entity_in_the_wire_powers_both_hooks_until_the_recheck() -> None:
    b = Bench()
    hook_b = _line(b)
    b.setblock((0, 2, 0), "redstone_lamp")
    _visit(b, (3, 1, 0), ticks=2)
    b.tick()  # pressed in the entity phase
    assert b.get((3, 1, 0), POWERED) is True
    assert b.get(HOOK_A, POWERED) is True and b.get(hook_b, POWERED) is True
    assert b.level.get_direct_signal_to((0, 1, 0)) == 15  # strong power into its block
    assert b.get((0, 2, 0), LIT) is True
    b.tick(9)
    assert b.get(HOOK_A, POWERED) is True  # the recheck comes 10 ticks after the press
    b.tick()
    assert b.get((3, 1, 0), POWERED) is False and b.get(HOOK_A, POWERED) is False


def test_breaking_a_wire_pulses_the_hooks_and_shears_do_not() -> None:
    b = Bench()
    _line(b)
    b.break_block((3, 1, 0))
    assert b.get(HOOK_A, POWERED) is True and b.get(HOOK_A, ATTACHED) is True
    b.tick(10)  # the hook's recheck: the line is broken
    assert b.get(HOOK_A, POWERED) is False and b.get(HOOK_A, ATTACHED) is False
    assert b.get((2, 1, 0), ATTACHED) is False

    c = Bench()
    _line(c)
    c.engine.apply(Action("break", (3, 1, 0), payload={"shears": True}))
    assert c.state((3, 1, 0)).is_air
    assert c.get(HOOK_A, POWERED) is False and c.get(HOOK_A, ATTACHED) is False


def test_stepping_on_a_disarmed_wire_detaches_the_line_for_ten_ticks() -> None:
    b = Bench()
    _line(b)
    b.setblock((3, 1, 0), "tripwire[disarmed=true,attached=true,east=true,west=true]")
    _visit(b, (3, 1, 0), ticks=100)
    b.tick()
    assert b.get((3, 1, 0), POWERED) is True and b.get((3, 1, 0), DISARMED) is True
    assert b.get(HOOK_A, POWERED) is False and b.get(HOOK_A, ATTACHED) is False
    b.tick(10)  # the hook's recheck: attached again (the wire stays pressed: no change)
    assert b.get(HOOK_A, ATTACHED) is True and b.get(HOOK_A, POWERED) is False


def test_hooks_put_by_setblock_wait_for_the_wire_to_change() -> None:
    b = Bench()
    b.setblock((0, 1, 0), "stone")
    b.setblock((4, 1, 0), "stone")
    b.place((2, 1, 0), "tripwire")
    b.setblock(HOOK_A, "tripwire_hook[facing=east]")
    b.setblock((3, 1, 0), "tripwire_hook[facing=west]")
    assert b.get(HOOK_A, ATTACHED) is False  # no setPlacedBy for /setblock
    _visit(b, (2, 1, 0), ticks=1)
    b.tick()
    assert b.get(HOOK_A, ATTACHED) is True and b.get(HOOK_A, POWERED) is True


def test_a_hook_needs_a_sturdy_block_behind_and_turns_from_the_look() -> None:
    from redsim.editor.placement import PlaceRequest, placement_state

    b = Bench()
    with pytest.raises(ActionError):
        b.place((5, 1, 5), "tripwire_hook[facing=east]")
    b.setblock((4, 1, 5), "stone")
    request = PlaceRequest(clicked_face=Direction.EAST, yaw=90.0, pitch=0.0)  # looking west
    state = placement_state(blocks.TRIPWIRE_HOOK, request, b.level, (5, 1, 5))
    assert state is not None and state.get(FACING) is Direction.EAST
    b.setblock((4, 1, 5), "air")
    assert placement_state(blocks.TRIPWIRE_HOOK, request, b.level, (5, 1, 5)) is None


def test_a_hook_breaks_with_its_block_and_the_wire_stays_attached() -> None:
    b = Bench()
    hook_b = _line(b)
    b.setblock((0, 1, 0), "air")
    assert b.state(HOOK_A).is_air
    assert b.get(hook_b, ATTACHED) is False  # onRemoved detached the other hook,
    assert b.get((2, 1, 0), ATTACHED) is True  # then stopped: the hook was gone already


def test_a_falling_block_passing_through_the_wire_triggers_it() -> None:
    b = Bench()
    _line(b)
    b.setblock((3, 4, 0), "sand")
    powered = False
    for _ in range(30):
        b.tick()
        powered |= bool(b.get(HOOK_A, POWERED))
    assert powered
    assert b.state((3, 1, 0)).is_(blocks.TRIPWIRE)  # the sand cannot land in the wire


def test_tripwire_turns_and_mirrors_its_sides() -> None:
    state = blocks.parse_state("tripwire[north=true,east=true]")
    turned = rotate_state(state, 1).properties_dict()
    assert turned["east"] == "true" and turned["south"] == "true"
    mirrored = mirror_state(state, "x").properties_dict()
    assert mirrored["west"] == "true" and mirrored["east"] == "false"
    hook = rotate_state(blocks.parse_state("tripwire_hook[facing=north]"), 1)
    assert hook.get(FACING) is Direction.EAST


# ------------------------------------------------------------------ scaffolding
def test_scaffolding_reaches_six_blocks_out_from_a_tower() -> None:
    b = Bench()
    b.place((0, 1, 0), "scaffolding")
    b.place((0, 2, 0), "scaffolding")
    for x in range(1, 7):
        b.place((x, 2, 0), "scaffolding")
    assert b.get((0, 2, 0), DISTANCE) == 0  # the distance of the one below
    assert b.get((6, 2, 0), DISTANCE) == 6 and b.get((6, 2, 0), BOTTOM) is True
    with pytest.raises(ActionError):
        b.place((7, 2, 0), "scaffolding")


def test_scaffolding_collapses_when_its_base_goes() -> None:
    b = Bench()
    b.place((0, 1, 0), "scaffolding")
    for x in range(1, 4):
        b.place((x, 1, 0), "scaffolding")  # on the floor: all distance 0
    b.place((0, 2, 0), "scaffolding")
    b.place((1, 2, 0), "scaffolding")
    assert b.get((1, 2, 0), DISTANCE) == 0
    b.break_block((0, 1, 0))
    b.tick(20)
    assert b.state((0, 2, 0)).is_(blocks.SCAFFOLDING)  # held by the one below (1, 2, 0)
    assert b.get((0, 2, 0), DISTANCE) == 1 and b.get((0, 2, 0), BOTTOM) is True


def test_unsupported_scaffolding_breaks_but_one_set_at_seven_falls() -> None:
    b = Bench()
    b.place((2, 1, 2), "scaffolding")
    b.place((2, 2, 2), "scaffolding")
    b.place((3, 2, 2), "scaffolding")
    b.break_block((2, 2, 2))
    b.tick(3)
    assert b.state((3, 2, 2)).is_air and not b.level.entities  # broken, no falling block

    b.setblock((2, 6, 2), "scaffolding")  # distance 7 already: it falls
    b.tick()
    assert b.state((2, 6, 2)).is_air and len(b.level.entities) == 1
    b.tick(20)
    landed = b.state((2, 2, 2))  # on top of the scaffolding below (its collision top)
    assert landed.is_(blocks.SCAFFOLDING) and landed.get(DISTANCE) == 0
    assert not b.level.entities


def test_scaffolding_holds_things_on_top_but_never_conducts() -> None:
    b = Bench()
    b.place((1, 1, 0), "scaffolding")
    b.place((1, 2, 0), "redstone_torch")
    b.place((0, 1, 0), "redstone_lamp")
    b.place((2, 1, 0), "repeater[facing=east]")
    b.setblock((3, 1, 0), "redstone_block")
    b.tick(4)
    assert b.get((2, 1, 0), POWERED) is True
    assert b.get((0, 1, 0), LIT) is False  # the repeater's output does not pass through
    assert b.get((1, 2, 0), LIT) is True
    state = b.state((1, 1, 0))
    assert not state.is_solid() and not state.is_redstone_conductor(b.level, (1, 1, 0))
    assert not state.is_face_sturdy(b.level, (1, 1, 0), Direction.EAST)
    with pytest.raises(ActionError):  # no lever on its side
        b.place((1, 1, 1), "lever[face=wall,facing=south]")


# ------------------------------------------------------------------ command line
def test_cli_plate_shears_and_map_codes(tmp_path: Path) -> None:
    from redsim.cli.main import main

    class _Stdin(io.StringIO):
        def isatty(self) -> bool:
            return False

    world = tmp_path / "w.redsim.json"

    def run(text: str) -> str:
        out = io.StringIO()
        assert main([str(world), "-c", text], stdin=_Stdin(""), out=out) == 0, out.getvalue()
        return out.getvalue()

    run("new size 16")
    text = run(
        "set 0 1 0 stone; set 6 1 0 stone; place 1 1 0 tripwire_hook facing=east; "
        "place 5 1 0 tripwire_hook facing=west; place 2 1 0 tripwire; place 3 1 0 tripwire; "
        "place 4 1 0 tripwire; at 2 plate 3 1 0 mobs 1 for 3; at 30 break 4 1 0 shears; "
        "run 40; waves 1 1 0; show y=1"
    )
    assert "cut with shears 4 1 0" in text
    waves = next(line for line in text.splitlines() if line.startswith("1 1 0"))
    assert waves.split()[-1].startswith("...ffffffffff....")
    assert "y>" in text and "y<" in text and "s." in text and "Y/y  tripwire hook" in text
