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
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document import Document, EditError
from redsim.editor.floating import Floating
from redsim.editor.groups import Group, Port
from redsim.io.schematics import FILE_FILTER as SCHEMATIC_FILTER
from redsim.io.schematics import read_schematic, write_schematic
from redsim.ui.names import block_name
from redsim.ui.viewport import BUILD
from redsim.world import blocks

if TYPE_CHECKING:
    from redsim.ui.main_window import MainWindow


class RegionActions:
    """Part of ``MainWindow`` (a mixin; its methods run on it)."""

    #: The name a paste is grouped under (the clipboard came from a prefab), else None.
    _paste_group: str | None = None

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
        view._paste_group = None  # a plain copy pastes as blocks only
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
        """Place the paste; a prefab (or an imported schematic) becomes a group named after
        it, so it shows as one piece with its outline (owner, 2026-10-14)."""
        view = cast("MainWindow", self)
        clipboard = view.document.clipboard
        revision = view.document.revision
        view._edit(view.document.paste, origin)
        if view._paste_group is None or clipboard is None or view.document.revision == revision:
            return
        sx, sy, sz = clipboard.size
        high = (origin[0] + sx - 1, origin[1] + sy - 1, origin[2] + sz - 1)
        name = view.document.groups.free_name(view._paste_group)
        view.document.groups.add(Group(name, Region(origin, high)))
        view._changed()
        view._message(f"Placed “{name}” as a group (Circuit → Groups).")

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
        """Turn or flip the selection: while it is edited, its boxes (no blocks); once
        confirmed, its blocks, as a preview that Enter places. Several selections turn
        together around the middle of the box around them all."""
        view = cast("MainWindow", self)
        viewport = view.viewport
        if viewport.region is None:
            return
        turns = quarter_turns % 4
        what = {1: "turned clockwise", 2: "turned around", 3: "turned counter-clockwise"}.get(
            turns, "flipped"
        )
        if not viewport.region_confirmed:
            boxes = Floating(tuple(viewport.all_regions()))
            boxes = boxes.turned(quarter_turns) if quarter_turns else boxes.flipped(mirror or "x")
            moved = list(boxes.boxes())
            viewport.extra_regions, viewport.region = moved[:-1], moved[-1]
            view._message(
                f"Selection box {what}. Enter confirms the selection: then "
                f"{view.keymap.describe('edit.rotate')} turns its blocks."
            )
            viewport.update()
            return
        if viewport.pending_stack is not None:
            view._message("Enter places the stacked copies first (Esc cancels them).")
            return
        floating = viewport.floating or Floating(tuple(viewport.all_regions()))
        floating = (
            floating.turned(quarter_turns) if quarter_turns else floating.flipped(mirror or "x")
        )
        viewport.floating = floating if floating.changed or floating.copy else None
        viewport.update()
        view._floating_changed()

    def _floating_changed(self) -> None:
        """A pending move, turn, flip, copy or stack was made, changed or dropped."""
        view = cast("MainWindow", self)
        viewport = view.viewport
        enter = view.keymap.describe("select.lock")
        if viewport.pending_stack is not None:
            count = viewport.pending_stack.count
            view._message(f"{count} stacked copies: {enter} places them, Esc cancels.")
        elif viewport.floating is not None:
            floating = viewport.floating
            replaced = len(floating.replaced(view.document.level)) if floating.changed else 0
            warning = f" It would replace {replaced} blocks (red)." if replaced else ""
            verb = "Copy" if floating.copy else "Preview"
            view._message(f"{verb}: {enter} places the blocks, Esc cancels.{warning}")

    def _confirm(self) -> None:
        """Enter, like GIMP: place what is pending; otherwise confirm the selection (its
        boxes are fixed, and moving, turning, flipping and stacking act on its blocks), or
        go back to editing its boxes."""
        view = cast("MainWindow", self)
        viewport = view.viewport
        if viewport.floating is not None:
            view._place_floating()
            return
        if viewport.pending_stack is not None:
            stack, viewport.pending_stack = viewport.pending_stack, None
            view._stack_region(stack.region, stack.offset(1), stack.count)
            return
        if viewport.region is None:
            view._message("Nothing to confirm: select a box first (V).")
            return
        viewport.region_confirmed = not viewport.region_confirmed
        viewport.update()
        if viewport.region_confirmed:
            view._message(
                "Selection confirmed: drag its blocks (Ctrl: a copy), turn or flip them, "
                f"Shift+drag an arrow to stack; {view.keymap.describe('select.lock')} "
                "places. Esc edits the boxes again."
            )
        else:
            view._message("Editing the selection's boxes again.")

    def _place_floating(self) -> None:
        """Enter on a pending move/turn/flip/copy: one edit, one undo step."""
        view = cast("MainWindow", self)
        viewport = view.viewport
        floating, viewport.floating = viewport.floating, None
        if floating is None or not floating.changed:
            viewport.update()
            return
        turns, mirror, pivot, offset = floating.action()
        try:
            view.document.transform_regions(
                list(floating.regions), turns, mirror, pivot, offset, copy=floating.copy
            )
        except EditError as exc:
            view._message(str(exc), error=True)
        else:
            moved = list(floating.boxes())
            viewport.extra_regions, viewport.region = moved[:-1], moved[-1]
            verb = "Copied" if floating.copy else "Placed"
            view._message(f"{verb} the blocks (no block updates).")
        view._changed()

    def _gizmo_transform(self, quarter_turns: int, mirror: str | None) -> None:
        view = cast("MainWindow", self)
        if mirror is not None:
            view._transform(mirror=mirror)
        else:
            view._rotate(quarter_turns)

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
        if view.viewport.floating is not None or view.viewport.pending_stack is not None:
            view._message("Enter places the pending blocks first (Esc cancels them).")
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
        """Circuit → Prefabs → Paste: the prefab follows the cursor; a click places it as
        a group (Ctrl+V places more copies, each its own group)."""
        view = cast("MainWindow", self)
        view.document.clipboard = view.document.prefabs[name]
        view._paste_group = name
        view.viewport.begin_paste(view.document.clipboard)
        view._message(
            f"Paste “{name}”: left click places it as a group · R rotates · right click or "
            "Esc cancels."
        )

    def _delete_prefab(self, name: str) -> None:
        view = cast("MainWindow", self)
        view.document.prefabs.pop(name, None)
        view._changed()

    def _import_prefab(self) -> None:
        """A prefab from a file: the simulator's JSON or a schematic (Litematica,
        Sponge/WorldEdit, structure file)."""
        view = cast("MainWindow", self)
        path, _ = QFileDialog.getOpenFileName(
            view, "Import prefab", "", f"Prefabs (*.json);;{SCHEMATIC_FILTER}"
        )
        if path:
            prefab = view._read_prefab_file(Path(path))
            if prefab is not None:
                view.document.prefabs[prefab.name] = prefab
                view._changed()

    def _read_prefab_file(self, path: Path) -> Prefab | None:
        view = cast("MainWindow", self)
        try:
            if path.suffix.lower() == ".json":
                return Prefab.from_json(json.loads(path.read_text()))
            return read_schematic(path)
        except (OSError, ValueError, KeyError, IndexError, EOFError) as exc:
            QMessageBox.critical(view, "Cannot read the file", f"{path.name}: {exc}")
            return None

    def _export_prefab(self, name: str) -> None:
        """A prefab to a file: the simulator's JSON or a schematic (by the file type)."""
        view = cast("MainWindow", self)
        path, _ = QFileDialog.getSaveFileName(
            view, "Export prefab", f"{name}.prefab.json", f"Prefabs (*.json);;{SCHEMATIC_FILTER}"
        )
        if path:
            view._write_prefab_file(Path(path), view.document.prefabs[name])

    def _write_prefab_file(self, path: Path, prefab: Prefab) -> None:
        view = cast("MainWindow", self)
        try:
            if path.suffix.lower() == ".json":
                path.write_text(json.dumps(prefab.to_json(), indent=1) + "\n")
            else:
                write_schematic(path, prefab)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(view, "Cannot write the file", str(exc))
            return
        view._message(f"Wrote {prefab.non_air_count} blocks to {path.name}.")

    def _import_schematic(self) -> None:
        """Region → Import schematic…: into the clipboard, shown at the cursor to paste."""
        view = cast("MainWindow", self)
        path, _ = QFileDialog.getOpenFileName(view, "Import schematic", "", SCHEMATIC_FILTER)
        if not path:
            return
        prefab = view._read_prefab_file(Path(path))
        if prefab is None:
            return
        view.document.clipboard = prefab
        view._paste_group = prefab.name
        view.viewport.begin_paste(prefab)
        size = "×".join(str(v) for v in prefab.size)
        view._message(
            f"{prefab.name} ({size}, {prefab.non_air_count} blocks) is in the clipboard: left "
            "click places it · R rotates · right click or Esc cancels."
        )

    def _export_schematic(self) -> None:
        """Region → Export selection as schematic…: every selection box (the cells
        between several boxes are left out)."""
        view = cast("MainWindow", self)
        if view._region() is None:
            return
        regions = view.viewport.all_regions()
        level = view.document.level
        prefab = (
            Prefab.capture_many(level, regions, "selection")
            if len(regions) > 1
            else Prefab.capture(level, regions[0], "selection")
        )
        path, _ = QFileDialog.getSaveFileName(
            view, "Export selection as schematic", "selection.litematic", SCHEMATIC_FILTER
        )
        if path:
            target = Path(path)
            if not target.suffix:
                target = target.with_suffix(".litematic")
            prefab.name = target.name.split(".")[0]
            view._write_prefab_file(target, prefab)

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
