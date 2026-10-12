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
from functools import lru_cache
from typing import Any

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFocusEvent,
    QImage,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QNativeGestureEvent,
    QPainter,
    QWheelEvent,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor import sources
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document import Document
from redsim.editor.placement import PlaceRequest, placement_state
from redsim.ui import theme
from redsim.ui.assets import Assets
from redsim.ui.atlas import Atlas
from redsim.ui.camera import MAX_DISTANCE, MIN_DISTANCE, Camera
from redsim.ui.debug_screen import block_lines
from redsim.ui.geometry import (
    ChunkedMesh,
    Hit,
    Mesher,
    block_outline,
    box_lines,
    ghost_mesh,
    pick,
    ray_box,
    solid_box,
    thick_edges,
)
from redsim.ui.gizmos import Hotspot, box_faces, pick_hotspot, selection_gizmos
from redsim.ui.keymap import HOLD, Keymap
from redsim.ui.names import block_name
from redsim.ui.pacing import RateMeter
from redsim.ui.preferences import Preferences
from redsim.ui.renderer import CLOUD_TEXTURE, GROUND_TEXTURE, Renderer
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
from redsim.world import blocks
from redsim.world.block import Block, BlockState
from redsim.world.properties import POWER
from redsim.world.rotation import mirror_state, rotate_state, upside_down

BACKGROUND = (0.53, 0.70, 0.86, 1.0)
ORBIT_DEGREES_PER_PIXEL = 0.3
#: Trackpad scrolling: pixels of finger travel per zoom notch and per block up/down.
TRACKPAD_PIXELS_PER_NOTCH = 40.0
TRACKPAD_PIXELS_PER_BLOCK = 30.0
ZOOM_PER_NOTCH = 1.15
DRAG_THRESHOLD = 4
#: The build preview is this much smaller than a block (no z-fighting with neighbors).
GHOST_SHRINK = 0.99
#: Longest line placed by one drag.
MAX_LINE = 64
DOUBLE_SHIFT_SECONDS = 0.35
#: Time constant of the smooth camera (seconds to cover ~63 % of the way).
GLIDE_SECONDS = 0.07
PIVOT_COLOR = (1.0, 0.35, 0.05, 1.0)
#: The selection's fill: opacity, how far it breathes, and one breath in seconds.
BODY_ALPHA = 0.2
BODY_PULSE = 0.06
PULSE_SECONDS = 1.8
SELECTION_COLOR = (0.0, 0.85, 0.95, 1.0)
LOCKED_COLOR = (1.0, 0.62, 0.15, 1.0)
TARGET_COLOR = (1.0, 1.0, 1.0, 1.0)

NORMAL, BUILD, SELECT = "normal", "build", "select"
INFO_LABEL_LIMIT = 300
INFO_COLORS = {
    "wire": QColor(170, 20, 20, 210),
    "source": QColor(120, 60, 160, 220),
    "comparator": QColor(40, 40, 40, 220),
}
PASTE_COLOR = QColor(140, 60, 170)
MODE_COLORS = {
    NORMAL: QColor(60, 100, 160),
    BUILD: QColor(50, 140, 60),
    SELECT: QColor(200, 115, 25),
}
#: Short verbs for the mode badge.
CLICK_VERBS = {
    "normal.inspect": "inspect",
    "normal.use": "use",
    "build.place": "place",
    "build.line": "line",
    "build.rotate": "turn",
    "build.break": "break",
    "select.block": "select",
    "select.box": "box / move / resize",
    "select.copy_drag": "copy",
    "select.stack": "stack",
    "select.extend": "extend",
    "pick": "pick",
}

_BUTTON_NAMES = {
    Qt.MouseButton.LeftButton: "Left",
    Qt.MouseButton.RightButton: "Right",
    Qt.MouseButton.MiddleButton: "Middle",
}


def _from_trackpad(event: QWheelEvent) -> bool:
    """Scrolling with fingers (it has scroll phases or pixel deltas), not a wheel."""
    return event.phase() != Qt.ScrollPhase.NoScrollPhase or not event.pixelDelta().isNull()


def _modifier_names(modifiers: Qt.KeyboardModifier) -> frozenset[str]:
    names = set()
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        names.add("Ctrl")
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        names.add("Shift")
    if modifiers & Qt.KeyboardModifier.AltModifier:
        names.add("Alt")
    if modifiers & Qt.KeyboardModifier.MetaModifier:
        names.add("Meta")
    return frozenset(names)


@lru_cache(maxsize=1)
def game_textures() -> tuple[Assets | None, Atlas | None]:
    """The game's block models and a texture atlas, if the client jar is available."""
    assets = Assets.find()
    if assets is None:
        return None, None
    return assets, Atlas.for_blocks(assets)


#: The layer grid around a build target or paste: reach (blocks) and strongest alpha.
GRID_REACH = 5
GRID_ALPHA = 0.8


