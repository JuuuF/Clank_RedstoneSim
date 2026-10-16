"""Time commands: the view (``run``, ``step``, ``back``, ``seek``, ``where``), the timeline
(``at``, ``edits``, ``edit``, ``pulse``, ``marker``) and ``undo``/``redo``.

Ticks (doc/cli.md, "Time"): tick 0 is the build; tick T is the world after T game ticks.
An edit "at tick T" happens between tick T and tick T+1, like a player acting at that
moment, so ``show`` at tick T already shows it.
"""

from __future__ import annotations

from typing import Any

from redsim.cli.commands.common import name_of, tick_line, view_data
from redsim.cli.language import Args, CliError, format_pos
from redsim.cli.registry import Output, command, lookup
from redsim.cli.session import Session, pop_version
from redsim.cli.views import short


@command(
    "at",
    group="time",
    usage="at T COMMAND [ARGS ...]",
    summary="Run a command at tick T: record an edit there, or look at that tick.",
    help="""
    With an editing command (`place`, `set`, `use`, `break`, `fill`, `plate`, `hit`, …) the
    edit is recorded on the timeline at tick T instead of changing the build: it happens
    between tick T and tick T+1, like a player acting at that moment, and runs again
    whenever the simulation passes that tick. Edits recorded later stay where they are
    (the history is simulated again from T). `at 0 …` is the same as no `at`: the build.

    With a command that only looks (`show`, `inspect`, `why`, …) it looks at tick T and
    leaves the view where it was.
    """,
    examples=(
        "at 5 use @A              # flip lever A at tick 5",
        "at 12 set 4 1 0 air      # remove the block at tick 12",
        "at 8 show y=1            # the map at tick 8",
        "at 20 inspect @OUT",
    ),
    kind="meta",
    data="the data of COMMAND",
)
def at(session: Session, args: Args) -> Output:
    tick = args.tick("the tick")
    words = args.rest()
    if not words:
        raise CliError("at: which command? at T COMMAND …")
    cmd = lookup(words[0])
    if cmd is None:
        raise CliError(f"at: unknown command {words[0]!r}")
    if cmd.kind == "edit":
        session.edit_tick = tick
        try:
            return session.execute(words)
        finally:
            session.edit_tick = 0
    if cmd.kind == "view":
        session.restore_view()
        view = session.view_now()
        session.goto(tick)
        try:
            return session.execute(words)
        finally:
            session.goto_view(view)
    raise CliError(f"at: {cmd.name} cannot run at a tick (only edits and inspections)")


@command(
    "run",
    group="time",
    usage="run [N] | run until T",
    summary="Move the view N ticks forward (default 1), simulating as needed.",
    help="""
    Advances the view by N ticks (or to tick T). Inside the recorded history this replays
    it (with its recorded edits); past its end the simulation runs on and the history
    grows. Then prints where the view is and, for every monitored or labeled block, its
    value now (see `waves` for a whole timeline).
    """,
    examples=("run", "run 20", "run until 100"),
    kind="time",
    data='{"tick", "end_tick", "inside_tick", "values": {name: value}}',
)
def run(session: Session, args: Args) -> Output:
    doc = session.doc
    if args.option("until"):
        target = args.tick()
    else:
        target = doc.tick + (args.number("a number of ticks") if args.more() else 1)
    args.done()
    if not doc.can_edit:
        doc.history.finish_tick()
        doc._changed()
    session.goto(max(0, target))
    session.changed = True
    return _where(session)


def _where(session: Session) -> Output:
    from redsim.editor.monitor import monitor_value

    doc = session.doc
    out = Output([f"now {tick_line(session)}"])
    positions: dict[str, Any] = {}
    for name, label in sorted(doc.labels.items()):
        positions[f"@{name}"] = label.pos
    for pos in doc.monitors:
        positions.setdefault(name_of(doc, pos), pos)
    values = {key: monitor_value(doc.level, pos) for key, pos in positions.items()}
    if values:
        out.add("  " + "  ".join(f"{k}={v}" for k, v in values.items()))
    out.data = {**view_data(session), "values": values}
    return out


