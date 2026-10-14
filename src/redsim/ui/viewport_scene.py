"""What the viewport draws besides the world: guide lines, selection boxes and their fill,
gizmos, highlights (flash, hovered coordinates, sequence power), previews and the camera
pivot with its shadow."""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, Any, cast

import numpy as np
from PySide6.QtCore import QPoint

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor.clipboard import Region
from redsim.editor.heat import signal_heat
from redsim.ui.geometry import (
    block_outline,
    box_lines,
    boxes_at,
    ghost_mesh,
    many_box_lines,
    solid_box,
    thick_edges,
)
from redsim.ui.gizmos import Hotspot, box_faces, many_box_faces, pick_hotspot, selection_gizmos
from redsim.ui.renderer import GROUND_Y, Renderer
from redsim.ui.selection_tools import (
    shifted,
)
from redsim.ui.view_common import (
    ANIMATE,
    BODY_ALPHA,
    BODY_MARGIN,
    BODY_PULSE,
    BUILD,
    EXTRA_SELECTION_COLOR,
    HEAT_HIGH,
    HEAT_LOW,
    HIGHLIGHT_SECONDS,
    LOCATE_COLOR,
    LOCKED_COLOR,
    PENDING_PULSE_SECONDS,
    PIVOT_COLOR,
    PULSE_SECONDS,
    REPLACED_COLOR,
    SELECT,
    SELECTION_COLOR,
    TARGET_COLOR,
    _bounds,
    _ghost_key,
    _hex_color,
    _layer_grid,
)
from redsim.world import ids
from redsim.world.properties import FACING, POWERED

if TYPE_CHECKING:
    from redsim.ui.viewport import Viewport


OBSERVER_ID = "minecraft:observer"
#: Observer lights (``_observer_body``): color and how long they fade after the pulse.
OBSERVER_LIGHT = (1.0, 0.16, 0.08)
OBSERVER_FADE_SECONDS = 0.45


def _observer_lights(
    pos: Pos, facing: Direction, strength: float, lift: float = 1.0
) -> list[np.ndarray]:
    """A small bright square with a faint halo on the observer's output face, and a
    smaller one on its top when it faces sideways. ``lift`` scales how far they stand off
    the face (more from far away, where the depth buffer cannot tell 0.008 blocks apart)."""
    center = np.array(pos, dtype=float) + 0.5
    lights = [(facing.opposite, 0.16, 0.30), (Direction.UP, 0.12, 0.24)]
    if not facing.axis.is_horizontal:
        lights = lights[:1]
    parts = []
    for side, core, halo in lights:
        normal = np.array(side.step, dtype=float)
        face = center + normal * 0.5
        for half, gap, alpha in ((halo, 0.004, 0.22), (core, 0.008, 0.9)):
            extent = np.where(normal != 0, 0.0, half)
            lo = face - extent + np.minimum(normal, 0) * gap * lift
            hi = face + extent + np.maximum(normal, 0) * gap * lift
            parts.append(box_faces(lo, hi, (*OBSERVER_LIGHT, alpha * strength)))
    return parts


