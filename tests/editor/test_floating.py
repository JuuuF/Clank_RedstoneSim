"""Pending selection changes (``editor/floating.py``): any sequence of moves, turns and
flips is placed by one ``transform_regions`` call, exactly where the preview shows it."""

from __future__ import annotations

import itertools

import pytest

from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.editor.floating import IDENTITY, Floating, decompose
from redsim.world import blocks

P = blocks.parse_state
A = Region((0, 1, 0), (2, 2, 1))  # 3 × 2 × 2: odd and even sides
B = Region((5, 1, 0), (5, 1, 0))


def document() -> Document:
    doc = Document.new_flat()
    with doc.batch():
        doc.setblock((0, 1, 0), P("redstone_block"))
        doc.setblock((1, 1, 0), P("repeater[facing=east]"))
        doc.setblock((2, 1, 1), P("observer[facing=north]"))
        doc.setblock((0, 2, 1), P("lever[face=floor,facing=west]"))
        doc.setblock((5, 1, 0), P("glass"))
    return doc


def changes() -> list[list[tuple[str, object]]]:
    steps = [
        ("turn", 1),
        ("turn", 3),
        ("turn", 2),
        ("flip", "x"),
        ("flip", "z"),
        ("move", (2, 1, -3)),
    ]
    return [list(seq) for seq in itertools.product(steps, repeat=3)]


def apply(floating: Floating, steps: list[tuple[str, object]]) -> Floating:
    for kind, value in steps:
        if kind == "turn":
            floating = floating.turned(value)  # type: ignore[arg-type]
        elif kind == "flip":
            floating = floating.flipped(value)  # type: ignore[arg-type]
        else:
            floating = floating.moved(value)  # type: ignore[arg-type]
    return floating


def test_every_turn_and_mirror_decomposes() -> None:
    seen = set()
    floating = Floating((A,))
    for steps in changes():
        linear = apply(floating, steps).linear
        turns, mirrored = decompose(linear)
        seen.add((turns, mirrored))
    assert len(seen) == 8
    assert decompose(IDENTITY) == (0, False)


@pytest.mark.parametrize("steps", changes()[::7])
def test_placing_matches_the_preview(steps: list[tuple[str, object]]) -> None:
    doc = document()
    floating = apply(Floating((A, B)), steps)
    expected = {floating.map(p): s for p, s in _shifted(floating, doc).items()}
    turns, mirror, pivot, offset = floating.action()
    if not floating.changed:
        return
    boxes = doc.transform_regions([A, B], turns, mirror, pivot, offset)
    assert tuple(boxes) == floating.boxes()
    for pos, state in expected.items():
        assert doc.state_at(pos) == state, (steps, pos)


def _shifted(floating: Floating, doc: Document) -> dict[tuple[int, int, int], object]:
    """The preview at the place itself: preview positions plus the shift, keyed by source."""
    a, b, c, d = floating.linear
    out = {}
    preview = floating.preview(doc.level)
    for pos in floating.cells():
        x, y, z = pos
        key = (a * x + b * z, y, c * x + d * z)
        if key in preview:
            out[pos] = preview[key]
    return out


def test_four_turns_return_exactly() -> None:
    floating = Floating((A,))
    for _ in range(4):
        floating = floating.turned(1)
    assert not floating.changed
    floating = Floating((A,)).turned(1).turned(3)
    assert not floating.changed


def test_blocks_in_the_way_are_reported() -> None:
    doc = document()
    floating = Floating((A,)).moved((3, 0, 0))  # x 3..5: the glass at 5 is in the way
    assert floating.replaced(doc.level) == [(5, 1, 0)]
    assert Floating((A,)).moved((1, 0, 0)).replaced(doc.level) == []  # only its own blocks
    assert Floating((A,), copy=True).moved((1, 0, 0)).replaced(doc.level)  # a copy keeps them