@command(
    "seek",
    group="time",
    usage="seek T",
    summary="Move the view to tick T (simulating further if needed).",
    help="Moves the view to tick T: back into the recorded history or forward past it.",
    examples=("seek 0", "seek 37"),
    kind="time",
    data='{"tick", "end_tick", "inside_tick", "values"}',
    aliases=("goto",),
)
def seek(session: Session, args: Args) -> Output:
    target = args.tick()
    args.done()
    session.goto(target)
    session.changed = True
    return _where(session)


@command(
    "back",
    group="time",
    usage="back [N]",
    summary="Move the view N ticks back (default 1).",
    help="Moves the view N ticks back in the recorded history (not before tick 0).",
    examples=("back", "back 10"),
    kind="time",
    data='{"tick", "end_tick", "inside_tick", "values"}',
)
def back(session: Session, args: Args) -> Output:
    count = args.number("a number of ticks") if args.more() else 1
    args.done()
    view = session.view_now()
    session.goto(max(0, view[0] - count + (1 if view[1] else 0)))
    session.changed = True
    return _where(session)


@command(
    "step",
    group="time",
    usage="step [N] | step back [N]",
    summary="Run N single engine steps (inside a tick) and show what each did, or go back.",
    help="""
    A game tick is a series of steps (doc/mechanics/tick-scheduling.md): the tick start,
    each scheduled tick (in priority order), each block event, each entity, each block
    entity. `step` runs them one at a time and prints each with the blocks it changed, so
    you can see the order things happen in. A tick with nothing to do is a single step.
    The view is then *inside* a tick: inspection commands show the world at that moment;
    edits still go to the build or `at T`. `run` finishes the tick. `step back [N]` goes
    back N steps (the same steps run again when you step forward).
    """,
    examples=("step", "step 5", "step back"),
    kind="time",
    data="""{"steps": [{"index", "kind", "pos", "changes": [{"pos", "from", "to"}]}],
    "tick", "inside_tick"}""",
)
def step(session: Session, args: Args) -> Output:
    from redsim.sim import trace as tr

    backwards = args.option("back")
    count = args.number("a number of steps") if args.more() else 1
    args.done()
    doc = session.doc
    if backwards:
        for _ in range(count):
            if not doc.step_back():
                break
        session.changed = True
        out = Output([f"stepped back {count}: now {tick_line(session)}; next: "
                      f"{doc.engine.peek_next_step()}"])  # fmt: skip
        out.data = {"steps": [], **view_data(session)}
        return out
    out = Output()
    steps = []
    for _ in range(count):
        info = doc.step()
        changes = []
        for record in doc.level.trace.for_step(info.index):
            d = record.detail
            if record.kind == tr.SET_BLOCK and d.get("old") != d.get("new"):
                changes.append(
                    {
                        "pos": list(record.pos),
                        "from": short(str(d.get("old"))),
                        "to": short(str(d.get("new"))),
                    }
                )
        where = f" at {name_of(doc, info.pos)}" if info.pos is not None else ""
        detail = info.detail.get("block") or info.detail.get("info") or ""
        out.add(
            f"  step {info.index}: {info.kind.replace('_', ' ')}{where} "
            f"{short(str(detail))}".rstrip()
        )
        for change in changes:
            out.add(f"      {format_pos(tuple(change['pos']))}  {change['from']} → {change['to']}")
        steps.append(
            {
                "index": info.index,
                "kind": info.kind,
                "pos": list(info.pos) if info.pos else None,
                "changes": changes,
            }
        )
    session.changed = True
    if doc.can_edit:
        out.add(f"tick {doc.tick} is complete; next: {doc.engine.peek_next_step()}")
    else:
        out.add(f"now {tick_line(session)}; next: {doc.engine.peek_next_step()}")
    out.data = {"steps": steps, **view_data(session)}
    return out


