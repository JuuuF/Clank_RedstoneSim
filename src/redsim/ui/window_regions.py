"""The main window's selection actions: copy, paste, move and copy by dragging, rotate,
flip, lock, stack, delete; prefabs and groups with ports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from redsim.core.pos import Pos
from redsim.editor.clipboard import Prefab, Region, bounding_box
from redsim.editor.document import Document, EditError
from redsim.editor.groups import Group, Port
from redsim.ui.names import block_name
from redsim.ui.viewport import BUILD
from redsim.world import blocks
from redsim.world.rotation import default_pivot2

if TYPE_CHECKING:
    from redsim.ui.main_window import MainWindow


class RegionActions:
    """Part of ``MainWindow`` (a mixin; its methods run on it)."""

    def _region_changed(self, region: Region | None) -> None:
        view = cast("MainWindow", self)
        if region is not None:
            size = region.size
            view._message(f"Selected {size[0]}×{size[1]}×{size[2]} blocks.")

    def _region(self) -> Region | None:
        view = cast("MainWindow", self)
        if view.viewport.region is None:
            view._message(
                "No selection: press V (select mode), then click or drag over blocks.", error=True
            )
        return view.viewport.region

    def _copy(self) -> None:
        view = cast("MainWindow", self)
        region = view._region()
        if region is None:
            return
        regions = view.viewport.all_regions()
        prefab = view.document.copy(regions if len(regions) > 1 else region)
        boxes = f" from {len(regions)} boxes" if len(regions) > 1 else ""
        view._message(
            f"Copied {prefab.non_air_count} blocks{boxes} (with air: {len(prefab.blocks)})."
        )

    def _paste(self) -> None:
        """Ctrl+V: preview the clipboard at the cursor; a left click places it."""
        view = cast("MainWindow", self)
        if view.document.clipboard is None:
            view._message("The clipboard is empty.", error=True)
            return
        view.viewport.begin_paste(view.document.clipboard)
        view._message("Paste: left click places it · R rotates · right click or Esc cancels.")

    def _paste_at(self, origin: Pos) -> None:
        view = cast("MainWindow", self)
        view._edit(view.document.paste, origin)

    def _move_region(self, region: Region, by: Pos, copy: bool) -> None:
        """A dragged selection: ``/clone … replace move`` (or ``force`` for a copy); with
        several selections, all of them move (or are copied) together."""
        view = cast("MainWindow", self)
        view.document.notice = ""
        viewport = view.viewport
        regions = viewport.all_regions()
        verb = "Copied" if copy else "Moved"
        try:
            if len(regions) > 1:
                moved = view.document.transform_regions(regions, offset=by, copy=copy)
                viewport.extra_regions, viewport.region = moved[:-1], moved[-1]
                what = f"the {len(regions)} selections"
            else:
                viewport.region = view.document.clone_region(
                    region, by, "force" if copy else "move"
                )
                what = "the selection"
        except EditError as exc:
            view._message(str(exc), error=True)
        else:
            view._message(f"{verb} {what} by {by[0]}, {by[1]}, {by[2]}.")
        view._changed()

    def _rotate(self, quarter_turns: int) -> None:
        """R / Shift+R: the paste preview if one is shown, else the selection in place,
        else the clipboard."""
        view = cast("MainWindow", self)
        viewport, document = view.viewport, view.document
        direction = "clockwise" if quarter_turns == 1 else "counter-clockwise"
        if viewport.mode == BUILD and viewport.paste_preview is None:  # the block to place
            variant = viewport.vary_build(turns=quarter_turns)
            view._message(
                f"Block to place: {variant} (R / Shift+R turn, H mirrors, Shift+H flips)."
            )
        elif viewport.paste_preview is not None and document.clipboard is not None:
            document.rotate_clipboard(quarter_turns)
            viewport.begin_paste(document.clipboard)
            view._message(f"Paste rotated 90° {direction}.")
        elif viewport.region is not None:
            view._transform(quarter_turns=quarter_turns)
        elif document.clipboard is not None:
            document.rotate_clipboard(quarter_turns)
            view._message(f"Clipboard rotated 90° {direction}.")
        else:
            view._message("Nothing to rotate: select a box (V) or copy something first.")

    def _flip(self, depth: bool) -> None:
        """H: mirror left/right as seen from the camera; Shift+H: front/back."""
        view = cast("MainWindow", self)
        right = view.viewport.camera.right()
        sideways = "x" if abs(right[0]) >= abs(right[2]) else "z"
        axis = ("z" if sideways == "x" else "x") if depth else sideways
        viewport, document = view.viewport, view.document
        if viewport.mode == BUILD and viewport.paste_preview is None:  # the block to place
            variant = viewport.vary_build(mirror=None if depth else axis, flip=depth)
            view._message(f"Block to place: {variant} (Shift+H turns it upside down).")
        elif viewport.paste_preview is not None and document.clipboard is not None:
            document.mirror_clipboard(axis)
            viewport.begin_paste(document.clipboard)
            view._message("Paste flipped.")
        elif viewport.region is not None:
            view._transform(mirror=axis)
        else:
            view._message("Nothing to flip: select a box (V) first.")

    def _transform(self, quarter_turns: int = 0, mirror: str | None = None) -> None:
        """Rotate or flip the selection in place; several selections turn together around
        the middle of the box around them all."""
        view = cast("MainWindow", self)
        viewport = view.viewport
        if viewport.region is None:
            return
        regions = viewport.all_regions()
        # Keep turning around the same pivot while the same selections are turned again,
        # so R then Shift+R (or R four times) returns exactly to the start.
        last = view._rotation_pivot
        pivot = last[1] if last is not None and last[0] == tuple(regions) else None
        if pivot is None:
            pivot = default_pivot2(*bounding_box(regions))
        try:
            if len(regions) > 1:
                moved = view.document.transform_regions(regions, quarter_turns, mirror, pivot)
                viewport.extra_regions, viewport.region = moved[:-1], moved[-1]
            else:
                moved = [view.document.transform_region(regions[0], quarter_turns, mirror, pivot)]
                viewport.region = moved[0]
            view._rotation_pivot = (tuple(moved), pivot)
        except EditError as exc:
            view._message(str(exc), error=True)
        else:
            what = f"rotated {quarter_turns * 90}°" if quarter_turns else "flipped"
            subject = f"{len(regions)} selections" if len(regions) > 1 else "Selection"
            view._message(f"{subject} {what} in place (no block updates).")
        view._changed()

    def _gizmo_transform(self, quarter_turns: int, mirror: str | None) -> None:
        view = cast("MainWindow", self)
        if mirror is not None:
            view._transform(mirror=mirror)
        else:
            view._rotate(quarter_turns)

    def _toggle_lock(self) -> None:
        """Enter (like GIMP): lock the selection so clicks cannot replace it; rotate, flip,
        move and stack keep working on it."""
        view = cast("MainWindow", self)
        viewport = view.viewport
        if viewport.region is None:
            view._message("Nothing to lock: select a box first (V).")
            return
        viewport.region_locked = not viewport.region_locked
        viewport.update()
        state = "locked (Enter or Esc unlocks)" if viewport.region_locked else "unlocked"
        view._message(f"Selection {state}.")

    def _stack_region(self, region: Region, step: Pos, count: int) -> None:
        view = cast("MainWindow", self)
        try:
            view.viewport.region = view.document.stack_region(region, step, count)
        except EditError as exc:
            view._message(str(exc), error=True)
        else:
            view._message(f"Stacked {count} copies (no block updates).")
        view._changed()

    def _delete_region(self) -> None:
        """Del: clear every selection, as one undo step (in BUILD mode, right click removes
        single blocks)."""
        view = cast("MainWindow", self)
        if view._region() is None and not view.viewport.extra_regions:
            return
        with view.document.batch():
            for region in view.viewport.all_regions():
                view._edit(view.document.fill, region, blocks.AIR.default_state)

    def _clear_selections(self) -> None:
        view = cast("MainWindow", self)
        view.viewport.clear_selections()
        view._changed()

    def _save_prefab(self) -> None:
        view = cast("MainWindow", self)
        region = view._region()
        if region is None:
            return
        name, ok = QInputDialog.getText(view, "Save prefab", "Name:")
        if ok and name:
            view.document.save_prefab(name, region)
            view._changed()

    def _load_prefab(self, name: str) -> None:
        view = cast("MainWindow", self)
        view.document.clipboard = view.document.prefabs[name]
        view._message(f"Prefab '{name}' is in the clipboard: Ctrl+V to paste.")

    def _delete_prefab(self, name: str) -> None:
        view = cast("MainWindow", self)
        view.document.prefabs.pop(name, None)
        view._changed()

    def _import_prefab(self) -> None:
        view = cast("MainWindow", self)
        path, _ = QFileDialog.getOpenFileName(view, "Import prefab", "", "Prefabs (*.json)")
        if path:
            try:
                prefab = Prefab.from_json(json.loads(Path(path).read_text()))
            except (OSError, ValueError, KeyError) as exc:
                QMessageBox.critical(view, "Cannot import prefab", str(exc))
                return
            view.document.prefabs[prefab.name] = prefab
            view._changed()

    def _export_prefab(self, name: str) -> None:
        view = cast("MainWindow", self)
        path, _ = QFileDialog.getSaveFileName(
            view, "Export prefab", f"{name}.prefab.json", "Prefabs (*.json)"
        )
        if path:
            Path(path).write_text(
                json.dumps(view.document.prefabs[name].to_json(), indent=1) + "\n"
            )

    def _create_group(self) -> None:
        view = cast("MainWindow", self)
        region = view._region()
        if region is None:
            return
        name, ok = QInputDialog.getText(view, "New group", "Name:")
        if ok and name:
            view.document.groups.add(Group(name, region))
            view._changed()

    def _add_port(self, group_name: str) -> None:
        view = cast("MainWindow", self)
        pos = view.viewport.selection
        if pos is None:
            view._message("Ctrl+click the block to expose as a port first.", error=True)
            return
        role, ok = QInputDialog.getItem(view, "Port", "Role:", ["input", "output"], 0, False)
        if not ok:
            return
        name, ok = QInputDialog.getText(view, "Port", "Port name:")
        if ok and name:
            view.document.groups.groups[group_name].ports.append(
                Port(name, pos, "input" if role == "input" else "output")
            )
            view._changed()

    def _toggle_port(self, group_name: str, index: int) -> None:
        view = cast("MainWindow", self)
        port = view.document.groups.groups[group_name].ports[index]
        if port.role != "input":
            return
        state = view.document.state_at(port.pos)
        if Document.is_usable(state.block):
            view._edit(view.document.use, port.pos)
        else:
            view._message(f"{block_name(state.block.id)} at {port.pos} cannot be used directly.")

    def _delete_group(self, name: str) -> None:
        view = cast("MainWindow", self)
        view.document.groups.remove(name)
        view._changed()
