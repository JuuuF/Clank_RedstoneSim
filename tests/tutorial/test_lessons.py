"""Every lesson step can be done: a play-through of the whole tutorial, doing each step
with the editor's own operations and checking that its check notices (and not before)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.tutorial import world as tw
from redsim.tutorial.lessons import LESSONS, Progress, Snapshot
from redsim.world import blocks
from redsim.world.properties import HORIZONTAL_FACING


class Player:
    """The user: a document and the view state the window would report."""

    def __init__(self) -> None:
        self.doc: Document = tw.build()
        x, y, z = tw.station_center(0)
        self.view: dict[str, Any] = {"pivot": (x, y, z), "yaw": 0.0, "pitch": 40.0}

    def snap(self) -> Snapshot:
        doc = self.doc
        return replace(
            Snapshot(doc=doc),
            tick=doc.tick,
            undo=tuple(doc.undo_labels),
            redo=len(doc._redo),
            **self.view,
        )

    def at(self, station: int, pos: tuple[int, int, int]) -> tuple[int, int, int]:
        return tw.station(station, pos)


def _actions(p: Player) -> list[Callable[[], None] | None]:
    """What the user does for each step, in order (None: a step without a check)."""
    doc, v = p.doc, p.view
    s = p.at
    inverter = Region.from_corners(s(4, (6, 1, 2)), s(4, (9, 1, 2)))
    lamp_why = s(6, tw.WHY_LAMP)

    def run_and_pause() -> None:
        v["running"] = True
        progress.poll(p.snap())
        v["running"] = False

    def step_to_lamp() -> None:
        doc.use(s(2, tw.TIME_LEVER))
        doc.run_ticks(6)

    def place_dust() -> None:
        v["build_block"] = "minecraft:redstone_wire"
        cells = [s(3, (x, 1, 4)) for x in range(3, 9)]
        doc.place_many(cells, blocks.REDSTONE_WIRE, _floor())

    def turn() -> None:
        pos = s(3, (5, 1, 7))
        doc.place(pos, blocks.REPEATER, _floor())
        state = doc.state_at(pos)
        doc.setblock(pos, state.with_(HORIZONTAL_FACING, state.get(HORIZONTAL_FACING).clockwise()))

    def copy() -> None:
        doc.copy(inverter)
        doc.paste(s(4, (6, 1, 6)))

    def zero_tick() -> None:
        doc.add_pulse(s(5, tw.SEQ_PISTON), 20, 15, 0)

    def watch() -> None:
        doc.jump("start")
        doc.run_ticks(24)

    def used_while_running() -> None:
        doc.run_ticks(3)
        doc.use(s(5, tw.SEQ_LEVER))

    def sign() -> None:
        pos = s(7, (3, 1, 6))
        doc.setblock(pos, blocks.parse_state("oak_sign[rotation=8]"))
        doc.set_sign_text(pos, "front", ["hello"])

    return [
        # 1. Look around
        None,
        lambda: v.update(yaw=60.0),
        lambda: v.update(distance=30.0),
        lambda: v.update(pivot=(v["pivot"][0] + 4, v["pivot"][1], v["pivot"][2])),
        lambda: v.update(pivot=tuple(c + 0.5 for c in s(0, tw.LOOK_LAMP))),
        # 2. Use and inspect
        lambda: doc.use(s(1, tw.USE_LEVER)),
        lambda: v.update(inspected=s(1, tw.USE_LAMP)),
        lambda: v.update(popup=True),
        lambda: doc.use(s(1, tw.USE_REPEATER)),
        # 3. Time
        run_and_pause,
        step_to_lamp,
        lambda: doc.tick_back(),
        lambda: doc.jump("start"),
        lambda: doc.seek_tick(5),
        # 4. Build
        lambda: v.update(mode="build"),
        lambda: v.update(build_block="minecraft:redstone_wire"),
        place_dust,
        lambda: doc.use(s(3, tw.BUILD_LEVER)),
        lambda: doc.break_block(s(3, (5, 1, 4))),
        turn,
        lambda: doc.undo(),
        lambda: v.update(pivot=(v["pivot"][0], v["pivot"][1] + 1, v["pivot"][2])),
        # 5. Select
        lambda: v.update(mode="select"),
        lambda: v.update(regions=(inverter,)),
        copy,
        lambda: doc.transform_region(inverter, quarter_turns=1),
        lambda: v.update(regions=(inverter, Region.from_corners(s(4, (1, 1, 6)), s(4, (2, 1, 7))))),
        lambda: doc.fill(inverter, blocks.AIR.default_state),
        # 6. Sequences
        used_while_running,
        lambda: v.update(mode="animate"),
        lambda: doc.add_pulse(s(5, tw.SEQ_LAMPS[0]), 10),
        zero_tick,
        watch,
        # 7. See inside
        lambda: v.update(info=True),
        lambda: v.update(heat=True),
        lambda: v.update(xray=1),
        lambda: doc.set_source(s(6, tw.SEE_BARREL), "barrel", 5),
        lambda: v.update(tab="Diagnostics/Why?", inspected=lamp_why),
        lambda: doc.toggle_monitor(lamp_why),
        # 8. Organize
        lambda: doc.assign_section(s(7, tw.ORG_LEVER), "input"),
        lambda: doc.groups.add(_group(s(7, tw.ORG_LAMP))),
        lambda: doc.save_prefab("mine", Region.from_corners(s(7, (6, 1, 3)), s(7, (8, 1, 3)))),
        sign,
        lambda: doc.set_marker(3, "here"),
        # 9. Files
        None,
        None,
        None,
        None,
        None,
    ]


def _floor() -> Any:
    from redsim.editor.builder import ON_FLOOR

    return ON_FLOOR


def _group(pos: tuple[int, int, int]) -> Any:
    from redsim.editor.groups import Group

    return Group("mine", Region(pos, pos))


progress = Progress()


def test_every_step_can_be_done() -> None:
    player = Player()
    actions = _actions(player)
    steps = [(i, j) for i, lesson in enumerate(LESSONS) for j in range(len(lesson.steps))]
    assert len(actions) == len(steps)
    for (lesson, step), action in zip(steps, actions, strict=True):
        progress.go(lesson, step)
        current = progress.current
        progress.begin(player.snap())
        name = f"{LESSONS[lesson].title}: {current.title}"
        if current.check is None:
            assert action is None, name
            continue
        assert action is not None, name
        assert not progress.poll(player.snap()), f"{name} passed before it was done"
        action()
        assert progress.poll(player.snap()), f"{name} did not notice"


def test_progress_moves_through_lessons_and_saves() -> None:
    p = Progress()
    p.go(0, len(LESSONS[0].steps) - 1)
    assert p.advance() and (p.lesson, p.step) == (1, 0)
    p.back()
    assert (p.lesson, p.step) == (0, len(LESSONS[0].steps) - 1)
    assert Progress.from_json(p.to_json()).to_json() == p.to_json()
    assert Progress.from_json({"lesson": 99, "step": 99}).lesson == len(LESSONS) - 1
    p.go(len(LESSONS) - 1, len(LESSONS[-1].steps) - 1)
    assert p.is_last and not p.advance()


def test_the_tutorial_world_is_ready() -> None:
    doc = tw.build()
    assert tw.is_tutorial(doc) and doc.tick == 0 and not doc.dirty
    assert len(tw.STATIONS) == len(LESSONS)
    assert [lesson.station for lesson in LESSONS] == list(range(len(LESSONS)))