@command(
    "settle",
    group="time",
    usage="settle [max N]",
    summary="Let the build settle (torches react, …) and make that state the build.",
    help="""
    Right after building, a contraption is often not in its steady state yet: a torch
    placed next to a powered block is still lit, a lamp still on, wire still powered. They
    react in the first ticks. `settle` simulates the build alone (without the timeline's
    edits) until a tick passes with no block change and nothing pending (scheduled ticks,
    block events, moving pistons, falling blocks), at most N ticks (default 200), and
    makes that state the new build (tick 0). The timeline's edits keep their tick numbers;
    the output lists what changed. A clock never settles: then nothing changes and
    `settle` says so. This is the editor's "Set tick 0 here" after letting the circuit
    run, without moving the timeline.
    """,
    examples=("settle", "settle max 50"),
    kind="time",
    data='{"ticks": ticks it took or null, "changes": [{"pos", "from", "to"}]}',
)
def settle(session: Session, args: Args) -> Output:
    from redsim.editor.document_history import EditError

    limit = args.option_int("max", 200)
    args.done()
    doc = session.doc
    old = dict(doc.history.base.level.blocks)
    try:
        ticks = doc.settle_build(limit)
    except EditError as exc:
        raise CliError(str(exc)) from exc
    if ticks is None:
        return Output(
            [
                f"did not settle within {limit} ticks (a clock, or something always moving): "
                "the build is unchanged"
            ],
            {"ticks": None, "changes": []},
        )
    if ticks == 0:
        return Output(["the build is settled already"], {"ticks": 0, "changes": []})
    session.changed = True
    new = doc.history.base.level.blocks
    air = doc.level.air
    changes = [
        {"pos": list(p), "from": short(repr(old.get(p, air))), "to": short(repr(new.get(p, air)))}
        for p in sorted(set(old) | set(new), key=lambda q: (q[1], q[2], q[0]))
        if old.get(p, air) is not new.get(p, air)
    ]
    out = Output(
        [f"settled after {ticks} ticks; that is the build now ({len(changes)} blocks changed)"]
    )
    for change in changes[:50]:
        out.add(f"  {name_of(doc, tuple(change['pos'])):<12} {change['from']} → {change['to']}")
    out.data = {"ticks": ticks, "changes": changes}
    return out


@command(
    "rebase",
    group="time",
    usage="rebase",
    summary='Make the view tick the new build (the editor\'s "Set tick 0 here").',
    help="""
    The world at the view tick becomes the build (tick 0): the history before it is
    dropped (edits recorded before the view tick are baked into the build), edits
    recorded later move earlier by the view tick, and the simulated length is kept. Use
    `settle` instead to just let a fresh build react.
    """,
    examples=("seek 6", "rebase"),
    kind="time",
    data='{"tick": the old tick that is now 0}',
)
def rebase(session: Session, args: Args) -> Output:
    from redsim.editor.document_history import EditError

    args.done()
    doc = session.doc
    here = doc.tick
    try:
        doc.set_tick_zero()
    except EditError as exc:
        raise CliError(str(exc)) from exc
    session.changed = True
    return Output([f"tick {here} is the build now (tick 0)"], {"tick": here})


@command(
    "where",
    group="time",
    usage="where",
    summary="Show the view tick, the simulated length and the next engine step.",
    help="""
    Prints where the view is in time, how far the history is simulated and, inside a
    tick, what the next engine step will do.
    """,
    examples=("where",),
    kind="view",
    data='{"tick", "end_tick", "inside_tick", "next"}',
)
def where(session: Session, args: Args) -> Output:
    args.done()
    doc = session.doc
    out = Output([f"view {tick_line(session)}", f"  next step: {doc.engine.peek_next_step()}"])
    out.data = {**view_data(session), "next": doc.engine.peek_next_step()}
    return out


# ---------------------------------------------------------------------------- timeline
def _timeline(session: Session) -> list[dict[str, Any]]:
    """The recorded edits in tick order, numbered E1, E2, … (pulses too)."""
    doc = session.doc
    entries: list[dict[str, Any]] = []
    for index in sorted(doc.history.inputs, key=lambda i: (doc.edit_ticks.get(i, 0), i)):
        action = doc.history.inputs[index]
        tick = doc.edit_ticks.get(index, 0)
        payload = action.payload or {}
        if action.kind == "power_pulse":
            what = f"power {payload.get('strength', 15)} for {payload.get('ticks', 1)} ticks" + (
                " (muted)" if payload.get("muted") else ""
            )
        else:
            what = action.label or action.kind
            if action.state and action.kind in ("place", "setblock", "fill"):
                what = f"{action.kind} {short(action.state)}"
        entries.append(
            {
                "id": f"E{len(entries) + 1}",
                "index": index,
                "tick": tick,
                "kind": action.kind,
                "pos": list(action.pos),
                "what": what,
            }
        )
    return entries


