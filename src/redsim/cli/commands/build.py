"""Build commands: everything that changes blocks.

Each runs inside ``Session.editing``: on the build (tick 0) unless the line started with
``at T`` (then the edit is recorded on the timeline at tick T), as one undo step. The
output names the resulting block state (after the game's own adjustments) and where the
edit went ("the build" or "tick T").
"""

from __future__ import annotations

import json
from typing import Any

from redsim.cli.commands.common import name_of, region, volume
from redsim.cli.language import Args, CliError, format_pos
from redsim.cli.registry import Output, command
from redsim.cli.session import Session
from redsim.cli.views import state_text
from redsim.core.pos import Pos

#: ``GameRules.MAX_BLOCK_MODIFICATIONS``: the largest /fill and /clone volume.
MAX_VOLUME = 32768


def _done(session: Session, verb: str, pos: Pos, data: dict[str, Any] | None = None) -> Output:
    doc = session.doc
    state = doc.state_at(pos)
    text = f"{verb} {name_of(doc, pos)}: {state_text(state)} ({session.where})"
    return Output(
        [text],
        {"pos": list(pos), "state": state_text(state), "tick": session.edit_tick, **(data or {})},
    )


@command(
    "place",
    group="build",
    usage="place POS BLOCK [PROP=VALUE ...]",
    summary="Place a block like a player, with the orientation you give.",
    help="""
    Places BLOCK at POS the way a player placing it would (`BlockItem.place`): the spot
    must be air and the block must have support (a torch needs a block to stand on, a
    lever a block to attach to). The orientation is what you write (`facing`, `face`,
    `half`, …); the game's placement rules derive the rest, so a lamp next to power is
    placed lit, a repeater next to a powered side repeater is placed locked, wire connects
    to its neighbors, a door gets its upper half. Properties you leave out keep their
    defaults (`facing=north` for most blocks).

    Directions: repeaters, comparators and observers have `facing` pointing to their
    input (the opposite of their output); write `out=DIRECTION` to give the output side
    instead. Pistons, dispensers, droppers and hoppers face where they push or output.
    Wall torches face away from their wall; levers and buttons use `face=floor|wall|ceiling`
    and, on a wall, `facing` away from the wall.

    Use `set` to put a block regardless of support or to replace one (the `/setblock`
    command), and `at T place …` to place it at tick T on the timeline instead of in the
    build.
    """,
    examples=(
        "place 0 1 0 redstone_wire",
        "place 1 1 0 repeater out=east delay=2   # output east, 2 ticks",
        "place 2 1 0 redstone_lamp",
        "place 0 2 1 lever face=wall facing=south",
        "at 10 place 4 1 0 redstone_block        # recorded at tick 10",
    ),
    kind="edit",
    data='{"pos", "state" (the placed state), "tick" (0 = the build)}',
)
def place(session: Session, args: Args) -> Output:
    pos = args.pos()
    state = args.block()
    args.done()
    with session.editing() as doc:
        if not doc.state_at(pos).is_air:
            raise CliError(
                f"place: {format_pos(pos)} holds {doc.state_at(pos).block.name}; "
                "break it first or use set"
            )
        if not state.can_survive(doc.level, pos):
            raise CliError(
                f"place: {state.block.name} cannot stay at {format_pos(pos)}: "
                f"{_support_hint(doc, state, pos)}"
            )
        doc.place_state(pos, state)
    return _done(session, "placed", pos)


def _support_hint(doc: Any, state: Any, pos: Pos) -> str:
    """Why a block has no support: the block it would rest on or hang from."""
    from redsim.cli.views import prop
    from redsim.core.direction import Direction
    from redsim.core.pos import offset

    facing = prop(state, "facing")
    face = prop(state, "face")
    if face == "ceiling":
        side = Direction.UP
    elif face == "wall" or state.block.id.endswith("wall_torch"):
        side = facing.opposite if isinstance(facing, Direction) else Direction.DOWN
    else:
        side = Direction.DOWN
    near = offset(pos, side)
    what = doc.state_at(near).block.name
    where = {"down": "below it", "up": "above it"}.get(side.serialized, f"to its {side.serialized}")
    return f"it needs a supporting block {where} ({format_pos(near)} is {what})"


