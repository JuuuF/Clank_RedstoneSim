"""The timeline played back: what moved, when, and what the doorway looked like.

``record(document)`` walks the recorded history engine step by engine step (the same
steps ``redsim-cli step`` shows) and keeps:

- per tick boundary, every block that changed (``changes``), so any block's state at any
  tick can be read back (``state``);
- every piston **block event** (``PistonEvent``): the piston, extend / retract / drop
  (the game's event types 0 / 1 / 2), and its effect, read from the moving-block entities
  that step created (the blocks it started to move, from where to where) and the ones it
  ended early (a retract during an extension places the pushed blocks at once: the
  "spit" of a short pulse);
- door frames: the output section's cells per tick (``frames``), and the phases of
  movement (``phases``).

Nothing is inferred from the block layout here: the events are the simulator's own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from redsim.cli.views import state_text
from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor.document import Document
from redsim.sim import causes
from redsim.sim import trace as tr
from redsim.sim.engine import Phase

EVENT_NAMES = {0: "extend", 1: "retract", 2: "drop"}
AIR = "air"


def _moving(level: Any) -> dict[int, Any]:
    return {
        id(be): be
        for be in level.block_entities.values()
        if type(be).__name__ == "PistonMovingBlockEntity"
    }


def _movement_direction(be: Any) -> Direction:
    """``PistonMovingBlockEntity.getMovementDirection``."""
    return be.direction if be.extending else be.direction.opposite


def _minus(pos: Pos, d: Direction) -> Pos:
    dx, dy, dz = d.step
    return (pos[0] - dx, pos[1] - dy, pos[2] - dz)


@dataclass
class Moved:
    """One block a piston started to move: from ``origin`` to ``dest``."""

    origin: Pos
    dest: Pos
    state: str
    source: bool  # the piston's own head (extend) or base (retract)

    def to_json(self) -> dict[str, Any]:
        return {
            "from": list(self.origin),
            "to": list(self.dest),
            "state": self.state,
            "source": self.source,
        }


@dataclass
class PistonEvent:
    tick: int  # the tick during which it ran (the boundary after it is ``tick``)
    order: int  # its rank among the tick's block events
    piston: Pos
    kind: str  # extend / retract / drop
    facing: str
    sticky: bool
    moved: list[Moved] = field(default_factory=list)
    finished_early: list[tuple[Pos, str]] = field(default_factory=list)
    skipped: bool = False  # the block changed before the event ran
    #: For an extension: where the piston's power came from (the trace's note when it
    #: queued the event): the block giving the signal (``via``), whether it was reached
    #: through the block above the piston (quasi-connectivity) and what powers ``via``.
    power: dict[str, Any] | None = None

    @property
    def outcome(self) -> str:
        if self.skipped:
            return "skipped"
        if self.kind == "extend":
            return (
                "pushed"
                if any(not m.source for m in self.moved)
                else ("extended" if self.moved else "failed")
            )
        pulled = any(not m.source for m in self.moved)
        early = bool(self.finished_early)
        if pulled:
            return "pulled"
        return "spat" if early else "retracted"

    def to_json(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "order": self.order,
            "piston": list(self.piston),
            "kind": self.kind,
            "facing": self.facing,
            "sticky": self.sticky,
            "outcome": self.outcome,
            "moved": [m.to_json() for m in self.moved if not m.source],
            "finished_early": [[list(p), s] for p, s in self.finished_early],
            **({"power": self.power} if self.power else {}),
        }


@dataclass
class Recording:
    start: dict[Pos, str]  # the build: non-air blocks
    changes: dict[int, dict[Pos, str]]  # tick → position → new state ("air" if removed)
    events: list[PistonEvent]
    end_tick: int
    links: list[Link] = field(default_factory=list)

    def state(self, pos: Pos, tick: int) -> str:
        value = self.start.get(pos, AIR)
        for t in range(1, tick + 1):
            value = self.changes.get(t, {}).get(pos, value)
        return value

    def history_of(self, pos: Pos) -> list[tuple[int, str]]:
        """(tick, state) each time the block changed, starting with the build."""
        out = [(0, self.start.get(pos, AIR))]
        for t in range(1, self.end_tick + 1):
            if pos in self.changes.get(t, {}):
                out.append((t, self.changes[t][pos]))
        return out

    def states_at(self, positions: list[Pos], tick: int) -> dict[Pos, str]:
        values = {p: self.start.get(p, AIR) for p in positions}
        for t in range(1, tick + 1):
            row = self.changes.get(t)
            if row:
                for p in positions:
                    if p in row:
                        values[p] = row[p]
        return values

    def events_at(self, tick: int) -> list[PistonEvent]:
        return [e for e in self.events if e.tick == tick]

    def fingerprint(self) -> list[tuple[int, int]]:
        """Per tick, a hash of the changes: two recordings of the same world agree."""
        return [
            (t, hash(tuple(sorted(self.changes.get(t, {}).items()))))
            for t in range(self.end_tick + 1)
        ]


def _new_records(trace: Any, last_id: int) -> list[Any]:
    """Trace records with an id above ``last_id`` (the trace may have been trimmed)."""
    start = max(0, last_id + 1 - trace.base_id)
    return trace.records[start:]


def record(document: Document, end_tick: int | None = None, causes: bool = False) -> Recording:
    """Play ``document``'s history from the build to ``end_tick`` (default: its end).

    With ``causes``, also the causal links between block changes (``Recording.links``):
    for each change, the change that caused it, read from the engine's trace with the
    same rules as ``redsim-cli why`` (``redsim.sim.causes.chain``)."""
    doc = document
    end = doc.end_tick if end_tick is None else end_tick
    if end > doc.end_tick:
        doc.seek_tick(doc.end_tick)
        doc.run_ticks(end - doc.tick)
    doc.history.seek(doc.history.start)
    doc.seek_tick(0)
    engine, history = doc.engine, doc.history
    trace = engine.level.trace
    last_id = trace.base_id + len(trace.records) - 1
    previous = {p: state_text(s) for p, s in engine.level.blocks.items() if not s.is_air}
    start = dict(previous)
    changes: dict[int, dict[Pos, str]] = {}
    events: list[PistonEvent] = []
    power: dict[Pos, dict[str, Any]] = {}  # piston → its latest power note
    links: list[Link] = []
    for tick in range(1, end + 1):
        stop = doc.tick_steps.get(tick)
        if stop is None:
            raise RuntimeError(f"tick {tick} is not in the recorded history")
        order = 0
        while history.position < stop:
            level = engine.level
            pending = None
            if engine.phase is Phase.BLOCK_EVENTS and level.block_events:
                pending = next(iter(level.block_events))
            before = _moving(level) if pending else None
            old_state = level.get_block_state(pending[0]) if pending else None
            history.seek(history.position + 1)
            fresh = _new_records(trace, last_id)
            if fresh:
                last_id = fresh[-1].id
            for rec in fresh:
                if rec.kind == tr.NOTE and rec.detail.get("kind") == "piston_power":
                    power[rec.pos] = {
                        "via": list(rec.detail["via"]),
                        "via_block": short(rec.detail["via_block"]),
                        "quasi": bool(rec.detail["quasi"]),
                        "sources": [[list(p), short(b)] for p, b in rec.detail["sources"]],
                        "tick": tick,
                    }
                elif causes and rec.kind == tr.SET_BLOCK:
                    link = _link(trace, rec, tick)
                    if link is not None:
                        links.append(link)
            if pending is None or before is None:
                continue
            pos, block_id, b0, b1 = pending
            if "piston" not in block_id:
                continue
            after = _moving(engine.level)
            event = PistonEvent(
                tick=tick,
                order=order,
                piston=pos,
                kind=EVENT_NAMES.get(b0, str(b0)),
                facing=Direction.from_data3d(b1).name.lower(),
                sticky="sticky" in block_id,
                skipped=old_state is not None and old_state.block.id != block_id,
            )
            if event.kind == "extend" and pos in power:
                event.power = power[pos]
            order += 1
            for key, be in after.items():
                if key in before:
                    continue
                move = _movement_direction(be)
                event.moved.append(
                    Moved(_minus(be.pos, move), be.pos, state_text(be.moved_state), be.is_source)
                )
            for key, be in before.items():
                if key not in after:
                    event.finished_early.append((be.pos, state_text(be.moved_state)))
            events.append(event)
        current = {p: state_text(s) for p, s in engine.level.blocks.items() if not s.is_air}
        row = {p: s for p, s in current.items() if previous.get(p) != s}
        row.update({p: AIR for p in previous if p not in current})
        if row:
            changes[tick] = row
        previous = current
    return Recording(start, changes, events, end, links)


@dataclass(frozen=True)
class Link:
    """A block change and the change that caused it (``None``: a player action, a
    recorded edit or the start of the run)."""

    tick: int
    pos: Pos
    new: str
    cause_pos: Pos | None
    cause_tick: int | None
    cause_new: str | None
    via: str  # how: "update" (neighbor/shape update), "tick" (scheduled), "event", "moved"


def _link(trace: Any, rec: Any, tick: int) -> Link | None:
    d = rec.detail
    if d.get("old") == d.get("new"):
        return None
    chain = causes.chain(trace, rec, limit=40)
    via = "update"
    for cause in chain[1:]:
        if cause.kind == tr.STEP:
            kind = cause.detail.get("kind")
            via = {"scheduled_tick": "tick", "block_event": "event", "block_entity": "moved"}.get(
                kind, via
            )
            if kind not in ("scheduled_tick", "block_event", "block_entity"):
                return Link(tick, rec.pos, short(d.get("new")), None, None, None, "action")
        if (
            cause.kind == tr.SET_BLOCK
            and cause.pos != rec.pos
            and (cause.detail.get("old") != cause.detail.get("new"))
        ):
            return Link(
                tick,
                rec.pos,
                short(d.get("new")),
                cause.pos,
                cause.game_time - rec.game_time + tick,
                short(cause.detail.get("new")),
                via,
            )
    return Link(tick, rec.pos, short(d.get("new")), None, None, None, "start")


def short(text: Any) -> str:
    return str(text).replace("minecraft:", "")


# --------------------------------------------------------------------------- the doorway
def solid(state: str) -> bool:
    """Is a door cell filled? Air and the moving-piston placeholder count as open."""
    return not (state == AIR or state.startswith("moving_piston") or state.endswith("_air"))


def frames(rec: Recording, cells: list[Pos]) -> list[str]:
    """Per tick, one character per cell (sorted like ``cells``): '#' solid, '.' open,
    '~' moving."""
    out = []
    for t in range(rec.end_tick + 1):
        values = rec.states_at(cells, t)
        out.append(
            "".join(
                "~" if values[c].startswith("moving_piston") else ("#" if solid(values[c]) else ".")
                for c in cells
            )
        )
    return out


def doorway_summary(rec: Recording, cells: list[Pos]) -> dict[str, Any]:
    """When the doorway is fully closed / fully open, tick by tick."""
    rows = frames(rec, cells)
    closed = [t for t, r in enumerate(rows) if set(r) == {"#"}]
    open_ = [t for t, r in enumerate(rows) if set(r) <= {"."}]
    return {"frames": rows, "closed_ticks": closed, "open_ticks": open_}


END_STATES = {"closed": "#", "opened": ".", "open": "."}


def check_markers(
    rec: Recording, cells: list[Pos], markers: dict[int, str]
) -> list[dict[str, Any]]:
    """The world's markers name end states ("Closed", "Opened") at ticks. A marker holds
    when the doorway is in that state there: every cell solid for "Closed", every cell
    empty for "Opened" (``door``), or, for contraptions whose rest state is not an empty
    hole (a staircase), the frame equals the build's frame and the build is that state
    (the end states' frames must differ: a doorway that never moves proves nothing).
    ``since``: the first tick of the run of
    identical frames that ends at the marker."""
    rows = frames(rec, cells)
    build = rows[0]
    ends = {t: n for t, n in markers.items() if n.lower() in END_STATES}
    # Which end state is the build? The one whose marker frame equals the build frame,
    # provided the end states differ at all (a doorway that never changes is no proof).
    distinct = len({rows[t] for t in ends if t <= rec.end_tick}) > 1
    build_state = (
        next(
            (n.lower() for t, n in sorted(ends.items()) if t <= rec.end_tick and rows[t] == build),
            None,
        )
        if distinct
        else None
    )
    results = []
    for tick, name in sorted(markers.items()):
        word = name.lower()
        if word not in END_STATES or tick > rec.end_tick:
            results.append({"tick": tick, "marker": name, "checked": False})
            continue
        frame = rows[tick]
        door = set(frame) == {END_STATES[word]}
        same_as_build = frame == build and build_state == word
        ok = door or same_as_build
        first = tick
        while first > 0 and rows[first - 1] == frame:
            first -= 1
        results.append(
            {
                "tick": tick,
                "marker": name,
                "checked": True,
                "ok": ok,
                "how": "door" if door else "build frame" if same_as_build else None,
                "since": first,
                "frame": frame,
            }
        )
    return results