@command(
    "edits",
    group="time",
    usage="edits",
    summary="List the timeline: recorded edits and power pulses, with ids E1, E2, ….",
    help="""
    Lists everything recorded on the timeline, in tick order: edits made with `at T …`
    and power pulses. Each gets an id (E1, E2, …) for `edit`; the ids are positions in this
    list, so they change when the timeline changes: list again before using them.
    """,
    examples=("edits",),
    kind="view",
    data='{"edits": [{"id", "tick", "kind", "pos", "what"}]}',
)
def edits(session: Session, args: Args) -> Output:
    args.done()
    doc = session.doc
    entries = _timeline(session)
    out = Output(
        [
            f"  {e['id']:<4} tick {e['tick']:<4} {name_of(doc, tuple(e['pos'])):<12} {e['what']}"
            for e in entries
        ]
        or ["  (the timeline is empty: everything is in the build)"]
    )
    out.data = {"edits": [{k: v for k, v in e.items() if k != "index"} for e in entries]}
    return out


def _ids(session: Session, words: list[str]) -> list[dict[str, Any]]:
    entries = {e["id"]: e for e in _timeline(session)}
    if words == ["all"]:
        return list(entries.values())
    chosen = []
    for word in words:
        entry = entries.get(word.upper())
        if entry is None:
            raise CliError(f"edit: no {word} on the timeline (see: edits)")
        chosen.append(entry)
    if not chosen:
        raise CliError("edit: which edits? give ids like E1 E2, or all")
    return chosen


@command(
    "edit",
    group="time",
    usage="edit move IDS to T | edit shift IDS by N | edit delete IDS | edit merge IDS [to T]",
    summary="Move, shift, delete or merge recorded edits (ids from 'edits').",
    help="""
    Changes the timeline. IDS are ids from `edits` (E1 E3 …) or `all`.

    - `move IDS to T`: the edits happen at tick T (all of them, keeping their order);
    - `shift IDS by N`: each moves N ticks (negative: earlier);
    - `delete IDS`: they are removed;
    - `merge IDS [to T]`: they all happen at T (default: the earliest of them).

    Moving an edit to tick 0 puts it into the build. The history is simulated again; edits
    that cannot happen at their new tick (their spot is taken) are dropped and reported.
    """,
    examples=("edit move E2 to 15", "edit shift E1 E2 by -3", "edit delete E4", "edit delete all"),
    kind="time",
    data='{"changed": [ids], "failed": number of edits dropped}',
)
def edit(session: Session, args: Args) -> Output:
    from redsim.editor.document_history import EditError

    doc = session.doc
    verb = args.choice(("move", "shift", "delete", "merge"), "move, shift, delete or merge")
    ids: list[str] = []
    while args.more() and args.peek() not in ("to", "by"):
        ids.append(args.word())
    chosen = _ids(session, ids)
    indices = [e["index"] for e in chosen]
    try:
        if verb == "delete":
            args.done()
            failed = doc.delete_edits(indices)
        elif verb == "move":
            if not args.option("to"):
                raise CliError("edit move: say where: to T")
            tick = args.tick()
            args.done()
            failed = doc.merge_edits(indices, tick)
        elif verb == "shift":
            if not args.option("by"):
                raise CliError("edit shift: say how far: by N")
            delta = args.number("a number of ticks")
            args.done()
            failed = doc.move_edits(indices, delta)
        else:
            merge_tick = args.tick() if args.option("to") else None
            args.done()
            failed = doc.merge_edits(indices, merge_tick)
    except EditError as exc:
        raise CliError(str(exc)) from exc
    session.changed = True
    out = Output(
        [
            f"{verb} {', '.join(e['id'] for e in chosen)}: done"
            + (f"; {failed} edits could not happen there and were dropped" if failed else "")
        ]
    )
    out.data = {"changed": [e["id"] for e in chosen], "failed": failed}
    return out


