"""Selection handles and drag math (no display needed)."""

from __future__ import annotations

import numpy as np

from redsim.editor.clipboard import Region
from redsim.ui.selection_tools import (
    Handle,
    horizontal_offset,
    paste_origin,
    plane_point,
    resized,
    shifted,
    steps_along,
)

BOX = Region((0, 0, 0), (3, 1, 2))  # 4 × 2 × 3 blocks


def test_resizing_moves_one_face_and_keeps_at_least_one_block() -> None:
    assert resized(BOX, Handle(0, True), 2) == Region((0, 0, 0), (5, 1, 2))
    assert resized(BOX, Handle(2, False), 1) == Region((0, 0, -1), (3, 1, 2))
    assert resized(BOX, Handle(1, True), -5) == Region((0, 0, 0), (3, 0, 2))


def test_drag_steps_follow_the_projected_axis() -> None:
    axis = np.array([20.0, 0.0])  # one block = 20 px to the right
    assert steps_along((61.0, 30.0), axis) == 3
    assert steps_along((-25.0, 0.0), axis) == -1
    assert steps_along((100.0, 0.0), np.array([1.0, 0.5])) == 0  # seen end-on: ignored


def test_move_drag_on_the_horizontal_plane() -> None:
    origin = np.array([0.5, 10.0, 0.5])
    start = plane_point(origin, np.array([0.0, -1.0, 0.0]), 1.0)
    assert start is not None and np.allclose(start, [0.5, 1.0, 0.5])
    later = plane_point(origin, np.array([0.3, -1.0, -0.2]), 1.0)
    assert later is not None
    assert horizontal_offset(start, later) == (3, -2)
    assert plane_point(origin, np.array([1.0, 0.0, 0.0]), 1.0) is None
    assert shifted(BOX, (3, 1, -2)) == Region((3, 1, -2), (6, 2, 0))


def test_paste_sits_on_the_camera_plane_centered_under_the_cursor() -> None:
    eye = np.array([0.5, 10.0, 0.5])
    down = np.array([0.0, -1.0, 0.0])
    assert paste_origin(eye, down, 4, (1, 1, 1)) == (0, 4, 0)
    assert paste_origin(eye, down, 4, (3, 2, 5)) == (-1, 4, -2)  # centered
    assert paste_origin(eye, np.array([0.0, 1.0, 0.0]), 4, (1, 1, 1)) is None  # plane behind


def test_a_drag_grabs_the_selection_through_air_inside_it() -> None:
    """Regression: Ctrl+drag copy did nothing when the drag started on air in the box."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from redsim.ui.viewport import Viewport

    box = Region((0, 1, 0), (1, 2, 0))
    grab = Viewport._grab_point(box, np.array([0.5, 10.0, 0.5]), np.array([0.0, -1.0, 0.0]), None)
    assert grab is not None and np.allclose(grab, [0.5, 3.0, 0.5])  # the box's top face
    miss = Viewport._grab_point(box, np.array([5.5, 10.0, 0.5]), np.array([0.0, -1.0, 0.0]), None)
    assert miss is None