def _layer_grid(box: Region) -> np.ndarray:
    """Grid lines on the working plane around ``box``, in one-block segments that fade
    out with the distance to the box, so the grid reads as a height guide and not as
    outlines of the blocks below it."""
    y = box.low[1] + 0.01  # just above the layer's floor: no z-fighting with block tops
    lo_x, hi_x = box.low[0], box.high[0] + 1
    lo_z, hi_z = box.low[2], box.high[2] + 1

    def alpha(x: float, z: float) -> float:
        dx = max(lo_x - x, 0.0, x - hi_x)
        dz = max(lo_z - z, 0.0, z - hi_z)
        fade = max(0.0, 1.0 - math.hypot(dx, dz) / GRID_REACH)
        return GRID_ALPHA * fade

    xs = range(lo_x - GRID_REACH, hi_x + GRID_REACH + 1)
    zs = range(lo_z - GRID_REACH, hi_z + GRID_REACH + 1)
    segments = [((x, z), (x, z + 1)) for x in xs for z in zs[:-1]]  # lines along z
    segments += [((x, z), (x + 1, z)) for z in zs for x in xs[:-1]]  # lines along x
    rows = []
    for p, q in segments:
        ap, aq = alpha(*p), alpha(*q)
        if ap > 0.0 or aq > 0.0:
            rows += [(p[0], y, p[1], 1.0, 1.0, 1.0, ap), (q[0], y, q[1], 1.0, 1.0, 1.0, aq)]
    return np.array(rows, dtype=np.float32).reshape(-1, 7)


