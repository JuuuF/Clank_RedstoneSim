"""Orbit camera math (no display needed)."""

from __future__ import annotations

import numpy as np
import pytest

from redsim.ui.camera import MAX_PITCH, MIN_DISTANCE, Camera


def test_eye_sits_behind_the_pivot() -> None:
    camera = Camera(pivot=np.array([0.0, 0.0, 0.0]), distance=10.0, yaw=0.0, pitch=0.0)
    assert np.allclose(camera.position, [0.0, 0.0, -10.0])  # yaw 0 looks south (+z)
    camera.pitch = 90.0 - 1e-9
    assert camera.position[1] == pytest.approx(10.0)  # looking straight down


def test_orbit_keeps_distance_and_clamps_pitch() -> None:
    camera = Camera(pivot=np.array([3.0, 2.0, 1.0]), distance=7.0)
    camera.orbit(123.0, 500.0)
    assert np.linalg.norm(camera.position - camera.pivot) == pytest.approx(7.0)
    assert camera.pitch == MAX_PITCH


def test_pan_is_horizontal_and_relative_to_the_view() -> None:
    camera = Camera(pivot=np.array([0.0, 5.0, 0.0]), yaw=90.0, pitch=60.0)  # looks west
    camera.pan(2.0, 0.0)
    assert np.allclose(camera.pivot, [-2.0, 5.0, 0.0])
    camera.raise_pivot(1.5)
    assert camera.pivot[1] == pytest.approx(6.5)


def test_zoom_is_clamped() -> None:
    camera = Camera(distance=4.0)
    camera.zoom(0.01)
    assert camera.distance == MIN_DISTANCE


@pytest.mark.parametrize(("yaw", "pitch"), [(0, 0), (90, 30), (200, -45), (315, 80)])
def test_angles_of_inverts_forward(yaw: float, pitch: float) -> None:
    camera = Camera(yaw=yaw, pitch=pitch)
    got_yaw, got_pitch = Camera.angles_of(camera.forward())
    assert got_yaw == pytest.approx(yaw % 360)
    assert got_pitch == pytest.approx(pitch)


def test_json_round_trip_and_old_fly_camera_format() -> None:
    camera = Camera(pivot=np.array([1.5, 2.0, -3.5]), distance=20.0, yaw=45.0, pitch=30.0)
    again = Camera.from_json(camera.to_json())
    assert np.allclose(again.pivot, camera.pivot) and again.distance == 20.0
    # Older files stored the eye position of the fly camera: the view must stay the same.
    old = Camera.from_json({"position": [4.5, 6.0, -18.0], "yaw": 0.0, "pitch": 33.0})
    assert np.allclose(old.position, [4.5, 6.0, -18.0])
    assert (old.yaw, old.pitch) == (0.0, 33.0)