@command(
    "set",
    group="build",
    usage="set POS BLOCK [PROP=VALUE ...] [nbt JSON]",
    summary="Set a block like the /setblock command (replaces what is there).",
    help="""
    Runs `/setblock POS BLOCK` (replace mode): the block replaces whatever is at POS, its
    shape-dependent properties are adjusted to its neighbors (wire connections, stairs
    corners) and the neighbors are updated, but placement rules are not applied: a lamp
    set next to power stays off until something updates it, as in the game. `nbt` adds
    block-entity data as JSON, like `/setblock … {…}`
    (`set 0 1 0 barrel nbt '{"Items":[{"Slot":0,"id":"minecraft:stone","count":64}]}'`).

    Blocks the simulator does not model (water, TNT, …) can be set too: they stay inert
    (see doc/differences.md). Setting an extended piston also puts its head in front.
    """,
    examples=(
        "set 0 1 0 redstone_block",
        "set 3 1 0 repeater[facing=west,delay=4]",
        "set 0 1 0 air            # remove without breaking (no drops, like the command)",
    ),
    kind="edit",
    data='{"pos", "state", "tick"}',
)
def set_(session: Session, args: Args) -> Output:
    pos = args.pos()
    state = args.block()
    nbt = None
    if args.option("nbt"):
        raw = args.word("JSON block-entity data")
        try:
            nbt = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CliError(f"set: the nbt data is not valid JSON: {exc}") from exc
    args.done()
    with session.editing() as doc:
        if nbt is None:
            doc.set_state(pos, state)
        else:
            doc.setblock(pos, state, nbt)
    return _done(session, "set", pos)


@command(
    "break",
    group="build",
    usage="break POS",
    summary="Break a block like a creative player (neighbors update, no drops).",
    help="""
    Removes the block at POS as a player in creative mode breaks it
    (`ServerPlayerGameMode.destroyBlock`): its neighbors are updated, a door takes its
    other half along. Items are not simulated, so nothing drops.
    """,
    examples=("break 2 1 0",),
    kind="edit",
    data='{"pos", "state" (air), "tick"}',
)
def break_(session: Session, args: Args) -> Output:
    pos = args.pos()
    args.done()
    with session.editing() as doc:
        if doc.state_at(pos).is_air:
            raise CliError(f"break: {format_pos(pos)} is air already")
        doc.break_block(pos)
    return _done(session, "broke", pos)


_YAW = {"south": 0.0, "west": 90.0, "north": 180.0, "east": 270.0}


@command(
    "use",
    group="build",
    usage="use POS [look DIRECTION]",
    summary="Right-click a block with an empty hand (levers, buttons, repeaters, …).",
    help="""
    Uses the block at POS like a player with an empty hand (`useWithoutItem`): a lever
    toggles, a button is pressed (it releases by itself after 20 or 30 ticks), a repeater
    cycles its delay, a comparator switches mode, a door, trapdoor or fence gate opens or
    closes, a note block plays. `look DIRECTION` is where the player looks (fence gates open
    away from the player); default: south.

    In the build (tick 0) a use changes the starting state; to flip a lever *during* a
    test, record it on the timeline: `at 5 use @LEVER`.
    """,
    examples=(
        "use 0 1 0",
        "at 5 use @A        # flip lever A at tick 5",
        "use 3 1 0   # repeater: next delay",
    ),
    kind="edit",
    data='{"pos", "state" (after the use), "tick"}',
)
def use(session: Session, args: Args) -> Output:
    pos = args.pos()
    yaw = None
    if args.option("look"):
        direction = args.direction("where the player looks")
        if direction.serialized not in _YAW:
            raise CliError("use: look must be north, south, east or west")
        yaw = _YAW[direction.serialized]
    args.done()
    with session.editing() as doc:
        doc.use(pos, yaw)
    return _done(session, "used", pos)


@command(
    "fill",
    group="build",
    usage="fill POS POS BLOCK [PROP=VALUE ...]",
    summary="Fill a box with a block like the /fill command.",
    help="""
    Runs `/fill` in replace mode over the box between the two corners (both included, at
    most 32768 blocks): every block in it becomes BLOCK, neighbors update as with
    `/setblock`. Use it for floors, walls of solid blocks, or to clear an area (`clear`).
    """,
    examples=("fill -5 1 -5 5 1 5 stone", "fill 0 1 0 0 1 9 redstone_wire"),
    kind="edit",
    data='{"low", "high", "state", "count", "tick"}',
)
def fill(session: Session, args: Args) -> Output:
    low, high = region(args)
    state = args.block()
    args.done()
    return _fill(session, low, high, state, "filled")