class Viewport(QOpenGLWidget):
    hover_changed = Signal(object)  # Hit | None
    place_requested = Signal(object)  # Pos: a cell on the working layer
    line_requested = Signal(object)  # [Pos]: a straight line on the working layer
    rotate_requested = Signal(object, int)  # Pos, quarter turns
    use_requested = Signal(object)  # Pos
    break_requested = Signal(object)  # Pos
    pick_requested = Signal(object)  # Pos
    select_requested = Signal(object)  # Pos | None (inspector selection)
    region_changed = Signal(object)  # Region | None
    region_move_requested = Signal(object, object, bool)  # Region, offset, copy
    region_stack_requested = Signal(object, object, int)  # Region, step, count
    transform_requested = Signal(int, object)  # quarter turns, mirror axis | None
    gizmo_hover_changed = Signal(object)  # Hotspot | None
    paste_requested = Signal(object)  # Pos (minimum corner)
    mode_changed = Signal(str)
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
        #: F3 debug screen: the left column comes from the main window (it knows the rates).
        self.debug_left: list[str] = []
        #: SELECT mode: the face handle under the cursor, and drags in progress.
        self.gizmo_hover: Hotspot | None = None
        self.region_locked = False  # Enter: clicks can no longer replace the selection
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
        self._pulse.setInterval(33)
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
        self.document = document
        self.selection = None
        self.region = None
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

    def set_build_block(self, block: Block, strength: int) -> None:
        if block is not self.build_block:  # a new block starts plain
            self.build_turns, self.build_mirrors, self.build_upside_down = 0, frozenset(), False
        self.build_block = block
        self.build_strength = strength
        self._update_build_ghost()

    def _update_build_ghost(self) -> None:
        """Preview of the block(s) to place: oriented like the placement would orient them
        (cursor-ray yaw/pitch, wire connections, source setup), or a red outline. While a
        line is dragged, the whole line."""
        ghost, blocked = None, None
        block = self.build_block
        busy = self.paste_preview is not None or self._move is not None
        if self._line is not None and block is not None:
            start = self._line
            cells = self.line_cells()
            request = PlaceRequest(Direction.UP, *self.player_view())
            states = [(cell, self._placed_state(block, request, cell)) for cell in cells]
            parts = tuple(
                ((c[0] - start[0], c[1] - start[1], c[2] - start[2]), st)
                for c, st in states
                if st is not None
            )
            if parts:
                ghost = (self._combined_ghost(parts), start)
        elif self.mode == BUILD and block is not None and not busy:
            target = self.build_target()
            self._build_cell = target
            request = PlaceRequest(Direction.UP, *self.player_view())
            state = None if target is None else self._placed_state(block, request, target)
            if target is not None and state is None:
                blocked = target
            elif target is not None and state is not None:
                ghost = (self._single_ghost(state), target)
        if _ghost_key(ghost) != _ghost_key(self._build_ghost) or blocked != self.build_blocked:
            self._build_ghost, self.build_blocked = ghost, blocked
            self.update()

    def _placed_state(self, block: Block, request: PlaceRequest, target: Pos) -> BlockState | None:
        level = self.document.level
        if not level.get_block_state(target).is_air:
            return None
        state = placement_state(block, request, level, target)
        if state is not None:
            state = self.vary_state(state)
        kind = sources.SOURCE_BLOCKS.get(block.id)
        if state is not None and kind is not None:
            text, _ = sources.source_setblock(kind, self.build_strength, state)
            state = blocks.parse_state(text)
        if state is None or not state.can_survive(level, target):
            return None
        return state

    def _single_ghost(self, state: BlockState) -> np.ndarray:
        vertices = self._build_meshes.get(state)
        if vertices is None:
            vertices = ghost_mesh({(0, 0, 0): state}, 0.5, self.world_mesh.mesher)
            # Shrink it a little around the block center, so none of its faces lies in the
            # plane of a neighbor's face (z-fighting flicker, e.g. wire on a block).
            vertices[:, :3] = 0.5 + (vertices[:, :3] - 0.5) * GHOST_SHRINK
            self._build_meshes[state] = vertices
        return vertices

    def _combined_ghost(self, parts: tuple[tuple[Pos, BlockState], ...]) -> np.ndarray:
        cached = self._line_ghost
        if cached is not None and cached[0] == parts:
            return cached[1]
        pieces = []
        for rel, state in parts:
            vertices = self._single_ghost(state).copy()
            vertices[:, :3] += np.array(rel, dtype=np.float32)
            pieces.append(vertices)
        combined = np.vstack(pieces)
        self._line_ghost = (parts, combined)
        return combined

    # ------------------------------------------------------------------ line drag
    def line_cells(self) -> list[Pos]:
        """The cells of the dragged line: from the start along the axis the cursor moved
        most on (x or z, on the start's layer), at most ``MAX_LINE`` long."""
        if self._line is None:
            return []
        start = self._line
        end = self._line_end or start
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
        """BUILD mode places on the working layer (the camera pivot's height; the wheel
        moves it), in the cell under the cursor, like Trackmania's editor."""
        point = point if point is not None else self._last_mouse
        if point is None:
            return None
        origin, direction = self._ray(point)
        self._hover_direction = direction
        return paste_origin(origin, direction, self.working_height(), (1, 1, 1))

    def _begin_line(self, point: QPoint) -> bool:
        start = self.build_target(point)
        if start is None or self.build_block is None:
            return False
        self._line = start
        self._line_end = None
        return True

    def _continue_line(self, point: QPoint) -> None:
        if self._line is None:
            return
        end = self.build_target(point)
        if end is not None and end != self._line_end:
            self._line_end = end
            self._update_build_ghost()

    def _end_line(self) -> None:
        if self._line is None:
            return
        cells = self.line_cells()
        self._line, self._line_end = None, None
        self.line_requested.emit(cells)
        self._update_build_ghost()

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

    def resizeGL(self, width: int, height: int) -> None:
        # The same mouse position now casts a different ray: retarget the previews.
        self._update_build_ghost()
        self._update_paste_ghost()

    def paintGL(self) -> None:
        renderer = self.renderer
        if renderer is None:
            return
        if self._mesh_revision != self.document.revision:
            # Only chunks whose blocks (or neighbors) changed are rebuilt and re-uploaded.
            chunks = self.world_mesh.chunks
            for key in self.world_mesh.update(self.document.level):
                mesh = chunks.get(key)
                if mesh is None:
                    renderer.remove_chunk(key)
                else:
                    renderer.set_chunk(key, mesh.opaque, mesh.translucent, mesh.solid)
            for stale in [stale for stale in renderer.chunks if stale not in chunks]:
                renderer.remove_chunk(stale)
            self._mesh_revision = self.document.revision
        renderer.upload_lines(self._overlay_lines())
        renderer.upload_overlay(self._overlay_triangles())
        renderer.upload_outline(self._outline_triangles())
        renderer.upload_volume(np.vstack([self._selection_body(), self._pivot_shadow()]))
        # The selection breathes: keep repainting while there is one.
        if self.region is not None and not self._pulse.isActive():
            self._pulse.start()
        elif self.region is None and self._pulse.isActive():
            self._pulse.stop()
        renderer.upload_top_lines(self._pivot_lines())
        self._upload_ghost(renderer)
        ratio = self.devicePixelRatioF()
        width, height = int(self.width() * ratio), int(self.height() * ratio)
        aspect = max(width, 1) / max(height, 1)
        mvp = self.camera.projection_matrix(aspect) @ self.camera.view_matrix()
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
        )
        self.frame_rate.record(time.monotonic())
        self._draw_overlays()

    def _draw_overlays(self) -> None:
        """2D overlays in the game's pixel font (``theme.draw_text``): status lines, the
        mode badge with the mouse hints, view tags, F3 columns and signal labels."""
        painter = QPainter(self)
        line = theme.line_height(2)
        if self.show_info:
            self._draw_info_labels(painter)
            self._draw_debug_columns(painter)
        if self.overlay_text and not self.show_info:
            for index, text in enumerate(self.overlay_text):
                top = 8 + index * (line + 4)
                painter.fillRect(
                    8, top, theme.text_width(text) + 12, line + 4, QColor(0, 0, 0, 110)
                )
                theme.draw_text(painter, 14, top + 3, text, "#ffffff")
        if not self.show_info and self.paste_preview is None:
            self._draw_welcome(painter)
        # Mode badge (bottom left) with what the mode works on (the hint bar below the
        # window lists the keys).
        pasting = self.paste_preview is not None
        badge = "PASTE" if pasting else self.mode.upper()
        top = self.height() - line - 16
        badge_width = theme.text_width(badge) + 16
        room = max(0, self.width() - badge_width - 40)
        hint = _elide(self.mode_status(), room)
        covered = self._overlay_top(8, 8 + badge_width + theme.text_width(hint) + 22)
        if covered is not None:  # the hotbar is in the way: sit just above it
            top = min(top, covered - line - 14)
        color = PASTE_COLOR if pasting else MODE_COLORS[self.mode]
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 120))
        if hint:
            width = badge_width + theme.text_width(hint) + 22
            painter.drawRoundedRect(8, top, width, line + 8, 5, 5)
        painter.setBrush(color)
        painter.drawRoundedRect(8, top, badge_width, line + 8, 5, 5)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        theme.draw_text(painter, 16, top + 5, badge, "#ffffff")
        theme.draw_text(painter, 18 + badge_width, top + 5, hint, theme.TEXT)
        xray_tag = ("", "X-RAY", "X-RAY ALL")[self.xray]
        flags = [name for name, on in ((xray_tag, self.xray), ("INFO", self.show_info)) if on]
        if flags:
            tag = " · ".join(flags)
            tag_top = top - line - 14
            painter.fillRect(8, tag_top, theme.text_width(tag) + 16, line + 8, QColor(0, 0, 0, 150))
            theme.draw_text(painter, 16, tag_top + 5, tag, theme.GOLD)
        painter.end()

    def info_labels(self, max_distance: float = 48.0) -> list[tuple[np.ndarray, str, str]]:
        """Signal values shown by the info overlay: (world point, text, kind), nearest last.

        Wire: its power; signal sources (barrel, lectern, cake): the value a comparator
        reads; comparators: their stored output signal."""
        level = self.document.level
        eye = self.camera.position
        labels: list[tuple[float, np.ndarray, str, str]] = []
        for pos, state in level.blocks.items():
            block_id = state.block.id
            if block_id == "minecraft:redstone_wire":
                text, kind, height = str(state.get(POWER)), "wire", 0.1
            elif block_id == "minecraft:comparator":
                entity = level.get_block_entity(pos, create=False)
                output = entity.to_json().get("OutputSignal", 0) if entity is not None else 0
                text, kind, height = str(output), "comparator", 0.3
            elif sources.kind_of(state) is not None:
                value = sources.strength_at(level, pos)
                text, kind = str(value), "source"
                height = 0.55 if block_id == "minecraft:cake" else 1.0
            elif block_id == "minecraft:hopper":
                value = state.block.get_analog_output_signal(state, level, pos, Direction.NORTH)
                text, kind, height = str(value), "source", 1.0
            else:
                continue
            point = np.array([pos[0] + 0.5, pos[1] + height, pos[2] + 0.5])
            distance = float(np.linalg.norm(point - eye))
            if distance <= max_distance:
                labels.append((distance, point, text, kind))
        labels.sort(key=lambda label: -label[0])
        return [(point, text, kind) for _, point, text, kind in labels[-INFO_LABEL_LIMIT:]]

    def _draw_debug_columns(self, painter: QPainter) -> None:
        """Minecraft's F3 text: world state on the left, the targeted block on the right,
        each line on its own grey strip."""
        line = theme.line_height(2) + 2
        right = block_lines(self.document, self.hover.pos) if self.hover is not None else []
        for lines, align_right in ((self.debug_left, False), (right, True)):
            for index, text in enumerate(lines):
                width = theme.text_width(text) + 6
                left = self.width() - width - 4 if align_right else 4
                top = 4 + index * line
                painter.fillRect(left, top, width, line, QColor(80, 80, 80, 144))
                theme.draw_text(painter, left + 3, top + 2, text, "#e0e0e0")

    def _draw_info_labels(self, painter: QPainter) -> None:
        width, height = max(self.width(), 1), max(self.height(), 1)
        mvp = self.camera.projection_matrix(width / height) @ self.camera.view_matrix()
        line = theme.line_height(2)
        for point, text, kind in self.info_labels():
            clip = mvp @ np.array([*point, 1.0])
            if clip[3] <= 0.05:
                continue  # behind the camera
            x = (clip[0] / clip[3] + 1) / 2 * width
            y = (1 - clip[1] / clip[3]) / 2 * height
            if not (0 <= x <= width and 0 <= y <= height):
                continue
            box_width = theme.text_width(text) + 10
            box_height = line + 4
            left, top = int(x - box_width / 2), int(y - box_height / 2)
            background = INFO_COLORS[kind]
            if text == "0":
                background = QColor(70, 70, 70, 170)
            painter.fillRect(left, top, box_width, box_height, background)
            theme.draw_text(painter, left + 5, top + 3, text, "#ffffff")

    def welcome_lines(self) -> list[str]:
        """How to start, while the world is only its floor (nothing above y=0)."""
        if any(pos[1] > 0 for pos in self.document.level.blocks):
            return []

        def key(action: str) -> str:
            bindings = self.keymap.bindings(action)
            return bindings[0] if bindings else "?"

        build = f"Press {key('mode.build')} to build" if self.mode != BUILD else "Building"
        return [
            f"{build}: pick a block with 1-9, the hotbar or {key('search.blocks')}",
            f"{key('camera.orbit')} orbits · the wheel moves the camera up and down",
            f"{key('help.controls')} lists every key",
        ]

    def _draw_welcome(self, painter: QPainter) -> None:
        lines = self.welcome_lines()
        if not lines:
            return
        line = theme.line_height(2) + 6
        top = self.height() // 4
        title = "An empty world"
        width = max(theme.text_width(text) for text in [title, *lines]) + 40
        height = (len(lines) + 1) * line + 30
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(16, 16, 20, 170))
        painter.drawRoundedRect((self.width() - width) // 2, top - 14, width, height, 6, 6)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        theme.draw_text(
            painter, (self.width() - theme.text_width(title)) // 2, top, title, theme.GOLD
        )
        for index, text in enumerate(lines, start=1):
            x = (self.width() - theme.text_width(text)) // 2
            theme.draw_text(painter, x, top + index * line + 6, text, "#ffffff")

    def vary_build(self, turns: int = 0, mirror: str | None = None, flip: bool = False) -> str:
        """R / H / Shift+H in BUILD: vary the block to place; returns how it is varied."""
        self.build_turns = (self.build_turns + turns) % 4
        if mirror is not None:
            self.build_mirrors = self.build_mirrors ^ {mirror}
        if flip:
            self.build_upside_down = not self.build_upside_down
        self._build_meshes.clear()
        self._update_build_ghost()
        self.update()
        return self.build_variant() or "as placed"

    def vary_state(self, state: BlockState) -> BlockState:
        """The block to place as varied by R / H / Shift+H."""
        state = rotate_state(state, self.build_turns)
        for axis in sorted(self.build_mirrors):
            state = mirror_state(state, axis)
        return upside_down(state) if self.build_upside_down else state

    def build_variant(self) -> str:
        parts = []
        if self.build_turns:
            parts.append(f"turned {90 * self.build_turns}°")
        if self.build_mirrors:
            parts.append("mirrored")
        if self.build_upside_down:
            parts.append("upside down")
        return ", ".join(parts)

    def mode_status(self) -> str:
        """What the badge shows next to the mode: the block to place and the layer, the
        selection's size, or the inspected block."""
        if self.paste_preview is not None:
            return f"layer y={self.working_height()}"
        if self.mode == BUILD:
            block = block_name(self.build_block.id) if self.build_block else "no block chosen"
            variant = self.build_variant()
            variant = f" ({variant})" if variant else ""
            return f"{block}{variant} · layer y={self.working_height()}"
        if self.mode == SELECT and self.region is not None:
            low, high = self.region.low, self.region.high
            dx, dy, dz = (high[i] - low[i] + 1 for i in range(3))
            locked = " · locked" if self.region_locked else ""
            return f"{dx}×{dy}×{dz} = {dx * dy * dz} blocks{locked}"
        if self.mode == NORMAL and self.selection is not None:
            state = self.document.state_at(self.selection)
            x, y, z = self.selection
            return f"{block_name(state.block.id)} at {x} {y} {z}"
        return ""

    def mode_hint(self) -> str:
        """``Left Click: place · Left Drag: line · …`` for the current mode."""
        parts = []
        for action, verb in CLICK_VERBS.items():
            prefix = action.split(".")[0]
            bindings = self.keymap.bindings(action)
            if bindings and prefix in (self.mode, "pick"):
                parts.append(f"{bindings[0]}: {verb}")
        if self.mode == BUILD:
            delete = self.keymap.bindings("edit.delete")
            if delete:
                parts.insert(3, f"{delete[0]}: remove")
            parts.insert(0, f"layer y={self.working_height()} (Wheel moves it)")
        return " · ".join(parts)

    def _overlay_lines(self) -> np.ndarray:
        level = self.document.level
        parts = []
        sections = self.document.sections.sections.values() if self.show_sections else ()
        groups = self.document.groups.groups.values() if self.show_groups else ()
        for section in sections:
            color = _hex_color(section.color)
            for pos in section.positions:
                parts.append(box_lines(pos, (pos[0] + 1, pos[1] + 1, pos[2] + 1), color, 0.01))
        for group in groups:
            low, high = group.region.low, group.region.high
            parts.append(
                box_lines(low, (high[0] + 1, high[1] + 1, high[2] + 1), (1, 1, 1, 1), 0.03)
            )
            for port in group.ports:
                color = (0.2, 0.5, 1.0, 1.0) if port.role == "input" else (1.0, 0.5, 0.1, 1.0)
                p = port.pos
                parts.append(box_lines(p, (p[0] + 1, p[1] + 1, p[2] + 1), color, 0.05))
        paste_box = self.paste_region()
        if paste_box is not None:
            parts.extend(self._paste_guides(paste_box))
        if self.selection is not None:
            parts.append(block_outline(level, self.selection, (1.0, 0.85, 0.1, 1.0)))
        if self.hover is not None:
            parts.append(block_outline(level, self.hover.pos, (0.05, 0.05, 0.05, 1.0)))
        if self.mode == BUILD and self.paste_preview is None:
            cell = self._line_end or self._build_cell  # where a block would go
            if cell is not None:
                parts.extend(self._paste_guides(Region(cell, cell)))  # layer grid
                color = (1.0, 0.2, 0.2, 1.0) if cell == self.build_blocked else (1, 1, 1, 1)
                parts.append(box_lines(cell, (cell[0] + 1, cell[1] + 1, cell[2] + 1), color))
        if not parts:
            return np.zeros((0, 7), dtype=np.float32)
        return np.vstack(parts)

    def _paste_guides(self, box: Region) -> list[np.ndarray]:
        """A grid on the working plane around the paste, and drop lines from its corners to
        the first block below, so its height reads at a glance (Trackmania-style)."""
        parts = [_layer_grid(box)]
        drop = (1.0, 0.9, 0.3, 1.0)
        level = self.document.level
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
        parts = [self._pivot_block()]
        width = self._edge_width()
        if self.region is not None:
            lo, hi = _bounds(self.region)
            color = LOCKED_COLOR if self.region_locked else SELECTION_COLOR
            parts.append(thick_edges(lo, hi, color, width))
            if self._gizmos_shown():
                parts.append(self._gizmos()[0])
        if self._move is not None:
            lo, hi = _bounds(shifted(self._move.region, self._move.offset_pos))
            parts.append(thick_edges(lo, hi, TARGET_COLOR, width))
        if self._stack is not None and self._stack.count:
            far = shifted(self._stack.region, self._stack.offset(self._stack.count))
            lo = np.minimum(_bounds(self._stack.region)[0], _bounds(far)[0])
            hi = np.maximum(_bounds(self._stack.region)[1], _bounds(far)[1])
            parts.append(thick_edges(lo, hi, TARGET_COLOR, width))
        paste_box = self.paste_region()
        if paste_box is not None:
            lo, hi = _bounds(paste_box)
            parts.append(thick_edges(lo, hi, TARGET_COLOR, width))
        if not parts:
            return np.zeros((0, 7), dtype=np.float32)
        return np.vstack(parts)

    def _edge_width(self) -> float:
        """Selection edges keep a similar on-screen thickness at any zoom."""
        return min(0.2, max(0.035, 0.006 * self.camera.distance))

    def gizmo_unit(self) -> float:
        """Gizmo scale: grows with the distance to the selection, so it stays usable."""
        if self.region is None:
            return 0.1
        lo, hi = _bounds(self.region)
        distance = float(np.linalg.norm((lo + hi) / 2 - self.camera.position))
        return min(0.6, max(0.07, 0.017 * distance))

    def _gizmos_shown(self) -> bool:
        busy = self._move is not None or self._stack is not None or self._resize is not None
        return (
            self.region is not None
            and self.mode == SELECT
            and not busy
            and self.paste_preview is None
        )

    def _gizmos(self) -> tuple[np.ndarray, list[Hotspot]]:
        """Gizmo triangles and hot spots for the current selection (cached)."""
        assert self.region is not None
        unit = self.gizmo_unit()
        key = (self.region, round(unit, 3), round(self.camera.yaw), self._shift, self.gizmo_hover)
        if self._gizmo_cache is None or self._gizmo_cache[0] != key:
            shells: list[np.ndarray] = []
            built = selection_gizmos(
                self.region, unit, self.camera.yaw, self._shift, self.gizmo_hover, shells
            )
            outline = np.vstack(shells) if shells else np.zeros((0, 7), dtype=np.float32)
            self._gizmo_cache = (key, built)
            self._gizmo_outline = outline
        return self._gizmo_cache[1]

    def _outline_triangles(self) -> np.ndarray:
        """The gizmos' outlines (drawn behind them)."""
        if not self._gizmos_shown():
            return np.zeros((0, 7), dtype=np.float32)
        self._gizmos()
        return self._gizmo_outline

    def _gizmo_at(self, point: QPoint) -> Hotspot | None:
        if not self._gizmos_shown():
            return None
        origin, direction = self._ray(point)
        return pick_hotspot(origin, direction, self._gizmos()[1])

    def _selection_body(self) -> np.ndarray:
        """The selection filled with its color (round 8), so what is inside reads at a
        glance; the fill breathes slowly, so the selection feels alive."""
        if self.region is None:
            return np.zeros((0, 7), dtype=np.float32)
        lo, hi = _bounds(self.region)
        color = LOCKED_COLOR if self.region_locked else SELECTION_COLOR
        return box_faces(lo, hi, (color[0], color[1], color[2], self.body_alpha()))

    def body_alpha(self, now: float | None = None) -> float:
        """The selection fill's opacity: BODY_ALPHA, breathing by ±BODY_PULSE."""
        t = time.monotonic() if now is None else now
        return BODY_ALPHA + BODY_PULSE * math.sin(2 * math.pi * t / PULSE_SECONDS)

    def _upload_ghost(self, renderer: Renderer) -> None:
        ghost = self._ghost or self._build_ghost
        key = _ghost_key(ghost)
        if key == self._ghost_uploaded:
            return
        self._ghost_uploaded = key
        if ghost is None:
            renderer.upload_ghost(np.zeros((0, 7), dtype=np.float32))
            return
        vertices = ghost[0].copy()
        vertices[:, :3] += np.array(ghost[1], dtype=np.float32)
        renderer.upload_ghost(vertices)

    def _pivot_size(self) -> float:
        """Half the pivot block's edge: about the same size on screen at any zoom."""
        return 0.08 + self.camera.distance * 0.008

    def pivot_ground(self) -> float:
        """The height of the first surface below the pivot (a block top, else the floor
        level), where its shadow falls."""
        x, y, z = (float(v) for v in self.camera.pivot)
        bx, bz = math.floor(x), math.floor(z)
        level = self.document.level
        for by in range(math.floor(y), max(level.min_y, math.floor(y) - 64) - 1, -1):
            if by + 1 <= y and (bx, by, bz) in level.blocks:
                return float(by + 1)
        return 1.0

    def _pivot_block(self) -> np.ndarray:
        """The pivot as a small orange block (round 8: its place in space should be clear);
        drawn with the overlays, so it shows dimly through blocks too."""
        center = np.asarray(self.camera.pivot, dtype=float)
        half = self._pivot_size()
        return solid_box(center - half, center + half, PIVOT_COLOR)

    def _pivot_shadow(self) -> np.ndarray:
        """A soft square shadow on the surface below the pivot block."""
        x, _, z = (float(v) for v in self.camera.pivot)
        y = self.pivot_ground() + 0.01
        rows = []
        for scale, alpha in ((1.0, 0.45), (1.8, 0.2)):  # a dark core and a fainter rim
            r = self._pivot_size() * scale
            a, b, c, d = (x - r, y, z - r), (x + r, y, z - r), (x + r, y, z + r), (x - r, y, z + r)
            color = (0.0, 0.0, 0.0, alpha)
            rows += [(*p, *color) for p in (a, c, b, a, d, c)]
        return np.array(rows, dtype=np.float32)

    def _pivot_lines(self) -> np.ndarray:
        """A thin line from the pivot block down to its shadow, drawn on top."""
        x, y, z = (float(v) for v in self.camera.pivot)
        ground = self.pivot_ground()
        if y - self._pivot_size() <= ground + 0.02:
            return np.zeros((0, 7), dtype=np.float32)
        faint = (*PIVOT_COLOR[:3], 0.7)
        rows = [(x, y - self._pivot_size(), z, *faint), (x, ground, z, *faint)]
        return np.array(rows, dtype=np.float32)

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
        if action is not None and not event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
            self._held.add(action)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Shift:
            self._track_shift(False)
        action = self._held_actions.get(event.key())
        if action is not None and not event.isAutoRepeat():
            self._held.discard(action)
            return
        super().keyReleaseEvent(event)

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
            self._ghost = (self._move.ghost, self._move.offset_pos)
            self.update()
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
            scale /= max(self.height(), 1)
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
        if action == "normal.inspect":
            self.selection = hit.pos if hit else None
            self.select_requested.emit(self.selection)
        elif action in ("select.block", "select.extend") and self.region_locked:
            return  # a locked selection keeps its box
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
    def _begin_select_drag(self, start: QPoint, copy: bool) -> None:
        """A left drag in SELECT mode: resize from a handle, move/copy from inside the box,
        otherwise draw a new box."""
        origin, direction = self._ray(start)
        block = pick(self.document.level, origin, direction)
        region = self.region
        spot = self._gizmo_at(start)
        if region is not None and not copy and spot is not None:
            if spot.kind == "resize":  # gizmos are drawn on top, so they win over blocks
                handle = spot.data
                center = face_center(region, handle)
                axis = self._screen_vector(center, center + handle.normal)
                self._resize = (handle, region, start, axis)
            return  # rotate/flip gizmos act on click, not drag
        grab = self._grab_point(region, origin, direction, block)
        if region is not None and grab is not None:
            ghost = self._region_ghost(region)
            self._move = _MoveDrag(region, copy, float(grab[1]), grab, ghost)
            self._ghost = (ghost, (0, 0, 0))
            return
        if copy or self.region_locked:
            return  # copy-drags start inside the selection; a locked one cannot be replaced
        self._region_anchor = block.pos if block else None
        self._extend_box()

    @staticmethod
    def _grab_point(
        region: Region | None, origin: np.ndarray, direction: np.ndarray, block: Hit | None
    ) -> np.ndarray | None:
        """Where a drag grabs the selection: a block inside it, else anywhere the ray meets
        the box itself (selections usually contain air)."""
        if region is None:
            return None
        if block is not None and region.contains(block.pos):
            return origin + direction * block.distance
        lo, hi = _bounds(region)
        hit = ray_box(origin, direction, lo, hi)
        return None if hit is None else origin + direction * hit[0]

    def _continue_select_drag(self) -> None:
        point = self._last_mouse
        if point is None:
            return
        if self._resize is not None:
            handle, region, start, axis = self._resize
            drag = (point.x() - start.x(), point.y() - start.y())
            self.region = resized(region, handle, steps_along(drag, axis))
            self.update()
        elif self._move is not None:
            origin, direction = self._ray(point)
            hit = plane_point(origin, direction, self._move.plane_y)
            if hit is not None:
                self._move.dx, self._move.dz = horizontal_offset(self._move.grab, hit)
                self._ghost = (self._move.ghost, self._move.offset_pos)
                self.update()
        else:
            self._extend_box()

    def _end_select_drag(self) -> None:
        move, self._move = self._move, None
        resize, self._resize = self._resize, None
        self._ghost = None
        if move is not None:
            if move.offset_pos != (0, 0, 0):
                self.region_move_requested.emit(move.region, move.offset_pos, move.copy)
        elif resize is not None or self._region_anchor is not None:
            self.region_changed.emit(self.region)

    def _begin_stack(self, start: QPoint) -> None:
        """Shift+drag on a face handle: repeat the selection along that face's normal."""
        region = self.region
        if region is None:
            return
        spot = self._gizmo_at(start)
        if spot is None or spot.kind != "resize":
            return
        handle = spot.data
        center = face_center(region, handle)
        axis = self._screen_vector(center, center + handle.normal)
        self._stack = _StackDrag(region, handle, start, axis, self._region_ghost(region))

    def _continue_stack(self) -> None:
        stack, point = self._stack, self._last_mouse
        if stack is None or point is None:
            return
        drag = (point.x() - stack.start.x(), point.y() - stack.start.y())
        count = max(0, round(steps_along(drag, stack.axis) / stack.length))
        if count != stack.count:
            stack.count = count
            copies = [stack.ghost.copy() for _ in range(count)]
            for i, vertices in enumerate(copies, start=1):
                vertices[:, :3] += np.array(stack.offset(i), dtype=np.float32)
            self._ghost = (np.vstack(copies), (0, 0, 0)) if copies else None
            self.update()

    def _end_stack(self) -> None:
        stack, self._stack = self._stack, None
        self._ghost = None
        if stack is not None and stack.count:
            self.region_stack_requested.emit(stack.region, stack.offset(1), stack.count)

    def _extend_box(self) -> None:
        if self._region_anchor is not None and self.hover is not None:
            self.region = Region.from_corners(self._region_anchor, self.hover.pos)
            self.update()

    def _region_ghost(self, region: Region) -> np.ndarray:
        level = self.document.level
        states = {pos: level.blocks[pos] for pos in region.positions() if pos in level.blocks}
        return ghost_mesh(states, mesher=self.world_mesh.mesher)

    # ------------------------------------------------------------------ paste preview
    def begin_paste(self, prefab: Prefab) -> None:
        """Show ``prefab`` as a ghost at the cursor; a left click places it."""
        states = {(dx, dy, dz): blocks.parse_state(text) for dx, dy, dz, text, _ in prefab.blocks}
        self.paste_preview = prefab
        self._paste_base = ghost_mesh(states, mesher=self.world_mesh.mesher)
        self._update_paste_ghost()

    def cancel_paste(self) -> None:
        self.paste_preview = None
        self._ghost = None
        self.update()

    def paste_target(self) -> Pos | None:
        """Minimum corner of the paste, Trackmania-editor style: on the horizontal plane at
        the camera's working height (the pivot's block layer; Ctrl+wheel moves it),
        centered under the cursor. Works in the air and inside blocks."""
        if self.paste_preview is None or self._last_mouse is None:
            return None
        origin, direction = self._ray(self._last_mouse)
        return paste_origin(origin, direction, self.working_height(), self.paste_preview.size)

    def _shift_glide(self, delta: np.ndarray) -> None:
        """A direct camera move while gliding moves the glide's target along."""
        if self._glide is not None and np.any(delta):
            self._glide = (self._glide[0] + delta, self._glide[1])

    def working_height(self) -> int:
        """The block layer the camera pivot is in (or is gliding to)."""
        pivot = self._glide[0] if self._glide is not None else self.camera.pivot
        return math.floor(float(pivot[1]))

    def paste_region(self) -> Region | None:
        target = self.paste_target()
        if self.paste_preview is None or target is None:
            return None
        sx, sy, sz = self.paste_preview.size
        return Region(target, (target[0] + sx - 1, target[1] + sy - 1, target[2] + sz - 1))

    def _update_paste_ghost(self) -> None:
        target = self.paste_target()
        if self.paste_preview is None:
            return
        self._ghost = None if target is None else (self._paste_base, target)
        self.update()

    def _paste_click(self, button: Qt.MouseButton) -> None:
        target = self.paste_target()
        if button == Qt.MouseButton.LeftButton and target is not None:
            self.cancel_paste()
            self.paste_requested.emit(target)
        elif button == Qt.MouseButton.RightButton:
            self.cancel_paste()

    # ------------------------------------------------------------------ targeting
    def _ray(self, point: QPoint) -> tuple[np.ndarray, np.ndarray]:
        width, height = max(self.width(), 1), max(self.height(), 1)
        ndc_x = 2.0 * point.x() / width - 1.0
        ndc_y = 1.0 - 2.0 * point.y() / height
        return self.camera.ray_through(ndc_x, ndc_y, width / height)

    def _screen_vector(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """On-screen vector (pixels) from world point ``a`` to ``b``."""
        width, height = max(self.width(), 1), max(self.height(), 1)
        mvp = self.camera.projection_matrix(width / height) @ self.camera.view_matrix()
        points = []
        for world in (a, b):
            clip = mvp @ np.array([*world, 1.0])
            w = clip[3] if abs(clip[3]) > 1e-9 else 1e-9
            points.append(np.array([(clip[0] / w + 1) / 2 * width, (1 - clip[1] / w) / 2 * height]))
        return points[1] - points[0]

    def _pick_at(self, point: QPoint) -> Hit | None:
        origin, direction = self._ray(point)
        self._hover_direction = direction
        return pick(self.document.level, origin, direction)

    def _update_hover(self, point: QPoint) -> None:
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
                self._ghost = (self._move.ghost, self._move.offset_pos)
                self.update()
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
        """Move the pivot to the center of the block under the cursor."""
        if self.hover is None:
            return False
        self.look_at(self.hover.pos)
        return True

    def player_view(self) -> tuple[float, float]:
        """Yaw and pitch of a player looking at the targeted block from the camera."""
        if self._hover_direction is not None:
            return Camera.angles_of(self._hover_direction)
        return self.camera.yaw, self.camera.pitch


class _MoveDrag:
    """A selection being dragged to a new place (or copied there)."""

    def __init__(
        self, region: Region, copy: bool, plane_y: float, grab: np.ndarray, ghost: np.ndarray
    ) -> None:
        self.region = region
        self.copy = copy
        self.plane_y = plane_y
        self.grab = grab
        self.ghost = ghost
        self.dx = self.dz = self.lift = 0

    @property
    def offset_pos(self) -> Pos:
        return (self.dx, self.lift, self.dz)


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

    def offset(self, copies: int) -> Pos:
        step = self.handle.normal * self.length * copies
        return (int(step[0]), int(step[1]), int(step[2]))


_HANDLES = tuple(Handle(axis, high) for axis in range(3) for high in (False, True))


def _elide(text: str, room: int) -> str:
    """Cut ``text`` (pixel font) to ``room`` pixels with an ellipsis."""
    if theme.text_width(text) <= room:
        return text
    while text and theme.text_width(text + "…") > room:
        text = text[:-1]
    return text + "…"


def _ghost_key(ghost: tuple[np.ndarray, Pos] | None) -> tuple[int, Pos] | None:
    """Compare ghosts by mesh identity and place (comparing arrays would be elementwise)."""
    return None if ghost is None else (id(ghost[0]), ghost[1])


def _bounds(region: Region) -> tuple[np.ndarray, np.ndarray]:
    low, high = region.low, region.high
    return np.array(low, dtype=float), np.array(high, dtype=float) + 1.0


def _hex_color(text: str) -> tuple[float, float, float, float]:
    text = text.lstrip("#")
    return (int(text[0:2], 16) / 255, int(text[2:4], 16) / 255, int(text[4:6], 16) / 255, 1.0)


__all__ = ["BUILD", "NORMAL", "SELECT", "Direction", "Viewport"]
