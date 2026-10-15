"""World commands: ``new``, ``info``, ``log``, ``save-as``."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from redsim.cli.commands.common import content_box, content_positions, tick_line, view_data
from redsim.cli.language import Args, CliError, format_pos, parse_block
from redsim.cli.registry import Output, command
from redsim.cli.session import Session


@command(
    "new",
    group="world",
    usage="new [size N] [floor BLOCK|none] [force]",
    summary="Create a new world file with a flat floor at y=0.",
    help="""
    Creates the world file named on the command line: an N×N floor (default 32×32) of
    smooth stone at y=0, from x,z = -N/2 to N/2-1, placed without block updates like
    terrain. Build on top of it, from y=1 up. `floor BLOCK` uses another block for the
    floor, `floor none` makes an empty world. An existing file is only replaced with
    `force` (its previous content goes to the undo file, so `undo` brings it back).

    The world starts at tick 0 (the build) with an empty timeline.
    """,
    examples=(
        "redsim-cli gate.redsim.json new",
        "redsim-cli big.redsim.json new size 64 floor stone",
        "redsim-cli sky.redsim.json new floor none",
    ),
    kind="file",
    data='{"path", "floor": block or null, "size"}',
)
def new(session: Session, args: Args) -> Output:
    from redsim.editor.document import Document
    from redsim.sim.engine import Engine

    size, floor = 32, "smooth_stone"
    force = False
    while args.more():
        if args.option("size"):
            size = args.number("the floor size")
            if not 1 <= size <= 1024:
                raise CliError("new: size must be 1 to 1024")
        elif args.option("floor"):
            floor = args.word("a floor block or none")
        elif args.option("force"):
            force = True
        else:
            args.done()
    if session.has_document and not force:
        raise CliError(f"{session.path} exists; add 'force' to replace it (undo restores it)")
    engine = Engine()
    if floor != "none":
        state = parse_block(floor, command="new")
        half = size // 2
        for x in range(-half, size - half):
            for z in range(-half, size - half):
                engine.level.blocks[(x, 0, z)] = state
    document = Document(engine=engine)
    document.path = session.path
    session.adopt(document)
    session.changed = True
    floor_text = "no floor" if floor == "none" else f"a {size}×{size} {floor} floor at y=0"
    return Output(
        [f"created {session.path}: {floor_text}; build from y=1 up"],
        {"path": str(session.path), "floor": None if floor == "none" else floor, "size": size},
    )


@command(
    "info",
    group="world",
    usage="info",
    summary="Summarize the world: blocks, view tick, timeline, labels, targets.",
    help="""
    Prints what is in the world: the box around the blocks above the floor, how many of
    each block there are, the view tick and the simulated length, the recorded timeline
    (edits and power pulses), monitors, labels, notes, targets, falling blocks and pending
    scheduled ticks. Running `redsim-cli WORLD` without a command in a terminal prints this.
    """,
    examples=("info",),
    kind="view",
    data="""{"tick", "end_tick", "box": [low, high] or null, "blocks": {id: count},
    "edits", "pulses", "labels": {name: [x, y, z]}, "notes", "targets", "monitors",
    "entities", "scheduled_ticks"}""",
)
def info(session: Session, args: Args) -> Output:
    args.done()
    doc = session.doc
    level = doc.level
    positions = content_positions(level)
    counts = Counter(level.blocks[p].block.id.removeprefix("minecraft:") for p in positions)
    box = content_box(level)
    out = Output()
    out.add(f"world {session.path}")
    out.add(f"  view      {tick_line(session)}")
    if box is None:
        out.add("  blocks    none above the floor yet")
    else:
        out.add(f"  box       {format_pos(box[0])} to {format_pos(box[1])} (above the floor)")
        common = ", ".join(f"{n} {b}" for b, n in counts.most_common(12))
        more = f", … {len(counts) - 12} more kinds" if len(counts) > 12 else ""
        out.add(f"  blocks    {len(positions)}: {common}{more}")
    pulses = doc.pulses()
    edits = [i for i, a in doc.history.inputs.items() if a.kind != "power_pulse"]
    out.add(
        f"  timeline  {len(edits)} recorded edits, {len(pulses)} power pulses"
        + ("" if edits or pulses else " (empty)")
    )
    if doc.labels:
        names = ", ".join(f"@{n} {format_pos(lab.pos)}" for n, lab in sorted(doc.labels.items()))
        out.add(f"  labels    {names}")
    if doc.monitors:
        out.add(f"  monitors  {', '.join(format_pos(p) for p in doc.monitors)}")
    if doc.targets:
        out.add(f"  targets   {', '.join(t['name'] for t in doc.targets)} (check them: check)")
    for note in doc.notes:
        out.add(f"  note      {note}")
    if level.entities:
        out.add(f"  entities  {len(level.entities)} falling blocks")
    pending = level.block_ticks.pending()
    if pending:
        out.add(f"  pending   {len(pending)} scheduled ticks (see: ticks)")
    out.data = {
        **view_data(session),
        "box": [list(box[0]), list(box[1])] if box else None,
        "blocks": dict(counts),
        "edits": len(edits),
        "pulses": len(pulses),
        "labels": {n: list(lab.pos) for n, lab in doc.labels.items()},
        "notes": list(doc.notes),
        "targets": [t["name"] for t in doc.targets],
        "monitors": [list(p) for p in doc.monitors],
        "entities": len(level.entities),
        "scheduled_ticks": len(pending),
    }
    return out


@command(
    "log",
    group="world",
    usage="log [N]",
    summary="Show the last N command lines that changed this world (default 20).",
    help="""
    Every command that changed the world (or the timeline, labels, notes, targets) is
    written to the world file's log (the last 500). `log` shows the newest ones, oldest
    first, so you can see how the world came to be, or continue where someone stopped.
    """,
    examples=("log", "log 100"),
    kind="view",
    data='{"lines": [command line, ...]}',
)
def log(session: Session, args: Args) -> Output:
    count = args.number("how many lines") if args.more() else 20
    args.done()
    lines = list((session.doc.extra.get("cli") or {}).get("log", [])) + session.log
    shown = lines[-count:]
    out = Output([f"  {line}" for line in shown] or ["  (no commands logged yet)"])
    out.data = {"lines": shown}
    return out


@command(
    "save-as",
    group="world",
    usage="save-as FILE",
    summary="Write the world to another file as well (the session's file stays).",
    help="""
    Saves a copy of the world, with everything in it (build, timeline, labels, targets,
    view), to FILE. The world file itself is still the one named on the command line.
    """,
    examples=("save-as backup.redsim.json",),
    kind="file",
    data='{"path"}',
)
def save_as(session: Session, args: Args) -> Output:
    target = Path(args.word("a file name"))
    args.done()
    doc = session.doc
    path = doc.path
    doc.save(target)
    doc.path = path
    return Output([f"saved a copy as {target}"], {"path": str(target)})
