"""Fly camera with Minecraft's yaw/pitch conventions (yaw 0 looks south, pitch > 0 looks down)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Camera:
    position: np.ndarray = field(default_factory=lambda: np.array([0.5, 6.0, -8.0]))
    yaw: float = 0.0
    pitch: float = 30.0
    fov: float = 70.0

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

    def rotate(self, d_yaw: float, d_pitch: float) -> None:
        self.yaw = (self.yaw + d_yaw) % 360.0
        self.pitch = max(-89.9, min(89.9, self.pitch + d_pitch))

    def move(self, forward: float, strafe: float, up: float) -> None:
        self.position = (
            self.position
            + self.horizontal_forward() * forward
            + self.right() * strafe
            + np.array([0.0, up, 0.0])
        )

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
        self, aspect: float, near: float = 0.05, far: float = 600.0
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
