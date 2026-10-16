"""Inspection commands: ``show``, ``inspect``, ``why``, ``trace``, ``waves``, ``monitor``,
``diff``, ``ticks``, ``find``, ``entities``. They only read (``kind="view"``); ``at T``
in front of one looks at tick T."""

from __future__ import annotations

from typing import Any

from redsim.cli.commands.common import content_box, name_of, named, region, tick_line, view_data
from redsim.cli.language import Args, CliError, format_pos, parse_block
from redsim.cli.registry import Output, command
from redsim.cli.session import Session
from redsim.cli.views import (
    PLANES,
    Legend,
    describe_signals,
    neighbors_text,
    orientation_text,
    render_map,
    short,
    side_signals,
    state_text,
    tick_ruler,
    wave_row,
)
from redsim.core.pos import Pos

#: The widest map ``show`` draws without ``wide``.
MAX_WIDTH = 64


def _range_value(text: str, what: str) -> tuple[int, int]:
    low, sep, high = text.partition("..")
    try:
        a = int(low)
        b = int(high) if sep else a
    except ValueError as exc:
        raise CliError(f"show: {what}= needs a number or A..B, found {text!r}") from exc
    return (min(a, b), max(a, b))


@command(
    "show",
    group="inspect",
    usage="show [y=Y|y=A..B|x=X|z=Z] [from POS to POS | around POS [radius R]] [power] [wide]",
    summary="Draw the world as text maps: layers from above, or a slice from the side.",
    help="""
    Draws maps with one two-character cell per block (doc/cli.md, "Reading a map"):
    upper-case letters are components that are on, lower-case ones are off, the second
    character is an arrow (where it outputs or pushes) or a signal strength. A legend
    under the maps explains every code used.

    - `y=Y` (or `y=A..B`): layers seen from above, x to the right, north at the top.
      Without a view, every layer of the area is drawn from above.
    - `z=Z`: a vertical slice seen from the south (x to the right, up at the top).
    - `x=X`: a vertical slice seen from the west (z to the right, south at the right).

    The area is the box around everything above the floor (plus one block around it),
    or `from POS to POS`, or `around POS [radius R]` (default radius 4: the layers just
    below, at and above POS). `power` draws signal strengths instead of blocks (hex digit,
    `.` for none). Maps wider than 64 blocks need `wide`. The labels inside the area are
    listed under the legend.
    """,
    examples=(
        "show",
        "show y=1",
        "show y=1..3 power",
        "show z=0",
        "show around @OUT radius 3",
        "at 10 show y=1",
    ),
    kind="view",
    data="""{"tick", "view": "y"|"x"|"z", "layers": [{"at": coordinate, "rows": [{"v":
    coordinate, "cells": [code, ...]}]}], "h": [first, last], "legend": {code: words},
    "entities": [[x, y, z], ...], "labels": {name: [x, y, z]} (the labels in the area)}""",
)
def show(session: Session, args: Args) -> Output:
    doc = session.doc
    level = doc.level
    view = "y"
    fixed: tuple[int, int] | None = None
    for axis in ("y", "x", "z"):
        value = args.pop_key(axis)
        if value is not None:
            view, fixed = axis, _range_value(value, axis)
    power = False
    wide = False
    low: Pos | None = None
    high: Pos | None = None
    while args.more():
        if args.option("power"):
            power = True
        elif args.option("wide"):
            wide = True
        elif args.option("from"):
            low, high = region(args)
        elif args.option("around"):
            center = args.pos("the center")
            radius = args.option_int("radius", 4)
            low = (center[0] - radius, center[1] - 1, center[2] - radius)
            high = (center[0] + radius, center[1] + 1, center[2] + radius)
        else:
            args.done()
    if low is None or high is None:
        box = content_box(level, margin=1)
        if box is None:
            return Output(["(nothing above the floor yet: build something first)"], {"layers": []})
        low, high = box
    plane = PLANES[view]
    axes = {"x": 0, "y": 1, "z": 2}
    h_index, v_index = axes[plane.h.value], axes[plane.v.value]
    h_range = range(low[h_index], high[h_index] + 1)
    v_range = range(low[v_index], high[v_index] + 1)
    if len(h_range) > MAX_WIDTH and not wide:
        raise CliError(
            f"show: the map would be {len(h_range)} blocks wide; narrow it with from … to … "
            f"or around …, or add 'wide'"
        )
    depth_index = axes[view]
    if fixed is None:
        fixed = (low[depth_index], high[depth_index])
    legend = Legend()
    falling = [m.block_position for m in level.entities.values()]
    out = Output()
    layers = []
    order = range(fixed[1], fixed[0] - 1, -1) if view == "y" else range(fixed[0], fixed[1] + 1)
    for at_value in order:
        lines, grid = render_map(level, plane, at_value, h_range, v_range, power, falling, legend)
        kind = "signal strength" if power else "blocks"
        out.add(f"{view}={at_value}  {kind} {tick_line(session)}  ({plane.caption})")
        for line in lines:
            out.add(line)
        out.add()
        rows = [
            {"v": v, "cells": cells}
            for v, cells in zip(
                (list(v_range) if plane.v_down else list(v_range)[::-1]), grid, strict=True
            )
        ]
        layers.append({"at": at_value, "rows": rows})
    if not power:
        out.add("legend:")
        for line in legend.lines():
            out.add(line)
    inside = [
        (name, lab.pos) for name, lab in sorted(doc.labels.items())
        if all(low[i] <= lab.pos[i] <= high[i] for i in range(3))
        and (fixed[0] <= lab.pos[depth_index] <= fixed[1])
    ]  # fmt: skip
    if inside:
        out.add("labels: " + ", ".join(f"@{n} {format_pos(p)}" for n, p in inside))
    if falling:
        out.add("falling blocks: " + ", ".join(format_pos(p) for p in falling))
    out.data = {
        **view_data(session),
        "view": view,
        "layers": layers,
        "h": [h_range.start, h_range.stop - 1],
        "power": power,
        "legend": dict(legend.entries),
        "entities": [list(p) for p in falling],
        "labels": {n: list(p) for n, p in inside},
    }
    return out


