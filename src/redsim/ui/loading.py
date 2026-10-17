"""Opening a world in the background, behind a loading screen (owner, 2026-10-17).

Reading a world, re-running its recorded edits, building the view's chunk meshes and the
prefab previews all run in a loading thread; the window shows a Minecraft-style loading
screen with how far it is and stays responsive (Esc cancels). Nothing the thread makes is
seen by the window before it is finished: then the document, its meshes (and atlas) and
the previews are handed over at once (``MainWindow._finish_open``).

The thread only touches Qt through ``QImage`` (the atlas, the previews), which Qt allows
outside the GUI thread; the GPU upload of the meshes happens on the next frame.
"""

from __future__ import annotations

import threading
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QObject, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QApplication, QWidget

from redsim.editor.document import Document
from redsim.sim.level import Level
from redsim.ui import game_gui, theme
from redsim.ui.atlas import Atlas
from redsim.ui.geometry import ChunkedMesh, Mesher
from redsim.ui.view_common import foreign_atlas

#: How often the window looks at the loading thread's progress.
POLL_MS = 33

#: What each stage is called on the screen, and what it counts.
STAGES: dict[str, tuple[str, str]] = {
    "read": ("Reading the file", ""),
    "world": ("Building the world", "blocks"),
    "history": ("Re-running the recorded edits", "ticks"),
    "chunks": ("Loading chunks", "chunks"),
    "meshes": ("Building the view", "chunks"),
    "previews": ("Drawing the prefab previews", "prefabs"),
}
#: How much of the bar each stage takes (roughly its share of the time).
WEIGHTS: dict[str, float] = {
    "read": 1.0,
    "world": 1.5,
    "history": 4.0,
    "chunks": 4.0,
    "meshes": 5.0,
    "previews": 1.0,
}


class LoadCancelled(Exception):
    """The loading was cancelled (Esc on the loading screen)."""


class LoadProgress:
    """How far the loading thread is: written by it (``__call__`` is a ``core.progress``
    report), read by the window's timer. A report after ``cancel()`` raises."""

    def __init__(self, stages: Sequence[str]) -> None:
        self.stages = list(stages)
        self.stage = self.stages[0] if self.stages else ""
        self.done = 0
        self.total = 0
        self.cancelled = False
        self._best = 0.0  # the bar never moves back (a second engine re-reports "world")

    def __call__(self, stage: str, done: int, total: int) -> None:
        if self.cancelled:
            raise LoadCancelled
        if stage not in self.stages:  # e.g. a world with recorded edits: before the view
            later = [s for s in ("meshes", "previews") if s in self.stages]
            at = self.stages.index(later[0]) if later else len(self.stages)
            self.stages.insert(at, stage)
        self.stage, self.done, self.total = stage, done, total

    def cancel(self) -> None:
        self.cancelled = True

    def fraction(self) -> float:
        """The whole loading, 0..1."""
        weights = [WEIGHTS.get(stage, 1.0) for stage in self.stages]
        if not weights or self.stage not in self.stages:
            return self._best
        at = self.stages.index(self.stage)
        part = self.done / self.total if self.total > 0 else 0.0
        value = (sum(weights[:at]) + weights[at] * min(1.0, part)) / sum(weights)
        self._best = max(self._best, value)
        return self._best

    def text(self) -> str:
        if self.cancelled:
            return "Cancelling…"
        label, unit = STAGES.get(self.stage, (self.stage, ""))
        if unit and self.total > 0:
            return f"{label}: {self.done:,} of {self.total:,} {unit}"
        return label


@dataclass
class PreparedView:
    """What the viewport needs to show a loaded world at once: its chunk meshes, made
    with ``atlas`` (a new one if the world has blocks the old atlas lacks textures for)."""

    atlas: Atlas | None
    mesh: ChunkedMesh


@dataclass
class LoadedWorld:
    document: Document
    prepared: PreparedView | None
    extra: dict[str, Any] = field(default_factory=dict)  # e.g. a Minecraft world's info


