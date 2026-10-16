"""Annotation commands: ``label``, ``labels``, ``note``, ``notes``. Annotations never
change the simulation; they make a world readable for the next person or agent."""

from __future__ import annotations

from redsim.cli.commands.common import region
from redsim.cli.language import Args, CliError, format_pos
from redsim.cli.registry import Output, command
from redsim.cli.session import Session
from redsim.cli.views import state_text


@command(
    "label",
    group="annotate",
    usage='label NAME POS ["NOTE"] | label NAME delete',
    summary="Name a position: @NAME then works wherever a position does.",
    help="""
    Gives the position POS the name NAME (letters, digits, `_`, `.`, `-`; starting with a
    letter or `_`), with an optional note saying what it is. Afterwards `@NAME` stands for
    the position in every command (`inspect @OUT`, `pulse @A at 2`), and `@NAME+1,0,0` for
    a position next to it. Labels are saved in the world and listed by `labels`, `info`
    and the editor. Labeling a contraption's inputs and outputs is the first step to
    testing it (`target`). `label NAME delete` removes the label.
    """,
    examples=('label A 0 1 0 "input A (lever)"', "label OUT 6 1 0", "label OUT delete"),
    kind="meta",
    data='{"name", "pos" or null, "note"}',
)
def label(session: Session, args: Args) -> Output:
    import re

    name = args.word("a label name")
    if name.startswith("@"):
        name = name[1:]
    if not re.fullmatch(r"[A-Za-z_][\w.-]*", name):
        raise CliError("label: names start with a letter or _ and contain letters, digits, _ . -")
    doc = session.doc
    if args.option("delete"):
        args.done()
        if name not in doc.labels:
            raise CliError(f"label: no label @{name}")
        doc.set_label(name, None)
        session.changed = True
        return Output([f"removed @{name}"], {"name": name, "pos": None})
    pos = args.pos()
    note = " ".join(args.rest())
    doc.set_label(name, pos, note)
    session.changed = True
    state = state_text(doc.state_at(pos))
    return Output(
        [f"@{name} = {format_pos(pos)} ({state})" + (f": {note}" if note else "")],
        {"name": name, "pos": list(pos), "note": note},
    )


@command(
    "labels",
    group="annotate",
    usage="labels",
    summary="List the labels with their positions, notes and current blocks.",
    help="Lists every label: its name, position, note and the block there at the view tick.",
    examples=("labels",),
    kind="view",
    data='{"labels": [{"name", "pos", "note", "state"}]}',
)
def labels(session: Session, args: Args) -> Output:
    args.done()
    doc = session.doc
    rows = []
    out = Output()
    for name, lab in sorted(doc.labels.items()):
        state = state_text(doc.state_at(lab.pos))
        out.add(
            f"  @{name:<10} {format_pos(lab.pos):<10} {state}"
            + (f"  — {lab.note}" if lab.note else "")
        )
        rows.append({"name": name, "pos": list(lab.pos), "note": lab.note, "state": state})
    if not rows:
        out.add("  (no labels yet: label NAME POS)")
    out.data = {"labels": rows}
    return out


@command(
    "note",
    group="annotate",
    usage='note "TEXT" | note delete N',
    summary="Add a note to the world (what it is, what is left to do), or delete one.",
    help="""
    Notes are free text saved with the world and shown by `info` and `notes`: what the
    contraption is for, how to use it, what still fails. Use them to hand a world over to
    a person or another agent. `note delete N` removes the N-th note (see `notes`).
    """,
    examples=('note "2-input AND gate; inputs @A @B, output @OUT"', "note delete 1"),
    kind="meta",
    data='{"notes": [text, ...]}',
)
def note(session: Session, args: Args) -> Output:
    doc = session.doc
    if args.option("delete"):
        number = args.number("the note's number")
        args.done()
        if not 1 <= number <= len(doc.notes):
            raise CliError(f"note: there is no note {number} (see: notes)")
        del doc.notes[number - 1]
    else:
        text = " ".join(args.rest())
        if not text:
            raise CliError('note: write the text: note "…"')
        doc.notes.append(text)
    session.changed = True
    doc.dirty = True
    return Output([f"{len(doc.notes)} notes"], {"notes": list(doc.notes)})


@command(
    "notes",
    group="annotate",
    usage="notes",
    summary="List the world's notes.",
    help="Lists the notes, numbered (for `note delete N`).",
    examples=("notes",),
    kind="view",
    data='{"notes": [text, ...]}',
)
def notes(session: Session, args: Args) -> Output:
    args.done()
    doc = session.doc
    out = Output([f"  {i}. {text}" for i, text in enumerate(doc.notes, 1)] or ["  (no notes)"])
    out.data = {"notes": list(doc.notes)}
    return out


@command(
    "group",
    group="annotate",
    usage="group NAME POS POS [in POS NAME ...] [out POS NAME ...] | group NAME delete | groups",
    summary="Mark a box as a named part of the circuit, with input and output ports.",
    help="""
    Groups name parts of a larger build ("adder bit 0", "clock") and their ports, the
    positions where signals enter and leave. The editor shows them under Circuit →
    Groups with live port readings and draws their boxes; they never change the
    simulation. `in POS NAME` and `out POS NAME` add ports (repeatable).
    `group NAME delete` removes a group; `groups` lists them.
    """,
    examples=("group and 0 1 0 4 2 2 in @A A in @B B out @OUT OUT", "groups", "group and delete"),
    kind="meta",
    data='{"groups": [{"name", "low", "high", "ports": [{"name", "pos", "role"}]}]}',
)
def group(session: Session, args: Args) -> Output:
    from redsim.editor.clipboard import Region
    from redsim.editor.groups import Group, Port

    doc = session.doc
    name = args.word("a group name")
    if args.option("delete"):
        args.done()
        if name not in doc.groups.groups:
            raise CliError(f"group: no group {name!r}")
        doc.groups.remove(name)
    else:
        a, b = region(args)
        ports = []
        while args.more():
            role = args.choice(("in", "out"), "in or out")
            pos = args.pos("the port's position")
            port_name = args.word("the port's name")
            ports.append(Port(port_name, pos, "input" if role == "in" else "output"))
        doc.groups.add(Group(name, Region.from_corners(a, b), ports))
    doc.dirty = True
    session.changed = True
    return _groups_output(doc)


@command(
    "groups",
    group="annotate",
    usage="groups",
    summary="List the groups with their boxes and ports.",
    help="Lists every group: its box and its ports with what they read now.",
    examples=("groups",),
    kind="view",
    data='{"groups": [{"name", "low", "high", "ports": [{"name", "pos", "role", "reading"}]}]}',
)
def groups(session: Session, args: Args) -> Output:
    args.done()
    return _groups_output(session.doc)


def _groups_output(doc: object) -> Output:
    from redsim.editor.groups import port_reading

    out = Output()
    rows = []
    for g in doc.groups.groups.values():  # type: ignore[attr-defined]
        out.add(f"  {g.name}: {format_pos(g.region.low)} to {format_pos(g.region.high)}")
        ports = []
        for port in g.ports:
            reading = port_reading(doc.level, port)  # type: ignore[attr-defined]
            out.add(f"    {port.role:<6} {port.name:<8} {format_pos(port.pos)}  {reading}")
            ports.append({"name": port.name, "pos": list(port.pos), "role": port.role,
                          "reading": reading})  # fmt: skip
        rows.append({"name": g.name, "low": list(g.region.low), "high": list(g.region.high),
                     "ports": ports})  # fmt: skip
    if not rows:
        out.add("  (no groups)")
    out.data = {"groups": rows}
    return out