@command(
    "inspect",
    group="inspect",
    usage="inspect POS [POS ...]",
    summary="Everything about a block: state, signals in and out, pending ticks, data.",
    help="""
    For each position: its full block state, its label and note, which way it works (for
    directional blocks: "input from the east, output to the west"), what signal it receives
    from each side and what it gives to each side, whether it is a solid block that
    conducts and how much power it has, its monitor value, what a comparator reads from
    it (containers, cauldrons, lecterns, …: `analog`), its pending scheduled ticks, its
    block-entity data (container items, comparator output, …) and its neighbors.

    Signals, as the game computes them (doc/mechanics/power-queries.md):

    - "receives west 15": the neighbor to the west gives this block 15 (`getSignal`:
      what a lamp, piston, repeater input or wire sees from that side);
    - "gives east 15": this block gives 15 to its east neighbor;
    - "(direct 15)": the direct part (`getDirectSignal`), which is what powers a solid
      block the signal goes into. A solid block powered directly then gives that power to
      the components around it ("powered 15" on its "conducts" line). Redstone wire gives
      a direct signal too, but other wire ignores blocks powered only by wire (that is
      Minecraft's "weak power"; torches, repeaters, comparators, levers and buttons give
      "strong power").
    - Sides are listed in the game's order: down, up, north, south, west, east. Wire on a
      solid block "receives" its own power back from below; the game's `getSignal`
      returns that, wire itself ignores it.
    """,
    examples=("inspect 3 1 0", "inspect @A @OUT", "at 7 inspect @OUT"),
    kind="view",
    data="""{"blocks": [{"pos", "state", "label", "signals": {side: {"in", "in_direct",
    "out", "out_direct"}}, "orientation", "conductor", "direct_power", "best_signal", "monitor",
    "analog" (comparator reading or null),
    "scheduled": [{"block", "tick", "priority"}], "block_entity", "neighbors":
    {side: state}}], "tick"}""",
)
def inspect(session: Session, args: Args) -> Output:
    from redsim.core.direction import ALL, Direction
    from redsim.core.pos import offset
    from redsim.editor.monitor import monitor_value

    positions = [args.pos()]
    while args.more():
        positions.append(args.pos())
    doc = session.doc
    level = doc.level
    base = doc.history.base_time
    out = Output()
    blocks = []
    for pos in positions:
        state = level.get_block_state(pos)
        label = next((n for n, lab in doc.labels.items() if lab.pos == pos), None)
        out.add(f"{named(doc, pos)}  {state_text(state)}   ({tick_line(session)})")
        if label and doc.labels[label].note:
            out.add(f"  note      {doc.labels[label].note}")
        orientation = orientation_text(state)
        if orientation:
            out.add(f"  faces     {orientation}")
        for line in describe_signals(level, pos):
            out.add(line)
        conductor = state.is_redstone_conductor(level, pos)
        direct = level.get_direct_signal_to(pos) if conductor else 0
        best = level.get_best_neighbor_signal(pos)
        if conductor:
            extra = " (it powers the components around it)" if direct else ""
            out.add(f"  conducts  yes, powered {direct} by direct signals{extra}")
        else:
            out.add("  conducts  no")
        value = monitor_value(level, pos)
        out.add(f"  value     {value}  (what the monitor and waves show)")
        analog = None
        if state.has_analog_output_signal():  # no simulated block reads the direction
            analog = state.get_analog_output_signal(level, pos, Direction.NORTH)
            out.add(f"  analog    {analog}  (what a comparator reads from it)")
        scheduled = [
            {
                "block": t.block_id.removeprefix("minecraft:"),
                "tick": t.trigger_tick - base,
                "priority": t.priority.name,
            }
            for t in [*level.block_ticks.pending(), *level.block_ticks.to_run]
            if t.pos == pos
        ]
        for t in scheduled:
            out.add(f"  pending   {t['block']} tick at tick {t['tick']} ({t['priority']})")
        events = [k for k in level.block_events if k[0] == pos]
        for _, block_id, b0, b1 in events:
            out.add(f"  event     {short(block_id)} block event ({b0}, {b1}) this tick")
        entity = level.get_block_entity(pos, create=False)
        data = entity.to_json() if entity is not None else None
        if data:
            out.add(f"  data      {data}")
        neighbor_lines = neighbors_text(level, pos, lambda p: name_of(doc, p))
        if neighbor_lines:
            out.add("  neighbors")
            for line in neighbor_lines:
                out.add(line)
        out.add()
        blocks.append(
            {
                "pos": list(pos),
                "state": state_text(state),
                "label": label,
                "signals": side_signals(level, pos),
                "conductor": conductor,
                "direct_power": direct,
                "best_signal": best,
                "orientation": orientation,
                "monitor": value,
                "analog": analog,
                "scheduled": scheduled,
                "block_entity": data,
                "neighbors": {
                    d.serialized: state_text(level.get_block_state(offset(pos, d))) for d in ALL
                },
            }
        )
    if out.lines and out.lines[-1] == "":
        out.lines.pop()
    out.data = {"blocks": blocks, **view_data(session)}
    return out