class SceneGeometry:
    """Part of ``Viewport`` (a mixin; its methods run on the viewport)."""

    def _overlay_lines(self) -> np.ndarray:
        view = cast("Viewport", self)
        level = view.document.level
        parts = []
        sections = view.document.sections.sections.values() if view.show_sections else ()
        groups = view.document.groups.groups.values() if view.show_groups else ()
        for section in sections:
            if section.positions:
                cells = np.array(list(section.positions), dtype=np.float32)
                parts.append(many_box_lines(cells, cells + 1, _hex_color(section.color), 0.01))
        shown = list(groups)
        if shown:
            lows = np.array([group.region.low for group in shown], dtype=np.float32)
            highs = np.array([group.region.high for group in shown], dtype=np.float32) + 1
            parts.append(many_box_lines(lows, highs, (1.0, 1.0, 1.0, 1.0), 0.03))
        ports = [port for group in shown for port in group.ports]
        if ports:
            cells = np.array([port.pos for port in ports], dtype=np.float32)
            colors = np.array(
                [
                    (0.2, 0.5, 1.0, 1.0) if port.role == "input" else (1.0, 0.5, 0.1, 1.0)
                    for port in ports
                ],
                dtype=np.float32,
            )
            parts.append(many_box_lines(cells, cells + 1, colors, 0.05))
        paste_box = view.paste_region()
        if paste_box is not None:
            parts.extend(view._paste_guides(paste_box))
        if view.selection is not None:
            parts.append(block_outline(level, view.selection, (1.0, 0.85, 0.1, 1.0)))
        if view.hover is not None:
            parts.append(block_outline(level, view.hover.pos, (0.05, 0.05, 0.05, 1.0)))
        if view.mode == BUILD and view.paste_preview is None:
            cell = view._line_end or view._build_cell  # where a block would go
            if cell is not None:
                parts.extend(view._paste_guides(Region(cell, cell)))  # layer grid
                color = (1.0, 0.2, 0.2, 1.0) if cell == view.build_blocked else (1, 1, 1, 1)
                parts.append(box_lines(cell, (cell[0] + 1, cell[1] + 1, cell[2] + 1), color))
        if not parts:
            return np.zeros((0, 7), dtype=np.float32)
        return np.vstack(parts)

    def _paste_guides(self, box: Region) -> list[np.ndarray]:
        """A grid on the working plane around the paste, and drop lines from its corners to
        the first block below, so its height reads at a glance (Trackmania-style)."""
        view = cast("Viewport", self)
        parts = [_layer_grid(box)]
        drop = (1.0, 0.9, 0.3, 1.0)
        level = view.document.level
        for cx in (box.low[0], box.high[0] + 1):
            for cz in (box.low[2], box.high[2] + 1):
                bx, bz = min(cx, box.high[0]), min(cz, box.high[2])  # the corner block column
                ground = box.low[1]
                while ground > max(level.min_y, box.low[1] - 64):
                    if (bx, ground - 1, bz) in level.blocks:
                        break
                    ground -= 1
                if ground < box.low[1]:
                    line = [(cx, box.low[1], cz, *drop), (cx, ground, cz, *drop)]
                    parts.append(np.array(line, dtype=np.float32))
        return parts

    def _overlay_triangles(self) -> np.ndarray:
        """Selection box, its handles and drop targets: thick, and visible through blocks;
        and the pivot block."""
        view = cast("Viewport", self)
        parts = [view._pivot_block()]
        width = view._edge_width()
        if view.located is not None:  # hovered coordinates: a bright frame through blocks
            lo = np.array(view.located, dtype=float) - 0.05
            parts.append(thick_edges(lo, lo + 1.1, LOCATE_COLOR, width * 0.8))
        for extra in view.extra_regions:
            lo, hi = _bounds(extra)
            parts.append(thick_edges(lo, hi, EXTRA_SELECTION_COLOR, width))
        if view.region is not None:
            lo, hi = _bounds(view.region)
            color = LOCKED_COLOR if view.region_confirmed else SELECTION_COLOR
            parts.append(thick_edges(lo, hi, color, width))
            if view._gizmos_shown():
                parts.append(view._gizmos()[0])
        if view.floating is not None:  # where the blocks would go
            for box in view.floating.boxes():
                lo, hi = _bounds(box)
                parts.append(thick_edges(lo, hi, TARGET_COLOR, width))
        stack = view._stack or view.pending_stack
        if stack is not None and stack.count:
            far = shifted(stack.region, stack.offset(stack.count))
            lo = np.minimum(_bounds(stack.region)[0], _bounds(far)[0])
            hi = np.maximum(_bounds(stack.region)[1], _bounds(far)[1])
            parts.append(thick_edges(lo, hi, TARGET_COLOR, width))
        paste_box = view.paste_region()
        if paste_box is not None:
            lo, hi = _bounds(paste_box)
            parts.append(thick_edges(lo, hi, TARGET_COLOR, width))
        if not parts:
            return np.zeros((0, 7), dtype=np.float32)
        return np.vstack(parts)

    def _edge_width(self) -> float:
        """Selection edges keep a similar on-screen thickness at any zoom."""
        view = cast("Viewport", self)
        return min(0.2, max(0.035, 0.006 * view.camera.distance))

    def gizmo_region(self) -> Region | None:
        """The box the gizmos sit on: the active selection, where its blocks are shown
        (a pending move or turn carries them along)."""
        view = cast("Viewport", self)
        if view.region is None:
            return None
        if view.floating is not None:
            return view.floating.boxes()[-1]
        return view.region

    def gizmo_unit(self) -> float:
        """Gizmo scale: grows with the distance to the selection, so it stays usable."""
        view = cast("Viewport", self)
        region = view.gizmo_region()
        if region is None:
            return 0.1
        lo, hi = _bounds(region)
        distance = float(np.linalg.norm((lo + hi) / 2 - view.camera.position))
        return min(0.6, max(0.07, 0.017 * distance))

    def _gizmos_shown(self) -> bool:
        view = cast("Viewport", self)
        busy = view._move is not None or view._stack is not None or view._resize is not None
        return (
            view.region is not None
            and view.mode == SELECT
            and not busy
            and view.paste_preview is None
            and view.pending_stack is None
        )

    def _gizmos(self) -> tuple[np.ndarray, list[Hotspot]]:
        """Gizmo triangles and hot spots for the current selection (cached). While the
        selection is edited: resize arrows and the turn ring (for its boxes); once
        confirmed: the ring, flip arrows and, with Shift, stacking chevrons."""
        view = cast("Viewport", self)
        region = view.gizmo_region()
        assert region is not None
        unit = view.gizmo_unit()
        confirmed = view.region_confirmed
        stacking = confirmed and view._shift and view.floating is None
        handles = not confirmed or stacking
        key = (
            region,
            round(unit, 3),
            round(view.camera.yaw),
            stacking,
            handles,
            confirmed,
            view.gizmo_hover,
        )
        if view._gizmo_cache is None or view._gizmo_cache[0] != key:
            shells: list[np.ndarray] = []
            built = selection_gizmos(
                region,
                unit,
                view.camera.yaw,
                stacking,
                view.gizmo_hover,
                shells,
                handles=handles,
                flips=confirmed,
            )
            outline = np.vstack(shells) if shells else np.zeros((0, 7), dtype=np.float32)
            view._gizmo_cache = (key, built)
            view._gizmo_outline = outline
        return view._gizmo_cache[1]

    def _outline_triangles(self) -> np.ndarray:
        """The gizmos' outlines (drawn behind them)."""
        view = cast("Viewport", self)
        if not view._gizmos_shown():
            return np.zeros((0, 7), dtype=np.float32)
        view._gizmos()
        return view._gizmo_outline

    def _gizmo_at(self, point: QPoint) -> Hotspot | None:
        view = cast("Viewport", self)
        if not view._gizmos_shown():
            return None
        origin, direction = view._ray(point)
        return pick_hotspot(origin, direction, view._gizmos()[1])

    def _selection_body(self) -> np.ndarray:
        """The selection filled with its color (round 8), so what is inside reads at a
        glance; the fill breathes slowly, so the selection feels alive."""
        view = cast("Viewport", self)
        extras = [
            box_faces(
                lo - BODY_MARGIN, hi + BODY_MARGIN, (*EXTRA_SELECTION_COLOR[:3], BODY_ALPHA / 2)
            )
            for lo, hi in (_bounds(extra) for extra in view.extra_regions)
        ]
        if view.region is None:
            return np.vstack(extras) if extras else np.zeros((0, 7), dtype=np.float32)
        lo, hi = _bounds(view.region)
        # A little larger than its blocks: faces in the same plane as block faces flicker
        # (z-fighting where the box meets them).
        lo, hi = lo - BODY_MARGIN, hi + BODY_MARGIN
        color = LOCKED_COLOR if view.region_confirmed else SELECTION_COLOR
        body = box_faces(lo, hi, (color[0], color[1], color[2], view.body_alpha()))
        return np.vstack([body, *extras])

    def _power_body(self) -> np.ndarray:
        """Sequence power: positions powered right now glow in their timeline group's color
        (in ANIMATE mode, and faintly in the others); in ANIMATE mode every position of a
        pulse is marked."""
        view = cast("Viewport", self)
        level = view.document.level
        animate = view.mode == ANIMATE
        parts = []
        lines = view.document.lines
        for pos, (strength, _) in level.forced_power.items():
            lo = np.array(pos, dtype=float) - 0.03
            alpha = (0.25 + 0.02 * strength) if animate else 0.15
            red, green, blue, _ = _hex_color(lines.color_of(pos))
            parts.append(box_faces(lo, lo + 1.06, (red, green, blue, alpha)))
        if animate:
            for pos in {pulse.pos for pulse in view.document.pulses() if not pulse.muted}:
                if pos not in level.forced_power:
                    lo = np.array(pos, dtype=float) - 0.02
                    red, green, blue, _ = _hex_color(lines.color_of(pos))
                    parts.append(box_faces(lo, lo + 1.04, (red, green, blue, 0.08)))
        return np.vstack(parts) if parts else np.zeros((0, 7), dtype=np.float32)

    def _heat_body(self) -> np.ndarray:
        """The signal heat view (View menu): powered blocks glow from dark red (1) to
        yellow (15); wire as a thin layer. Computed again only after a step or an edit."""
        view = cast("Viewport", self)
        if not view.show_heat:
            return np.zeros((0, 7), dtype=np.float32)
        document = view.document
        level = document.level
        key = (id(level), document.engine.step_index, document.revision)
        if view._heat_cache is not None and view._heat_cache[0] == key:
            return view._heat_cache[1]
        heat = signal_heat(level)
        if heat:
            positions = np.array(list(heat), dtype=float)
            strength = np.array(list(heat.values()), dtype=float)
            flat = np.array(
                [level.blocks[pos].block.id == ids.REDSTONE_WIRE for pos in heat], dtype=bool
            )
            lows = positions - 0.03
            highs = positions + 1.03
            highs[flat, 1] = positions[flat, 1] + 0.12
            t = ((strength - 1) / 14)[:, None]
            colors = np.hstack(
                [HEAT_LOW + (HEAT_HIGH - HEAT_LOW) * t, (0.28 + 0.02 * strength)[:, None]]
            )
            body = many_box_faces(lows, highs, colors)
        else:
            body = np.zeros((0, 7), dtype=np.float32)
        view._heat_cache = (key, body)
        return body

    def _observer_body(self) -> np.ndarray:
        """Observers sending a pulse: a small red light on the output face (and on the top
        of a sideways observer, which the usual camera sees), fading out for a moment
        after the pulse so a 2-tick pulse can be seen at full speed. Powered observers are
        found from the pending ticks (each one has its turn-off tick), so this stays cheap
        in big worlds."""
        view = cast("Viewport", self)
        document = view.document
        level = document.level
        now = time.monotonic()
        glow = view._observer_glow
        key = (id(level), document.engine.step_index, document.revision)
        if key != view._observer_key:
            view._observer_key = key
            for tick in level.block_ticks.pending():
                if tick.block_id != OBSERVER_ID:
                    continue
                state = level.blocks.get(tick.pos)
                if state is not None and state.block.id == OBSERVER_ID and state.get(POWERED):
                    glow[tick.pos] = (now, state.get(FACING))
            for pos in list(glow):
                state = level.blocks.get(pos)
                if state is None or state.block.id != OBSERVER_ID:
                    del glow[pos]
        parts = []
        for pos, (since, facing) in list(glow.items()):
            state = level.blocks.get(pos)
            if state is not None and state.get(POWERED):
                glow[pos] = (now, facing)
                strength = 1.0
            else:
                strength = 1.0 - (now - since) / OBSERVER_FADE_SECONDS
                if strength <= 0:
                    del glow[pos]
                    continue
            eye = np.asarray(view.camera.position, dtype=float)
            distance = float(np.linalg.norm(np.array(pos, dtype=float) + 0.5 - eye))
            parts.extend(_observer_lights(pos, facing, strength, max(1.0, distance / 20.0)))
        return np.vstack(parts) if parts else np.zeros((0, 7), dtype=np.float32)

    def locate(self, pos: Pos | None) -> None:
        """Light up ``pos`` while its coordinates are hovered elsewhere (None: stop)."""
        view = cast("Viewport", self)
        if pos != view.located:
            view.located = pos
            view.update()

    def flash(self, pos: Pos) -> None:
        """Highlight a block for a few seconds (a click in the Diagnostics tab)."""
        view = cast("Viewport", self)
        view.highlight = (pos, time.monotonic())
        view.update()

    def _highlight_body(self) -> np.ndarray:
        """The flashed block: a gold box that blinks and fades out; a located block (its
        coordinates hovered): a gold box that breathes."""
        view = cast("Viewport", self)
        parts = []
        if view.located is not None:
            lo = np.array(view.located, dtype=float) - 0.05
            alpha = 0.1 + 0.04 * math.sin(time.monotonic() * 2 * math.pi)
            parts.append(box_faces(lo, lo + 1.1, (*LOCATE_COLOR[:3], alpha)))
        flashed = view._flash_body()
        if len(flashed):
            parts.append(flashed)
        return np.vstack(parts) if parts else np.zeros((0, 7), dtype=np.float32)

    def _flash_body(self) -> np.ndarray:
        view = cast("Viewport", self)
        if view.highlight is None:
            return np.zeros((0, 7), dtype=np.float32)
        pos, since = view.highlight
        age = time.monotonic() - since
        if age > HIGHLIGHT_SECONDS:
            view.highlight = None
            return np.zeros((0, 7), dtype=np.float32)
        alpha = 0.45 * (1 - age / HIGHLIGHT_SECONDS) * (0.6 + 0.4 * math.cos(age * 2 * math.pi))
        lo = np.array(pos, dtype=float) - 0.04
        return box_faces(lo, lo + 1.08, (1.0, 0.82, 0.25, alpha))

    def body_alpha(self, now: float | None = None) -> float:
        """The selection fill's opacity: BODY_ALPHA, breathing by ±BODY_PULSE."""
        t = time.monotonic() if now is None else now
        return BODY_ALPHA + BODY_PULSE * math.sin(2 * math.pi * t / PULSE_SECONDS)

    def _upload_ghost(self, renderer: Renderer) -> None:
        view = cast("Viewport", self)
        stack = view._stack or view.pending_stack
        ghost = (
            view._ghost
            or ((stack.copies(), (0, 0, 0)) if stack is not None else None)
            or view._floating_ghost()
            or view._build_ghost
        )
        key = _ghost_key(ghost)
        if key == view._ghost_uploaded:
            return
        view._ghost_uploaded = key
        if ghost is None:
            renderer.upload_ghost(np.zeros((0, 7), dtype=np.float32))
            return
        vertices = ghost[0].copy()
        vertices[:, :3] += np.array(ghost[1], dtype=np.float32)
        renderer.upload_ghost(vertices)

    def _hidden_blocks(self) -> frozenset[Pos]:
        """The blocks a pending move takes away from where they are (a copy leaves them)."""
        view = cast("Viewport", self)
        floating = view.floating
        if floating is None or floating.keeps_source or not floating.changed:
            return frozenset()
        key = (floating.regions, id(view.document.level), view.document.revision)
        if view._hidden_cache is None or view._hidden_cache[0] != key:
            blocks_ = view.document.level.blocks
            cells = frozenset(pos for pos in floating.cells() if pos in blocks_)
            view._hidden_cache = (key, cells)
        return view._hidden_cache[1]

    def _floating_key(self) -> tuple[Any, ...] | None:
        """What the pending blocks' preview depends on, apart from its shift."""
        view = cast("Viewport", self)
        floating = view.floating
        if floating is None:
            return None
        document = view.document
        level = document.level
        return (
            floating.regions,
            floating.linear,
            id(floating.prefab),
            id(level),
            document.engine.step_index,
            document.revision,
        )

    def _floating_ghost(self) -> tuple[np.ndarray, Pos] | None:
        """The blocks of a pending move/turn/flip/copy where they would go: made once per
        turn or flip (and after an edit or a step); a move only shifts it."""
        view = cast("Viewport", self)
        floating = view.floating
        key = view._floating_key()
        if floating is None or key is None:
            return None
        if view._floating_mesh is None or view._floating_mesh[0] != key:
            states = floating.preview(view.document.level)
            vertices = ghost_mesh(states, mesher=view.world_mesh.mesher)
            view._floating_mesh = (key, vertices)
        return view._floating_mesh[1], floating.shift

    def _replaced_body(self) -> np.ndarray:
        """Blocks a pending move would overwrite: a red box around each."""
        view = cast("Viewport", self)
        floating = view.floating
        if floating is None:
            return np.zeros((0, 7), dtype=np.float32)
        key = (view._floating_key(), floating.shift, floating.copy)
        if view._replaced_mesh is None or view._replaced_mesh[0] != key:
            cells = floating.replaced(view.document.level) if floating.changed else []
            if cells:
                lows = np.array(cells, dtype=np.float32) - 0.03
                colors = np.tile(np.array(REPLACED_COLOR, dtype=np.float32), (len(cells), 1))
                body = many_box_faces(lows, lows + 1.06, colors)
            else:
                body = np.zeros((0, 7), dtype=np.float32)
            view._replaced_mesh = (key, body)
        return view._replaced_mesh[1]

    def ghost_alpha(self) -> float:
        """Pending blocks and the paste preview pulse, so they never pass for real ones."""
        view = cast("Viewport", self)
        pending = (
            view.floating is not None
            or view.pending_stack is not None
            or view._stack is not None
            or view.paste_preview is not None
        )
        if not pending:
            return 1.0
        t = time.monotonic()
        return 0.95 + 0.4 * math.sin(2 * math.pi * t / PENDING_PULSE_SECONDS)

    def _pivot_size(self) -> float:
        """Half the pivot block's edge: about the same size on screen at any zoom."""
        view = cast("Viewport", self)
        return 0.04 + view.camera.distance * 0.004

    def pivot_ground(self) -> float:
        """The height of the first surface below the pivot (a block top, else the floor
        level), where its shadow falls."""
        view = cast("Viewport", self)
        x, y, z = (float(v) for v in view.camera.pivot)
        bx, bz = math.floor(x), math.floor(z)
        level = view.document.level
        fx, fz = (x - bx) * 16.0, (z - bz) * 16.0  # the pivot's spot inside its column
        for by in range(math.floor(y), max(level.min_y, math.floor(y) - 64) - 1, -1):
            if (bx, by, bz) not in level.blocks:
                continue
            # The top of the block's shape under the pivot (dust, repeaters and signs are
            # lower than a full block; a part beside the pivot does not count).
            tops = [
                box.hi[1]
                for box in boxes_at(level, (bx, by, bz))
                if box.lo[0] <= fx <= box.hi[0] and box.lo[2] <= fz <= box.hi[2]
            ]
            if tops and by + max(tops) / 16.0 <= y:
                return by + max(tops) / 16.0
        return GROUND_Y

    def _pivot_block(self) -> np.ndarray:
        """The pivot as a small orange block (round 8: its place in space should be clear);
        drawn with the overlays, so it shows dimly through blocks too."""
        view = cast("Viewport", self)
        center = np.asarray(view.camera.pivot, dtype=float)
        half = view._pivot_size()
        return solid_box(center - half, center + half, PIVOT_COLOR)

    def _pivot_shadow(self) -> np.ndarray:
        """A soft square shadow on the surface below the pivot block."""
        view = cast("Viewport", self)
        x, _, z = (float(v) for v in view.camera.pivot)
        y = view.pivot_ground() + 0.01
        rows = []
        for scale, alpha in ((1.0, 0.45), (1.8, 0.2)):  # a dark core and a fainter rim
            r = view._pivot_size() * scale
            a, b, c, d = (x - r, y, z - r), (x + r, y, z - r), (x + r, y, z + r), (x - r, y, z + r)
            color = (0.0, 0.0, 0.0, alpha)
            rows += [(*p, *color) for p in (a, c, b, a, d, c)]
        return np.array(rows, dtype=np.float32)

    def _pivot_lines(self) -> np.ndarray:
        """A thin line from the pivot block down to its shadow, drawn on top."""
        view = cast("Viewport", self)
        x, y, z = (float(v) for v in view.camera.pivot)
        ground = view.pivot_ground()
        if y - view._pivot_size() <= ground + 0.02:
            return np.zeros((0, 7), dtype=np.float32)
        faint = (*PIVOT_COLOR[:3], 0.7)
        rows = [(x, y - view._pivot_size(), z, *faint), (x, ground, z, *faint)]
        return np.array(rows, dtype=np.float32)
