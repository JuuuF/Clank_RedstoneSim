"""The main window's tutorial (Help → Tutorial) and "go to a group": the tutorial world,
the card over the view, and the snapshots its lessons check."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import numpy as np

from redsim.editor.document import Document
from redsim.tutorial import world as tutorial_world
from redsim.tutorial.lessons import LESSONS, Snapshot, Step
from redsim.ui.tutorial_bar import TutorialBar
from redsim.ui.tutorial_card import TutorialCard

if TYPE_CHECKING:
    from redsim.ui.main_window import MainWindow

#: Height of the F3 debug screen's top-right column the card moves below.
DEBUG_COLUMN = 260


@dataclass
class TutorialSession:
    """The tutorial as a mode: the world that was open before (kept as it was, unsaved
    changes included) and the tutorial world (kept while you visit other worlds)."""

    before: Document
    world: Document


class TutorialActions:
    """Part of ``MainWindow`` (a mixin; its methods run on it)."""

    tutorial: TutorialCard | None = None
    tutorial_bar: TutorialBar | None = None
    tutorial_session: TutorialSession | None = None
    #: Saves and Select World screens so far (the Files lesson checks them).
    saves = 0
    world_screens = 0

    def start_tutorial(self) -> None:
        """Help → Tutorial: the tutorial mode. The open world is put aside (Exit tutorial
        brings it back as it was) and the card shows where the user left off."""
        view = cast("MainWindow", self)
        session = view.tutorial_session
        if session is None:
            view._store_camera()
            session = view.tutorial_session = TutorialSession(view.document, tutorial_world.build())
            view._set_document(session.world)
        card = view.tutorial
        if card is None:
            card = view.tutorial = TutorialCard(view.keymap, view.viewport)
            card.step_started.connect(view._tutorial_step)
            card.closed.connect(lambda: view.viewport.setFocus())
        bar = view.tutorial_bar
        if bar is None:
            bar = view.tutorial_bar = TutorialBar(view.viewport)
            bar.exit_requested.connect(view.exit_tutorial)
            bar.card_requested.connect(view.start_tutorial)
        bar.show()
        bar.raise_()
        card.show_step()
        card.show()
        card.raise_()
        view._place_tutorial()
        view._exit_tutorial_action.setEnabled(True)
        view.viewport.setFocus()
        view._message("Tutorial: follow the card at the top right; Exit tutorial at the top.")

    def exit_tutorial(self) -> bool:
        """Leave the tutorial mode: back to the world that was open before. False if the
        user kept a world opened during the tutorial (unsaved changes, Cancel)."""
        view = cast("MainWindow", self)
        session = view.tutorial_session
        if session is None:
            return True
        if view.document is not session.world and not view._confirm_discard():
            return False
        view.tutorial_session = None
        if view.tutorial is not None:
            view.tutorial.close_card()
        if view.tutorial_bar is not None:
            view.tutorial_bar.hide()
        view._exit_tutorial_action.setEnabled(False)
        view._set_document(session.before)
        name = session.before.path.name if session.before.path is not None else "your world"
        view._message(f"Left the tutorial: back to {name} (Help → Tutorial continues it).")
        return True

    def in_tutorial_world(self) -> bool:
        """The tutorial world is shown (its changes need no saving)."""
        view = cast("MainWindow", self)
        session = view.tutorial_session
        return session is not None and view.document is session.world

    def _place_tutorial(self) -> None:
        view = cast("MainWindow", self)
        if view.tutorial is not None:
            below = DEBUG_COLUMN if view.viewport.show_info else 0
            view.tutorial.place(view.viewport, below)
        bar = view.tutorial_bar
        if bar is not None and bar.isVisible():
            card = view.tutorial
            shown = card is not None and card.isVisible()
            lesson = f"lesson {card.progress.lesson + 1} of {len(LESSONS)}" if card else ""
            elsewhere = "" if view.in_tutorial_world() else " · another world is open"
            bar.set_state(lesson + elsewhere, shown)
            bar.place(view.viewport)

    def _tutorial_step(self, step: Step) -> None:
        """A step started: move the camera to its station, if it names one (back in the
        tutorial world, if another world was opened meanwhile)."""
        view = cast("MainWindow", self)
        session = view.tutorial_session
        away = session is not None and not view.in_tutorial_world()
        if step.focus is not None and session is not None and away and view._confirm_discard():
            view._set_document(session.world)
        if step.focus is not None and tutorial_world.is_tutorial(view.document):
            view.viewport.glide_to(pivot=np.array(step.focus, dtype=float), distance=18.0)
        view._place_tutorial()

    def tutorial_snapshot(self) -> Snapshot:
        view = cast("MainWindow", self)
        viewport, camera = view.viewport, view.viewport.camera
        tab = view.tabs.tabText(view.tabs.currentIndex())
        if view.tabs.currentWidget() is view.diagnostics:
            tab += "/" + view.diagnostics.tabText(view.diagnostics.currentIndex())
        regions = tuple(r for r in (viewport.region, *viewport.extra_regions) if r is not None)
        return Snapshot(
            doc=view.document,
            mode=viewport.mode,
            tick=view.document.tick,
            running=view.play_timer.isActive(),
            inspected=viewport.selection,
            regions=regions,
            pivot=(float(camera.pivot[0]), float(camera.pivot[1]), float(camera.pivot[2])),
            yaw=float(camera.yaw),
            pitch=float(camera.pitch),
            distance=float(camera.distance),
            pasting=viewport.paste_preview is not None,
            confirmed=viewport.region_confirmed,
            heat=viewport.show_heat,
            xray=viewport.xray,
            info=viewport.show_info,
            popup=view.block_popup.isVisible(),
            tab=tab,
            build_block=view.current_block.id if viewport.build_block is not None else None,
            undo=tuple(view.document.undo_labels),
            redo=len(view.document._redo),
            saves=view.saves,
            world_screens=view.world_screens,
        )

    def _poll_tutorial(self) -> None:
        view = cast("MainWindow", self)
        card = view.tutorial
        if card is not None and card.isVisible():
            card.poll(view.tutorial_snapshot())
        view._place_tutorial()

    def _go_to_group(self, name: str) -> None:
        """Circuit → Groups, double click: the camera goes to the group's box."""
        view = cast("MainWindow", self)
        group = view.document.groups.groups.get(name)
        if group is None:
            return
        low, high = np.array(group.region.low, float), np.array(group.region.high, float) + 1
        size = float(np.max(high - low))
        view.viewport.glide_to(pivot=(low + high) / 2, distance=max(10.0, size * 1.6))
        ports = [port.pos for port in group.ports]
        if ports:
            view.viewport.flash(ports[0])
        view._message(f"Group “{name}”.")