def _fill(session: Session, low: Pos, high: Pos, state: Any, verb: str) -> Output:
    from redsim.editor.clipboard import Region

    count = volume(low, high)
    if count > MAX_VOLUME:
        raise CliError(f"{verb}: {count} blocks is more than the game allows ({MAX_VOLUME})")
    with session.editing() as doc:
        doc.fill(Region(low, high), state)
    what = f"{format_pos(low)} to {format_pos(high)} ({count} blocks)"
    text = f"{verb} {what} with {state_text(state)} ({session.where})"
    return Output(
        [text],
        {
            "low": list(low),
            "high": list(high),
            "state": state_text(state),
            "count": count,
            "tick": session.edit_tick,
        },
    )


@command(
    "clear",
    group="build",
    usage="clear POS POS",
    summary="Make a box air (the /fill command with air).",
    help="Same as `fill POS POS air`.",
    examples=("clear -3 1 -3 3 4 3",),
    kind="edit",
    data='{"low", "high", "state", "count", "tick"}',
)
def clear(session: Session, args: Args) -> Output:
    from redsim.world import blocks

    low, high = region(args)
    args.done()
    return _fill(session, low, high, blocks.AIR.default_state, "cleared")


@command(
    "line",
    group="build",
    usage="line POS POS BLOCK [PROP=VALUE ...] [support BLOCK]",
    summary="Place a straight line of blocks like a player (skips taken spots).",
    help="""
    Places BLOCK like `place` at every position from the first to the second (both
    included); the two must differ along one axis only. Spots that are not air, or where
    the block has no support, are skipped and listed. Use it for lines of wire, solid
    blocks or repeaters (all with the same properties). `support BLOCK` first sets BLOCK
    under every spot of the line that has air below it, so wire can run over a gap.
    """,
    examples=(
        "line 0 1 0 9 1 0 redstone_wire",
        "line 0 1 2 0 1 8 stone",
        "line 0 3 0 6 3 0 redstone_wire support stone   # wire in the air, on stone",
    ),
    kind="edit",
    data='{"placed": [[x, y, z], ...], "skipped": [{"pos", "reason"}], "tick"}',
)
def line(session: Session, args: Args) -> Output:
    a = args.pos("the start")
    b = args.pos("the end")
    state = args.block()
    support = args.block("a support block") if args.option("support") else None
    args.done()
    differ = [i for i in range(3) if a[i] != b[i]]
    if len(differ) > 1:
        raise CliError("line: the two ends must differ along one axis only")
    axis = differ[0] if differ else 0
    step = 1 if b[axis] >= a[axis] else -1
    positions = []
    for v in range(a[axis], b[axis] + step, step):
        p = list(a)
        p[axis] = v
        positions.append((p[0], p[1], p[2]))
    placed: list[Pos] = []
    skipped: list[tuple[Pos, str]] = []
    from redsim.editor.document_history import EditError

    with session.editing() as doc:
        for pos in positions:
            under = (pos[0], pos[1] - 1, pos[2])
            if support is not None and doc.state_at(pos).is_air and doc.state_at(under).is_air:
                doc.setblock(under, support)
            if not doc.state_at(pos).is_air:
                skipped.append((pos, f"holds {doc.state_at(pos).block.name}"))
                continue
            try:
                doc.place_state(pos, state)
            except EditError as exc:
                skipped.append((pos, str(exc)))
                continue
            placed.append(pos)
    out = Output(
        [
            f"placed {len(placed)} × {state.block.name} from {format_pos(a)} "
            f"to {format_pos(b)} ({session.where})"
        ]
    )
    for pos, reason in skipped:
        out.add(f"  skipped {format_pos(pos)}: {reason}")
    out.data = {
        "placed": [list(p) for p in placed],
        "skipped": [{"pos": list(p), "reason": r} for p, r in skipped],
        "tick": session.edit_tick,
    }
    return out


