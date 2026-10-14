"""3D viewport: orbit camera, modes, targeting and edit requests.

Controls follow the owner's decisions (doc/ui-direction.md) and are rebindable through the
keymap (``redsim.ui.keymap``). By default: middle-drag orbits around the highlighted pivot,
Shift+middle-drag pans it, Ctrl+wheel moves it up and down, the wheel zooms, WASD moves the
pivot. Clicks depend on the mode: NORMAL (left inspects, right uses), BUILD (left breaks,
right places) and SELECT (left click or drag selects boxes); middle click picks a block type
in every mode.

The viewport never edits the world itself; it emits signals that the main window turns into
document edits.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Any

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QFocusEvent,
    QImage,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QNativeGestureEvent,
    QWheelEvent,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document import Document
from redsim.editor.floating import Floating
from redsim.ui.atlas import Atlas
from redsim.ui.camera import MAX_DISTANCE, MIN_DISTANCE, Camera
from redsim.ui.geometry import (
    ChunkedMesh,
    Hit,
    Mesher,
    pick,
)
from redsim.ui.gizmos import Hotspot
from redsim.ui.keymap import HOLD, Keymap
from redsim.ui.pacing import RateMeter
from redsim.ui.panel_circuit import PREFAB_MIME
from redsim.ui.preferences import Preferences
from redsim.ui.renderer import CLOUD_TEXTURE, GROUND_TEXTURE, Renderer
from redsim.ui.selection_tools import (
    Handle,
)
from redsim.ui.view_common import (
    _BUTTON_NAMES,
    ANIMATE,
    BACKGROUND,
    BODY_ALPHA,
    BODY_PULSE,
    BUILD,
    DOUBLE_SHIFT_SECONDS,
    DRAG_THRESHOLD,
    FOV_SCREEN_SHARE,
    FRAME_INTERVAL_MS,
    GLIDE_SECONDS,
    GRID_ALPHA,
    MODE_COLORS,
    MOVING_KEY,
    NORMAL,
    ORBIT_DEGREES_PER_PIXEL,
    PICK_REACH,
    PULSE_SECONDS,
    SELECT,
    TRACKPAD_PIXELS_PER_BLOCK,
    TRACKPAD_PIXELS_PER_NOTCH,
    ZOOM_PER_NOTCH,
    _from_trackpad,
    _layer_grid,
    _modifier_names,
    game_textures,
)
from redsim.ui.viewport_edit import EditTools, _grab_any, _MoveDrag, _StackDrag
from redsim.ui.viewport_scene import SceneGeometry
from redsim.ui.viewport_text import LabelRange, TextOverlays
from redsim.world import blocks
from redsim.world.block import Block, BlockState


class Viewport(EditTools, SceneGeometry, TextOverlays, QOpenGLWidget):
    hover_changed = Signal(object)  # Hit | None
    place_requested = Signal(object)  # Pos: a cell on the working layer
    line_requested = Signal(object)  # [Pos]: a straight line on the working layer
    rotate_requested = Signal(object, int)  # Pos, quarter turns
    use_requested = Signal(object)  # Pos
    break_requested = Signal(object)  # Pos
    pick_requested = Signal(object)  # Pos
    select_requested = Signal(object)  # Pos | None (inspector selection)
    region_changed = Signal(object)  # Region | None
    #: A move, turn, flip, copy or stack of the confirmed selection is now pending (or was
    #: dropped): ``floating`` / ``pending_stack``; Enter places it.
    floating_changed = Signal()
    message_requested = Signal(str)  # a short note for the status bar
    #: A prefab dragged in from the Prefabs list (its name): the window starts its paste.
    prefab_dragged = Signal(str)
    prefab_dropped = Signal(str, object)  # its name, the minimum corner where it was dropped
    transform_requested = Signal(int, object)  # quarter turns, mirror axis | None
    gizmo_hover_changed = Signal(object)  # Hotspot | None
    paste_requested = Signal(object)  # Pos (minimum corner)
    mode_changed = Signal(str)
    mode_requested = Signal(str)  # the Tab ring chose a mode
    pulse_requested = Signal(object)  # Pos (ANIMATE: left click)
    pulse_remove_requested = Signal(object)  # Pos (ANIMATE: right click)
    search_requested = Signal()  # Shift pressed twice (like Rider's search everywhere)

    def __init__(
        self, document: Document, keymap: Keymap | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.document = document
        self.camera = Camera()
        self.renderer: Renderer | None = None
        self.mode = NORMAL
        self.hover: Hit | None = None
        self._hover_direction: np.ndarray | None = None
        self.selection: Pos | None = None
        self.region: Region | None = None
        self._region_anchor: Pos | None = None
        #: Annotation outlines (View menu): sections (colored cells) and groups (white boxes).
        self.show_sections = True
        self.show_groups = True
        #: Blender-like X-ray (building blocks see-through) and the block-info overlay.
        self.xray = 0  # 0 off, 1 building blocks see-through, 2 everything see-through
        self.show_info = False
        #: The signal heat view (View menu) and its triangles for the step shown.
        self.show_heat = False
        self._heat_cache: tuple[tuple[int, int, int], np.ndarray] | None = None
        #: Observers sending a pulse (or just done): position → (last seen powered, facing).
        self._observer_glow: dict[Pos, tuple[float, Direction]] = {}
        self._observer_key: tuple[int, int, int] | None = None
        #: F3 debug screen: the left column comes from the main window (it knows the rates).
        self.debug_left: list[str] = []
        #: SELECT mode: the face handle under the cursor, and drags in progress.
        self.gizmo_hover: Hotspot | None = None
        #: Enter confirms the selection (like GIMP): its boxes are fixed, and drags, turns
        #: and flips then act on its blocks, as a preview until the next Enter.
        self.region_confirmed = False
        self.floating: Floating | None = None  # the blocks' pending move/turn/flip/copy
        self.pending_stack: _StackDrag | None = None  # copies waiting for Enter
        self._floating_mesh: tuple[Any, np.ndarray] | None = None
        self._hidden_cache: tuple[Any, frozenset[Pos]] | None = None
        self._replaced_mesh: tuple[Any, np.ndarray] | None = None
        self._overlays: list[QWidget] = []  # widgets drawn over the bottom (add_overlay)
        #: BUILD: how the block to place is varied (R, H, Shift+H, round 8): quarter turns
        #: clockwise, mirrored axes, upside down (top slabs, pistons facing down, …).
        self.build_turns = 0
        self.build_mirrors: frozenset[str] = frozenset()
        self.build_upside_down = False
        self._shift = False  # Shift held: resize arrows show their stacking look
        self._gizmo_cache: tuple[Any, tuple[np.ndarray, list[Hotspot]]] | None = None
        self._gizmo_outline = np.zeros((0, 7), dtype=np.float32)
        self._pulse = QTimer(self)  # repaints while a selection breathes
        self._pulse.setInterval(FRAME_INTERVAL_MS)
        self._pulse.setTimerType(Qt.TimerType.PreciseTimer)
        #: While the simulation runs: how far into the next tick the wall clock is (the
        #: main window sets it); None when paused.
        self.tick_fraction: Callable[[], float] | None = None
        self._pulse.timeout.connect(self.update)
        self._resize: tuple[Handle, Region, QPoint, np.ndarray] | None = None
        self._move: _MoveDrag | None = None
        self._stack: _StackDrag | None = None
        #: Ctrl+V preview: the prefab follows the cursor until a click places it.
        self.paste_preview: Prefab | None = None
        self._ghost: tuple[np.ndarray, Pos] | None = None  # vertices at offset 0, offset
        self._paste_base = np.zeros((0, 7), dtype=np.float32)
        #: BUILD mode preview: the block as it would be placed, translucent.
        self.build_block: Block | None = None
        self.build_strength = 15
        self._build_ghost: tuple[np.ndarray, Pos] | None = None
        self._build_meshes: dict[BlockState, np.ndarray] = {}
        self._line_ghost: tuple[Any, np.ndarray] | None = None
        self._last_shift = 0.0
        self.build_blocked: Pos | None = None  # target cell where placing is impossible
        self.build_face = Direction.UP  # the face BUILD mode places against
        self.highlight: tuple[Pos, float] | None = None  # flashed block, since when
        #: A block whose coordinates are hovered in a panel (timeline, inspector, …): it
        #: lights up so its place is clear.
        self.located: Pos | None = None
        self.hovered_label: Pos | None = None  # the F3 label under the cursor
        #: The Tab ring while Tab is held: (center, the mode pointed at or None).
        self.ring: tuple[QPoint, str | None] | None = None
        #: Further selections (Shift+drag adds one; the active one is ``region``).
        self.extra_regions: list[Region] = []
        self._moving_shown = False  # the moving-piston mesh holds something
        self._label_rects: list[tuple[QRect, Pos]] = []
        self._label_range: LabelRange | None = None  # F3's label range slider (lazy)
        self._red_meshes: dict[BlockState, np.ndarray] = {}  # blocked previews
        #: BUILD mode line drag: the start cell.
        self._line: Pos | None = None
        self._line_end: Pos | None = None
        self._build_cell: Pos | None = None  # the layer cell the preview was made for
        self._ghost_uploaded: tuple[int, Pos] | None = None
        self.preferences = Preferences.load()
        self.assets, self.atlas = (
            game_textures() if self.preferences.game_textures else (None, None)
        )
        self.world_mesh = ChunkedMesh(Mesher(self.assets, self.atlas))
        self._mesh_revision = -1
        #: Lines of text drawn over the top-left corner (run status, achieved rates).
        self.overlay_text: list[str] = []
        self.frame_rate = RateMeter()
        self.keymap = Keymap()
        self._held_actions: dict[int, str] = {}
        self.set_keymap(keymap if keymap is not None else Keymap())
        self._held: set[str] = set()
        self._trackpad_rise = 0.0  # trackpad up/down travel not yet a whole block
        # Mouse gesture in progress: press point, button, modifiers; drag action once moving.
        self._press: tuple[QPoint, Qt.MouseButton, frozenset[str]] | None = None
        self._drag_action: str | None = None
        self._drag_last: QPoint | None = None
        self._last_mouse: QPoint | None = None
        self._last_frame = time.monotonic()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)  # prefabs dragged from the Prefabs list
        self.setMinimumSize(320, 240)
        #: Smooth camera (Blender-like view transitions): wheel zoom, layer steps and focus
        #: glide to their target pivot and distance instead of jumping.
        self._glide: tuple[np.ndarray, float] | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_camera)
        self._timer.start(16)

    # ------------------------------------------------------------------ setup
    def set_keymap(self, keymap: Keymap) -> None:
        self.keymap = keymap
        self._held_actions = {}
        for action in keymap.actions(HOLD):
            for binding in keymap.bindings(action):
                sequence = QKeySequence(binding)
                if sequence.count():
                    key = sequence[0].key()  # type: ignore[index]
                    self._held_actions[int(key.value)] = action
        self.update()

    def set_mode(self, mode: str) -> None:
        if mode != self.mode:
            self.mode = mode
            self.mode_changed.emit(mode)
            self._update_build_ghost()
        self.update()

    def set_document(self, document: Document) -> None:
        """Show another document: nothing of the old one's view state stays (selections,
        a paste preview, drags, hover, highlights)."""
        if self.paste_preview is not None:
            self.cancel_paste()
        self.document = document
        self.selection = None
        self.region = None
        self.region_confirmed = False
        self.extra_regions = []
        self.floating = None
        self.pending_stack = None
        self.hover = None
        self.highlight = None
        self.located = None
        self.hovered_label = None
        self.ring = None
        self._move = None
        self._resize = None
        self._stack = None
        self._line = None
        self._ghost = None
        self._press = None
        self._drag_action = None
        self._mesh_revision = -1  # the diff against the old world drops what is gone
        self._cover_foreign_textures()
        self.update()

    def _cover_foreign_textures(self) -> None:
        """Blocks of an opened Minecraft world the simulator does not model have textures
        the atlas lacks: rebuild it with them (once per new set of blocks)."""
        if self.assets is None or self.atlas is None:
            return
        foreign = {
            state.block.id
            for state in set(self.document.level.blocks.values())
            if state.block.id not in blocks.REGISTRY
        }
        missing = {
            block_id
            for block_id in foreign
            if not all(self.atlas.has(t) for t in self.assets.block_textures(block_id))
        }
        if not missing:
            return
        self.atlas = Atlas.for_blocks(self.assets, foreign)
        self.world_mesh = ChunkedMesh(Mesher(self.assets, self.atlas))
        self._build_meshes.clear()
        self._red_meshes.clear()
        if self.renderer is not None:
            self.makeCurrent()
            for key in list(self.renderer.chunks):
                self.renderer.remove_chunk(key)
            self._upload_atlas()
            self.doneCurrent()

    def refresh(self) -> None:
        """Call after the world changed (edits or simulation steps)."""
        self._update_build_ghost()
        self.update()

    # ------------------------------------------------------------------ line drag

    # ------------------------------------------------------------------ GL
    def initializeGL(self) -> None:
        # Called again whenever Qt recreates the context (e.g. on re-parenting), so all GPU
        # data must be uploaded again.
        self.renderer = Renderer()
        self._upload_atlas()
        self.world_mesh.reset()
        self._mesh_revision = -1
        context = self.context()
        if context is not None:  # free GPU textures while the context still exists
            context.aboutToBeDestroyed.connect(self.release_gl, Qt.ConnectionType.UniqueConnection)

    @property
    def textures_available(self) -> bool:
        return game_textures()[0] is not None

    def set_game_textures(self, on: bool) -> None:
        """Switch between the game's textured models and the colored box models."""
        self.assets, self.atlas = game_textures() if on else (None, None)
        self.world_mesh = ChunkedMesh(Mesher(self.assets, self.atlas))
        self._build_meshes.clear()
        self._red_meshes.clear()
        self._line_ghost = None
        self._mesh_revision = -1
        if self.renderer is not None:
            self.makeCurrent()
            for key in list(self.renderer.chunks):
                self.renderer.remove_chunk(key)
            self._upload_atlas()
            self.doneCurrent()
        self._update_build_ghost()
        self.update()

    def _horizon_ndc(self, mvp: np.ndarray) -> float:
        """Screen height (normalized device coordinates) of the horizon: a far point
        straight ahead at eye height."""
        eye = np.asarray(self.camera.position, dtype=float)
        far = eye + self.camera.horizontal_forward() * 900.0
        clip = mvp @ np.array([far[0], far[1], far[2], 1.0])
        return float(clip[1] / clip[3]) if clip[3] > 1e-6 else -1.0

    def _upload_atlas(self) -> None:
        """The block atlas and the ground's texture tile (context current)."""
        assert self.renderer is not None
        atlas = self.atlas
        self.renderer.set_atlas(atlas.image() if atlas is not None else None)
        clouds = self.assets.texture_bytes(CLOUD_TEXTURE) if self.assets is not None else None
        self.renderer.set_clouds(QImage.fromData(clouds) if clouds else None)
        if atlas is None:
            self.renderer.set_ground(None, (0.0, 0.0, 0.0))
            return
        average = atlas.tile(GROUND_TEXTURE)[..., :3].reshape(-1, 3).mean(axis=0) / 255.0
        self.renderer.set_ground(atlas.rect(GROUND_TEXTURE), tuple(float(c) for c in average))

    def release_gl(self) -> None:
        """Free the GPU textures with the context current (on close, and before Qt
        destroys the context); later, nothing is left for a destructor to complain about."""
        if self.renderer is not None and self.isValid():
            self.makeCurrent()
            self.renderer.set_atlas(None)
            self.renderer.set_clouds(None)
            self.doneCurrent()

    # ------------------------------------------------------------------ overlays
    def add_overlay(self, widget: QWidget) -> None:
        """A widget drawn over the bottom of the view, centered (the BUILD hotbar); it
        moves when the view or the widget changes size, without resizing anything."""
        widget.setParent(self)
        self._overlays.append(widget)
        widget.installEventFilter(self)
        self.place_overlays()

    def place_overlays(self) -> None:
        for widget in self._overlays:
            size = widget.sizeHint().expandedTo(widget.minimumSizeHint())
            widget.resize(size)
            widget.move((self.width() - size.width()) // 2, self.height() - size.height() - 6)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched in self._overlays and event.type() in (
            QEvent.Type.LayoutRequest,
            QEvent.Type.Show,
        ):
            self.place_overlays()
            self.update()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event: Any) -> None:
        if self._label_range is not None:
            self._label_range.place()
        super().resizeEvent(event)
        self.place_overlays()

    def _overlay_top(self, left: int, right: int) -> int | None:
        """The top of a visible overlay overlapping the columns ``left``..``right``."""
        tops = [
            w.y()
            for w in self._overlays
            if w.isVisible() and w.x() < right and w.x() + w.width() > left
        ]
        return min(tops) if tops else None

    @property
    def lens(self) -> float:
        """How much the camera's field of view narrows for this viewport's height (see
        ``FOV_SCREEN_SHARE``): resizing crops or widens the view, it never rescales it."""
        screen = self.screen()
        reference = screen.availableGeometry().height() if screen is not None else 0
        if reference <= 0:
            return 1.0
        return reference * FOV_SCREEN_SHARE / max(self.height(), 1)

    def resizeGL(self, width: int, height: int) -> None:
        # The same mouse position now casts a different ray: retarget the previews.
        self._update_build_ghost()
        self._update_paste_ghost()

    def paintGL(self) -> None:
        renderer = self.renderer
        if renderer is None:
            return
        # While running, a heavy tick runs in parts: keep showing the last complete tick.
        # Stepping event by event (paused) shows every step.
        at_boundary = self.document.can_edit or self.tick_fraction is None
        if self._mesh_revision != self.document.revision and at_boundary:
            # Only chunks whose blocks (or neighbors) changed are rebuilt and re-uploaded.
            chunks = self.world_mesh.chunks
            for key in self.world_mesh.update(self.document.level):
                mesh = chunks.get(key)
                if mesh is None:
                    renderer.remove_chunk(key)
                else:
                    renderer.set_chunk(key, mesh.opaque, mesh.translucent, mesh.solid)
            for stale in [
                stale for stale in renderer.chunks if stale not in chunks and stale != MOVING_KEY
            ]:
                renderer.remove_chunk(stale)
            self._mesh_revision = self.document.revision
        hidden = self._hidden_blocks()
        if hidden != self.world_mesh.hidden:
            # A pending move shows its blocks only where they go (owner, 2026-10-14).
            chunks = self.world_mesh.chunks
            for key in self.world_mesh.hide(self.document.level, hidden):
                mesh = chunks.get(key)
                if mesh is None:
                    renderer.remove_chunk(key)
                else:
                    renderer.set_chunk(key, mesh.opaque, mesh.translucent, mesh.solid)
        partial = self.tick_fraction() if self.tick_fraction is not None else 1.0
        world = self.world_mesh
        if (world.has_moving or self._moving_shown) and at_boundary:
            # Moving pistons: one small mesh of their own, every frame while they move.
            world.mesher.partial_tick = partial
            moving = world.moving_mesh(self.document.level)
            renderer.set_chunk(MOVING_KEY, moving.opaque, moving.translucent, moving.solid)
            self._moving_shown = world.has_moving
        renderer.upload_lines(self._overlay_lines())
        renderer.upload_overlay(self._overlay_triangles())
        renderer.upload_outline(self._outline_triangles())
        renderer.upload_volume(
            np.vstack(
                [
                    self._selection_body(),
                    self._replaced_body(),
                    self._highlight_body(),
                    self._power_body(),
                    self._heat_body(),
                    self._observer_body(),
                    self._pivot_shadow(),
                ]
            )
        )
        # The selection breathes: keep repainting while there is one.
        # Frames at ~60 per second while anything moves: the breathing selection, a
        # running simulation (moving pistons between ticks), drifting clouds.
        animating = (
            self.region is not None
            or self.highlight is not None
            or self.located is not None
            or bool(self._observer_glow)
            or self.tick_fraction is not None
            or (self.preferences.scenery and self.window().isActiveWindow())
        )
        if animating and not self._pulse.isActive():
            self._pulse.start()
        elif not animating and self._pulse.isActive():
            self._pulse.stop()
        renderer.upload_top_lines(self._pivot_lines())
        self._upload_ghost(renderer)
        ratio = self.devicePixelRatioF()
        width, height = int(self.width() * ratio), int(self.height() * ratio)
        aspect = max(width, 1) / max(height, 1)
        mvp = self.camera.projection_matrix(aspect, lens=self.lens) @ self.camera.view_matrix()
        prefs = self.preferences
        renderer.draw(
            mvp,
            width,
            height,
            BACKGROUND,
            xray=self.xray,
            building_alpha=prefs.xray_building_alpha,
            circuit_alpha=prefs.xray_circuit_alpha,
            eye=tuple(float(v) for v in self.camera.position),  # type: ignore[arg-type]
            fog=(40.0 + self.camera.distance, 160.0 + 2 * self.camera.distance),
            horizon=self._horizon_ndc(mvp) if prefs.scenery else -1.0,
            scenery=prefs.scenery,
            ghost_alpha=self.ghost_alpha(),
        )
        self.frame_rate.record(time.monotonic())
        self._draw_overlays()

    # ------------------------------------------------------------------ keyboard
    def _track_shift(self, held: bool) -> None:
        if held != self._shift:
            self._shift = held
            self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Shift and not event.isAutoRepeat():
            now = time.monotonic()
            if now - self._last_shift < DOUBLE_SHIFT_SECONDS:
                self._last_shift = 0.0
                self.search_requested.emit()
            else:
                self._last_shift = now
        elif event.key() != Qt.Key.Key_Shift:
            self._last_shift = 0.0
        if event.key() == Qt.Key.Key_Shift:
            self._track_shift(True)
        action = self._held_actions.get(event.key())
        if action == "mode.ring":
            if not event.isAutoRepeat() and self.ring is None:
                center = self._last_mouse or QPoint(self.width() // 2, self.height() // 2)
                self.ring = (center, None)
                self.update()
            return
        if action is not None and not event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
            self._held.add(action)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Shift:
            self._track_shift(False)
        action = self._held_actions.get(event.key())
        if action == "mode.ring":
            if not event.isAutoRepeat() and self.ring is not None:
                chosen = self.ring[1]
                self.ring = None
                self.update()
                if chosen is not None:
                    self.mode_requested.emit(chosen)
            return
        if action is not None and not event.isAutoRepeat():
            self._held.discard(action)
            return
        super().keyReleaseEvent(event)

    def focusNextPrevChild(self, next: bool) -> bool:  # noqa: A002 - Qt's name
        """Tab is the mode ring here, not focus navigation."""
        return False

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self._held.clear()

    def glide_to(self, pivot: np.ndarray | None = None, distance: float | None = None) -> None:
        """Ease the camera towards a new pivot and/or distance over a few frames."""
        current_pivot, current_distance = self._glide or (
            np.asarray(self.camera.pivot, dtype=float),
            self.camera.distance,
        )
        target_pivot = np.asarray(pivot if pivot is not None else current_pivot, dtype=float)
        target_distance = current_distance if distance is None else distance
        target_distance = max(MIN_DISTANCE, min(MAX_DISTANCE, target_distance))
        self._glide = (target_pivot, target_distance)
        self._camera_moved()  # the working layer follows the target at once

    def _advance_glide(self, dt: float) -> bool:
        if self._glide is None:
            return False
        target_pivot, target_distance = self._glide
        alpha = 1.0 - math.exp(-dt / GLIDE_SECONDS)
        pivot = np.asarray(self.camera.pivot, dtype=float)
        pivot = pivot + (target_pivot - pivot) * alpha
        distance = self.camera.distance + (target_distance - self.camera.distance) * alpha
        if (
            float(np.abs(target_pivot - pivot).max()) < 1e-3
            and abs(target_distance - distance) < 1e-3
        ):
            pivot, distance = target_pivot, target_distance
            self._glide = None
        self.camera.pivot = pivot
        self.camera.distance = distance
        return True

    def _tick_camera(self) -> None:
        now = time.monotonic()
        dt = min(now - self._last_frame, 0.1)
        self._last_frame = now
        if self._advance_glide(dt):
            self._camera_moved()
        held = self._held
        if not held:
            return
        speed = max(4.0, self.camera.distance * 0.8) * dt
        forward = ("camera.forward" in held) - ("camera.back" in held)
        strafe = ("camera.right" in held) - ("camera.left" in held)
        up = ("camera.up" in held) - ("camera.down" in held)
        before = np.asarray(self.camera.pivot, dtype=float)
        if forward or strafe:
            self.camera.pan(forward * speed, strafe * speed)
        if up:
            self.camera.raise_pivot(up * speed)
        self._shift_glide(np.asarray(self.camera.pivot, dtype=float) - before)
        if forward or strafe or up:
            self._camera_moved()

    # ------------------------------------------------------------------ mouse
    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        if self._press is not None:
            return  # one gesture at a time
        point = event.position().toPoint()
        self._press = (point, event.button(), _modifier_names(event.modifiers()))
        self._drag_action = None
        self._drag_last = point

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        point = event.position().toPoint()
        self._last_mouse = point
        if self.ring is not None:
            chosen = self.ring_mode_at(point)
            if chosen != self.ring[1]:
                self.ring = (self.ring[0], chosen)
                self.update()
            return
        self._track_shift(bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
        self._update_hover(point)
        if self.paste_preview is not None:
            self._update_paste_ghost()
        if self._press is None:
            return
        start, button, modifiers = self._press
        if self._drag_action is None:
            if (point - start).manhattanLength() <= DRAG_THRESHOLD:
                return
            name = _BUTTON_NAMES.get(button)
            action = self.keymap.mouse_action(self.mode, modifiers, name, "Drag")
            self._drag_action = action or ""
            if self._drag_action == "build.line" and not self._begin_line(start):
                self._drag_action = ""
            if self._drag_action in ("select.box", "select.copy_drag"):
                self._begin_select_drag(start, copy=self._drag_action == "select.copy_drag")
            elif self._drag_action == "select.stack":
                self._begin_stack(start)
        last = self._drag_last or point
        self._drag(self._drag_action, point.x() - last.x(), point.y() - last.y())
        self._drag_last = point

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._press is None or event.button() != self._press[1]:
            return
        _, button, modifiers = self._press
        drag_action = self._drag_action
        self._press = None
        self._drag_action = None
        if drag_action is None:
            self._update_hover(event.position().toPoint())
            spot = self.gizmo_hover
            if self.paste_preview is not None:
                self._paste_click(button)
            elif button == Qt.MouseButton.LeftButton and spot is not None:
                if spot.kind == "rotate":
                    self.transform_requested.emit(1 if spot.data == 1 else 3, None)
                elif spot.kind == "flip":
                    self.transform_requested.emit(0, spot.data)
            else:
                name = _BUTTON_NAMES.get(button)
                action = self.keymap.mouse_action(self.mode, modifiers, name, "Click")
                if action is not None:
                    self._click(action)
        elif drag_action in ("select.box", "select.copy_drag"):
            self._end_select_drag()
        elif drag_action == "select.stack":
            self._end_stack()
        elif drag_action == "build.line":
            self._end_line()
        self.update()

    # ------------------------------------------------------------------ dropped prefabs
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """A prefab dragged in from the list: its paste preview follows the cursor."""
        data = event.mimeData()
        if not data.hasFormat(PREFAB_MIME):
            event.ignore()
            return
        event.acceptProposedAction()
        self._last_mouse = event.position().toPoint()
        self.prefab_dragged.emit(bytes(data.data(PREFAB_MIME).data()).decode())

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if self.paste_preview is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self._last_mouse = event.position().toPoint()
        self._update_paste_ghost()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        if self.paste_preview is not None:
            self.cancel_paste()

    def dropEvent(self, event: QDropEvent) -> None:
        """Dropped: a pending selection where the preview was (Enter places it)."""
        self._last_mouse = event.position().toPoint()
        target = self.paste_target()
        data = event.mimeData()
        if self.paste_preview is None or target is None or not data.hasFormat(PREFAB_MIME):
            event.ignore()
            return
        event.acceptProposedAction()
        self.cancel_paste()
        self.prefab_dropped.emit(bytes(data.data(PREFAB_MIME).data()).decode(), target)
        self.setFocus()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.preferences.trackpad_navigation and _from_trackpad(event):
            self._trackpad_scroll(event)
            return
        delta = event.angleDelta()
        steps = (delta.y() or delta.x()) / 120.0  # some systems turn Shift+wheel sideways
        if not steps:
            return
        if self._move is not None:  # while dragging a selection, the wheel lifts it
            self._move.lift += 1 if steps > 0 else -1
            self._apply_move()
            return
        modifiers = _modifier_names(event.modifiers())
        mode = "paste" if self.paste_preview is not None else self.mode
        action = self.keymap.mouse_action(mode, modifiers, None, "Wheel")
        target_pivot, target_distance = self._glide or (
            np.asarray(self.camera.pivot, dtype=float),
            self.camera.distance,
        )
        if action in ("camera.zoom", "paste.zoom", "build.zoom"):
            self.glide_to(distance=target_distance * ZOOM_PER_NOTCH**-steps)
        elif action in ("camera.vertical", "paste.layer", "build.layer"):
            # One block per notch; the build/paste layer follows the target at once.
            self.glide_to(pivot=target_pivot + np.array([0.0, steps, 0.0]))

    def _drag(self, action: str, dx: int, dy: int) -> None:
        camera = self.camera
        if action == "camera.orbit":
            camera.orbit(dx * ORBIT_DEGREES_PER_PIXEL, dy * ORBIT_DEGREES_PER_PIXEL)
        elif action == "camera.pan":
            # The world follows the mouse: blocks per pixel at the pivot's distance.
            scale = 2 * camera.distance * math.tan(math.radians(camera.fov) / 2)
            scale /= max(self.height(), 1) * self.lens
            before = np.asarray(camera.pivot, dtype=float)
            camera.pan(dy * scale, -dx * scale)
            self._shift_glide(np.asarray(camera.pivot, dtype=float) - before)
        elif action in ("select.box", "select.copy_drag"):
            self._continue_select_drag()
            return
        elif action == "select.stack":
            self._continue_stack()
            return
        elif action == "build.line":
            if self._drag_last is not None:
                self._continue_line(self._drag_last + QPoint(dx, dy))
            return
        else:
            return
        self._camera_moved()

    def _click(self, action: str) -> None:
        hit = self.hover
        if action in ("animate.pulse", "animate.remove"):
            if hit is not None:
                signal = (
                    self.pulse_requested
                    if action == "animate.pulse"
                    else (self.pulse_remove_requested)
                )
                signal.emit(hit.pos)
            return
        if action == "normal.inspect":
            self.selection = hit.pos if hit else None
            self.select_requested.emit(self.selection)
        elif action in ("select.block", "select.extend") and self.region_confirmed:
            return  # a confirmed selection keeps its boxes
        elif action == "select.block" and self._click_box(hit) is not None:
            self.activate_region(self._click_box(hit))  # type: ignore[arg-type]
            self.region_changed.emit(self.region)
        elif action == "select.block":
            self._region_anchor = hit.pos if hit else None
            self.region = Region.from_corners(hit.pos, hit.pos) if hit else None
            self.region_changed.emit(self.region)
        elif action == "select.extend" and hit is not None:
            anchor = self._region_anchor or hit.pos
            self._region_anchor = anchor
            self.region = Region.from_corners(anchor, hit.pos)
            self.region_changed.emit(self.region)
        elif action == "build.place":
            target = self.build_target()
            if target is not None:
                self.place_requested.emit(target)
        elif hit is None:
            return
        elif action == "pick":
            self.pick_requested.emit(hit.pos)
        elif action in ("normal.use", "build.use"):
            self.use_requested.emit(hit.pos)
        elif action == "build.break":
            self.break_requested.emit(hit.pos)

        elif action in ("build.rotate", "build.rotate_back"):
            self.rotate_requested.emit(hit.pos, 1 if action == "build.rotate" else 3)

    # ------------------------------------------------------------------ selections
    def _click_box(self, hit: Hit | None) -> int | None:
        """A click inside one of the further boxes (not the active one): its index."""
        if self._last_mouse is None or not self.extra_regions:
            return None
        origin, direction = self._ray(self._last_mouse)
        grab = _grab_any(self.all_regions(), origin, direction, hit)
        if grab is None or grab[0] == len(self.extra_regions):
            return None
        return grab[0]

    # ------------------------------------------------------------------ paste preview

    def _shift_glide(self, delta: np.ndarray) -> None:
        """A direct camera move while gliding moves the glide's target along."""
        if self._glide is not None and np.any(delta):
            self._glide = (self._glide[0] + delta, self._glide[1])

    # ------------------------------------------------------------------ targeting
    def _ray(self, point: QPoint) -> tuple[np.ndarray, np.ndarray]:
        width, height = max(self.width(), 1), max(self.height(), 1)
        ndc_x = 2.0 * point.x() / width - 1.0
        ndc_y = 1.0 - 2.0 * point.y() / height
        return self.camera.ray_through(ndc_x, ndc_y, width / height, self.lens)

    def _screen_vector(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """On-screen vector (pixels) from world point ``a`` to ``b``."""
        width, height = max(self.width(), 1), max(self.height(), 1)
        mvp = (
            self.camera.projection_matrix(width / height, lens=self.lens)
            @ self.camera.view_matrix()
        )
        points = []
        for world in (a, b):
            clip = mvp @ np.array([*world, 1.0])
            w = clip[3] if abs(clip[3]) > 1e-9 else 1e-9
            points.append(np.array([(clip[0] / w + 1) / 2 * width, (1 - clip[1] / w) / 2 * height]))
        return points[1] - points[0]

    def _pick_at(self, point: QPoint) -> Hit | None:
        """The block under the cursor, as far as the view reaches: at least the fixed reach,
        and well past the pivot however far out the camera is (F from far away)."""
        origin, direction = self._ray(point)
        self._hover_direction = direction
        reach = max(PICK_REACH, 2.0 * self.camera.distance + PICK_REACH)
        return pick(self.document.level, origin, direction, reach)

    def _update_hover(self, point: QPoint) -> None:
        label = self.label_at(point) if self.show_info else None
        if label != self.hovered_label:
            self.hovered_label = label
            self.update()
        hit = self._pick_at(point)
        spot = self._gizmo_at(point) if self._press is None else self.gizmo_hover
        if spot != self.gizmo_hover:
            self.gizmo_hover = spot
            self.gizmo_hover_changed.emit(spot)
            self.update()
        if hit != self.hover:
            self.hover = hit
            self.hover_changed.emit(hit)
            self._update_paste_ghost()
            self.update()
        self._update_build_ghost()  # orientation follows the cursor ray even on one cell

    def _camera_moved(self) -> None:
        if self._last_mouse is not None:
            self._update_hover(self._last_mouse)
        self._update_paste_ghost()
        self._update_build_ghost()
        self.update()

    # ------------------------------------------------------------------ helpers
    def look_at(self, target: Pos) -> None:
        self.glide_to(pivot=np.array(target, dtype=float) + 0.5)

    # ------------------------------------------------------------------ trackpad
    def _trackpad_scroll(self, event: QWheelEvent) -> None:
        """Two-finger scrolling (``trackpad_navigation``): the fingers drag the view like
        a middle-button drag; with Shift it pans, Ctrl (⌘) zooms, Alt (⌥) moves the camera
        (and the build layer) up or down."""
        if event.phase() == Qt.ScrollPhase.ScrollMomentum:
            return  # no coasting after the fingers lift: the view stays where it was put
        pixels = event.pixelDelta()
        dx, dy = (
            (pixels.x(), pixels.y())
            if not pixels.isNull()
            else (
                event.angleDelta().x() / 8,
                event.angleDelta().y() / 8,
            )
        )
        modifiers = _modifier_names(event.modifiers())
        if self._move is not None:  # dragging a selection: lift it, block by block
            self._trackpad_rise += dy / TRACKPAD_PIXELS_PER_BLOCK
            whole = int(self._trackpad_rise)
            if whole:
                self._trackpad_rise -= whole
                self._move.lift += whole
                self._apply_move()
            return
        if "Ctrl" in modifiers:
            self.zoom_by(dy / TRACKPAD_PIXELS_PER_NOTCH)
        elif "Alt" in modifiers:
            self._trackpad_rise += dy / TRACKPAD_PIXELS_PER_BLOCK
            whole = int(self._trackpad_rise)
            if whole:
                self._trackpad_rise -= whole
                target = (
                    self._glide[0] if self._glide else np.asarray(self.camera.pivot, dtype=float)
                )
                self.glide_to(pivot=target + np.array([0.0, float(whole), 0.0]))
        elif "Shift" in modifiers:
            self._drag("camera.pan", int(dx), int(dy))
        else:
            self._drag("camera.orbit", int(dx), int(dy))
        self.update()

    def zoom_by(self, notches: float) -> None:
        """Zoom in (positive) or out like that many wheel notches."""
        distance = self._glide[1] if self._glide else self.camera.distance
        self.glide_to(distance=distance * ZOOM_PER_NOTCH**-notches)

    def event(self, event: QEvent) -> bool:
        """Trackpad gestures (macOS): pinch zooms, two-finger rotation turns the view,
        a smart-zoom double tap focuses the block under the cursor."""
        if event.type() == QEvent.Type.NativeGesture and isinstance(event, QNativeGestureEvent):
            kind = event.gestureType()
            if kind == Qt.NativeGestureType.ZoomNativeGesture:
                distance = self._glide[1] if self._glide else self.camera.distance
                self.glide_to(distance=distance / max(0.2, 1.0 + event.value()))
                return True
            if kind == Qt.NativeGestureType.RotateNativeGesture:
                self.camera.orbit(-event.value(), 0.0)
                self._camera_moved()
                self.update()
                return True
            if kind == Qt.NativeGestureType.SmartZoomNativeGesture:
                self.focus_hover()
                return True
        return super().event(event)

    def focus_hover(self) -> bool:
        """Move the pivot to the center of the block under the cursor (or of the hovered
        F3 label's block)."""
        if self.show_info and self.hovered_label is not None:
            self.look_at(self.hovered_label)
            return True
        if self.hover is None:
            return False
        self.look_at(self.hover.pos)
        return True

    def player_view(self) -> tuple[float, float]:
        """Yaw and pitch of a player looking at the targeted block from the camera."""
        if self._hover_direction is not None:
            return Camera.angles_of(self._hover_direction)
        return self.camera.yaw, self.camera.pitch


__all__ = [
    "ANIMATE",
    "BODY_ALPHA",
    "BODY_PULSE",
    "BUILD",
    "Direction",
    "GRID_ALPHA",
    "MODE_COLORS",
    "NORMAL",
    "PULSE_SECONDS",
    "SELECT",
    "Viewport",
    "_layer_grid",
    "game_textures",
]