def prepare_view(
    level: Level,
    mesher: Mesher,
    progress: Callable[[str, int, int], None] | None = None,
) -> PreparedView:
    """The chunk meshes of ``level`` (in the loading thread), made by ``mesher`` (a copy
    of the view's, ``Mesher.copy``) unless the world needs a new atlas."""
    atlas = foreign_atlas(level, mesher.assets, mesher.atlas)
    if atlas is not None:  # blocks of a Minecraft world: their textures, new templates
        mesher = Mesher(mesher.assets, atlas)
    mesh = ChunkedMesh(mesher)
    mesh.update(level, progress)
    return PreparedView(mesher.atlas, mesh)


def draw_previews(document: Document, size: int, progress: LoadProgress) -> None:
    """Draw the document's prefab previews into the preview cache (``icons.prefab_image``)."""
    from redsim.ui.icons import prefab_image

    prefabs = list(document.prefabs.values())
    for done, prefab in enumerate(prefabs):
        progress("previews", done, len(prefabs))
        prefab_image(prefab, size)
    progress("previews", len(prefabs), len(prefabs))


def world_job(
    path: Path, mesher: Mesher, preview_size: int
) -> Callable[[LoadProgress], LoadedWorld]:
    """Open a ``.redsim.json`` world: the document, its view and its previews."""

    def job(progress: LoadProgress) -> LoadedWorld:
        document = Document.open(path, progress)
        prepared = prepare_view(document.level, mesher, progress)
        draw_previews(document, preview_size, progress)
        return LoadedWorld(document, prepared)

    return job


def minecraft_job(
    folder: Path, radius: int, mesher: Mesher
) -> Callable[[LoadProgress], LoadedWorld]:
    """Open the area around the player of a Minecraft save, and its view."""

    def job(progress: LoadProgress) -> LoadedWorld:
        from redsim.mcworld.importer import open_world

        opened = open_world(folder, radius, progress=progress)
        prepared = prepare_view(opened.document.level, mesher, progress)
        return LoadedWorld(opened.document, prepared, {"opened": opened})

    return job


class LoadingRun(QObject):
    """One loading: the thread that runs ``job``, the screen over ``window`` and the timer
    that shows the progress. Calls ``finished(result)`` when done, ``failed(error)`` if it
    raised, ``failed(None)`` if it was cancelled (all on the GUI thread)."""

    def __init__(
        self,
        window: QWidget,
        title: str,
        subtitle: str,
        stages: Sequence[str],
        job: Callable[[LoadProgress], Any],
        finished: Callable[[Any], None],
        failed: Callable[[BaseException | None], None],
    ) -> None:
        super().__init__(window)
        self.progress = LoadProgress(stages)
        self.result: Any = None
        self.error: BaseException | None = None
        self.done = False
        self._finished, self._failed = finished, failed
        self.screen = LoadingScreen(window, title, subtitle)
        self.screen.cancel_requested.connect(self.cancel)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(POLL_MS)
        self._thread = threading.Thread(target=self._run, args=(job,), daemon=True)
        self._thread.name = "redsim-load"
        self._thread.start()

    def _run(self, job: Callable[[LoadProgress], Any]) -> None:
        try:
            self.result = job(self.progress)
        except BaseException as exc:  # noqa: BLE001 - handed to the GUI thread
            if not isinstance(exc, LoadCancelled):
                traceback.print_exc()
            self.error = exc
        finally:
            self.done = True

    def cancel(self) -> None:
        self.progress.cancel()
        self.screen.show_progress(self.progress.text(), self.progress.fraction())

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    def _poll(self) -> None:
        self.screen.show_progress(self.progress.text(), self.progress.fraction())
        if not self.done:
            return
        self._timer.stop()
        self.screen.close_screen()
        if isinstance(self.error, LoadCancelled):
            self._failed(None)
        elif self.error is not None:
            self._failed(self.error)
        else:
            self._finished(self.result)
        self.deleteLater()

    def wait(self, timeout: float = 120.0) -> None:
        """Process events until the loading is over (tests, scripted use)."""
        self._thread.join(timeout)
        if self.running:
            self._poll()


