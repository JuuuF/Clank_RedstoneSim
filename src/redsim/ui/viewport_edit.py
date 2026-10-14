"""The viewport's editing gestures: what BUILD mode places (target cell, preview, variants,
dragged lines), SELECT mode's boxes (draw, resize, move, copy, stack, several boxes) and
the paste preview. Edits leave as signals; the main window applies them."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import numpy as np
from PySide6.QtCore import QPoint, Qt

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor import sources
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.floating import Floating
from redsim.editor.placement import PlaceRequest, placement_state
from redsim.ui.geometry import (
    Hit,
    ghost_mesh,
    pick,
    ray_box,
)
from redsim.ui.selection_tools import (
    Handle,
    face_center,
    horizontal_offset,
    paste_origin,
    plane_point,
    resized,
    shifted,
    steps_along,
)
from redsim.ui.view_common import BLOCKED_TINT, BUILD, GHOST_SHRINK, MAX_LINE, _bounds, _ghost_key
from redsim.world import blocks
from redsim.world.block import Block, BlockState
from redsim.world.rotation import mirror_state, rotate_state, upside_down

if TYPE_CHECKING:
    from redsim.ui.viewport import Viewport


class EditTools:
    """Part of ``Viewport`` (a mixin; its methods run on the viewport)."""

    def set_build_block(self, block: Block, strength: int) -> None:
        view = cast("Viewport", self)
        if block is not view.build_block:  # a new block starts plain
            view.build_turns, view.build_mirrors, view.build_upside_down = 0, frozenset(), False
        view.build_block = block
        view.build_strength = strength
        view._update_build_ghost()

    def _update_build_ghost(self) -> None:
        """Preview of the block(s) to place: oriented like the placement would orient them
        (cursor-ray yaw/pitch, wire connections, source setup), or a red outline. While a
        line is dragged, the whole line."""
        view = cast("Viewport", self)
        ghost, blocked = None, None
        block = view.build_block
        busy = view.paste_preview is not None or view._move is not None
        if view._line is not None and block is not None:
            start = view._line
            cells = view.line_cells()
            request = PlaceRequest(Direction.UP, *view.player_view())
            states = [(cell, view._placed_state(block, request, cell)) for cell in cells]
            parts = tuple(
                ((c[0] - start[0], c[1] - start[1], c[2] - start[2]), st)
                for c, st in states
                if st is not None
            )
            if parts:
                ghost = (view._combined_ghost(parts), start)
        elif view.mode == BUILD and block is not None and not busy:
            target = view.build_target()
            view._build_cell = target
            request = PlaceRequest(view.build_face, *view.player_view())
            state = None if target is None else view._placed_state(block, request, target)
            if target is not None and state is None:
                # Cannot be placed here: the preview stays, tinted red (round 9).
                blocked = target
                shown = placement_state(block, request, view.document.level, target)
                ghost = (view._single_ghost(shown or block.default_state, red=True), target)
            elif target is not None and state is not None:
                ghost = (view._single_ghost(state), target)
        if _ghost_key(ghost) != _ghost_key(view._build_ghost) or blocked != view.build_blocked:
            view._build_ghost, view.build_blocked = ghost, blocked
            view.update()

    def _placed_state(self, block: Block, request: PlaceRequest, target: Pos) -> BlockState | None:
        view = cast("Viewport", self)
        level = view.document.level
        if not level.get_block_state(target).is_air:
            return None
        state = placement_state(block, request, level, target)
        if state is not None:
            state = view.vary_state(state)
        kind = sources.PLACED_AS_SOURCE.get(block.id)
        if state is not None and kind is not None:
            text, _ = sources.source_setblock(kind, view.build_strength, state)
            state = blocks.parse_state(text)
        if state is None or not state.can_survive(level, target):
            return None
        return state

    def _single_ghost(self, state: BlockState, red: bool = False) -> np.ndarray:
        view = cast("Viewport", self)
        if red:
            tinted = view._red_meshes.get(state)
            if tinted is None:
                tinted = view._single_ghost(state).copy()
                tinted[:, 3:6] *= np.array(BLOCKED_TINT, dtype=np.float32)
                view._red_meshes[state] = tinted
            return tinted
        vertices = view._build_meshes.get(state)
        if vertices is None:
            vertices = ghost_mesh({(0, 0, 0): state}, 0.5, view.world_mesh.mesher)
            # Shrink it a little around the block center, so none of its faces lies in the
            # plane of a neighbor's face (z-fighting flicker, e.g. wire on a block).
            vertices[:, :3] = 0.5 + (vertices[:, :3] - 0.5) * GHOST_SHRINK
            view._build_meshes[state] = vertices
        return vertices

    def _combined_ghost(self, parts: tuple[tuple[Pos, BlockState], ...]) -> np.ndarray:
        view = cast("Viewport", self)
        cached = view._line_ghost
        if cached is not None and cached[0] == parts:
            return cached[1]
        pieces = []
        for rel, state in parts:
            vertices = view._single_ghost(state).copy()
            vertices[:, :3] += np.array(rel, dtype=np.float32)
            pieces.append(vertices)
        combined = np.vstack(pieces)
        view._line_ghost = (parts, combined)
        return combined

    def line_cells(self) -> list[Pos]:
        """The cells of the dragged line: from the start along the axis the cursor moved
        most on (x or z, on the start's layer), at most ``MAX_LINE`` long."""
        view = cast("Viewport", self)
        if view._line is None:
            return []
        start = view._line
        end = view._line_end or start
        dx, dz = end[0] - start[0], end[2] - start[2]
        if abs(dx) >= abs(dz):
            length, step = abs(dx), (1 if dx >= 0 else -1, 0, 0)
        else:
            length, step = abs(dz), (0, 0, 1 if dz >= 0 else -1)
        length = min(length, MAX_LINE - 1)
        return [
            (start[0] + step[0] * i, start[1], start[2] + step[2] * i) for i in range(length + 1)
        ]

    def build_target(self, point: QPoint | None = None) -> Pos | None:
        """Where BUILD mode places: like Minecraft, against the face of the block the
        cursor points at (``build_face`` is that face) when the ray meets a block before
        the working layer; otherwise on the working layer (the camera pivot's height; the
        wheel moves it), in the cell under the cursor, like Trackmania's editor."""
        view = cast("Viewport", self)
        point = point if point is not None else view._last_mouse
        if point is None:
            return None
        origin, direction = view._ray(point)
        view._hover_direction = direction
        layer_y = view.working_height()
        on_layer = paste_origin(origin, direction, layer_y, (1, 1, 1))
        crossing = plane_point(origin, direction, float(layer_y))
        hit = pick(view.document.level, origin, direction)
        layer_distance = (
            float(np.linalg.norm(crossing - origin)) if crossing is not None else math.inf
        )
        if hit is not None and hit.distance <= layer_distance:
            view.build_face = hit.face
            step = hit.face.step
            return (hit.pos[0] + step[0], hit.pos[1] + step[1], hit.pos[2] + step[2])
        view.build_face = Direction.UP
        return on_layer

    def _begin_line(self, point: QPoint) -> bool:
        view = cast("Viewport", self)
        start = view.build_target(point)
        if start is None or view.build_block is None:
            return False
        view._line = start
        view._line_end = None
        return True

    def _continue_line(self, point: QPoint) -> None:
        view = cast("Viewport", self)
        if view._line is None:
            return
        end = view.build_target(point)
        if end is not None and end != view._line_end:
            view._line_end = end
            view._update_build_ghost()

    def _end_line(self) -> None:
        view = cast("Viewport", self)
        if view._line is None:
            return
        cells = view.line_cells()
        view._line, view._line_end = None, None
        view.line_requested.emit(cells)
        view._update_build_ghost()

    def vary_build(self, turns: int = 0, mirror: str | None = None, flip: bool = False) -> str:
        """R / H / Shift+H in BUILD: vary the block to place; returns how it is varied."""
        view = cast("Viewport", self)
        view.build_turns = (view.build_turns + turns) % 4
        if mirror is not None:
            view.build_mirrors = view.build_mirrors ^ {mirror}
        if flip:
            view.build_upside_down = not view.build_upside_down
        view._build_meshes.clear()
        view._red_meshes.clear()
        view._update_build_ghost()
        view.update()
        return view.build_variant() or "as placed"

    def vary_state(self, state: BlockState) -> BlockState:
        """The block to place as varied by R / H / Shift+H."""
        view = cast("Viewport", self)
        state = rotate_state(state, view.build_turns)
        for axis in sorted(view.build_mirrors):
            state = mirror_state(state, axis)
        return upside_down(state) if view.build_upside_down else state

    def build_variant(self) -> str:
        view = cast("Viewport", self)
        parts = []
        if view.build_turns:
            parts.append(f"turned {90 * view.build_turns}°")
        if view.build_mirrors:
            parts.append("mirrored")
        if view.build_upside_down:
            parts.append("upside down")
        return ", ".join(parts)

    def _begin_select_drag(self, start: QPoint, copy: bool) -> None:
        """A left drag in SELECT mode. While the selection is edited (before Enter): from a
        face handle it resizes the box, from inside a box it moves that box, elsewhere it
        draws a new box. Once confirmed (Enter): from inside, the blocks move (Ctrl: a
        copy) as a preview that the next Enter places."""
        view = cast("Viewport", self)
        origin, direction = view._ray(start)
        block = pick(view.document.level, origin, direction)
        region = view.region
        spot = view._gizmo_at(start)
        if spot is not None:  # gizmos are drawn on top, so they win over blocks
            if spot.kind == "resize" and region is not None and not view.region_confirmed:
                handle = spot.data
                center = face_center(region, handle)
                axis = view._screen_vector(center, center + handle.normal)
                view._resize = (handle, region, start, axis)
            return  # rotate/flip gizmos act on click, not drag
        if view.region_confirmed:
            if view.pending_stack is not None:
                view.message_requested.emit(
                    "Enter places the stacked copies first (Esc cancels them)."
                )
                return
            floating = view.floating or Floating(tuple(view.all_regions()))
            grab = _grab_any(floating.boxes(), origin, direction, block)
            if grab is None:
                return  # a confirmed selection keeps its boxes
            if copy:
                floating = replace(floating, copy=True)
            view._move = _MoveDrag(float(grab[1][1]), grab[1], floating=floating)
            return
        grab = _grab_any(tuple(view.all_regions()), origin, direction, block)
        if grab is not None:  # move the box itself (no blocks): it becomes the active one
            view.activate_region(grab[0])
            assert view.region is not None
            view._move = _MoveDrag(float(grab[1][1]), grab[1], outline=view.region)
            return
        if copy:
            view.message_requested.emit(
                "Press Enter to confirm the selection first: then Ctrl+drag copies its blocks."
            )
            return
        view._region_anchor = block.pos if block else None
        view._extend_box()

    def activate_region(self, index: int) -> None:
        """Make the ``index``-th box of ``all_regions`` the active one (the last)."""
        view = cast("Viewport", self)
        regions = view.all_regions()
        if index == len(regions) - 1:
            return
        chosen = regions.pop(index)
        view.extra_regions, view.region = regions, chosen

    def _continue_select_drag(self) -> None:
        view = cast("Viewport", self)
        point = view._last_mouse
        if point is None:
            return
        if view._resize is not None:
            handle, region, start, axis = view._resize
            drag = (point.x() - start.x(), point.y() - start.y())
            view.region = resized(region, handle, steps_along(drag, axis))
            view.update()
        elif view._move is not None:
            origin, direction = view._ray(point)
            hit = plane_point(origin, direction, view._move.plane_y)
            if hit is not None:
                view._move.dx, view._move.dz = horizontal_offset(view._move.grab, hit)
                view._apply_move()
        else:
            view._extend_box()

    def _apply_move(self) -> None:
        """Show the dragged box (editing) or blocks (confirmed) at the drag's offset."""
        view = cast("Viewport", self)
        move = view._move
        if move is None:
            return
        if move.floating is not None:
            view.floating = move.floating.moved(move.offset_pos)
        elif move.outline is not None:
            view.region = shifted(move.outline, move.offset_pos)
        view.update()

    def _end_select_drag(self) -> None:
        view = cast("Viewport", self)
        move, view._move = view._move, None
        resize, view._resize = view._resize, None
        if move is not None and move.floating is not None:
            floating = view.floating
            if floating is not None and not floating.changed:
                view.floating = None  # dropped where it was: nothing to place
            view.floating_changed.emit()
        elif move is not None or resize is not None or view._region_anchor is not None:
            view.region_changed.emit(view.region)

    def _begin_extra_box(self, start: QPoint) -> None:
        """Keep the current selection and draw another one (Shift+drag off the handles)."""
        view = cast("Viewport", self)
        if view.region_confirmed:
            view.message_requested.emit(
                "The selection is confirmed: Esc goes back to editing its boxes."
            )
            view._drag_action = ""
            return
        if view.region is not None:
            view.extra_regions.append(view.region)
        view.region = None
        origin, direction = view._ray(start)
        block = pick(view.document.level, origin, direction)
        view._region_anchor = block.pos if block else None
        view._drag_action = "select.box"  # the rest of the drag draws the new box
        view._extend_box()

    def clear_selections(self) -> None:
        """Remove every selection (Alt+A; Esc in NORMAL mode) and what was pending."""
        view = cast("Viewport", self)
        view.extra_regions = []
        view.region, view.region_confirmed = None, False
        view.floating = None
        view.pending_stack = None
        view.region_changed.emit(None)
        view.update()

    def cancel_pending(self) -> bool:
        """Esc: drop a pending move, turn, flip, copy or stack; whether there was one."""
        view = cast("Viewport", self)
        if view.floating is None and view.pending_stack is None:
            return False
        view.floating = None
        view.pending_stack = None
        view.update()
        return True

    def all_regions(self) -> list[Region]:
        """Every selection, the active one last."""
        view = cast("Viewport", self)
        return [*view.extra_regions, *([view.region] if view.region is not None else [])]

    def _begin_stack(self, start: QPoint) -> None:
        """Shift+drag on a face handle of a confirmed selection: copies along that face's
        normal (placed by Enter); elsewhere, or while editing: one more selection."""
        view = cast("Viewport", self)
        region = view.region
        spot = view._gizmo_at(start)
        if region is None or spot is None or spot.kind != "resize" or not view.region_confirmed:
            view._begin_extra_box(start)
            return
        if view.floating is not None:
            view.message_requested.emit("Enter places the moved blocks first (Esc cancels).")
            view._drag_action = ""
            return
        handle = spot.data
        center = face_center(region, handle)
        axis = view._screen_vector(center, center + handle.normal)
        view.pending_stack = None
        view._stack = _StackDrag(region, handle, start, axis, view._region_ghost(region))

    def _continue_stack(self) -> None:
        view = cast("Viewport", self)
        stack, point = view._stack, view._last_mouse
        if stack is None or point is None:
            return
        drag = (point.x() - stack.start.x(), point.y() - stack.start.y())
        count = max(0, round(steps_along(drag, stack.axis) / stack.length))
        if count != stack.count:
            stack.count = count
            view.update()

    def _end_stack(self) -> None:
        view = cast("Viewport", self)
        stack, view._stack = view._stack, None
        if stack is not None and stack.count:
            view.pending_stack = stack
            view.floating_changed.emit()
        view.update()

    def _extend_box(self) -> None:
        view = cast("Viewport", self)
        if view._region_anchor is not None and view.hover is not None:
            view.region = Region.from_corners(view._region_anchor, view.hover.pos)
            view.update()

    def _region_ghost(self, *regions: Region) -> np.ndarray:
        view = cast("Viewport", self)
        level = view.document.level
        states = {
            pos: level.blocks[pos]
            for region in regions
            for pos in region.positions()
            if pos in level.blocks
        }
        return ghost_mesh(states, mesher=view.world_mesh.mesher)

    def begin_paste(self, prefab: Prefab) -> None:
        """Show ``prefab`` as a ghost at the cursor; a left click places it."""
        view = cast("Viewport", self)
        states = {(dx, dy, dz): blocks.parse_state(text) for dx, dy, dz, text, _ in prefab.blocks}
        view.paste_preview = prefab
        view._paste_base = ghost_mesh(states, mesher=view.world_mesh.mesher)
        view._update_paste_ghost()

    def cancel_paste(self) -> None:
        view = cast("Viewport", self)
        view.paste_preview = None
        view._ghost = None
        view.update()

    def paste_target(self) -> Pos | None:
        """Minimum corner of the paste, Trackmania-editor style: on the horizontal plane at
        the camera's working height (the pivot's block layer; Ctrl+wheel moves it),
        centered under the cursor. Works in the air and inside blocks."""
        view = cast("Viewport", self)
        if view.paste_preview is None or view._last_mouse is None:
            return None
        origin, direction = view._ray(view._last_mouse)
        return paste_origin(origin, direction, view.working_height(), view.paste_preview.size)

    def working_height(self) -> int:
        """The block layer the camera pivot is in (or is gliding to)."""
        view = cast("Viewport", self)
        pivot = view._glide[0] if view._glide is not None else view.camera.pivot
        return math.floor(float(pivot[1]))

    def paste_region(self) -> Region | None:
        view = cast("Viewport", self)
        target = view.paste_target()
        if view.paste_preview is None or target is None:
            return None
        sx, sy, sz = view.paste_preview.size
        return Region(target, (target[0] + sx - 1, target[1] + sy - 1, target[2] + sz - 1))

    def _update_paste_ghost(self) -> None:
        view = cast("Viewport", self)
        target = view.paste_target()
        if view.paste_preview is None:
            return
        view._ghost = None if target is None else (view._paste_base, target)
        view.update()

    def _paste_click(self, button: Qt.MouseButton) -> None:
        view = cast("Viewport", self)
        target = view.paste_target()
        if button == Qt.MouseButton.LeftButton and target is not None:
            view.cancel_paste()
            view.paste_requested.emit(target)
        elif button == Qt.MouseButton.RightButton:
            view.cancel_paste()


class _MoveDrag:
    """A drag from inside the selection: its box (``outline``, while editing) or its
    blocks (``floating``, once confirmed) follow the cursor on the grabbed height; the
    wheel lifts them."""

    def __init__(
        self,
        plane_y: float,
        grab: np.ndarray,
        floating: Floating | None = None,
        outline: Region | None = None,
    ) -> None:
        self.plane_y = plane_y
        self.grab = grab
        self.floating = floating
        self.outline = outline
        self.dx = self.dz = self.lift = 0

    @property
    def offset_pos(self) -> Pos:
        return (self.dx, self.lift, self.dz)


def _grab_any(
    boxes: tuple[Region, ...] | list[Region],
    origin: np.ndarray,
    direction: np.ndarray,
    block: Hit | None,
) -> tuple[int, np.ndarray] | None:
    """Which box a drag grabs (its index) and where: the nearest box the ray meets, or a
    block inside one (selections usually contain air). Later boxes win ties (the active
    one is last)."""
    best: tuple[float, int] | None = None
    for index, region in enumerate(boxes):
        if block is not None and region.contains(block.pos):
            distance = block.distance
        else:
            lo, hi = _bounds(region)
            hit = ray_box(origin, direction, lo, hi)
            if hit is None:
                continue
            distance = hit[0]
        if best is None or distance <= best[0]:
            best = (distance, index)
    if best is None:
        return None
    return best[1], origin + direction * best[0]


class _StackDrag:
    """Copies being pulled out of a selection along one face's normal."""

    def __init__(
        self, region: Region, handle: Handle, start: QPoint, axis: np.ndarray, ghost: np.ndarray
    ) -> None:
        self.region = region
        self.handle = handle
        self.start = start
        self.axis = axis
        self.ghost = ghost
        self.length = region.size[handle.axis]
        self.count = 0
        self._copies: tuple[int, np.ndarray] | None = None

    def offset(self, copies: int) -> Pos:
        step = self.handle.normal * self.length * copies
        return (int(step[0]), int(step[1]), int(step[2]))

    def copies(self) -> np.ndarray:
        """The preview of every copy (made again only when the count changes)."""
        if self._copies is None or self._copies[0] != self.count:
            parts = [self.ghost.copy() for _ in range(self.count)]
            for i, vertices in enumerate(parts, start=1):
                vertices[:, :3] += np.array(self.offset(i), dtype=np.float32)
            stacked = np.vstack(parts) if parts else np.zeros((0, 7), dtype=np.float32)
            self._copies = (self.count, stacked)
        return self._copies[1]
