"""Pixel-art button icons: one size for all, art made of ``#`` and ``.`` only."""

from __future__ import annotations

import os
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from redsim.ui import pixel_icons  # noqa: E402


@pytest.fixture(scope="module")
def app() -> Any:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_every_icon_has_the_common_size(app: Any) -> None:
    for name, rows in pixel_icons.ICONS.items():
        assert len({len(row) for row in rows}) == 1, name  # rectangular art
        assert set("".join(rows)) <= {"#", "."}, name
        assert pixel_icons.pixel_pixmap(name).size() == pixel_icons.ICON_SIZE, name


def test_derived_icons_mirror_their_originals() -> None:
    rotate, back = pixel_icons.ICONS["rotate"], pixel_icons.ICONS["rotate_back"]
    assert all(a == b[::-1] for a, b in zip(rotate, back, strict=True))
    flip, depth = pixel_icons.ICONS["flip"], pixel_icons.ICONS["flip_depth"]
    assert len(depth) == len(flip[0]) and len(depth[0]) == len(flip)


def test_pixel_text_cache_is_bounded(app: Any) -> None:
    from redsim.ui import theme

    font = theme.PixelFont.load()
    if font is None:
        pytest.skip("no client jar: no pixel font")
    for n in range(theme.PIXEL_TEXT_CACHE + 50):  # e.g. a status line while running
        font.pixmap(f"tick {n}")
    assert len(font._cache) <= theme.PIXEL_TEXT_CACHE
    assert ("tick 0", "#ffffff", 2, True) not in font._cache  # the oldest went first