@command(
    "source",
    group="build",
    usage="source POS KIND STRENGTH",
    summary="Put an analog signal source (barrel, lectern, cake, …) of a strength.",
    help="""
    Puts a block that a comparator reads as STRENGTH (1-15) at POS: KIND is `barrel`,
    `chest`, `hopper`, `lectern`, `cake` or `composter`, backed by the real block with the
    contents that give that reading (a barrel with items, a lectern on a page, a cake with
    bites, …). If POS holds a source already its strength (or kind) changes in place. Some
    kinds cannot make every strength (cakes: even values); the nearest is used and said.
    """,
    examples=("source 0 1 0 barrel 7", "source @IN lectern 3"),
    kind="edit",
    data='{"pos", "state", "kind", "strength", "tick"}',
)
def source(session: Session, args: Args) -> Output:
    from redsim.editor import sources
    from redsim.editor.builder import ON_FLOOR

    pos = args.pos()
    kind = args.choice(tuple(sources.KINDS), "a source kind")
    strength = args.number("a strength 1-15")
    args.done()
    if not 1 <= strength <= 15:
        raise CliError("source: strength must be 1 to 15")
    with session.editing() as doc:
        if doc.state_at(pos).is_air:
            doc.place_source(pos, kind, strength, ON_FLOOR)
        elif sources.kind_of(doc.state_at(pos)) is not None:
            doc.set_source(pos, kind, strength)
        else:
            raise CliError(f"source: {format_pos(pos)} holds {doc.state_at(pos).block.name}")
    actual = sources.nearest_strength(kind, strength)
    return _done(session, f"{kind} source {actual} at", pos, {"kind": kind, "strength": actual})


@command(
    "container",
    group="build",
    usage="container POS SLOT ITEM COUNT | container POS empty",
    summary="Set one slot of a barrel, chest, hopper, dropper or dispenser.",
    help="""
    Puts COUNT of ITEM (an item id like `stone` or `minecraft:redstone`) into slot SLOT
    (0-based) of the container at POS, replacing what was there (`/setblock` with the
    block-entity data, so comparators update; a hopper keeps its transfer cooldown).
    `container POS empty` empties every slot. Stacks are limited to the item's stack size.
    """,
    examples=("container 0 1 0 0 stone 64", "container @CHEST empty"),
    kind="edit",
    data='{"pos", "state", "items": "slot:id*count ...", "tick"}',
)
def container(session: Session, args: Args) -> Output:
    pos = args.pos()
    if args.option("empty"):
        slot, item, count = None, None, 0
    else:
        slot = args.number("a slot number")
        item = args.word("an item id")
        item = item if ":" in item else f"minecraft:{item}"
        count = args.number("a count")
    args.done()
    with session.editing() as doc:
        doc.set_container_slot(pos, slot, item, count)
    entity = session.doc.level.get_block_entity(pos, create=False)
    items = entity.contents() if entity is not None else ""
    out = _done(session, "filled" if item else "emptied", pos, {"items": items})
    out.add(f"  items: {items or 'none'}")
    return out


@command(
    "sign",
    group="build",
    usage='sign POS front|back "LINE" ["LINE" ...]',
    summary="Write up to four lines on a sign.",
    help="""
    Writes the lines on the given side of the sign at POS, as a player does (the sign's
    block entity changes; comparators around it update). Quote lines that have spaces.
    Signs are useful as labels inside a build that people see in the editor.
    """,
    examples=('sign 0 2 0 front "AND gate" "inputs: A B" "output: lamp"',),
    kind="edit",
    data='{"pos", "state", "side", "lines", "tick"}',
)
def sign(session: Session, args: Args) -> Output:
    pos = args.pos()
    side = args.choice(("front", "back"), "front or back")
    lines = args.rest()
    if len(lines) > 4:
        raise CliError("sign: a sign has four lines")
    with session.editing() as doc:
        doc.set_sign_text(pos, side, (lines + [""] * 4)[:4])
    return _done(session, f"wrote on the {side} of", pos, {"side": side, "lines": lines})


