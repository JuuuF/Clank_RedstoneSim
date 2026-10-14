"""The main window's file actions: new, open (the Select World screen), Minecraft worlds
(open, stream chunks around the camera, save into a copy), save and save as, the camera
stored in a file."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from redsim.editor.document import Document
from redsim.mcworld.importer import attach_world, open_world, stream_chunks
from redsim.mcworld.index import Build, scan_builds
from redsim.mcworld.writer import save_world_copy
from redsim.ui import pixel_icons, theme
from redsim.ui.camera import Camera
from redsim.ui.names import block_name
from redsim.ui.window_common import FILE_FILTER, STREAM_BUDGET_S, _plain_cube
from redsim.ui.world_builds import BuildsDialog
from redsim.ui.world_picker import (
    MINECRAFT,
    SIMULATION,
    WorldPicker,
    remember_world,
    save_thumbnail,
    thumbnail_path,
)

if TYPE_CHECKING:
    from redsim.ui.main_window import MainWindow

#: How long after opening a world without a thumbnail its view is captured for one (the
#: meshes and textures are ready by then).
THUMBNAIL_DELAY_MS = 1500
#: Blocks: going to a build farther than this jumps instead of gliding.
FAR_JUMP = 96.0


class FileActions:
    """Part of ``MainWindow`` (a mixin; its methods run on it)."""

    def _confirm_discard(self, closing: bool = False) -> bool:
        """Ask before unsaved changes would be lost; True means go ahead."""
        view = cast("MainWindow", self)
        if not view.document.dirty:
            return True
        box = QMessageBox(view)
        box.setIconPixmap(pixel_icons.pixel_pixmap("warning", theme.GOLD, 4, tight=True))
        box.setWindowTitle("Unsaved changes")
        box.setText("You still have unsaved changes. Do you want to save the changes?")
        discard = box.addButton(
            "Close without saving" if closing else "Discard changes",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel = box.addButton(QMessageBox.StandardButton.Cancel)
        save = box.addButton(
            "Save" if view.document.path is not None else "Save as…",
            QMessageBox.ButtonRole.AcceptRole,
        )
        box.setDefaultButton(save)
        box.setEscapeButton(cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is discard:
            return True
        if clicked is save:
            view._save()
            return not view.document.dirty  # a cancelled "Save as" keeps the window open
        return False

    def _apply_saved_camera(self) -> None:
        """Restore the camera stored in the file (``extra["camera"]``), else a default view."""
        view = cast("MainWindow", self)
        camera = view.document.extra.get("camera")
        view.viewport.camera = Camera.from_json(camera) if camera else Camera()
        view.viewport.update()

    def _store_camera(self) -> None:
        view = cast("MainWindow", self)
        view.document.extra["camera"] = view.viewport.camera.to_json()

    def _new(self) -> None:
        view = cast("MainWindow", self)
        if view._confirm_discard():
            view._set_document(Document.new_flat())

    def _open(self, tab: str = SIMULATION) -> None:
        """The "Select World" screen (Minecraft saves, simulation worlds, Browse…)."""
        view = cast("MainWindow", self)
        if not view._confirm_discard():
            return
        picker = WorldPicker(view, tab)
        if not picker.exec() or picker.chosen is None:
            return
        kind, path = picker.chosen
        if kind == MINECRAFT:
            view.open_minecraft_world(path)
        else:
            view.open_path(path)

    def _open_minecraft_world(self) -> None:
        """Import the area around the player of a Minecraft Java save (doc/world-import.md)."""
        view = cast("MainWindow", self)
        view._open(MINECRAFT)

    def open_minecraft_world(self, folder: Path, radius: int = 4) -> None:
        view = cast("MainWindow", self)
        if not (folder / "level.dat").exists():
            QMessageBox.critical(view, "Not a Minecraft world", f"{folder} has no level.dat.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            opened = open_world(folder, radius)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.critical(view, "Cannot open the world", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        view._set_document(opened.document)
        remember_world(folder, MINECRAFT)
        approx = [
            f"{block_name(i)} ×{n}" for i, n in opened.foreign.most_common() if not _plain_cube(i)
        ]
        note = f" Approximated (not simulated yet): {', '.join(approx)}." if approx else ""
        stream = opened.stream
        view._message(
            f"Opened {opened.info.name}: {len(stream.loaded)} chunks around the player, "
            f"{len(opened.document.level.blocks)} blocks ({stream.skipped()} buried terrain "
            f"blocks left out); more load around the camera.{note}"
        )

    def _stream_world(self) -> None:
        """Load the next chunks of an opened world around the camera (a little per call,
        nearest first), while the simulation is not mid-tick."""
        view = cast("MainWindow", self)
        document = view.document
        if document.world is None or not document.can_edit:
            return
        x, _, z = (float(v) for v in view.viewport.camera.pivot)
        center = (math.floor(x) >> 4, math.floor(z) >> 4)
        radius = view.viewport.preferences.world_view_distance
        if stream_chunks(document, center, radius, STREAM_BUDGET_S):
            view.viewport.update()

    def _show_builds(self) -> None:
        """File → Builds in this world…: the save's builds (scanned once per opened
        world); choosing one takes the camera there."""
        view = cast("MainWindow", self)
        stream = view.document.world
        if stream is None:
            view._message(
                "Builds are listed for a world opened with File → Open Minecraft world….",
                error=True,
            )
            return
        if stream.builds is None:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                stream.builds = scan_builds(stream.info.regions)
            except (OSError, ValueError, KeyError) as exc:
                QMessageBox.critical(view, "Cannot read the world", str(exc))
                return
            finally:
                QApplication.restoreOverrideCursor()
        dialog = BuildsDialog(stream.builds, stream.info.name, view)
        if dialog.exec() and dialog.chosen is not None:
            view._go_to_build(dialog.chosen)

    def _go_to_build(self, build: Build) -> None:
        """The camera above a build, far enough to see it; the chunks around stream in.
        Far away the camera jumps (gliding there would load every chunk on the way)."""
        view = cast("MainWindow", self)
        viewport = view.viewport
        x, y, z = build.center
        target = np.array([x, y, z])
        distance = min(120.0, max(10.0, 1.3 * max(build.size)))
        if float(np.linalg.norm(target - np.asarray(viewport.camera.pivot))) > FAR_JUMP:
            viewport.camera.pivot = target
            viewport.camera.distance = distance
        viewport.glide_to(target, distance)
        view._message(f"Going to the build at {round(x)} {round(y)} {round(z)}.")

    def _save_minecraft_world(self) -> None:
        """Write the document into a copy of the Minecraft save it was opened from."""
        view = cast("MainWindow", self)
        stream = view.document.world
        if stream is None:
            view._message(
                "Only a world opened with File → Open Minecraft world… can be saved back.",
                error=True,
            )
            return
        source = stream.info.path
        name, ok = QInputDialog.getText(
            view,
            "Save as Minecraft world",
            f"Name of the copy (a new folder next to '{source.name}'; the original stays "
            "untouched):",
            text=f"{source.name} (redsim)",
        )
        if not ok or not name.strip():
            return
        view._finish_tick()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            report = save_world_copy(view.document, source.parent / name.strip())
        except (OSError, ValueError) as exc:
            QMessageBox.critical(view, "Cannot save the world", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        note = (
            f" {report.outside} changed blocks outside the loaded chunks were left out."
            if (report.outside)
            else ""
        )
        view._message(
            f"Saved the world '{report.target.name}': {report.blocks} changed blocks in "
            f"{report.chunks} chunks.{note}"
        )

    def open_path(self, path: Path) -> None:
        view = cast("MainWindow", self)
        try:
            document = Document.open(path)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.critical(view, "Cannot open file", str(exc))
            return
        stream = attach_world(document)
        view._set_document(document)
        remember_world(path, SIMULATION)
        if stream is not None:
            view._message(
                f"Connected to the Minecraft world {stream.info.name} again: its chunks "
                "load around the camera as before."
            )
        if not thumbnail_path(path).exists():  # worlds saved before thumbnails existed
            QTimer.singleShot(THUMBNAIL_DELAY_MS, lambda: view._thumbnail_if_missing(path))

    def _thumbnail_if_missing(self, path: Path) -> None:
        """A thumbnail of the opened world's first frames, for the Select World screen."""
        view = cast("MainWindow", self)
        if view.document.path == path and not thumbnail_path(path).exists():
            save_thumbnail(path, view.viewport.grabFramebuffer())

    def _saved(self, path: Path | None) -> None:
        """After saving: the world goes to the recent list with a thumbnail of the view."""
        view = cast("MainWindow", self)
        if path is None or view.document.dirty:
            return
        remember_world(path, SIMULATION)
        save_thumbnail(path, view.viewport.grabFramebuffer())

    def _save(self) -> None:
        view = cast("MainWindow", self)
        if view.document.path is None:
            view._save_as()
            return
        view._store_camera()
        view._edit(view.document.save)
        view._saved(view.document.path)
        view._message(f"Saved {view.document.path}")

    def _save_as(self) -> None:
        view = cast("MainWindow", self)
        path, _ = QFileDialog.getSaveFileName(
            view, "Save world", "circuit.redsim.json", FILE_FILTER
        )
        if path:
            view._store_camera()
            view._edit(view.document.save, Path(path))
            view._saved(Path(path))
            view._message(f"Saved {path}")
