"""The shipped example world must load and every station in it must work."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from redsim.core.pos import Pos
from redsim.editor.document import Document
from redsim.world import blocks
from redsim.world.blocks.composter import LEVEL
from redsim.world.blocks.sign import SignBlockEntity
from redsim.world.properties import EXTENDED, LIT, POWER, POWERED
from tools import make_examples
from tools.make_examples import origin

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "showcase.redsim.json"


@pytest.fixture(scope="module")
def saved() -> Document:
    return Document.open(EXAMPLE)


@pytest.fixture
def doc(saved: Document) -> Document:
    """A fresh copy of the example world for each test."""
    return Document.open(EXAMPLE)


def district(column: int, row: int) -> Callable[[int, int, int], Pos]:
    ox, _, oz = origin(column, row)
    return lambda x, y, z: (ox + x, y, oz + z)


A, B, C, D = (district(c, 0) for c in range(4))
E, F, G = (district(c, 1) for c in range(3))


def lit(doc: Document, pos: Pos) -> bool:
    return bool(doc.state_at(pos).get(LIT))


def test_example_world_matches_its_generator(saved: Document) -> None:
    fresh = make_examples.build()
    assert saved.level.blocks == fresh.level.blocks
    assert set(saved.groups.groups) == set(fresh.groups.groups)
    assert len(saved.pulses()) == len(fresh.pulses()) == 18
    assert saved.tick == 0 and saved.end_tick == fresh.end_tick


def test_every_sign_line_fits(saved: Document) -> None:
    """Signs hold 90 font pixels per line (the game's limit); 15 characters as a rule of
    thumb without the font."""
    signs = [e for e in saved.level.block_entities.values() if isinstance(e, SignBlockEntity)]
    assert len(signs) >= 50
    for sign in signs:
        assert all(len(line) <= 17 for line in sign.front), sign.front


def test_basics(doc: Document) -> None:
    doc.use(A(6, 1, 0))  # 1. lever → lamp at once
    assert lit(doc, A(5, 1, 0))

    assert lit(doc, A(3, 1, 3))  # 2. inverter output starts on
    doc.use(A(6, 1, 3))
    doc.run_ticks(6)
    assert not lit(doc, A(3, 1, 3))

    doc.use(A(7, 1, 6))  # 3. delay-4 repeater: 8 ticks
    doc.run_ticks(7)
    assert not lit(doc, A(1, 1, 6))
    doc.run_ticks(1)
    assert lit(doc, A(1, 1, 6))

    doc.use(A(7, 1, 9))  # 4. AND gate: one input is not enough
    doc.run_ticks(6)
    assert not lit(doc, A(4, 1, 10))
    doc.use(A(7, 1, 11))
    doc.run_ticks(6)
    assert lit(doc, A(4, 1, 10))

    assert lit(doc, A(3, 1, 14))  # 5. comparator: barrel source 14 - side 0
    doc.use(A(5, 1, 17))  # side input 14: output 0
    doc.run_ticks(8)
    assert not lit(doc, A(3, 1, 14))

    doc.use(A(7, 1, 20))  # 6. sticky piston pushes the planks
    doc.run_ticks(3)
    assert doc.state_at(A(6, 1, 20)).get(EXTENDED)
    assert doc.state_at(A(4, 1, 20)).is_(blocks.OAK_PLANKS)

    doc.use(A(7, 2, 23))  # 7. both door pistons extend together
    doc.run_ticks(3)
    assert doc.state_at(A(4, 1, 23)).is_(blocks.OAK_PLANKS)
    assert doc.state_at(A(4, 2, 23)).is_(blocks.OAK_PLANKS)


def test_logic(doc: Document) -> None:
    doc.use(B(6, 1, 1))  # 1. OR: input B alone
    doc.run_ticks(1)
    assert lit(doc, B(3, 1, 0))

    doc.use(B(9, 1, 4))  # 2. repeater lock: data on → lamp on
    doc.run_ticks(4)
    assert lit(doc, B(4, 1, 4))
    doc.use(B(5, 1, 6))  # lock
    doc.run_ticks(4)
    doc.use(B(9, 1, 4))  # data off: the locked repeater holds
    doc.run_ticks(8)
    assert lit(doc, B(4, 1, 4))

    for presses, expect in ((1, True), (2, False)):  # 3. copper bulb toggles per press
        doc.use(B(9, 1, 8))
        doc.run_ticks(25)
        assert lit(doc, B(6, 1, 8)) is expect, presses

    doc.use(B(10, 1, 12))  # 4. observer chain: the lamp blinks
    seen = []
    for _ in range(14):
        doc.run_ticks(1)
        seen.append(lit(doc, B(5, 1, 12)))
    assert any(seen) and not seen[-1]

    doc.use(B(8, 1, 16))  # 5. stone button 20 ticks, oak 30
    doc.use(B(4, 1, 16))
    doc.run_ticks(24)
    assert not lit(doc, B(7, 1, 16)) and lit(doc, B(3, 1, 16))

    doc.use(B(10, 1, 20))  # 6. torch tower: the lamp on top follows the lever
    doc.run_ticks(14)
    assert lit(doc, B(8, 9, 20))

    doc.plate_visitors(B(9, 1, 24), 1, 0, 10)  # 7. pressure plates
    doc.plate_visitors(B(5, 1, 24), 6, 0, 10)
    doc.run_ticks(2)
    assert lit(doc, B(8, 1, 24)) and lit(doc, B(0, 1, 24))

    doc.projectile_hit(B(8, 1, 28), 15, True)  # 8. target block
    doc.run_ticks(2)
    assert lit(doc, B(4, 1, 28))

    doc.use(B(9, 1, 32))  # 9. a new note: the observer blinks the lamp
    doc.run_ticks(3)
    assert lit(doc, B(7, 1, 32))


@pytest.mark.parametrize(("z", "kind", "power"), [s[:3] for s in make_examples.SOURCES])
def test_signal_sources(saved: Document, z: int, kind: str, power: int) -> None:
    comparator = saved.state_at(C(14, 1, z))
    assert comparator.is_(blocks.COMPARATOR) and comparator.get(POWERED)
    assert saved.level.get_block_entity(C(14, 1, z)).output == power  # type: ignore[union-attr]
    assert saved.state_at(C(13, 1, z)).get(POWER) == power
    assert lit(saved, C(0, 1, z)) is (power >= 13)


def test_strength_lines(doc: Document) -> None:
    assert lit(doc, C(4, 1, 28))  # 8. through a block: 10, minus 9 dust
    doc.use(C(16, 1, 24))  # 7. 15 dust still light the lamp
    doc.run_ticks(1)
    assert doc.state_at(C(1, 1, 24)).get(POWER) == 1
    assert lit(doc, C(0, 1, 24))


def test_pistons(doc: Document) -> None:
    doc.use(D(16, 1, 0))  # 1. push limit: 12 planks move
    doc.run_ticks(3)
    assert doc.state_at(D(2, 1, 0)).is_(blocks.OAK_PLANKS)

    doc.use(D(14, 1, 4))  # 2. slime carries its neighbors, not the honey
    doc.run_ticks(3)
    assert doc.state_at(D(11, 2, 4)).is_(blocks.SLIME_BLOCK)
    assert doc.state_at(D(11, 3, 4)).is_(blocks.STONE)
    assert doc.state_at(D(11, 2, 5)).is_(blocks.STONE)
    assert doc.state_at(D(12, 2, 3)).is_(blocks.HONEY_BLOCK)

    doc.use(D(16, 1, 8))  # 3. moving power
    doc.run_ticks(3)
    assert lit(doc, D(12, 1, 8))

    assert not doc.state_at(D(14, 1, 12)).get(EXTENDED)  # 4. budded until updated
    doc.setblock(D(14, 1, 13), blocks.STONE.default_state)
    doc.run_ticks(3)
    assert doc.state_at(D(12, 1, 12)).is_(blocks.OAK_PLANKS)

    doc.use(D(14, 1, 16))  # 5. the observer sees the piston
    seen = []
    for _ in range(8):
        doc.run_ticks(1)
        seen.append(lit(doc, D(13, 1, 18)))
    assert any(seen)

    doc.use(D(15, 1, 22))  # 6. powered rails: 9 powered, the rest not
    doc.run_ticks(2)
    powered = [bool(doc.state_at(D(x, 1, 22)).get(POWERED)) for x in range(14, 2, -1)]
    assert powered == [True] * 9 + [False] * 3

    before = doc.state_at(D(11, 1, 27))  # 7. the junction switches
    doc.use(D(11, 1, 26))
    doc.run_ticks(1)
    assert doc.state_at(D(11, 1, 27)) != before


def count(doc: Document, pos: Pos) -> int:
    container = doc.level.get_block_entity(pos)
    return sum(stack[1] for stack in container.items if stack)  # type: ignore[union-attr]


def test_items(doc: Document) -> None:
    assert not lit(doc, E(12, 1, 4))  # 2. hopper chain: the last barrel starts empty
    doc.use(E(15, 1, 0))  # 1. one press moves one item into the chest
    doc.run_ticks(40)
    assert count(doc, E(12, 1, 0)) == 1
    assert lit(doc, E(12, 1, 2))

    assert count(doc, E(12, 1, 10)) > 0  # 3. the unlocked hopper passes items on
    doc.run_ticks(60)
    assert lit(doc, E(12, 1, 4))
    assert lit(doc, E(13, 1, 17)) and lit(doc, E(14, 1, 17))  # 4. both chest halves

    assert doc.state_at(E(14, 2, 20)).get(LEVEL) == 0  # 5. the composter was emptied
    assert count(doc, E(13, 1, 20)) == 1  # its bone meal is in the chest
    assert doc.level.get_block_entity(E(14, 2, 21)).output == 0  # type: ignore[union-attr]


def test_hopper_lock(doc: Document) -> None:
    doc.use(E(14, 1, 11))
    before = count(doc, E(12, 1, 10))
    doc.run_ticks(60)
    assert count(doc, E(12, 1, 10)) <= before + 1


def test_clocks(doc: Document) -> None:
    doc.use(F(13, 1, 0))  # 1. delays 1-4: 2, 4, 6, 8 ticks
    order = []
    for tick in range(1, 10):
        doc.run_ticks(1)
        for i, z in enumerate((0, 2, 4, 6)):
            if lit(doc, F(10, 1, z)) and i not in order:
                order.append(i)
        if tick == 2:
            assert order == [0]
    assert order == [0, 1, 2, 3]

    changes = 0  # 2. the observer clock keeps running
    previous = doc.state_at(F(14, 1, 9)).get(POWER)
    for _ in range(20):
        doc.run_ticks(1)
        now = doc.state_at(F(14, 1, 9)).get(POWER)
        changes += now != previous
        previous = now
    assert changes >= 4

    doc.use(F(13, 1, 12))  # 3. the loop: a pulse keeps running around
    corners = [F(12, 0, 12), F(10, 0, 12), F(10, 0, 14), F(12, 0, 14)]
    doc.run_ticks(60)
    patterns = set()
    for _ in range(40):
        doc.run_ticks(1)
        patterns.add(tuple(lit(doc, pos) for pos in corners))
    assert len(patterns) >= 3

    readings = set()  # 4. the hopper clock alternates
    for _ in range(40):
        doc.run_ticks(1)
        readings.add((lit(doc, F(13, 1, 16)), lit(doc, F(12, 1, 20))))
    assert len(readings) >= 2


def test_sequences(doc: Document) -> None:
    """The recorded history replays: the chaser, the 0-tick spit, the lever and the
    inspector change, the placed and removed block."""
    pulses = doc.pulses()
    assert [p.ticks for p in pulses if p.pos == G(13, 1, 4)] == [0, 10]
    assert set(doc.markers.values()) >= {"chaser", "0-tick", "lever on", "block removed"}
    assert len(doc.monitors) == 3
    doc.run_ticks(make_examples.CHASER_START + 1)
    assert lit(doc, G(14, 1, 0)) and not lit(doc, G(7, 1, 0))
    doc.run_ticks(make_examples.ZERO_TICK + 3 - doc.tick)
    assert doc.state_at(G(11, 1, 4)).is_(blocks.OAK_PLANKS)  # spat
    doc.run_ticks(make_examples.LONG_PULSE + 14 - doc.tick)
    assert doc.state_at(G(12, 1, 4)).is_(blocks.OAK_PLANKS)  # pulled back
    doc.run_ticks(make_examples.LEVER_OFF + 4 - doc.tick)
    assert lit(doc, G(12, 1, 8))  # delay 4 now: still on 4 ticks after the lever
    doc.run_ticks(make_examples.BLOCK_PLACED + 1 - doc.tick)
    assert lit(doc, G(9, 1, 8)) and not lit(doc, G(12, 1, 8))
    doc.run_ticks(make_examples.BLOCK_REMOVED + 6 - doc.tick)
    assert not lit(doc, G(9, 1, 8))


def test_annotations(saved: Document) -> None:
    assert len(saved.groups.groups) == 44
    assert set(saved.prefabs) == {"AND gate", "T flip-flop", "Repeater lock"}
    names = [g.name for g in saved.lines_of("power").groups]
    assert names == ["Chaser", "0-tick piston"]
    assert saved.extra["camera"]["yaw"] == 0.0
