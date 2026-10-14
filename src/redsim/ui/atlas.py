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

#: Extra textures needed besides the block models' (none yet).
#: The ground around the floor (``renderer.GROUND_TEXTURE``).
EXTRA_TEXTURES: tuple[str, ...] = (
    "minecraft:block/stone",
    "minecraft:block/grass_block_top",
    # Chests: no block model (assets.ENTITY_MODELS); single chests and double halves.
    *(
        f"minecraft:entity/chest/{name}{half}"
        for name in ("normal", "trapped")
        for half in ("", "_left", "_right")
    ),
)


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


#: The largest tile kept at full size (entity textures such as the chest's are 64×64);
#: bigger textures are scaled down to it.
MAX_TILE = 64


def _tile(pixels: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """The texture as one square tile: its first animation frame, block textures (and
    anything odd) at 16×16, larger square textures (entity textures) at full size up to
    ``MAX_TILE``, scaled by nearest neighbor."""
    height, width = pixels.shape[:2]
    if height > width:
        pixels = pixels[:width]
        height = width
    size = width if height == width and TILE <= width <= MAX_TILE else TILE
    if (height, width) != (size, size):
        rows = (np.arange(size) * height // size).clip(0, height - 1)
        cols = (np.arange(size) * width // size).clip(0, width - 1)
        pixels = pixels[rows][:, cols]
    return pixels


class Atlas:
    """Tiles of named textures in one RGBA image; ``uv`` maps texture UVs into it. Block
    textures are 16×16 tiles; larger ones (the chest's 64×64) keep their pixels. Tiles
    are packed in shelves, largest first, each with a 1-pixel border of its edge."""

    def __init__(self, assets: Assets, textures: Iterable[str]) -> None:
        names = sorted(set(textures))
        missing = np.zeros((TILE, TILE, 4), dtype=np.uint8)  # the game's magenta/black
        missing[:, :] = (248, 0, 248, 255)
        missing[: TILE // 2, : TILE // 2] = (0, 0, 0, 255)
        missing[TILE // 2 :, TILE // 2 :] = (0, 0, 0, 255)
        tiles: dict[str, npt.NDArray[np.uint8]] = {"#missing": missing}
        for name in names:
            data = assets.texture_bytes(name)
            decoded = decode_png(data) if data else None
            tiles[name] = _tile(decoded) if decoded is not None else missing
        order = sorted(tiles, key=lambda n: (-tiles[n].shape[0], n != "#missing", n))
        area = sum((tiles[n].shape[0] + 2) ** 2 for n in order)
        size = 1 << max(6, math.ceil(math.log2(math.sqrt(area))))
        while (placed := _pack([tiles[n].shape[0] + 2 for n in order], size)) is None:
            size *= 2
        self.size = size
        self.pixels = np.zeros((size, size, 4), dtype=np.uint8)
        self._origin: dict[str, tuple[int, int]] = {}
        self._size: dict[str, int] = {}
        for name, (x, y) in zip(order, placed, strict=True):
            tile = tiles[name]
            cell = tile.shape[0] + 2
            self.pixels[y : y + cell, x : x + cell] = np.pad(
                tile, ((1, 1), (1, 1), (0, 0)), mode="edge"
            )
            self._origin[name] = (x + 1, y + 1)
            self._size[name] = tile.shape[0]

    @staticmethod
    def for_blocks(assets: Assets, extra_blocks: Iterable[str] = ()) -> Atlas:
        """An atlas with every texture of every registered block's models, and of
        ``extra_blocks`` (blocks of an opened Minecraft world the simulator does not model)."""
        textures: set[str] = set(EXTRA_TEXTURES)
        for block_id in {*blocks.REGISTRY, *extra_blocks}:
            textures |= assets.block_textures(block_id)
        return Atlas(assets, textures)

    def has(self, texture: str) -> bool:
        return texture in self._origin

    def _where(self, texture: str) -> tuple[int, int, int]:
        name = texture if texture in self._origin else "#missing"
        x, y = self._origin[name]
        return x, y, self._size[name]

    def uv(self, texture: str, u: float, v: float) -> tuple[float, float]:
        x, y, tile = self._where(texture)
        return ((x + u * tile) / self.size, (y + v * tile) / self.size)

    def rect(self, texture: str) -> tuple[float, float, float, float]:
        """The texture's tile in atlas coordinates: (u, v, width, height)."""
        x, y, tile = self._where(texture)
        return (x / self.size, y / self.size, tile / self.size, tile / self.size)

    def tile(self, texture: str) -> npt.NDArray[np.uint8]:
        x, y, tile = self._where(texture)
        return self.pixels[y : y + tile, x : x + tile]

    def image(self) -> QImage:
        return QImage(
            self.pixels.tobytes(),
            self.size,
            self.size,
            self.size * 4,
            QImage.Format.Format_RGBA8888,
        ).copy()


def _pack(cells: list[int], size: int) -> list[tuple[int, int]] | None:
    """Shelf packing of squares (sizes ``cells``, largest first) into a ``size`` square:
    their top-left corners, or None if they do not fit."""
    out = []
    x = y = shelf = 0
    for cell in cells:
        if x + cell > size:
            x, y, shelf = 0, y + shelf, 0
        if y + cell > size:
            return None
        out.append((x, y))
        x += cell
        shelf = max(shelf, cell)
    return out