@command(
    "plate",
    group="build",
    usage="plate POS [mobs N] [others N] for TICKS",
    summary="Entities stand on a pressure plate for some ticks (an editor stand-in).",
    help="""
    Mobs and items are not simulated, so this puts *visitors* on the pressure plate at
    POS: N mobs (players count as mobs) and N other entities (items) from the next tick on,
    for TICKS ticks. The plate is pressed in the entity phase and released at its next
    recheck after they leave, exactly as with real entities (EXP-046). Stone plates only
    count mobs; weighted plates count everything. Usually recorded on the timeline:
    `at 5 plate @PLATE mobs 1 for 10`.
    """,
    examples=("at 5 plate 0 1 0 mobs 1 for 10", "at 2 plate @P others 3 for 40"),
    kind="edit",
    data='{"pos", "state", "mobs", "others", "ticks", "tick"}',
)
def plate(session: Session, args: Args) -> Output:
    pos = args.pos()
    mobs = args.option_int("mobs", 0)
    others = args.option_int("others", 0)
    if not args.option("for"):
        raise CliError("plate: say how long: for TICKS")
    ticks = args.number("a number of ticks")
    args.done()
    if mobs + others <= 0:
        mobs = 1
    with session.editing() as doc:
        doc.plate_visitors(pos, mobs, others, ticks)
    return _done(session, "visitors on", pos, {"mobs": mobs, "others": others, "ticks": ticks})


@command(
    "hit",
    group="build",
    usage="hit POS [strength S] [arrow|snowball]",
    summary="A projectile hits a target block (an editor stand-in).",
    help="""
    Projectiles are not simulated: this makes one hit the target block at POS in the next
    tick's entity phase with signal strength S (1-15, default 15: the center), keeping it
    powered for 20 ticks (arrow, default) or 8 (snowball and other projectiles), as the
    game does (EXP-037). Usually recorded: `at 3 hit @TARGET strength 9`.
    """,
    examples=("at 3 hit 0 1 0", "at 3 hit @T strength 9 snowball"),
    kind="edit",
    data='{"pos", "state", "strength", "arrow", "tick"}',
)
def hit(session: Session, args: Args) -> Output:
    pos = args.pos()
    strength = args.option_int("strength", 15)
    arrow = True
    if args.option("snowball"):
        arrow = False
    else:
        args.option("arrow")
    args.done()
    if not 1 <= strength <= 15:
        raise CliError("hit: strength must be 1 to 15")
    with session.editing() as doc:
        doc.projectile_hit(pos, strength, arrow)
    return _done(session, "hit", pos, {"strength": strength, "arrow": arrow})


@command(
    "page",
    group="build",
    usage="page POS N",
    summary="Turn a lectern's book to page N (as a player).",
    help="""
    A player turns the book on the lectern at POS to page N (0-based): its comparator
    reading changes and it gives a 2-tick redstone pulse (`LecternBlockEntity.setPage`).
    """,
    examples=("at 4 page @LECTERN 2",),
    kind="edit",
    data='{"pos", "state", "page", "tick"}',
)
def page(session: Session, args: Args) -> Output:
    pos = args.pos()
    number = args.number("a page number")
    args.done()
    with session.editing() as doc:
        doc.turn_page(pos, number)
    return _done(session, f"turned to page {number}:", pos, {"page": number})


# ---------------------------------------------------------------------------- regions
def _region_text(low: Pos, high: Pos) -> str:
    return f"{format_pos(low)} to {format_pos(high)}"


@command(
    "copy",
    group="build",
    usage="copy POS POS to POS",
    summary="Copy a box to another place (like /clone … strict: no block updates).",
    help="""
    Copies the box between the first two corners so that its lowest corner lands at the
    third position. Like the editor's copy: `/clone … strict replace force`, so nothing in
    the copy is updated (a torch keeps its state even if its input differs there) and
    pending scheduled ticks inside come along. Air is copied too.
    """,
    examples=("copy 0 1 0 4 2 2 to 0 1 5",),
    kind="edit",
    data='{"from": [low, high], "to": [low, high], "tick"}',
)
def copy(session: Session, args: Args) -> Output:
    return _clone(session, args, "force", "copied")


@command(
    "move",
    group="build",
    usage="move POS POS to POS",
    summary="Move a box (like /clone … strict replace move).",
    help="""
    Moves the box between the first two corners so that its lowest corner lands at the
    third position; the old place becomes air. No block updates (strict), pending ticks
    move along.
    """,
    examples=("move 0 1 0 4 2 2 to 10 1 0",),
    kind="edit",
    data='{"from": [low, high], "to": [low, high], "tick"}',
)
def move(session: Session, args: Args) -> Output:
    return _clone(session, args, "move", "moved")