@command(
    "why",
    group="inspect",
    usage="why POS [max N]",
    summary="Why did this block last change? The chain of causes, back to its origin.",
    help="""
    Finds the last change of the block at POS (up to the view tick) and follows its causes
    backwards: the update that made it change, the block change that sent that update,
    the scheduled tick or block event behind that, back across ticks to the edit, pulse or
    build that started it. For a piston that extended it also says where its power came
    from (quasi-connectivity included) and why that is on. Newest first; each line shows
    the tick and position. Use `at T why POS` to ask about an earlier moment. The chain
    shows at most N links (default 60); a long one (a signal through many repeaters)
    ends with a line saying it goes on: ask `why` about the block it stopped at, or give
    a larger N.
    """,
    examples=("why @OUT", "at 9 why 3 1 0", "why @END max 400"),
    kind="view",
    data='{"pos", "causes": [{"tick", "pos", "text", "branch"}], "complete", "tick"}',
)
def why(session: Session, args: Args) -> Output:
    from redsim.sim.causes import MAX_LINKS
    from redsim.sim.causes import why as find_causes

    pos = args.pos()
    limit = args.option_int("max", MAX_LINKS)
    args.done()
    doc = session.doc
    base = doc.history.base_time
    view = session.view_now()
    if doc.can_edit:
        doc.trace_through(doc.tick)  # a trace without gaps back to the build
    causes = find_causes(doc.level.trace, pos, limit=max(2, limit))
    session.goto_view(view)
    complete = sum(1 for c in causes if not c.branch) < max(2, limit)
    out = Output()
    if not causes:
        out.add(f"{named(doc, pos)} has not changed since the build (up to {tick_line(session)})")
        out.data = {"pos": list(pos), "causes": [], "complete": True, **view_data(session)}
        return out
    first = causes[0]
    main = [c for c in causes if not c.branch]
    out.add(f"{named(doc, pos)} last changed at tick {first.tick - base}: {first.text}")
    branch_shown = False
    for cause in causes[1:]:
        if cause.branch and not branch_shown:
            out.add("  where the piston's power comes from:")
            branch_shown = True
        where = name_of(doc, cause.pos) if cause.pos is not None else "-"
        out.add(f"  ← tick {cause.tick - base:<4} {where:<12} {cause.text}")
        if not complete and cause is main[-1]:
            out.add(f"  … the chain goes on before this (shown: {len(main)} links; more "
                    "with max N, or ask why about that block)")  # fmt: skip
    out.data = {
        "pos": list(pos),
        "complete": complete,
        **view_data(session),
        "causes": [
            {
                "tick": c.tick - base,
                "pos": list(c.pos) if c.pos is not None else None,
                "text": c.text,
                "branch": c.branch,
            }
            for c in causes
        ],
    }
    return out


