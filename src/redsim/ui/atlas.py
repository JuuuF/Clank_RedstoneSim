"""A texture atlas of the game's block textures (from ``assets.Assets``) for the renderer.

Every texture becomes a 16×16 tile with a 1-pixel border copied from its edges, so
nearest-neighbor sampling at a tile edge never picks up the next tile. Animated textures
(frames stacked vertically) use their first frame. Textures are decoded with Qt.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import numpy.typing as npt
from PySide6.QtGui import QImage

from redsim.ui.assets import Assets
from redsim.world import blocks

TILE = 16
CELL = TILE + 2

#: Extra textures needed besides the block models' (none yet).
#: The ground around the floor (``renderer.GROUND_TEXTURE``).
EXTRA_TEXTURES: tuple[str, ...] = ("minecraft:block/stone",)


def decode_png(data: bytes) -> npt.NDArray[np.uint8] | None:
    """RGBA pixels (h, w, 4) of a PNG, or None."""
    image = QImage.fromData(data)
    if image.isNull():
        return None
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = image.width(), image.height()
    buffer = image.constBits()
    array = np.frombuffer(buffer, dtype=np.uint8, count=image.sizeInBytes())
    return (
        array.reshape(height, image.bytesPerLine())[:, : width * 4].reshape(height, width, 4).copy()
    )


def _tile(pixels: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """The texture as one 16×16 tile (first animation frame, scaled by nearest neighbor)."""
    height, width = pixels.shape[:2]
    if height > width:
        pixels = pixels[:width]
        height = width
    if (height, width) != (TILE, TILE):
        rows = (np.arange(TILE) * height // TILE).clip(0, height - 1)
        cols = (np.arange(TILE) * width // TILE).clip(0, width - 1)
        pixels = pixels[rows][:, cols]
    return pixels


class Atlas:
    """Tiles of named textures in one RGBA image; ``uv`` maps texture UVs into it."""

    def __init__(self, assets: Assets, textures: Iterable[str]) -> None:
        names = sorted(set(textures))
        per_row = max(1, math.ceil(math.sqrt(len(names) + 1)))
        size = 1 << max(6, math.ceil(math.log2(per_row * CELL)))
        self.size = size
        self.pixels = np.zeros((size, size, 4), dtype=np.uint8)
        self._origin: dict[str, tuple[int, int]] = {}
        missing = np.zeros((TILE, TILE, 4), dtype=np.uint8)  # the game's magenta/black
        missing[:, :] = (248, 0, 248, 255)
        missing[: TILE // 2, : TILE // 2] = (0, 0, 0, 255)
        missing[TILE // 2 :, TILE // 2 :] = (0, 0, 0, 255)
        for index, name in enumerate(["#missing", *names]):
            data = assets.texture_bytes(name) if index else None
            decoded = decode_png(data) if data else None
            tile = _tile(decoded) if decoded is not None else missing
            x, y = (index % per_row) * CELL, (index // per_row) * CELL
            padded = np.pad(tile, ((1, 1), (1, 1), (0, 0)), mode="edge")
            self.pixels[y : y + CELL, x : x + CELL] = padded
            self._origin[name] = (x + 1, y + 1)

    @staticmethod
    def for_blocks(assets: Assets) -> Atlas:
        """An atlas with every texture of every registered block's models."""
        textures: set[str] = set(EXTRA_TEXTURES)
        for block_id in blocks.REGISTRY:
            textures |= assets.block_textures(block_id)
        return Atlas(assets, textures)

    def uv(self, texture: str, u: float, v: float) -> tuple[float, float]:
        x, y = self._origin.get(texture, self._origin["#missing"])
        return ((x + u * TILE) / self.size, (y + v * TILE) / self.size)

    def rect(self, texture: str) -> tuple[float, float, float, float]:
        """The texture's tile in atlas coordinates: (u, v, width, height)."""
        u, v = self.uv(texture, 0.0, 0.0)
        return (u, v, TILE / self.size, TILE / self.size)

    def tile(self, texture: str) -> npt.NDArray[np.uint8]:
        x, y = self._origin.get(texture, self._origin["#missing"])
        return self.pixels[y : y + TILE, x : x + TILE]

    def image(self) -> QImage:
        return QImage(
            self.pixels.tobytes(),
            self.size,
            self.size,
            self.size * 4,
            QImage.Format.Format_RGBA8888,
        ).copy()
