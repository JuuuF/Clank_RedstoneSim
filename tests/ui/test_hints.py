"""Context hints (no display needed)."""

from __future__ import annotations

from redsim.ui.hints import Context, context_hints
from redsim.ui.keymap import Keymap


def texts(context: Context) -> list[str]:
    return [text for _, text in context_hints(Keymap(), context)]


def test_hints_follow_the_context() -> None:
    assert "place" in texts(Context("build"))
    assert "draw a box" in texts(Context("select"))
    assert "rotate" in texts(Context("select", has_region=True))
    assert "unlock" in texts(Context("select", has_region=True, locked=True))
    assert "stack copies" in texts(Context("select", has_region=True, shift=True))
    assert "layer up/down" in texts(Context("select", pasting=True))
    assert "rotate 90° this way" in texts(Context("select", has_region=True, gizmo="rotate"))
    assert "pause" in texts(Context("normal", running=True))


def test_hints_use_the_keymap() -> None:
    keymap = Keymap({"edit.rotate": ["K"]})
    hints = dict((text, keys) for keys, text in context_hints(keymap, Context("select", True)))
    assert hints["rotate"] == "K"