@command(
    "effects",
    group="inspect",
    usage="effects POS [max N]",
    summary="Where a signal goes: every block change the block's last change caused.",
    help="""
    The forward view of `why`: takes the last change of the block at POS up to the view
    tick (a lever switched on, a repeater turning on) and lists every block change it
    caused afterwards, oldest first: through the updates it sent, the scheduled ticks and
    block events those queued (in later ticks too), and so on, to the end of the simulated
    history. One line per block and tick: a block that changed several times in a tick
    (wire turning off passes through every power level) shows its first and last state
    and the number of changes. Use it to see where a signal goes and what it reaches, or
    to find out why something far away reacted. At most N lines (default 200).
    """,
    examples=("effects @A", "at 3 effects @CLOCK max 40"),
    kind="view",
    data="""{"pos", "change": {"tick", "text"} or null, "effects": [{"tick", "pos", "text",
    "changes"}]}""",
)
def effects(session: Session, args: Args) -> Output:
    from redsim.sim.causes import describe, last_change, state_change
    from redsim.sim.causes import effects as find_effects

    pos = args.pos()
    limit = args.option_int("max", 200)
    args.done()
    doc = session.doc
    base = doc.history.base_time
    view = session.view_now()
    upto = doc.tick
    doc.trace_through(doc.end_tick)  # the trace of the whole history, without gaps
    trace = doc.level.trace
    boundary = next((r.id for r in trace.records if r.game_time > upto + base), None)
    change = last_change(trace, pos, before=boundary)
    raw_limit = limit * 20
    found = find_effects(trace, change, raw_limit) if change is not None else []
    session.goto_view(view)
    out = Output()
    if change is None:
        out.add(f"{named(doc, pos)} has not changed since the build (up to tick {upto})")
        out.data = {"pos": list(pos), "change": None, "effects": []}
        return out
    # One line per block and tick: wire turning off passes through every power level.
    groups: dict[tuple[int, Any], list[Any]] = {}
    for r in found:
        groups.setdefault((r.game_time - base, r.pos), []).append(r)
    effects_data = []
    for (tick, where), records in list(groups.items())[:limit]:
        old, new = records[0].detail.get("old"), records[-1].detail.get("new")
        if old != new:
            text = state_change(str(old), str(new))
        else:
            text = describe(records[0]) + " and back"
        if len(records) > 1:
            text += f" ({len(records)} changes)"
        effects_data.append({"tick": tick, "pos": list(where) if where else None,
                             "text": text, "changes": len(records)})  # fmt: skip
    out.add(f"{named(doc, pos)} changed at tick {change.game_time - base}: {describe(change)}")
    count = len(effects_data)
    out.add(f"  it caused {count} change{'' if count == 1 else 's'}" + (":" if count else ""))
    for e in effects_data:
        where = name_of(doc, tuple(e["pos"])) if e["pos"] else "?"  # type: ignore[arg-type]
        out.add(f"  → tick {e['tick']:<4} {where:<12} {e['text']}")
    if len(groups) > limit or len(found) >= raw_limit:
        out.add(f"  … (stopped at {limit}; more with max N)")
    out.data = {"pos": list(pos),
                "change": {"tick": change.game_time - base, "text": describe(change)},
                "effects": effects_data}  # fmt: skip
    return out


