"""Barrel and lectern as comparator sources (game comparisons: EXP-024, EXP-025)."""

from __future__ import annotations

from typing import Any

from redsim.io.save import engine_from_json, engine_to_json
from redsim.sim.engine import Action, Engine
from redsim.world import blocks
from redsim.world.blocks.container import BarrelBlockEntity, container_signal
from redsim.world.blocks.lectern import LecternBlockEntity, page_signal
from redsim.world.properties import EXTENDED, LIT, POWERED


def book(pages: int, page: int) -> dict[str, Any]:
    return {"Book": {"id": "minecraft:writable_book", "count": 1, "pages": pages}, "Page": page}


def world() -> Engine:
    engine = Engine()
    for x in range(-2, 6):
        for z in range(-2, 6):
            engine.level.blocks[(x, 0, z)] = blocks.STONE.default_state
    return engine


def output(engine: Engine, pos: tuple[int, int, int]) -> int:
    entity = engine.level.get_block_entity(pos)
    return int(entity.to_json()["OutputSignal"]) if entity else -1


def test_container_thresholds_match_the_known_table() -> None:
    def signal(total: int) -> int:
        stacks = [("minecraft:stone", 64)] * (total // 64)
        if total % 64:
            stacks.append(("minecraft:stone", total % 64))
        return container_signal(stacks, 27)

    first = [min(t for t in range(1, 1729) if signal(t) >= s) for s in range(1, 16)]
    assert first == [1, 124, 247, 371, 494, 618, 741, 864, 988, 1111, 1235, 1358, 1482, 1605, 1728]
    assert container_signal([("minecraft:ender_pearl", 16)] * 27, 27) == 15  # 16-stacks
    assert container_signal([], 27) == 0


def test_lectern_signal_formula() -> None:
    assert page_signal(0, 1, True) == 15  # one page: progress 1
    assert [page_signal(p, 15, True) for p in range(15)] == list(range(1, 16))
    assert page_signal(3, 10, True) == 5
    assert page_signal(0, 0, False) == 14  # no book: the block reads 0 before calling this


def test_item_change_updates_the_comparator_after_its_delay() -> None:
    engine = world()
    engine.apply(Action("setblock", (0, 1, 1), "minecraft:comparator[facing=north]"))
    items = {"Items": [{"Slot": 0, "id": "minecraft:stone", "count": 64}]}
    engine.apply(Action("setblock", (0, 1, 0), "minecraft:barrel", payload={"nbt": items}))
    engine.run_ticks(2)
    assert output(engine, (0, 1, 1)) == 1
    for slot in range(1, 27):  # fill it up: one setChanged per slot, like /item replace
        payload = {"slot": slot, "item": "minecraft:stone", "count": 99}  # limited to 64
        engine.apply(Action("container_item", (0, 1, 0), payload=payload))
    entity = engine.level.get_block_entity((0, 1, 0))
    assert isinstance(entity, BarrelBlockEntity) and entity.items[5] == ("minecraft:stone", 64)
    engine.run_ticks(1)
    assert output(engine, (0, 1, 1)) == 1
    engine.run_ticks(1)
    assert output(engine, (0, 1, 1)) == 15


def test_page_turn_pulses_the_block_below_for_two_ticks() -> None:
    engine = world()
    engine.apply(Action("setblock", (0, 1, 0), "minecraft:stone"))
    engine.apply(Action("setblock", (1, 1, 0), "minecraft:redstone_lamp"))
    nbt = {"nbt": book(5, 0)}
    engine.apply(Action("setblock", (0, 2, 0), "minecraft:lectern[has_book=true]", payload=nbt))
    engine.apply(Action("lectern_page", (0, 2, 0), payload={"page": 3}))
    lectern = engine.level.get_block_entity((0, 2, 0))
    assert isinstance(lectern, LecternBlockEntity) and lectern.page == 3
    assert engine.level.get_block_state((0, 2, 0)).get(POWERED) is True
    # The stone below is strongly powered, so the lamp beside it lights.
    assert engine.level.get_block_state((1, 1, 0)).get(LIT)
    engine.run_ticks(2)
    assert engine.level.get_block_state((0, 2, 0)).get(POWERED) is False


def test_containers_and_lecterns_cannot_be_pushed() -> None:
    engine = world()
    engine.apply(Action("setblock", (2, 1, 0), "minecraft:barrel"))
    engine.apply(Action("setblock", (1, 1, 0), "minecraft:piston[facing=east]"))
    engine.apply(Action("setblock", (0, 1, 0), "minecraft:redstone_block"))
    engine.run_ticks(4)
    assert engine.level.get_block_state((2, 1, 0)).is_(blocks.BARREL)
    assert engine.level.get_block_state((1, 1, 0)).get(EXTENDED) is False


def test_block_entity_data_survives_save_and_load() -> None:
    engine = world()
    items = {"Items": [{"Slot": 3, "id": "minecraft:ender_pearl", "count": 7}]}
    engine.apply(Action("setblock", (0, 1, 0), "minecraft:barrel", payload={"nbt": items}))
    lectern = {"nbt": book(9, 4)}
    engine.apply(Action("setblock", (2, 1, 0), "minecraft:lectern[has_book=true]", payload=lectern))
    again = engine_from_json(engine_to_json(engine))
    for pos in ((0, 1, 0), (2, 1, 0)):
        a = engine.level.get_block_entity(pos)
        b = again.level.get_block_entity(pos)
        assert a is not None and b is not None and a.to_json() == b.to_json()
