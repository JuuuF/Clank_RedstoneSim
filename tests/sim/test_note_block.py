"""Note block: powered tracking, block events, instruments (NoteBlock.java)."""

from __future__ import annotations

from redsim.world.blocks.note_block import INSTRUMENT, NOTE
from redsim.world.properties import POWERED
from tests.sim.bench import Bench


def test_instrument_comes_from_the_block_below_and_follows_it() -> None:
    b = Bench()  # stone floor: basedrum
    b.place((1, 1, 0), "note_block")
    assert b.get((1, 1, 0), INSTRUMENT) == "basedrum"
    b.setblock((1, 2, 0), "glass")  # above: not a head, does not count
    assert b.get((1, 1, 0), INSTRUMENT) == "basedrum"
    b.setblock((1, 0, 0), "glass")  # the block below changes: hat
    assert b.get((1, 1, 0), INSTRUMENT) == "hat"


def test_rising_signal_plays_once_and_sets_powered() -> None:
    b = Bench()
    b.place((1, 1, 0), "note_block")
    b.place((0, 1, 0), "lever[face=floor,facing=north]")
    b.use((0, 1, 0))
    assert b.get((1, 1, 0), POWERED) is True
    events = [e for e in b.level.block_events if e[0] == (1, 1, 0)]
    assert len(events) == 1  # queued for the block-event phase
    b.tick()
    assert not b.level.block_events
    b.use((0, 1, 0))
    assert b.get((1, 1, 0), POWERED) is False
    assert not b.level.block_events  # a falling signal plays nothing


def test_no_note_with_a_block_above() -> None:
    b = Bench()
    b.place((1, 1, 0), "note_block")
    b.setblock((1, 2, 0), "stone")
    b.place((0, 1, 0), "lever[face=floor,facing=north]")
    b.use((0, 1, 0))
    assert b.get((1, 1, 0), POWERED) is True and not b.level.block_events


def test_use_tunes_and_wraps() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "note_block[instrument=basedrum,note=24]")  # placing resets it
    b.use((1, 1, 0))
    assert b.get((1, 1, 0), NOTE) == 0
    assert len(b.level.block_events) == 1