@command(
    "trace",
    group="inspect",
    usage="trace [T] [near POS [radius R]]",
    summary="What happened during tick T, step by step (default: the view tick).",
    help="""
    Lists the engine steps of tick T in the order they ran (tick start, scheduled ticks,
    block events, entities, block entities, edits) and under each step the blocks it
    changed. `near POS` keeps only changes within R blocks (default 3) of POS. The tick
    is replayed for this (simulated first if it is past the end of the history); the
    view stays where it is.
    """,
    examples=("trace", "trace 7", "trace 7 near @OUT"),
    kind="view",
    data='{"tick", "steps": [{"index", "kind", "pos", "changes": [{"pos", "from", "to"}]}]}',
)
def trace(session: Session, args: Args) -> Output:
    from redsim.sim import trace as tr

    doc = session.doc
    tick = args.tick() if args.more() and (args.peek() or "").isdigit() else doc.tick
    near: Pos | None = None
    radius = 3
    if args.option("near"):
        near = args.pos()
        radius = args.option_int("radius", 3)
    args.done()
    view = session.view_now()
    if doc.can_edit and not doc.trace_tick(tick) and tick > doc.end_tick:
        session.goto(tick)  # simulate up to it (traced as it runs)
    game_time = tick + doc.history.base_time
    # Tick T's steps run between the boundaries after T-1 and T (the tick start of T is
    # recorded with game time T-1: the time advances inside it).
    low, high = doc.tick_steps.get(tick - 1), doc.tick_steps.get(tick)
    steps: dict[int, dict[str, Any]] = {}
    for record in doc.level.trace.records:
        if low is not None and high is not None:
            if not low <= record.step < high:
                continue
        elif record.game_time != game_time:
            continue
        if record.kind == tr.STEP:
            steps[record.step] = {
                "index": record.step,
                "kind": str(record.detail.get("kind")),
                "pos": list(record.pos) if record.pos else None,
                "block": short(str(record.detail.get("block") or "")),
                "changes": [],
            }
        elif record.kind == tr.SET_BLOCK and record.detail.get("old") != record.detail.get("new"):
            if near is not None and max(abs(record.pos[i] - near[i]) for i in range(3)) > radius:
                continue
            entry = steps.get(record.step)
            if entry is not None:
                entry["changes"].append(
                    {
                        "pos": list(record.pos),
                        "from": short(str(record.detail.get("old"))),
                        "to": short(str(record.detail.get("new"))),
                    }
                )
    shown = [s for s in steps.values() if near is None or s["changes"]]
    near_text = f", {len(shown)} of them changed blocks near {format_pos(near)}" if near else ""
    count = f"{len(steps)} step{'' if len(steps) == 1 else 's'}"
    out = Output([f"tick {tick}: {count}{near_text}"])
    for entry in shown:
        where = f" at {name_of(doc, tuple(entry['pos']))}" if entry["pos"] else ""
        out.add(
            f"  step {entry['index']}: {entry['kind'].replace('_', ' ')}{where} "
            f"{entry['block']}".rstrip()
        )
        for change in entry["changes"]:
            out.add(
                f"      {name_of(doc, tuple(change['pos'])):<12} {change['from']} → {change['to']}"
            )
    session.goto_view(view)
    if not steps:
        out.add(
            "  (tick 0 is the build: nothing runs in it)"
            if tick == 0
            else "  (no trace for that tick)"
        )
    out.data = {"tick": tick, "steps": shown}
    return out


def _positions_to_watch(session: Session, args: Args) -> list[Pos]:
    positions = []
    while args.more() and args.peek() != "ticks":
        positions.append(args.pos())
    if positions:
        return positions
    doc = session.doc
    found: list[Pos] = [label.pos for _, label in sorted(doc.labels.items())]
    found += [p for p in doc.monitors if p not in found]
    return found


