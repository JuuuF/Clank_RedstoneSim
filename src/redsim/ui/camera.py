"""Orbit camera around a pivot, with Minecraft's yaw/pitch conventions.

Yaw 0 looks south (+z), yaw 90 looks west; pitch > 0 looks down. The eye sits ``distance``
blocks behind the pivot along the view direction, so orbiting turns the view around the
pivot, panning and the vertical controls move the pivot, and zooming changes the distance
(owner decision, doc/ui-direction.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

MIN_DISTANCE = 1.5
MAX_DISTANCE = 300.0
MAX_PITCH = 89.0


@dataclass
class Camera:
    pivot: np.ndarray = field(default_factory=lambda: np.array([0.5, 1.0, 0.5]))
    distance: float = 12.0
    yaw: float = 0.0
    pitch: float = 35.0
    fov: float = 70.0

    # ------------------------------------------------------------------ directions
    def forward(self) -> np.ndarray:
        yaw, pitch = math.radians(self.yaw), math.radians(self.pitch)
        return np.array(
            [-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch)]
        )

    def horizontal_forward(self) -> np.ndarray:
        yaw = math.radians(self.yaw)
        return np.array([-math.sin(yaw), 0.0, math.cos(yaw)])

    def right(self) -> np.ndarray:
        f = self.horizontal_forward()
        return np.array([-f[2], 0.0, f[0]])  # forward × up

    @property
    def position(self) -> np.ndarray:
        """The eye."""
        return np.asarray(self.pivot, dtype=float) - self.forward() * self.distance

    @staticmethod
    def angles_of(direction: np.ndarray) -> tuple[float, float]:
        """Yaw and pitch of a player looking along ``direction`` (Minecraft conventions)."""
        dx, dy, dz = (float(v) for v in direction / np.linalg.norm(direction))
        yaw = math.degrees(math.atan2(-dx, dz)) % 360.0
        pitch = math.degrees(-math.asin(max(-1.0, min(1.0, dy))))
        return yaw, pitch

    # ------------------------------------------------------------------ controls
    def orbit(self, d_yaw: float, d_pitch: float) -> None:
        self.yaw = (self.yaw + d_yaw) % 360.0
        self.pitch = max(-MAX_PITCH, min(MAX_PITCH, self.pitch + d_pitch))

    def pan(self, forward: float, strafe: float) -> None:
        """Move the pivot in the horizontal plane, relative to the view direction."""
        self.pivot = (
            np.asarray(self.pivot, dtype=float)
            + self.horizontal_forward() * forward
            + self.right() * strafe
        )

    def raise_pivot(self, amount: float) -> None:
        self.pivot = np.asarray(self.pivot, dtype=float) + np.array([0.0, amount, 0.0])

    def zoom(self, factor: float) -> None:
        """Multiply the distance to the pivot (factor < 1 zooms in)."""
        self.distance = max(MIN_DISTANCE, min(MAX_DISTANCE, self.distance * factor))

    def focus(self, point: np.ndarray) -> None:
        self.pivot = np.asarray(point, dtype=float)

    # ------------------------------------------------------------------ persistence
    def to_json(self) -> dict[str, object]:
        return {
            "pivot": [round(float(v), 3) for v in self.pivot],
            "distance": round(self.distance, 3),
            "yaw": round(self.yaw, 2),
            "pitch": round(self.pitch, 2),
        }

    @staticmethod
    def from_json(data: dict[str, object]) -> Camera:
        """Read a stored view; older files store the eye ``position`` of the fly camera."""
        camera = Camera(yaw=float(data["yaw"]), pitch=float(data["pitch"]))  # type: ignore[arg-type]
        if "pivot" in data:
            camera.pivot = np.array(data["pivot"], dtype=float)
            camera.distance = float(data.get("distance", camera.distance))  # type: ignore[arg-type]
        else:
            eye = np.array(data["position"], dtype=float)
            camera.pivot = eye + camera.forward() * camera.distance
        return camera

    # ------------------------------------------------------------------ matrices
    def view_matrix(self) -> np.ndarray:
        f = self.forward()
        f = f / np.linalg.norm(f)
        world_up = np.array([0.0, 1.0, 0.0])
        s = np.cross(f, world_up)
        s = s / np.linalg.norm(s)
        u = np.cross(s, f)
        m = np.identity(4)
        m[0, :3], m[1, :3], m[2, :3] = s, u, -f
        m[:3, 3] = -m[:3, :3] @ self.position
        return m

    def projection_matrix(
        self, aspect: float, near: float = 0.05, far: float = 1000.0
    ) -> np.ndarray:
        f = 1.0 / math.tan(math.radians(self.fov) / 2)
        m = np.zeros((4, 4))
        m[0, 0] = f / aspect
        m[1, 1] = f
        m[2, 2] = (far + near) / (near - far)
        m[2, 3] = 2 * far * near / (near - far)
        m[3, 2] = -1.0
        return m

    def ray_through(
        self, ndc_x: float, ndc_y: float, aspect: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """World-space ray (origin, direction) through normalized device coordinates."""
        inverse = np.linalg.inv(self.projection_matrix(aspect) @ self.view_matrix())
        near = inverse @ np.array([ndc_x, ndc_y, -1.0, 1.0])
        far = inverse @ np.array([ndc_x, ndc_y, 1.0, 1.0])
        near, far = near[:3] / near[3], far[:3] / far[3]
        direction = far - near
        return near, direction / np.linalg.norm(direction)