#: Events the window does not get while it loads (Esc cancels).
_INPUT = {
    QEvent.Type.MouseButtonPress,
    QEvent.Type.MouseButtonRelease,
    QEvent.Type.MouseButtonDblClick,
    QEvent.Type.MouseMove,
    QEvent.Type.Wheel,
    QEvent.Type.KeyPress,
    QEvent.Type.KeyRelease,
    QEvent.Type.ShortcutOverride,
    QEvent.Type.Shortcut,
    QEvent.Type.ContextMenu,
    QEvent.Type.DragEnter,
    QEvent.Type.DragMove,
    QEvent.Type.Drop,
}
#: The progress bar: width in GUI pixels (scaled like the game's GUI) and height.
BAR_WIDTH, BAR_HEIGHT = 200, 9
DIRT_SHADE = 0.25


class LoadingScreen(QWidget):
    """The game's loading screen over the whole window: dirt, the title, what it is doing
    and a progress bar. It takes all input while shown; Esc asks to cancel."""

    cancel_requested = Signal()

    def __init__(self, window: QWidget, title: str, subtitle: str) -> None:
        super().__init__(window)
        self.title, self.subtitle = title, subtitle
        self.text = ""
        self.fraction = 0.0
        self._dirt = game_gui.dirt_brush(DIRT_SHADE)
        # It paints all of itself: the window under it is not painted with every update.
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setGeometry(window.rect())
        window.installEventFilter(self)  # follow the window's size
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self.show()
        self.raise_()

    def show_progress(self, text: str, fraction: float) -> None:
        if text != self.text or abs(fraction - self.fraction) > 1e-4:
            self.text, self.fraction = text, fraction
            self.update()

    def close_screen(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        parent = self.parentWidget()
        if parent is not None:
            parent.removeEventFilter(self)
        self.hide()
        self.deleteLater()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        kind = event.type()
        parent = self.parentWidget()
        if kind == QEvent.Type.Resize and parent is not None and watched is parent:
            self.setGeometry(parent.rect())
            return False
        if kind in _INPUT:
            if (
                kind == QEvent.Type.KeyPress
                and isinstance(event, QKeyEvent)
                and event.key() == Qt.Key.Key_Escape
            ):
                self.cancel_requested.emit()
            return True
        return False

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.WINDOW))
        if self._dirt is not None:
            painter.fillRect(self.rect(), self._dirt)
        scale = game_gui.SCALE
        width, height = self.width(), self.height()
        line = theme.line_height(scale)
        top = height // 2 - 3 * line
        for text, color, y in (
            (self.title, "#ffffff", top),
            (self.subtitle, theme.TEXT_DIM, top + line + scale * 2),
            (self.text, "#ffffff", top + 3 * line),
        ):
            if text:
                x = (width - theme.text_width(text, scale)) // 2
                theme.draw_text(painter, x, y, text, color, scale)
        bar = QRect(0, 0, BAR_WIDTH * scale, BAR_HEIGHT * scale)
        bar.moveCenter(self.rect().center())
        bar.moveTop(top + 4 * line + scale * 4)
        painter.fillRect(bar, QColor("#ffffff"))
        inner = bar.adjusted(scale, scale, -scale, -scale)
        painter.fillRect(inner, QColor(0, 0, 0))
        filled = QRect(
            inner.left(), inner.top(), round(inner.width() * self.fraction), inner.height()
        )
        painter.fillRect(filled.adjusted(scale, scale, -scale, -scale), QColor("#ffffff"))
        hint = "Esc: cancel"
        x = (width - theme.text_width(hint, scale)) // 2
        theme.draw_text(painter, x, bar.bottom() + line, hint, theme.TEXT_DIM, scale)
        painter.end()


__all__ = [
    "LoadCancelled",
    "LoadProgress",
    "LoadedWorld",
    "LoadingRun",
    "LoadingScreen",
    "PreparedView",
    "minecraft_job",
    "prepare_view",
    "world_job",
]