@command(
    "waves",
    group="inspect",
    usage="waves [POS ...] [ticks A..B]",
    summary="Signal timelines: one hex digit per tick for each block (a logic analyzer).",
    help="""
    Prints, for each position, its value at every tick of the range as one character: a
    hex digit 1-f for 1-15, `.` for 0. The value is what the editor's monitor shows: the
    power of wire and target blocks, a comparator's output, 15 or 0 for lit/powered/
    extended blocks (lamps, torches, repeaters, levers, pistons), a source's reading, and
    for other blocks the strongest signal they receive. Without positions: every labeled
    and monitored block. The range defaults to the whole simulated history (at most 120
    ticks; give `ticks A..B` for others; ticks past the end are simulated).
    """,
    examples=("waves", "waves @A @B @OUT ticks 0..40", "waves 0 1 0 5 1 0"),
    kind="view",
    data='{"from", "to", "rows": [{"pos", "name", "block", "values": [int, ...]}]}',
)
def waves(session: Session, args: Args) -> Output:
    from redsim.editor.monitor import monitor_value

    doc = session.doc
    positions = _positions_to_watch(session, args)
    low, high = 0, min(doc.end_tick, 119)
    if args.option("ticks"):
        low, high = args.tick_range()
    args.done()
    if not positions:
        raise CliError("waves: which blocks? give positions, or label/monitor some first")
    if high - low > 400:
        raise CliError("waves: at most 400 ticks at once")
    view = session.view_now()
    values: dict[Pos, list[int]] = {p: [] for p in positions}
    for tick in range(low, high + 1):
        session.goto(tick)
        for pos in positions:
            values[pos].append(monitor_value(doc.level, pos))
    blocks = {p: doc.level.get_block_state(p).block.name for p in positions}
    session.goto_view(view)
    names = {p: f"{name_of(doc, p)} {blocks[p]}" for p in positions}
    width = max(len(n) for n in names.values())
    ruler = tick_ruler(low, high)
    out = Output([f"{'tick':<{width}}  {ruler[0]}", f"{'':<{width}}  {ruler[1]}"])
    for pos in positions:
        out.add(f"{names[pos]:<{width}}  {wave_row(values[pos])}")
    out.add(f"(ticks {low}..{high}; digit = value 1-15 in hex, . = 0)")
    out.data = {
        "from": low,
        "to": high,
        "rows": [
            {"pos": list(p), "name": name_of(doc, p), "block": blocks[p], "values": values[p]}
            for p in positions
        ],
    }
    return out


@command(
    "changes",
    group="inspect",
    usage="changes POS [POS ...] [ticks A..B]",
    summary="How a block's state changed over time: each new state with its tick.",
    help="""
    For each position, the block state at the start of the range and then every tick
    where it changed, with the new state. Where `waves` shows signal values, `changes`
    shows the blocks themselves: a piston extending, a block arriving where a piston
    pushed it, a repeater locking. The range defaults to the whole simulated history.
    """,
    examples=("changes 2 1 0", "changes @DOOR @P ticks 0..30"),
    kind="view",
    data='{"from", "to", "rows": [{"pos", "name", "changes": [{"tick", "state"}]}]}',
)
def changes(session: Session, args: Args) -> Output:
    doc = session.doc
    positions = []
    while args.more() and args.peek() != "ticks":
        positions.append(args.pos())
    low, high = 0, doc.end_tick
    if args.option("ticks"):
        low, high = args.tick_range()
    args.done()
    if not positions:
        raise CliError("changes: which positions?")
    view = session.view_now()
    seen: dict[Pos, list[tuple[int, str]]] = {p: [] for p in positions}
    for tick in range(low, high + 1):
        session.goto(tick)
        for pos in positions:
            text = state_text(doc.level.get_block_state(pos))
            if not seen[pos] or seen[pos][-1][1] != text:
                seen[pos].append((tick, text))
    session.goto_view(view)
    out = Output()
    for pos in positions:
        out.add(f"{named(doc, pos)} (ticks {low}..{high}):")
        for tick, text in seen[pos]:
            out.add(f"  tick {tick:<4} {text}")
    out.data = {
        "from": low,
        "to": high,
        "rows": [
            {
                "pos": list(p),
                "name": name_of(doc, p),
                "changes": [{"tick": t, "state": text} for t, text in seen[p]],
            }
            for p in positions
        ],
    }
    return out


@command(
    "monitor",
    group="inspect",
    usage="monitor add POS [POS ...] | monitor remove POS [POS ...] | monitor list",
    summary="Choose the blocks the editor's timeline monitors (and waves shows).",
    help="""
    Monitored blocks get a signal track in the editor's timeline and are shown by `waves`
    and `run` when no positions are given (labeled blocks are shown too). They are saved
    with the world.
    """,
    examples=("monitor add @OUT 4 1 0", "monitor remove 4 1 0", "monitor list"),
    kind="meta",
    data='{"monitors": [[x, y, z], ...]}',
)
def monitor(session: Session, args: Args) -> Output:
    doc = session.doc
    verb = args.choice(("add", "remove", "list"), "add, remove or list")
    if verb != "list":
        positions = [args.pos()]
        while args.more():
            positions.append(args.pos())
        for pos in positions:
            if (pos in doc.monitors) != (verb == "add"):
                doc.toggle_monitor(pos)
        session.changed = True
    args.done()
    out = Output([f"monitored: {', '.join(name_of(doc, p) for p in doc.monitors) or 'nothing'}"])
    out.data = {"monitors": [list(p) for p in doc.monitors]}
    return out


