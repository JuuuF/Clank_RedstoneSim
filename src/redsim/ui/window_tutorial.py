"""The main window's tutorial (Help → Tutorial) and "go to a group": the tutorial world,
the card over the view, and the snapshots its lessons check."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import numpy as np

from redsim.tutorial import world as tutorial_world
from redsim.tutorial.lessons import Snapshot, Step
from redsim.ui.tutorial_card import TutorialCard

if TYPE_CHECKING:
    from redsim.ui.main_window import MainWindow

#: Height of the F3 debug screen's top-right column the card moves below.
DEBUG_COLUMN = 260


class TutorialActions:
    """Part of ``MainWindow`` (a mixin; its methods run on it)."""

    tutorial: TutorialCard | None = None

    def start_tutorial(self) -> None:
        """Help → Tutorial: open the tutorial world (after asking about unsaved changes)
        and show the card where the user left off."""
        view = cast("MainWindow", self)
        if not tutorial_world.is_tutorial(view.document):
            if not view._confirm_discard():
                return
            view._set_document(tutorial_world.build())
        card = view.tutorial
        if card is None:
            card = view.tutorial = TutorialCard(view.keymap, view.viewport)
            card.step_started.connect(view._tutorial_step)
            card.closed.connect(lambda: view.viewport.setFocus())
        card.show_step()
        card.show()
        card.raise_()
        view._place_tutorial()
        view.viewport.setFocus()
        view._message("Tutorial: follow the card at the top right.")

    def _place_tutorial(self) -> None:
        view = cast("MainWindow", self)
        if view.tutorial is not None:
            below = DEBUG_COLUMN if view.viewport.show_info else 0
            view.tutorial.place(view.viewport, below)

    def _tutorial_step(self, step: Step) -> None:
        """A step started: move the camera to its station, if it names one."""
        view = cast("MainWindow", self)
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
            heat=viewport.show_heat,
            xray=viewport.xray,
            info=viewport.show_info,
            popup=view.block_popup.isVisible(),
            tab=tab,
            build_block=view.current_block.id if viewport.build_block is not None else None,
            undo=tuple(view.document.undo_labels),
            redo=len(view.document._redo),
        )

    def _poll_tutorial(self) -> None:
        view = cast("MainWindow", self)
        card = view.tutorial
        if card is not None and card.isVisible():
            view._place_tutorial()
            card.poll(view.tutorial_snapshot())

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
