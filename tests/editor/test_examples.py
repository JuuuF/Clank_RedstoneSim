"""The shipped example world must load and every circuit in it must work."""

from __future__ import annotations

from pathlib import Path

from redsim.editor.document import Document
from redsim.world import blocks
from redsim.world.properties import EXTENDED, LIT

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "showcase.redsim.json"
Z = -12  # tools/make_examples.Z_SHIFT


def at(x: int, y: int, z: int) -> tuple[int, int, int]:
    return (x, y, z + Z)


def lit(doc: Document, pos: tuple[int, int, int]) -> bool:
    return bool(doc.state_at(pos).get(LIT))


def test_example_world_matches_its_generator() -> None:
    from tools.make_examples import build

    saved = Document.open(EXAMPLE)
    fresh = build()
    assert saved.level.blocks == fresh.level.blocks
    assert set(saved.groups.groups) == set(fresh.groups.groups)


def test_every_example_circuit_works() -> None:
    doc = Document.open(EXAMPLE)

    doc.use(at(6, 1, 0))  # 1. lever → lamp at once
    assert lit(doc, at(5, 1, 0))

    assert lit(doc, at(3, 1, 3))  # 2. inverter output starts on
    doc.use(at(6, 1, 3))
    doc.run_ticks(6)
    assert not lit(doc, at(3, 1, 3))

    doc.use(at(7, 1, 6))  # 3. delay-4 repeater: 8 ticks
    doc.run_ticks(7)
    assert not lit(doc, at(1, 1, 6))
    doc.run_ticks(1)
    assert lit(doc, at(1, 1, 6))

    doc.use(at(7, 1, 9))  # 4. AND gate: one input is not enough
    doc.run_ticks(6)
    assert not lit(doc, at(4, 1, 10))
    doc.use(at(7, 1, 11))
    doc.run_ticks(6)
    assert lit(doc, at(4, 1, 10))

    assert lit(doc, at(3, 1, 14))  # 5. comparator: barrel source 14 - side 0
    doc.use(at(5, 1, 17))  # side input 14: output 0
    doc.run_ticks(8)
    assert not lit(doc, at(3, 1, 14))

    doc.use(at(7, 1, 20))  # 6. sticky piston pushes the planks
    doc.run_ticks(3)
    assert doc.state_at(at(6, 1, 20)).get(EXTENDED)
    assert doc.state_at(at(4, 1, 20)).is_(blocks.OAK_PLANKS)

    doc.use(at(7, 2, 23))  # 7. both door pistons extend together
    doc.run_ticks(3)
    assert doc.state_at(at(4, 1, 23)).is_(blocks.OAK_PLANKS)
    assert doc.state_at(at(4, 2, 23)).is_(blocks.OAK_PLANKS)