@command(
    "diff",
    group="inspect",
    usage="diff A [B]",
    summary="Which blocks differ between tick A and tick B (default: the view tick).",
    help="""
    Compares the world at two ticks and lists every block that is different, with its
    state at A and at B. Handy after `run` (`diff 0` shows everything that changed since
    the build) and for finding what a pulse or an edit affected.
    """,
    examples=("diff 0", "diff 4 9"),
    kind="view",
    data='{"from", "to", "changes": [{"pos", "from", "to"}]}',
)
def diff(session: Session, args: Args) -> Output:
    doc = session.doc
    first = args.tick("the first tick")
    second = args.tick("the second tick") if args.more() else doc.tick
    args.done()
    view = session.view_now()
    session.goto(first)
    before = dict(doc.level.blocks)
    session.goto(second)
    after = dict(doc.level.blocks)
    session.goto_view(view)
    air = doc.level.air
    changes = []
    for pos in sorted(set(before) | set(after), key=lambda p: (p[1], p[2], p[0])):
        a, b = before.get(pos, air), after.get(pos, air)
        if a is not b:
            changes.append({"pos": list(pos), "from": state_text(a), "to": state_text(b)})
    out = Output([f"{len(changes)} blocks differ between tick {first} and tick {second}"])
    for change in changes[:200]:
        out.add(f"  {name_of(doc, tuple(change['pos'])):<12} {change['from']} → {change['to']}")
    if len(changes) > 200:
        out.add(f"  … {len(changes) - 200} more (see --json)")
    out.data = {"from": first, "to": second, "changes": changes}
    return out


@command(
    "ticks",
    group="inspect",
    usage="ticks",
    summary="Pending scheduled ticks and block events at the view.",
    help="""
    Lists what is waiting to happen: scheduled ticks (a repeater about to switch, a lamp
    about to turn off, …) with the tick they run at and their priority, and block events
    (pistons) queued in the current tick.
    """,
    examples=("ticks", "at 3 ticks"),
    kind="view",
    data="""{"scheduled": [{"pos", "block", "tick", "priority"}], "events": [{"pos",
    "block", "b0", "b1"}]}""",
)
def ticks(session: Session, args: Args) -> Output:
    args.done()
    doc = session.doc
    level = doc.level
    base = doc.history.base_time
    scheduled = sorted(
        [*level.block_ticks.pending(), *level.block_ticks.to_run],
        key=lambda t: (t.trigger_tick, t.priority.value, t.sub_tick),
    )
    out = Output(
        [
            f"{tick_line(session)}: {len(scheduled)} scheduled ticks, "
            f"{len(level.block_events)} block events"
        ]
    )
    for t in scheduled:
        out.add(
            f"  tick {t.trigger_tick - base:<4} {name_of(doc, t.pos):<12} "
            f"{short(t.block_id)} ({t.priority.name})"
        )
    for pos, block_id, b0, b1 in level.block_events:
        out.add(f"  event     {name_of(doc, pos):<12} {short(block_id)} ({b0}, {b1})")
    out.data = {
        "scheduled": [
            {
                "pos": list(t.pos),
                "block": short(t.block_id),
                "tick": t.trigger_tick - base,
                "priority": t.priority.name,
            }
            for t in scheduled
        ],
        "events": [
            {"pos": list(p), "block": short(b), "b0": b0, "b1": b1}
            for p, b, b0, b1 in level.block_events
        ],
    }
    return out