def _clone(session: Session, args: Args, mode: str, verb: str) -> Output:
    from redsim.editor.clipboard import Region

    low, high = region(args)
    if not args.option("to"):
        raise CliError(f"{verb}: say where: to POS")
    dest = args.pos("the destination")
    args.done()
    if volume(low, high) > MAX_VOLUME:
        raise CliError(f"{verb}: the box is larger than the game allows ({MAX_VOLUME})")
    shift = (dest[0] - low[0], dest[1] - low[1], dest[2] - low[2])
    with session.editing() as doc:
        new = doc.clone_region(Region(low, high), shift, mode)
    text = (
        f"{verb} {_region_text(low, high)} to {_region_text(new.low, new.high)} ({session.where})"
    )
    return Output(
        [text],
        {
            "from": [list(low), list(high)],
            "to": [list(new.low), list(new.high)],
            "tick": session.edit_tick,
        },
    )


@command(
    "rotate",
    group="build",
    usage="rotate POS POS [times N]",
    summary="Turn a box clockwise (seen from above) in place, N quarter turns.",
    help="""
    Turns the box between the corners N quarter turns clockwise seen from above (default 1)
    around its center; the blocks' facing turns with it. No block updates, pending ticks
    move along. A box that is not square ends up at a new place: the output says where.
    """,
    examples=("rotate 0 1 0 4 2 2", "rotate 0 1 0 4 2 2 times 2"),
    kind="edit",
    data='{"from": [low, high], "to": [low, high], "tick"}',
)
def rotate(session: Session, args: Args) -> Output:
    from redsim.editor.clipboard import Region

    low, high = region(args)
    turns = args.option_int("times", 1)
    args.done()
    with session.editing() as doc:
        new = doc.transform_region(Region(low, high), quarter_turns=turns % 4)
    now = _region_text(new.low, new.high)
    text = f"rotated {_region_text(low, high)} by {turns * 90}°, now {now} ({session.where})"
    return Output(
        [text],
        {
            "from": [list(low), list(high)],
            "to": [list(new.low), list(new.high)],
            "tick": session.edit_tick,
        },
    )


@command(
    "mirror",
    group="build",
    usage="mirror POS POS x|z",
    summary="Mirror a box in place (x: east-west, z: north-south).",
    help="""
    Mirrors the box between the corners in place: `x` swaps east and west, `z` north and
    south; facing properties mirror with it. No block updates, pending ticks move along.
    """,
    examples=("mirror 0 1 0 4 2 2 x",),
    kind="edit",
    data='{"from": [low, high], "axis", "tick"}',
)
def mirror(session: Session, args: Args) -> Output:
    from redsim.editor.clipboard import Region

    low, high = region(args)
    axis = args.choice(("x", "z"), "x or z")
    args.done()
    with session.editing() as doc:
        doc.transform_region(Region(low, high), mirror=axis)
    return Output(
        [f"mirrored {_region_text(low, high)} along {axis} ({session.where})"],
        {"from": [list(low), list(high)], "axis": axis, "tick": session.edit_tick},
    )


@command(
    "stack",
    group="build",
    usage="stack POS POS DIRECTION [times N] [gap G]",
    summary="Repeat a box N times next to itself in a direction.",
    help="""
    Puts N copies (default 1) of the box between the corners next to it, one after the
    other in DIRECTION (north, south, east, west, up, down), with G blocks between copies
    (default 0). Strict (no block updates); pending ticks are copied. Useful for repeating
    a cell of a circuit (a bit of a register, a slice of a door).
    """,
    examples=("stack 0 1 0 2 3 0 east times 7", "stack 0 1 0 0 1 3 up times 3 gap 1"),
    kind="edit",
    data='{"from": [low, high], "box": [low, high] (all copies), "tick"}',
)
def stack(session: Session, args: Args) -> Output:
    from redsim.editor.clipboard import Region

    low, high = region(args)
    direction = args.direction()
    count = args.option_int("times", 1)
    gap = args.option_int("gap", 0)
    args.done()
    size = (high[0] - low[0] + 1, high[1] - low[1] + 1, high[2] - low[2] + 1)
    step = tuple(direction.step[i] * (size[i] + gap) for i in range(3))
    with session.editing() as doc:
        box = doc.stack_region(Region(low, high), step, count)
    whole = _region_text(box.low, box.high)
    text = (
        f"stacked {_region_text(low, high)} {count}× {direction.serialized}, "
        f"all: {whole} ({session.where})"
    )
    return Output(
        [text],
        {
            "from": [list(low), list(high)],
            "box": [list(box.low), list(box.high)],
            "tick": session.edit_tick,
        },
    )


