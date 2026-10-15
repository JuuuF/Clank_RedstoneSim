"""Exchange commands: schematics and structure files (``export``, ``import``), Minecraft
saves (``open-save``, ``export-save``)."""

from __future__ import annotations

from pathlib import Path

from redsim.cli.commands.common import content_box, region
from redsim.cli.language import Args, CliError, format_pos
from redsim.cli.registry import Output, command
from redsim.cli.session import Session


@command(
    "export",
    group="io",
    usage="export FILE [from POS POS]",
    summary="Write the build (or a box) as a .litematic, .schem or .nbt file for Minecraft.",
    help="""
    Writes the blocks of the box (default: everything above the floor) at the view tick
    to FILE, in the format of its extension: `.litematic` (Litematica), `.schem`
    (Sponge/WorldEdit) or `.nbt` (a structure file for structure blocks and
    `/place template`). Block-entity data (container items, comparator outputs, signs)
    goes along. This is how a contraption designed here gets into Minecraft.
    """,
    examples=("export gate.litematic", "export door.nbt from -2 1 -2 4 5 3"),
    kind="view",
    data='{"path", "low", "high", "blocks"}',
)
def export(session: Session, args: Args) -> Output:
    from redsim.editor.clipboard import Prefab, Region
    from redsim.io.schematics import SUFFIXES, write_schematic

    path = Path(args.word("a file name"))
    if path.suffix.lower() not in SUFFIXES:
        raise CliError(f"export: the file must end in {', '.join(SUFFIXES)}")
    if args.option("from"):
        low, high = region(args)
    else:
        box = content_box(session.doc.level)
        if box is None:
            raise CliError("export: nothing above the floor to export")
        low, high = box
    args.done()
    prefab = Prefab.capture(session.doc.level, Region(low, high), path.stem)
    write_schematic(path, prefab)
    count = prefab.non_air_count
    return Output(
        [f"wrote {count} blocks ({format_pos(low)} to {format_pos(high)}) to {path}"],
        {"path": str(path), "low": list(low), "high": list(high), "blocks": count},
    )


@command(
    "import",
    group="io",
    usage="import FILE at POS [rotate N] [mirror x|z]",
    summary="Paste a .litematic, .schem or .nbt file into the build at POS.",
    help="""
    Reads a schematic or structure file and pastes it with its lowest corner at POS, like
    the editor's paste (`/clone … strict`: no block updates, air included), after turning
    it N quarter turns clockwise and/or mirroring it. Blocks the simulator does not model
    come in as inert foreign blocks. `at T import …` pastes it at tick T instead.
    """,
    examples=("import gate.litematic at 0 1 0", "import door.nbt at 10 1 0 rotate 1"),
    kind="edit",
    data='{"path", "low", "high", "blocks", "tick"}',
)
def import_(session: Session, args: Args) -> Output:
    from redsim.io.schematics import read_schematic

    path = Path(args.word("a file name"))
    if not args.option("at"):
        raise CliError("import: say where: at POS")
    pos = args.pos()
    turns = args.option_int("rotate", 0)
    axis = args.word("x or z") if args.option("mirror") else None
    args.done()
    try:
        prefab = read_schematic(path)
    except (OSError, ValueError, KeyError) as exc:
        raise CliError(f"import: cannot read {path}: {exc}") from exc
    if turns % 4:
        prefab = prefab.rotated(turns % 4)
    if axis is not None:
        if axis not in ("x", "z"):
            raise CliError("import: mirror x or z")
        prefab = prefab.mirrored(axis)
    with session.editing() as doc:
        doc.paste(pos, prefab)
    high = tuple(pos[i] + prefab.size[i] - 1 for i in range(3))
    return Output(
        [
            f"imported {prefab.non_air_count} blocks from {path} at {format_pos(pos)} "
            f"({session.where})"
        ],
        {
            "path": str(path),
            "low": list(pos),
            "high": list(high),
            "blocks": prefab.non_air_count,
            "tick": session.edit_tick,
        },
    )


@command(
    "open-save",
    group="io",
    usage="open-save SAVE [center X Z] [radius R] [force]",
    summary="Create the world file from a Minecraft Java save (around the player).",
    help="""
    Reads the Minecraft save folder SAVE (the one with `level.dat`) and makes the world
    file from the chunks within R chunks (default 2) around the player, or around the
    chunk holding block X Z. Blocks come in as they are, without updates; blocks the
    simulator does not model are inert foreign blocks (listed). The world remembers the
    save, so `export-save` can write changes back into a copy. Replaces an existing world
    file only with `force`.
    """,
    examples=(
        "open-save ~/.minecraft/saves/Redstone",
        "open-save ./Redstone center 120 -40 radius 3",
    ),
    kind="file",
    data='{"save", "blocks", "foreign": {id: count}, "ticks"}',
)
def open_save(session: Session, args: Args) -> Output:
    from redsim.mcworld.importer import open_world

    save = Path(args.word("a save folder")).expanduser()
    center = None
    radius = 2
    force = False
    while args.more():
        if args.option("center"):
            x, z = args.number("x"), args.number("z")
            center = (x >> 4, z >> 4)
        elif args.option("radius"):
            radius = args.number("a radius in chunks")
        elif args.option("force"):
            force = True
        else:
            args.done()
    if session.has_document and not force:
        raise CliError(f"{session.path} exists; add 'force' to replace it")
    if not (save / "level.dat").exists():
        raise CliError(f"open-save: {save} is not a Minecraft save (no level.dat)")
    opened = open_world(save, radius=radius, center=center)
    document = opened.document
    document.path = session.path
    session.adopt(document)
    session.changed = True
    foreign = dict(opened.foreign.most_common())
    out = Output(
        [
            f"opened {save}: {len(document.level.blocks)} blocks, "
            f"{opened.ticks_imported} pending ticks"
        ]
    )
    if foreign:
        out.add(
            "  not simulated (inert): "
            + ", ".join(f"{n}× {b}" for b, n in list(foreign.items())[:12])
        )
    out.data = {
        "save": str(save),
        "blocks": len(document.level.blocks),
        "foreign": foreign,
        "ticks": opened.ticks_imported,
    }
    return out


@command(
    "export-save",
    group="io",
    usage="export-save TARGET",
    summary="Write the world into a copy of the Minecraft save it came from.",
    help="""
    For a world made with `open-save`: copies the original save to the new folder TARGET
    and writes the world's blocks (at the view tick) and pending scheduled ticks into the
    copy, which Minecraft then opens. The original save is never changed.
    """,
    examples=("export-save ~/.minecraft/saves/Redstone-edited",),
    kind="view",
    data='{"target", "blocks", "chunks"}',
)
def export_save(session: Session, args: Args) -> Output:
    from redsim.mcworld.importer import attach_world
    from redsim.mcworld.writer import save_world_copy

    target = Path(args.word("a target folder")).expanduser()
    args.done()
    doc = session.doc
    if doc.world is None and attach_world(doc) is None:
        raise CliError("export-save: this world was not opened from a Minecraft save (open-save)")
    try:
        report = save_world_copy(doc, target)
    except ValueError as exc:
        raise CliError(f"export-save: {exc}") from exc
    return Output(
        [f"wrote {report.blocks} changed blocks in {report.chunks} chunks to {target}"],
        {"target": str(target), "blocks": report.blocks, "chunks": report.chunks},
    )