@command(
    "pulse",
    group="time",
    usage="pulse POS at T [for N] [strength S]",
    summary="Power a position from tick T for N ticks (a test signal, editor power).",
    help="""
    Adds a power pulse to the timeline: the position gets signal strength S (default 15)
    from every side, like an invisible redstone block next to it, from tick T (at least 1)
    for N ticks (default 2). It is locked to the position, whatever block is there
    (ADR-026). `for 0` makes a 0-tick pulse: on and off inside tick T+1. This is the
    simplest way to drive a contraption's inputs in tests; it is an editor tool, not a
    game mechanic (doc/differences.md).

    Exactly when it is on: it switches on between tick T and tick T+1 (like an edit at
    tick T, so the view at tick T already shows it) and off at the start of tick T+N+1:
    the views of ticks T … T+N show it on. A lamp powered by it lights at tick T and goes
    off 4 ticks after the pulse ends, at tick T+N+5.
    """,
    examples=("pulse @A at 2 for 10", "pulse 0 1 0 at 5 for 1 strength 7", "pulse @CLK at 3 for 0"),
    kind="time",
    data='{"pos", "tick", "ticks", "strength"}',
)
def pulse(session: Session, args: Args) -> Output:
    from redsim.editor.document_history import EditError

    pos = args.pos()
    if not args.option("at"):
        raise CliError("pulse: say when: at T")
    tick = args.tick()
    if tick < 1:
        raise CliError("pulse: pulses start at tick 1 or later (tick 0 is the build)")
    ticks = args.option_int("for", 2)
    strength = args.option_int("strength", 15)
    args.done()
    try:
        session.doc.add_pulse(pos, tick, strength, ticks)
    except EditError as exc:
        raise CliError(str(exc)) from exc
    if session.doc.notice == "power pulse.":  # the editor's confirmation, nothing more
        session.doc.notice = ""
    session.changed = True
    what = "a 0-tick pulse" if ticks == 0 else f"{ticks} ticks"
    out = Output(
        [f"pulse at {name_of(session.doc, pos)}: strength {strength} from tick {tick}, {what}"]
    )
    out.data = {"pos": list(pos), "tick": tick, "ticks": ticks, "strength": strength}
    return out


@command(
    "marker",
    group="time",
    usage='marker T ["NAME"]',
    summary="Name a tick on the timeline (no name: remove the marker).",
    help="""
    Markers name moments ("door open", "clock period") for people looking at the
    timeline in the editor.
    """,
    examples=('marker 12 "door open"', "marker 12"),
    kind="time",
    data='{"tick", "name"}',
)
def marker(session: Session, args: Args) -> Output:
    tick = args.tick()
    name = " ".join(args.rest())
    session.doc.set_marker(tick, name)
    session.changed = True
    return Output([f"marker at tick {tick}: {name or '(removed)'}"], {"tick": tick, "name": name})


@command(
    "undo",
    group="time",
    usage="undo",
    summary="Undo the last change (this run's last command, or the last earlier run).",
    help="""
    Within one run of redsim-cli (a script, `-c` or a shell) `undo` reverts the last
    command that changed something. When there is nothing left to undo in this run, it
    restores the world file as it was before the previous run that changed it (the undo
    file `WORLD.undo` keeps 20 versions). `redo` goes forward again.
    """,
    examples=("undo",),
    kind="time",
    data='{"undid": "command" or "file version"}',
)
def undo(session: Session, args: Args) -> Output:
    args.done()
    doc = session.doc
    if doc._undo:
        label = doc.undo_labels[0]
        view = session.view_now()
        doc.undo()
        session.goto_view(view)  # the editor's undo goes to the edit's tick; keep the view
        session.changed = True
        return Output([f"undid: {label}"], {"undid": "command", "label": label})
    return _file_version(session, "undo")


@command(
    "redo",
    group="time",
    usage="redo",
    summary="Redo what undo undid.",
    help="""
    The reverse of `undo`: within the run command by command, else the file version that
    `undo` replaced.
    """,
    examples=("redo",),
    kind="time",
    data='{"redid": "command" or "file version"}',
)
def redo(session: Session, args: Args) -> Output:
    args.done()
    doc = session.doc
    if doc._redo:
        view = session.view_now()
        doc.redo()
        session.goto_view(view)
        session.changed = True
        return Output(["redid the last undone command"], {"redid": "command"})
    return _file_version(session, "redo")


def _file_version(session: Session, which: str) -> Output:
    import tempfile
    from pathlib import Path

    from redsim.editor.document import Document

    version = pop_version(session.path, which)
    if version is None:
        raise CliError(f"{which}: nothing to {which}")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "version.redsim.json"
        path.write_text(version)
        document = Document.open(path)
    document.path = session.path
    session.adopt(document)
    session.file_undone = True
    key = "undid" if which == "undo" else "redid"
    return Output(
        [f"{key} the previous run: the file is back to its earlier version"], {key: "file version"}
    )
