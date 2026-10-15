"""Text views of a world (doc/cli.md, "Reading a map"): maps of a layer or a slice, the
description of one block, signal timelines.

**Map cells.** A map is a grid with one cell of two characters per block. The first
character says what the block is; for components an **upper-case** letter means the block
is on (powered, lit, extended, pressed) and a **lower-case** one that it is off. The
second character is a direction arrow, a signal strength or a mark:

    ..  air                         ##  full block that conducts   ::  full block that does not
    w7  redstone wire, power 7 (hex: wa = 10, wf = 15)      **  redstone block
    R>  repeater, output east       C>  comparator (K> in subtract mode)
    T.  torch on the floor          T>  wall torch pointing east (away from its wall)
    V.  lever   B.  button   P_  pressure plate   L.  lamp   Q.  copper bulb
    O>  observer, output east (it watches the west)
    I>  piston pushing east         J>  sticky piston   H>  piston head   M>  moving block
    X7  target block, power 7       N.  note block      D>  dispenser     E>  dropper
    U-  hopper pointing down (U: locked by power)
    ==  rail   G=  powered rail   A=  activator rail
    %%  falling block (an entity)
    Ab  any other block: its own two letters, listed in the legend

Arrows: ``>`` and ``<`` along the map's horizontal axis, ``^`` and ``v`` along its vertical
axis (up the page / down the page), ``+`` and ``-`` along the axis looking into the page.
Which world directions these are depends on the view and is printed above each map:

* ``y=Y`` (from above): x to the right (east ``>``), z downwards (north ``^`` at the top,
  south ``v``), up ``+``, down ``-``;
* ``z=Z`` (from the south, looking north): x to the right, y upwards (up ``^``), south
  ``+`` (towards you), north ``-``;
* ``x=X`` (from the west, looking east): z to the right (south ``>``), y upwards, east
  ``+`` (away from you), west ``-``.

The **power** map (``show … power``) has the same grid with each block's signal strength
instead: ``f`` = 15 … ``1``, ``.`` = none (signal sources: their own output; other blocks:
the strongest signal they receive, ``getBestNeighborSignal``).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from redsim.core.direction import ALL, Axis, Direction
from redsim.core.pos import Pos, offset

if TYPE_CHECKING:
    from redsim.sim.level import Level
    from redsim.world.block import BlockState

HEX = "0123456789abcdef"


def short(state_text: str) -> str:
    """A state without the ``minecraft:`` prefix (the language reads both)."""
    return state_text.replace("minecraft:", "")


def state_text(state: BlockState) -> str:
    return short(repr(state))


def prop(state: BlockState, name: str) -> Any:
    """A property value by name, or None if the block has no such property."""
    for p in state.block.properties:
        if p.name == name:
            return state.get(p)
    extra = getattr(state.block, "extra_properties", None) or {}
    return extra.get(name)


# ---------------------------------------------------------------------------- planes
@dataclass(frozen=True)
class Plane:
    """A view: which world axis runs to the right (``h``), which up the page (``v``,
    with ``v_down`` when it runs down the page) and which into it (``depth``)."""

    name: str  # "y", "z" or "x": the fixed axis
    h: Axis
    v: Axis
    v_down: bool
    depth: Axis
    caption: str

    def arrow(self, direction: Direction) -> str:
        step = dict(zip((Axis.X, Axis.Y, Axis.Z), direction.step, strict=True))
        if step[self.h]:
            return ">" if step[self.h] > 0 else "<"
        if step[self.v]:
            up_the_page = (step[self.v] < 0) if self.v_down else (step[self.v] > 0)
            return "^" if up_the_page else "v"
        return "+" if step[self.depth] > 0 else "-"


PLANES = {
    "y": Plane(
        "y",
        Axis.X,
        Axis.Z,
        True,
        Axis.Y,
        "from above: x → right (east >), z ↓ (north ^ at the top), up +, down -",
    ),
    "z": Plane(
        "z",
        Axis.X,
        Axis.Y,
        False,
        Axis.Z,
        "from the south: x → right (east >), y ↑ (up ^), south + (towards you), north -",
    ),
    "x": Plane(
        "x",
        Axis.Z,
        Axis.Y,
        False,
        Axis.X,
        "from the west: z → right (south >), y ↑ (up ^), east + (away), west -",
    ),
}


# ---------------------------------------------------------------------------- codes
def _case(letter: str, on: bool) -> str:
    return letter.upper() if on else letter.lower()


#: The legend's words for each fixed key (``block_code``).
WORDS = {
    "..": "air",
    "##": "full block that conducts",
    "::": "full block that does not conduct",
    "**": "redstone block",
    "==": "rail",
    "%%": "falling block (an entity)",
    "w": "redstone wire, digit = power (hex: a = 10 … f = 15)",
    "R": "repeater, arrow = output",
    "C": "comparator, arrow = output",
    "K": "comparator in subtract mode, arrow = output",
    "T": "redstone torch (T. on the floor; T> on a wall, pointing away from it)",
    "V": "lever",
    "B": "button",
    "P": "pressure plate",
    "L": "redstone lamp",
    "Q": "copper bulb",
    "O": "observer, arrow = output (it watches the opposite side)",
    "I": "piston, arrow = push direction",
    "J": "sticky piston, arrow = push direction",
    "H": "piston head, arrow = facing",
    "M": "block being moved by a piston, arrow = movement",
    "X": "target block, digit = power",
    "N": "note block",
    "D": "dispenser, arrow = output",
    "E": "dropper, arrow = output",
    "U": "hopper, arrow = output (upper case = locked by power)",
    "G": "powered rail",
    "A": "activator rail",
}


def block_code(state: BlockState, level: Level, pos: Pos, plane: Plane) -> tuple[str, str]:
    """A block's map cell and its legend key (``WORDS``): the code's letter for
    components (``R`` for repeaters, ``w`` for wire), the code itself for the others. An
    empty code means "any other block" (``Legend`` gives it two letters)."""
    bid = state.block.id.removeprefix("minecraft:")
    if state.is_air:
        return "..", ".."
    facing = prop(state, "facing")
    powered = bool(prop(state, "powered"))
    lit = bool(prop(state, "lit"))
    arrow = plane.arrow
    if bid == "redstone_wire":
        return "w" + HEX[int(prop(state, "power"))], "w"
    if bid == "repeater":
        return _case("r", powered) + arrow(facing.opposite), "R"
    if bid == "comparator":
        letter = "k" if prop(state, "mode") == "subtract" else "c"
        return _case(letter, powered) + arrow(facing.opposite), letter.upper()
    if bid == "redstone_torch":
        return _case("t", lit) + ".", "T"
    if bid == "redstone_wall_torch":
        return _case("t", lit) + arrow(facing), "T"
    if bid == "lever":
        return _case("v", powered) + ".", "V"
    if bid.endswith("_button"):
        return _case("b", powered) + ".", "B"
    if bid.endswith("_pressure_plate"):
        return _case("p", powered or bool(prop(state, "power") or 0)) + "_", "P"
    if bid == "redstone_lamp":
        return _case("l", lit) + ".", "L"
    if "copper_bulb" in bid:
        return _case("q", lit) + ".", "Q"
    if bid == "observer":
        return _case("o", powered) + arrow(facing.opposite), "O"
    if bid in ("piston", "sticky_piston"):
        letter = "j" if bid == "sticky_piston" else "i"
        return _case(letter, bool(prop(state, "extended"))) + arrow(facing), letter.upper()
    if bid == "piston_head":
        return "H" + arrow(facing), "H"
    if bid == "moving_piston":
        entity = level.get_block_entity(pos, create=False)
        direction = getattr(entity, "push_direction", None)
        return "M" + (arrow(direction) if direction is not None else "?"), "M"
    if bid == "redstone_block":
        return "**", "**"
    if bid == "target":
        power = int(prop(state, "power"))
        return ("X" if power else "x") + HEX[power], "X"
    if bid == "note_block":
        return _case("n", powered) + ".", "N"
    if bid in ("dispenser", "dropper"):
        letter = "d" if bid == "dispenser" else "e"
        return _case(letter, bool(prop(state, "triggered"))) + arrow(facing), letter.upper()
    if bid == "hopper":
        return _case("u", prop(state, "enabled") is False) + arrow(facing), "U"
    if bid == "rail":
        return "==", "=="
    if bid in ("powered_rail", "activator_rail"):
        letter = "g" if bid == "powered_rail" else "a"
        return _case(letter, powered) + "=", letter.upper()
    full = state.get_collision_shape().is_full_block()
    if full and state.is_redstone_conductor(level, pos):
        return "##", "##"
    if full and not getattr(state.block, "extra_properties", None):
        return "::", "::"
    return "", ""


#: Legend keys whose case means on (upper) and off (lower).
ON_OFF_KEYS = frozenset("RCKTVBPLQOIJNDEUGA")


class Legend:
    """The codes used on one map with their meaning. Blocks without a fixed code get two
    letters of their own (upper then lower case: ``Ba`` barrel), unique on the map."""

    def __init__(self) -> None:
        self.entries: dict[str, str] = {}
        self.kinds: dict[str, set[str]] = {}
        self.generic: dict[str, str] = {}

    def code(self, state: BlockState, level: Level, pos: Pos, plane: Plane) -> str:
        code, key = block_code(state, level, pos, plane)
        bid = state.block.id.removeprefix("minecraft:")
        if not code:
            code = self.generic.get(bid) or self._new_generic(bid)
            key = code
        self.entries.setdefault(key, WORDS.get(key, bid))
        if key in ("##", "::"):
            self.kinds.setdefault(key, set()).add(bid)
        return code

    def _new_generic(self, bid: str) -> str:
        used = set(self.generic.values())
        letters = [c for c in bid.replace("_", "") if c.isalpha()]
        first = letters[0].upper() if letters else "Z"
        for c in letters[1:] + list("abcdefghijklmnopqrstuvwxyz"):
            code = first + c.lower()
            if code not in used:
                self.generic[bid] = code
                return code
        self.generic[bid] = "??"
        return "??"

    def lines(self) -> list[str]:
        out = []
        for key in sorted(self.entries, key=lambda k: (len(k), k.lower())):
            what = self.entries[key]
            if key in self.kinds:
                what = f"{what}: {', '.join(sorted(self.kinds[key]))}"
            if key in ON_OFF_KEYS:
                out.append(f"  {key}/{key.lower()}  {what} (upper case = on, lower case = off)")
            elif key in ("w", "X"):
                out.append(f"  {key}0-{key}f  {what}" if key == "w" else f"  x0/X1-Xf  {what}")
            else:
                out.append(f"  {key:<5}{what}" if len(key) == 2 else f"  {key}  {what}")
        return out


def layer_cells(
    level: Level, plane: Plane, fixed: int, h_range: range, v_range: range
) -> list[tuple[int, list[Pos]]]:
    """The positions of a map: rows (top to bottom) of positions (left to right)."""
    rows = []
    v_values = list(v_range)
    if not plane.v_down:
        v_values = v_values[::-1]
    for v in v_values:
        row = []
        for h in h_range:
            coords = {plane.h: h, plane.v: v, plane.depth: fixed}
            row.append((coords[Axis.X], coords[Axis.Y], coords[Axis.Z]))
        rows.append((v, row))
    return rows


def render_map(
    level: Level,
    plane: Plane,
    fixed: int,
    h_range: range,
    v_range: range,
    power: bool = False,
    entities: Iterable[Pos] = (),
    legend: Legend | None = None,
) -> tuple[list[str], list[list[str]]]:
    """A map as text lines (header, rows) and as a grid of cells (for ``--json``)."""
    from redsim.editor.heat import signal_heat

    legend = legend if legend is not None else Legend()
    falling = set(entities)
    heat = signal_heat(level) if power else {}
    h_name, v_name = plane.h.value, plane.v.value
    lines = [f"{h_name + ':':<6}" + "".join(f"{h:>3}" for h in h_range)]
    grid: list[list[str]] = []
    for v, row in layer_cells(level, plane, fixed, h_range, v_range):
        cells = []
        for pos in row:
            if power:
                strength = heat.get(pos, 0)
                cells.append(" " + (HEX[strength] if strength else "."))
            elif pos in falling and level.get_block_state(pos).is_air:
                legend.entries.setdefault("%%", "falling block (an entity)")
                cells.append("%%")
            else:
                cells.append(legend.code(level.get_block_state(pos), level, pos, plane))
        grid.append([c.strip() for c in cells])
        lines.append(f"{v_name}={v:>3} " + "".join(f"{c:>3}" for c in cells))
    return lines, grid


# ---------------------------------------------------------------------------- signals
def side_signals(level: Level, pos: Pos) -> dict[str, dict[str, int]]:
    """What the block at ``pos`` receives from and gives to each side.

    * ``in``: the signal arriving from the neighbor on that side (``Level.getSignal`` of
      the neighbor towards this block: what this block's ``hasNeighborSignal`` sees);
    * ``in_direct``: the direct part of it (``getDirectSignal``): the part that powers a
      solid block it touches;
    * ``out``: the signal this block gives the neighbor on that side (``getSignal``);
    * ``out_direct``: the direct part of that (``getDirectSignal``).
    """
    state = level.get_block_state(pos)
    out: dict[str, dict[str, int]] = {}
    for direction in ALL:
        near = offset(pos, direction)
        out[direction.serialized] = {
            "in": level.get_signal(near, direction),
            "in_direct": level.get_direct_signal(near, direction),
            "out": state.get_signal(level, pos, direction.opposite),
            "out_direct": state.get_direct_signal(level, pos, direction.opposite),
        }
    return out


def wave_row(values: list[int]) -> str:
    """Signal values (0-15) as one hex digit per tick, ``.`` for 0."""
    return "".join(HEX[v] if v else "." for v in values)


def tick_ruler(low: int, high: int) -> list[str]:
    """Two header lines numbering the columns of a timeline from ``low`` to ``high``: the
    tens (every tenth column) and the units."""
    tens = "".join(str((t // 10) % 10) if t % 10 == 0 else " " for t in range(low, high + 1))
    units = "".join(str(t % 10) for t in range(low, high + 1))
    return [tens, units]


def describe_signals(level: Level, pos: Pos) -> list[str]:
    """``inspect``'s signal lines: what arrives from which side and what leaves."""
    sides = side_signals(level, pos)

    def fmt(key: str, direct: str) -> str:
        parts = []
        for name, values in sides.items():
            if values[key]:
                extra = f" (direct {values[direct]})" if values[direct] else ""
                parts.append(f"{name} {values[key]}{extra}")
        return ", ".join(parts) or "nothing"

    return [f"  receives  {fmt('in', 'in_direct')}", f"  gives     {fmt('out', 'out_direct')}"]


def neighbors_text(level: Level, pos: Pos, name: Callable[[Pos], str]) -> list[str]:
    """The six neighbors, one per line: side, position, state."""
    lines = []
    for direction in ALL:
        near = offset(pos, direction)
        state = level.get_block_state(near)
        if state.is_air:
            continue
        lines.append(f"    {direction.serialized:<5} {name(near)}  {state_text(state)}")
    return lines
