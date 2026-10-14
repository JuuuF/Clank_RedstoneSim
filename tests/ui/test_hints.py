"""Context hints (no display needed)."""

from __future__ import annotations

from redsim.ui.hints import Context, context_hints
from redsim.ui.keymap import Keymap


def texts(context: Context) -> list[str]:
    return [text for _, text in context_hints(Keymap(), context)]


def test_hints_follow_the_context() -> None:
    assert "place" in texts(Context("build"))
    assert "draw a box" in texts(Context("select"))
    assert "move the box" in texts(Context("select", has_region=True))
    assert "confirm: act on the blocks" in texts(Context("select", has_region=True))
    assert "move the blocks" in texts(Context("select", has_region=True, confirmed=True))
    assert "rotate" in texts(Context("select", has_region=True, confirmed=True))
    assert "stack copies" in texts(Context("select", has_region=True, confirmed=True, shift=True))
    assert "add another box" in texts(Context("select", has_region=True, shift=True))
    pending = Context("select", has_region=True, confirmed=True, pending=True)
    assert texts(pending)[:2] == ["place the blocks", "cancel"]
    assert "layer up/down" in texts(Context("select", pasting=True))
    assert "rotate 90° this way" in texts(Context("select", has_region=True, gizmo="rotate"))
    assert "pause" in texts(Context("normal", running=True))


def test_hints_use_the_keymap() -> None:
    keymap = Keymap({"edit.rotate": ["K"]})
    context = Context("select", True, confirmed=True)
    hints = dict((text, keys) for keys, text in context_hints(keymap, context))
    assert hints["rotate"] == "K"
