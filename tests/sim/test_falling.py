"""Gravity blocks and falling block entities (``world/blocks/falling.py``,
``sim/entities.py``); EXP-054 and EXP-055 compare them with the real server."""

from __future__ import annotations

from pathlib import Path

import pytest

from redsim.io import save as save_io
from redsim.sim.engine import Action, ActionError, Engine
from redsim.world import blocks


def flat(size: int = 4) -> Engine:
    engine = Engine()
    for x in range(-size, size + 1):
        for z in range(-size, size + 1):
            engine.level.blocks[(x, 0, z)] = blocks.STONE.default_state
    return engine


def setblock(engine: Engine, pos: tuple[int, int, int], state: str) -> None:
    engine.apply(Action("setblock", pos, state))


def ticks(engine: Engine, count: int) -> None:
    for _ in range(count):
        engine.step()
        engine.finish_tick()


def test_sand_falls_two_ticks_after_placing_and_lands() -> None:
    engine = flat()
    setblock(engine, (0, 5, 0), "minecraft:sand")
    ticks(engine, 1)
    assert engine.level.get_block_state((0, 5, 0)).is_(blocks.get("sand"))
    assert not engine.level.entities
    ticks(engine, 1)  # the scheduled tick: an entity, ticked in the same tick
    assert engine.level.get_block_state((0, 5, 0)).is_air
    (entity,) = engine.level.entities.values()
    # The game's numbers (EXP-054): gravity 0.04 then drag 0.98F.
    assert entity.position == (0.5, 4.96, 0.5)
    assert entity.delta == (0.0, -0.03920000076293945, 0.0)
    ticks(engine, 20)
    assert not engine.level.entities
    assert engine.level.get_block_state((0, 1, 0)).is_(blocks.get("sand"))


def test_a_torch_holds_sand_and_a_carpet_breaks_it() -> None:
    engine = flat()
    setblock(engine, (0, 1, 0), "minecraft:redstone_torch")
    setblock(engine, (0, 2, 0), "minecraft:sand")
    setblock(engine, (2, 1, 0), "minecraft:white_carpet")
    setblock(engine, (2, 4, 0), "minecraft:red_sand")
    ticks(engine, 20)
    assert engine.level.get_block_state((0, 2, 0)).is_(blocks.get("sand"))
    assert engine.level.get_block_state((2, 1, 0)).is_(blocks.get("white_carpet"))
    assert all(engine.level.get_block_state((2, y, 0)).is_air for y in (2, 3, 4))
    assert not engine.level.entities


def test_the_dragon_egg_waits_five_ticks() -> None:
    engine = flat()
    setblock(engine, (0, 3, 0), "minecraft:dragon_egg")
    ticks(engine, 4)
    assert not engine.level.entities
    ticks(engine, 1)
    assert len(engine.level.entities) == 1


def test_concrete_powder_hardens_next_to_water() -> None:
    engine = flat()
    setblock(engine, (0, 1, 0), "minecraft:white_concrete_powder")
    assert engine.level.get_block_state((0, 1, 0)).is_(blocks.get("white_concrete_powder"))
    setblock(engine, (1, 1, 0), "minecraft:water")  # a foreign block, but water
    assert engine.level.get_block_state((0, 1, 0)).is_(blocks.get("white_concrete"))
    # /setblock applies the shape update at once (updateFromNeighbourShapes); above the
    # concrete there is no water next to it.
    setblock(engine, (0, 2, 0), "minecraft:white_concrete_powder")
    assert engine.level.get_block_state((0, 2, 0)).is_(blocks.get("white_concrete_powder"))


def test_snapshots_and_saves_keep_falling_blocks(tmp_path: Path) -> None:
    engine = flat()
    setblock(engine, (0, 9, 0), "minecraft:gravel")
    ticks(engine, 6)
    snapshot = engine.snapshot()
    save_io.save(tmp_path / "w.redsim.json", engine)
    ticks(engine, 4)
    expected = [(e.position, e.delta) for e in engine.level.entities.values()]
    engine.restore(snapshot)
    ticks(engine, 4)
    assert [(e.position, e.delta) for e in engine.level.entities.values()] == expected
    loaded, _ = save_io.load(tmp_path / "w.redsim.json")
    ticks(loaded, 4)
    assert [(e.position, e.delta) for e in loaded.level.entities.values()] == expected


def test_a_falling_block_is_in_the_way_of_placing() -> None:
    engine = flat()
    setblock(engine, (0, 6, 0), "minecraft:sand")
    ticks(engine, 3)
    (entity,) = engine.level.entities.values()
    cell = entity.block_position
    with pytest.raises(ActionError):
        engine.apply(Action("place", cell, "minecraft:stone"))
    engine.apply(Action("setblock", cell, "minecraft:stone"))  # commands do not check


def test_editor_history_replays_falls() -> None:
    from redsim.editor.document import Document

    doc = Document.new_flat()
    doc.run_ticks(2)
    doc.setblock((0, 8, 0), blocks.get("sand").default_state)
    doc.run_ticks(30)
    assert doc.state_at((0, 1, 0)).is_(blocks.get("sand"))
    assert doc.seek_tick(10) and len(doc.level.entities) == 1
    assert doc.seek_tick(32) and doc.state_at((0, 1, 0)).is_(blocks.get("sand"))


def test_using_a_dragon_egg_is_refused() -> None:
    """Its teleport is random in the game; the simulator says so instead of guessing."""
    engine = flat()
    setblock(engine, (0, 1, 0), "minecraft:dragon_egg")
    with pytest.raises(ActionError, match="random"):
        engine.apply(Action("use", (0, 1, 0)))
