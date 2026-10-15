"""Helpers shared by the commands: names of positions, the content box, regions, ticks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.cli.language import Args, CliError, format_pos
from redsim.core.pos import Pos

if TYPE_CHECKING:
    from redsim.cli.session import Session
    from redsim.editor.document import Document
    from redsim.sim.level import Level

#: Maps and summaries leave out blocks at or below this height (the floor of a new world).
FLOOR_Y = 0


def name_of(doc: Document, pos: Pos) -> str:
    """``@LABEL`` if a label names the position, else ``x y z``."""
    for name, label in doc.labels.items():
        if label.pos == pos:
            return f"@{name}"
    return format_pos(pos)


def named(doc: Document, pos: Pos) -> str:
    """``x y z`` followed by ``(@LABEL)`` when labeled."""
    for name, label in doc.labels.items():
        if label.pos == pos:
            return f"{format_pos(pos)} (@{name})"
    return format_pos(pos)


def content_positions(level: Level) -> list[Pos]:
    """The non-air blocks above the floor (y > 0); all non-air blocks if there are none."""
    above = [p for p, s in level.blocks.items() if p[1] > FLOOR_Y and not s.is_air]
    return above or [p for p, s in level.blocks.items() if not s.is_air]


def content_box(level: Level, margin: int = 0) -> tuple[Pos, Pos] | None:
    """The box around ``content_positions`` (with ``margin`` around x and z), or None."""
    positions = content_positions(level)
    if not positions:
        return None
    low = [min(p[i] for p in positions) for i in range(3)]
    high = [max(p[i] for p in positions) for i in range(3)]
    return (
        (low[0] - margin, low[1], low[2] - margin),
        (high[0] + margin, high[1], high[2] + margin),
    )


def region(args: Args) -> tuple[Pos, Pos]:
    """Two corners (any order) → (low, high)."""
    a = args.pos("the first corner")
    b = args.pos("the second corner")
    low = (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]))
    high = (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))
    return low, high


def volume(low: Pos, high: Pos) -> int:
    return (high[0] - low[0] + 1) * (high[1] - low[1] + 1) * (high[2] - low[2] + 1)


def tick_line(session: Session) -> str:
    """``at tick 12 of 40`` (the view and the simulated length), or ``inside tick 3 (2
    steps after tick 2)`` when the view is between two engine steps of a tick."""
    doc = session.doc
    if doc.can_edit:
        return f"at tick {doc.tick} of {doc.end_tick}"
    view = session.view_now()
    steps = "1 step" if view[1] == 1 else f"{view[1]} steps"
    return f"inside tick {view[0] + 1} ({steps} after tick {view[0]})"


def view_data(session: Session) -> dict[str, Any]:
    doc = session.doc
    return {"tick": doc.tick, "end_tick": doc.end_tick, "inside_tick": not doc.can_edit}


def require_air_or_same(doc: Document, pos: Pos) -> None:
    if not doc.state_at(pos).is_air:
        raise CliError(
            f"{format_pos(pos)} holds {doc.state_at(pos).block.name}: "
            "break it first, or use 'set' to replace it"
        )