# ---------------------------------------------------------------------------- prefabs
@command(
    "prefab",
    group="build",
    usage="prefab save NAME POS POS | prefab list | prefab delete NAME",
    summary="Keep a box of the build as a named prefab (a reusable module).",
    help="""
    `prefab save NAME POS POS` captures the box between the corners **from the build**
    (tick 0; air and block-entity data included) under NAME, saved with the world; the
    editor lists it under Circuit → Prefabs. `paste NAME at POS` places a copy. Use it to
    reuse a module that passed its targets (a gate, a memory cell, a door slice).
    `prefab list` lists them with their sizes, `prefab delete NAME` removes one.
    """,
    examples=("prefab save and 0 1 0 4 2 2", "prefab list", "paste and at 0 1 6"),
    kind="meta",
    data='{"prefabs": [{"name", "size", "blocks"}]}',
)
def prefab(session: Session, args: Args) -> Output:
    from redsim.editor.clipboard import Prefab, Region

    doc = session.doc
    verb = args.choice(("save", "list", "delete"), "save, list or delete")
    if verb == "save":
        name = args.word("a prefab name")
        low, high = region(args)
        args.done()
        if volume(low, high) > MAX_VOLUME:
            raise CliError(f"prefab: the box is larger than {MAX_VOLUME} blocks")
        doc.prefabs[name] = Prefab.capture(doc.history.base.level, Region(low, high), name)
        doc.dirty = True
        session.changed = True
    elif verb == "delete":
        name = args.word("a prefab name")
        args.done()
        if doc.prefabs.pop(name, None) is None:
            raise CliError(f"prefab: no prefab {name!r}")
        session.changed = True
    else:
        args.done()
    rows = [{"name": n, "size": list(p.size), "blocks": p.non_air_count}
            for n, p in sorted(doc.prefabs.items())]  # fmt: skip
    out = Output([f"  {r['name']:<16} {'×'.join(str(v) for v in r['size'])}  {r['blocks']} blocks"
                  for r in rows] or ["  (no prefabs: prefab save NAME POS POS)"])  # fmt: skip
    out.data = {"prefabs": rows}
    return out


@command(
    "paste",
    group="build",
    usage="paste NAME at POS [rotate N] [mirror x|z]",
    summary="Place a copy of a prefab with its lowest corner at POS.",
    help="""
    Places the prefab NAME (see `prefab`) with its lowest corner at POS, turned N quarter
    turns clockwise seen from above and/or mirrored, like the editor's paste (`/clone …
    strict`: no block updates, air included). Run `settle` afterwards if the copy sits
    next to something it should react to.
    """,
    examples=("paste and at 0 1 6", "paste door at 10 1 0 rotate 2"),
    kind="edit",
    data='{"name", "low", "high", "tick"}',
)
def paste(session: Session, args: Args) -> Output:
    doc = session.doc
    name = args.word("a prefab name")
    if name not in doc.prefabs:
        known = ", ".join(sorted(doc.prefabs)) or "none yet"
        raise CliError(f"paste: no prefab {name!r} (prefabs: {known})")
    if not args.option("at"):
        raise CliError("paste: say where: at POS")
    pos = args.pos()
    turns = args.option_int("rotate", 0)
    axis = args.choice(("x", "z"), "x or z") if args.option("mirror") else None
    args.done()
    item = doc.prefabs[name]
    if turns % 4:
        item = item.rotated(turns % 4)
    if axis is not None:
        item = item.mirrored(axis)
    with session.editing() as edited:
        edited.paste(pos, item)
    high = tuple(pos[i] + item.size[i] - 1 for i in range(3))
    text = f"pasted {name} at {format_pos(pos)} to {format_pos(high)} ({session.where})"
    return Output([text], {"name": name, "low": list(pos), "high": list(high),
                           "tick": session.edit_tick})  # fmt: skip
