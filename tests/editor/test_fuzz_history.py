"""Randomized checks of the editor's history: whatever is built, played, edited at later
ticks and pulsed, these must hold:

* replay is deterministic: seeking back and forth gives the states seen while running;
* saving and opening gives the same history (every tick);
* undoing every step returns to the start, redoing them returns to the end.
"""

from __future__ import annotations

import contextlib
import random
from pathlib import Path

import pytest

from redsim.editor.clipboard import Region
from redsim.editor.document import Document, EditError
from redsim.world import blocks

P = blocks.parse_state
PALETTE = [
    "stone",
    "redstone_block",
    "redstone_wire",
    "redstone_lamp",
    "repeater[facing=east,delay=2]",
    "comparator[facing=west]",
    "redstone_torch",
    "sticky_piston[facing=east]",
    "piston[facing=up]",
    "observer[facing=north]",
    "lever[face=floor,facing=east]",
    "slime_block",
    "glass",
]


def random_document(seed: int) -> tuple[Document, dict[int, dict[tuple[int, int, int], str]]]:
    """A document with random edits at random ticks; the states seen at each tick."""
    rng = random.Random(seed)
    doc = Document.new_flat()

    def cell() -> tuple[int, int, int]:
        return (rng.randrange(-4, 5), rng.randrange(1, 4), rng.randrange(-4, 5))

    with doc.batch():  # the build at tick 0
        for _ in range(40):
            pos = cell()
            if doc.state_at(pos).is_air:
                with contextlib.suppress(EditError):
                    doc.setblock(pos, P(rng.choice(PALETTE)))
    seen: dict[int, dict[tuple[int, int, int], str]] = {}
    for _ in range(12):
        doc.run_ticks(rng.randrange(1, 4))
        action = rng.random()
        try:
            if action < 0.3:
                pos = cell()
                doc.setblock(pos, P(rng.choice(PALETTE)))
            elif action < 0.5:
                levers = [p for p, s in doc.level.blocks.items() if s.is_(blocks.LEVER)]
                if levers:
                    doc.use(rng.choice(levers))
            elif action < 0.7:
                doc.add_pulse(cell(), doc.tick, rng.randrange(1, 16), rng.choice([0, 1, 2, 5]))
            elif action < 0.85:
                low = cell()
                region = Region(low, (low[0] + 1, low[1], low[2] + 1))
                doc.clone_region(region, (rng.choice([-2, 2]), 0, 0), "move")
            else:
                doc.break_block(cell())
        except EditError:
            pass
        seen[doc.tick] = {p: repr(s) for p, s in doc.level.blocks.items()}
    doc.run_ticks(4)
    seen[doc.tick] = {p: repr(s) for p, s in doc.level.blocks.items()}
    return doc, seen


def blocks_of(doc: Document) -> dict[tuple[int, int, int], str]:
    return {p: repr(s) for p, s in doc.level.blocks.items()}


@pytest.mark.parametrize("seed", range(6))
def test_replay_is_deterministic(seed: int) -> None:
    doc, seen = random_document(seed)
    ticks = sorted(seen)
    for tick in [*reversed(ticks), *ticks]:
        assert doc.seek_tick(tick)
        assert blocks_of(doc) == seen[tick], f"tick {tick}"


@pytest.mark.parametrize("seed", range(6))
def test_saving_keeps_the_whole_history(seed: int, tmp_path: Path) -> None:
    doc, seen = random_document(seed)
    doc.save(tmp_path / "fuzz.redsim.json")
    loaded = Document.open(tmp_path / "fuzz.redsim.json")
    assert [(p.tick, p.pos, p.ticks) for p in loaded.pulses()] == [
        (p.tick, p.pos, p.ticks) for p in doc.pulses()
    ]
    for tick in sorted(seen):
        assert loaded.seek_tick(tick)
        assert blocks_of(loaded) == seen[tick], f"tick {tick}"


@pytest.mark.parametrize("seed", range(4))
def test_undo_all_and_redo_all(seed: int) -> None:
    doc, seen = random_document(seed)
    end = blocks_of(doc)
    start = Document.new_flat()
    steps = 0
    while doc.undo():
        steps += 1
    assert steps > 0
    doc.seek_tick(0)
    assert blocks_of(doc) == {p: repr(s) for p, s in start.level.blocks.items()}
    while doc.redo():
        pass
    doc.seek_tick(max(seen))
    assert blocks_of(doc) == end