@command(
    "find",
    group="inspect",
    usage="find BLOCK [PROP=VALUE ...] [in POS POS]",
    summary="Where are blocks of a kind (with these properties)?",
    help="""
    Lists the positions of every block of that id; properties given must match too
    (`find repeater powered=true`). `in POS POS` limits the search to a box.
    """,
    examples=("find redstone_lamp", "find repeater powered=true", "find piston in 0 1 0 9 3 9"),
    kind="view",
    data='{"block", "positions": [[x, y, z], ...]}',
)
def find(session: Session, args: Args) -> Output:
    words = [args.word("a block")]
    while args.more() and "=" in (args.peek() or ""):
        words.append(args.word())
    box: tuple[Pos, Pos] | None = None
    if args.option("in"):
        box = region(args)
    args.done()
    target = parse_block(words[0], command="find")
    wanted = {}
    for word in words[1:]:
        key, _, value = word.partition("=")
        wanted[key] = value
    found = []
    for pos, state in session.doc.level.blocks.items():
        if state.block is not target.block:
            continue
        if box is not None and not all(box[0][i] <= pos[i] <= box[1][i] for i in range(3)):
            continue
        props = state.properties_dict()
        if all(props.get(k) == v for k, v in wanted.items()):
            found.append(pos)
    found.sort(key=lambda p: (p[1], p[2], p[0]))
    out = Output([f"{len(found)} × {' '.join(words)}"])
    for pos in found[:200]:
        out.add(f"  {named(session.doc, pos)}  {state_text(session.doc.level.blocks[pos])}")
    out.data = {"block": " ".join(words), "positions": [list(p) for p in found]}
    return out


@command(
    "entities",
    group="inspect",
    usage="entities",
    summary="The falling blocks in the world (the only simulated entities).",
    help="""
    Lists every falling block: its block, exact position and motion, and how long it has
    been falling.
    """,
    examples=("entities",),
    kind="view",
    data='{"entities": [{"id", "state", "pos", "motion", "time"}]}',
)
def entities(session: Session, args: Args) -> Output:
    args.done()
    mobs = list(session.doc.level.entities.values())
    out = Output([f"{len(mobs)} falling blocks {tick_line(session)}"])
    for m in mobs:
        x, y, z = m.position
        out.add(
            f"  {state_text(m.state)} at {x:.3f} {y:.3f} {z:.3f}, "
            f"motion {m.delta[1]:+.4f}/tick, falling {m.time} ticks"
        )
    out.data = {
        "entities": [
            {
                "id": m.id,
                "state": state_text(m.state),
                "pos": list(m.position),
                "motion": list(m.delta),
                "time": m.time,
            }
            for m in mobs
        ]
    }
    return out


@command(
    "delays",
    group="inspect",
    usage="delays FROM TO [ticks A..B]",
    summary="Measure how long a change at FROM takes to show at TO.",
    help="""
    Follows the values of FROM and TO (as `waves` shows them) over the range (default:
    the whole simulated history) and, for every change of FROM, reports the first change
    of TO at or after it, and the delay in ticks. Use it to measure a circuit's delay
    (input lever to output lamp), a pulse's length, or how long a piston sequence takes.
    A change of FROM with no later change of TO says "no change".
    """,
    examples=("delays @A @OUT", "delays @IN @LAMP ticks 0..60"),
    kind="view",
    data='{"from", "to", "changes": [{"tick", "value", "to_tick", "to_value", "delay"}]}',
)
def delays(session: Session, args: Args) -> Output:
    from redsim.editor.monitor import monitor_value

    doc = session.doc
    first = args.pos("the input")
    args.option("to")
    second = args.pos("the output")
    low, high = 0, doc.end_tick
    if args.option("ticks"):
        low, high = args.tick_range()
    args.done()
    view = session.view_now()
    a_values, b_values = [], []
    for tick in range(low, high + 1):
        session.goto(tick)
        a_values.append(monitor_value(doc.level, first))
        b_values.append(monitor_value(doc.level, second))
    session.goto_view(view)
    rows = []
    out = Output([f"{name_of(doc, first)} → {name_of(doc, second)} (ticks {low}..{high}):"])
    for i in range(1, len(a_values)):
        if a_values[i] == a_values[i - 1]:
            continue
        tick = low + i
        found = next(
            (j for j in range(i, len(b_values)) if j and b_values[j] != b_values[j - 1]), None
        )
        row: dict[str, Any] = {"tick": tick, "value": a_values[i], "to_tick": None,
                               "to_value": None, "delay": None}  # fmt: skip
        change = f"  tick {tick:<4} {a_values[i - 1]} → {a_values[i]}:"
        if found is None:
            out.add(f"{change} no change at the output after it")
        else:
            row.update(to_tick=low + found, to_value=b_values[found], delay=found - i)
            out.add(
                f"{change} output {b_values[found - 1]} → {b_values[found]} "
                f"at tick {low + found} ({found - i} ticks later)"
            )
        rows.append(row)
    if not rows:
        out.add("  the input does not change in this range")
    out.data = {"from": list(first), "to": list(second), "changes": rows}
    return out
