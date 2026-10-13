"""Sequences: power pulses locked to positions, at chosen ticks, for chosen durations."""

from __future__ import annotations

from pathlib import Path

from redsim.editor.document import Document
from redsim.world import blocks
from redsim.world.properties import EXTENDED, LIT

P = blocks.parse_state


def piston_doc() -> Document:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("sticky_piston[facing=east]"))
    doc.setblock((1, 1, 0), P("stone"))
    return doc


def extended_at(doc: Document, tick: int) -> bool:
    assert doc.seek_tick(tick)
    return bool(doc.state_at((0, 1, 0)).get(EXTENDED))


def test_a_pulse_extends_a_piston_and_releases_it_after_its_duration() -> None:
    doc = piston_doc()
    doc.add_pulse((0, 1, 0), tick=3, strength=15, ticks=4)
    doc.run_ticks(15 - doc.tick)
    assert not extended_at(doc, 2)
    assert extended_at(doc, 4)  # powered from tick 3 on, extended a tick later
    assert extended_at(doc, 7)
    assert not extended_at(doc, 12)  # off after 4 ticks, retracted (sticky: pulled back)
    assert doc.state_at((1, 1, 0)).is_(blocks.STONE)
    assert [(p.tick, p.pos, p.ticks) for p in doc.pulses()] == [(3, (0, 1, 0), 4)]


def test_adding_an_earlier_pulse_keeps_the_later_ones_and_edits_change_them() -> None:
    doc = piston_doc()
    doc.add_pulse((0, 1, 0), tick=10, ticks=3)
    doc.add_pulse((0, 1, 0), tick=2, ticks=3)  # earlier: the tick-10 pulse stays
    assert [p.tick for p in doc.pulses()] == [2, 10]
    doc.run_ticks(20 - doc.tick)
    assert extended_at(doc, 4) and not extended_at(doc, 8) and extended_at(doc, 12)
    late = doc.pulses()[1]
    doc.edit_pulse(late.index, 14, 15, 2)
    assert [p.tick for p in doc.pulses()] == [2, 14]
    doc.run_ticks(20 - doc.tick)
    assert not extended_at(doc, 12) and extended_at(doc, 15)
    doc.undo()  # one undo step per change
    assert [p.tick for p in doc.pulses()] == [2, 10]


def test_power_belongs_to_the_position_not_the_block() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("redstone_lamp"))
    doc.add_pulse((0, 1, 0), tick=2, ticks=10)
    doc.run_ticks(4 - doc.tick)
    assert doc.state_at((0, 1, 0)).get(LIT)
    doc.setblock((0, 1, 0), P("stone"))  # another block there: the position stays powered
    assert (0, 1, 0) in doc.level.forced_power
    doc.setblock((0, 1, 0), P("redstone_lamp"))  # /setblock: no placement check, unlit
    doc.setblock((0, 2, 0), P("stone"))  # a neighbor update: the lamp sees the power
    doc.run_ticks(1)
    assert doc.state_at((0, 1, 0)).get(LIT)
    doc.run_ticks(16 - doc.tick)
    assert not doc.state_at((0, 1, 0)).get(LIT)  # the pulse ended


def test_a_running_pulse_survives_saving(tmp_path: Path) -> None:
    doc = piston_doc()
    doc.add_pulse((0, 1, 0), tick=2, ticks=20)
    doc.run_ticks(5 - doc.tick)
    doc.save(tmp_path / "seq.redsim.json")
    loaded = Document.open(tmp_path / "seq.redsim.json")
    # The loaded file starts its clock at 0: the pulse still has the same time left.
    (strength, until), now = doc.level.forced_power[(0, 1, 0)], doc.level.game_time
    assert loaded.level.forced_power == {
        (0, 1, 0): (strength, until - now + loaded.level.game_time)
    }


def test_extending_a_piston_in_the_inspector_adds_its_head() -> None:
    from redsim.world.properties import EXTENDED

    doc = Document.new_flat()
    doc.setblock((1, 1, 0), P("piston[facing=east]"))
    assert doc.state_at((2, 1, 0)).is_air
    doc.set_state((1, 1, 0), doc.state_at((1, 1, 0)).with_(EXTENDED, True))
    assert doc.state_at((1, 1, 0)).get(EXTENDED)
    assert doc.state_at((2, 1, 0)).is_(blocks.PISTON_HEAD)  # at once, in the same edit


def test_a_0_tick_pulse_is_on_and_off_at_the_same_moment() -> None:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("redstone_lamp"))
    doc.add_pulse((0, 1, 0), tick=2, ticks=0)
    assert [(p.tick, p.ticks) for p in doc.pulses()] == [(2, 0)]
    doc.run_ticks(6 - doc.tick)
    assert doc.level.forced_power == {}  # never left on
    assert doc.seek_tick(2)  # the lamp saw the power: lit at once (a lamp lights at once)
    assert doc.state_at((0, 1, 0)).get(LIT)
    assert doc.seek_tick(6)
    assert not doc.state_at((0, 1, 0)).get(LIT)  # and goes off 4 ticks later


def test_dragging_a_moving_piston_keeps_its_movement() -> None:
    from redsim.editor.clipboard import Region

    doc = Document.new_flat()
    doc.setblock((0, 1, 0), P("sticky_piston[facing=east]"))
    doc.setblock((1, 1, 0), P("stone"))
    doc.run_ticks(1)
    doc.setblock((-1, 1, 0), P("redstone_block"))
    doc.run_ticks(1)  # the extension started: moving pistons at this tick boundary
    moving = [p for p, s in doc.level.blocks.items() if s.block is blocks.MOVING_PISTON]
    assert moving and doc.can_edit
    low = min(moving)
    high = max(moving)
    doc.clone_region(Region(low, high), (0, 0, 3), "move")
    moved = [(x, y, z + 3) for x, y, z in moving]
    assert all(doc.level.get_block_entity(p, create=False) is not None for p in moved)
    doc.run_ticks(4)
    assert all(doc.state_at(p).block is not blocks.MOVING_PISTON for p in moved)
