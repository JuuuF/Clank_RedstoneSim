""" "Why did this block change?" from the trace, and the signal heat view."""

from __future__ import annotations

from redsim.editor.document import Document
from redsim.editor.heat import signal_heat
from redsim.sim.causes import state_change, why
from redsim.world import blocks

P = blocks.parse_state
LEVER, WIRE, REPEATER, LAMP = (0, 1, 0), (1, 1, 0), (2, 1, 0), (3, 1, 0)


def circuit() -> Document:
    doc = Document.new_flat()
    doc.setblock(LEVER, P("lever[face=floor,facing=east]"))
    doc.setblock(WIRE, P("redstone_wire"))
    doc.setblock(REPEATER, P("repeater[facing=west]"))  # input from the west
    doc.setblock(LAMP, P("redstone_lamp"))
    return doc


def test_the_chain_reaches_back_across_ticks_to_the_lever() -> None:
    doc = circuit()
    doc.run_ticks(2)
    doc.use(LEVER)
    doc.run_ticks(5)
    causes = why(doc.level.trace, LAMP)
    texts = [c.text for c in causes]
    assert texts[0] == "redstone lamp: lit false → true"
    assert causes[0].tick == 4  # the repeater's delay: 2 ticks after the lever
    assert "repeater: powered false → true" in texts
    assert "scheduled tick of repeater" in texts
    assert "repeater scheduled a tick for tick 4" in texts
    assert "redstone wire: power 0 → 15" in texts
    assert "lever: powered false → true" in texts
    assert texts[-1] == "edit or player action: use"
    assert [c.pos for c in causes][-1] == LEVER
    ticks = [c.tick for c in causes]
    assert ticks == sorted(ticks, reverse=True)  # newest first


def test_a_block_that_never_changed_has_no_causes() -> None:
    doc = circuit()
    doc.run_ticks(3)
    assert why(doc.level.trace, (5, 1, 5)) == []


def test_sequence_power_is_named_as_the_cause() -> None:
    doc = Document.new_flat()
    doc.setblock(LAMP, P("redstone_lamp"))
    doc.add_pulse(LAMP, 2, 15, 4)
    doc.run_ticks(4)
    texts = [c.text for c in why(doc.level.trace, LAMP)]
    assert texts[0] == "redstone lamp: lit false → true"
    assert any(t.startswith("sequence power 15") for t in texts)


def test_state_changes_in_words() -> None:
    assert state_change("minecraft:air", "minecraft:stone") == "stone placed"
    assert state_change("minecraft:stone", "minecraft:air") == "stone removed"
    assert (
        state_change(
            "minecraft:lever[face=floor,powered=false]", "minecraft:lever[face=floor,powered=true]"
        )
        == "lever: powered false → true"
    )


def test_heat_follows_the_signal() -> None:
    doc = circuit()
    for x in range(4, 8):  # a longer wire after the lamp's line
        doc.setblock((x, 1, 2), P("redstone_wire"))
    doc.setblock((3, 1, 2), P("redstone_block"))
    doc.run_ticks(2)
    doc.use(LEVER)
    doc.run_ticks(5)
    heat = signal_heat(doc.level)
    assert heat[LEVER] == 15 and heat[WIRE] == 15 and heat[LAMP] == 15
    assert [heat[(x, 1, 2)] for x in range(4, 8)] == [15, 14, 13, 12]
    assert heat[(0, 0, 0)] == 15  # the lever powers the block it stands on
    assert (9, 0, 9) not in heat  # the rest of the floor is not powered
