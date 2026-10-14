"""A pending change of the selected blocks, like GIMP's floating selection: the blocks
moved, turned, flipped or copied are only shown (a pulsing preview) until Enter places
them (owner, 2026-10-14: "only place the blocks upon confirming the position with Enter").

``Floating`` keeps where every selected cell goes as one map on block positions: a turn or
a mirror of x/z (one of the 8 the editor can make) plus a shift. Moving, turning and
flipping again only change the map; ``action`` turns it into one
``Document.transform_regions`` call (mirror, quarter turns around a pivot, offset), so
placing is one edit and one undo step, whatever was done before.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace

from redsim.core.pos import Pos
from redsim.editor.clipboard import Prefab, Region, bounding_box
from redsim.sim.level import Level
from redsim.world import blocks
from redsim.world.block import BlockState
from redsim.world.rotation import default_pivot2, mirror_state, rotate_about, rotate_state

Linear = tuple[int, int, int, int]  # x' = a x + b z, z' = c x + d z
IDENTITY: Linear = (1, 0, 0, 1)


def _turn(linear: Linear) -> Linear:
    """The linear part followed by a clockwise quarter turn ((x, z) → (−z, x))."""
    a, b, c, d = linear
    return (-c, -d, a, b)


def _mirror_x(linear: Linear) -> Linear:
    a, b, c, d = linear
    return (-a, -b, c, d)


def decompose(linear: Linear) -> tuple[int, bool]:
    """Quarter turns and whether x is mirrored first: ``linear`` = turns ∘ mirror."""
    for mirrored in (False, True):
        start = _mirror_x(IDENTITY) if mirrored else IDENTITY
        for turns in range(4):
            if start == linear:
                return turns, mirrored
            start = _turn(start)
    raise ValueError(f"not a turn or mirror: {linear}")


@dataclass(frozen=True)
class Floating:
    """The selected boxes (``regions``, where the blocks are now) and where they go."""

    regions: tuple[Region, ...]
    copy: bool = False
    linear: Linear = IDENTITY
    shift: Pos = (0, 0, 0)
    #: A prefab dragged into the view (owner, 2026-10-14: "a non-pasted selection instead
    #: of a disruptive place action"): its blocks come from here, not from the world, at
    #: ``regions[0]``; Enter pastes it (``placed_prefab``).
    prefab: Prefab | None = None
    #: The doubled x/z point the last turn went around, with the boxes it left: further
    #: turns of the same boxes keep it, so four turns (or R, Shift+R) return exactly.
    turn_pivot: tuple[tuple[Region, ...], tuple[int, int]] | None = None

    # ------------------------------------------------------------------ the map
    def map(self, pos: Pos) -> Pos:
        a, b, c, d = self.linear
        x, y, z = pos
        return (a * x + b * z + self.shift[0], y + self.shift[1], c * x + d * z + self.shift[2])

    def boxes(self) -> tuple[Region, ...]:
        """Where the boxes go (same order as ``regions``)."""
        return tuple(Region.from_corners(self.map(r.low), self.map(r.high)) for r in self.regions)

    @property
    def changed(self) -> bool:
        """Whether placing would change anything (a copy in place changes nothing; a
        dragged-in prefab always places something)."""
        return self.prefab is not None or self.linear != IDENTITY or self.shift != (0, 0, 0)

    @property
    def keeps_source(self) -> bool:
        """The blocks stay where they are (a copy, or a prefab that is not in the world)."""
        return self.copy or self.prefab is not None

    @staticmethod
    def of_prefab(prefab: Prefab, origin: Pos) -> Floating:
        sx, sy, sz = prefab.size
        high = (origin[0] + sx - 1, origin[1] + sy - 1, origin[2] + sz - 1)
        return Floating((Region(origin, high),), prefab=prefab)

    def _sources(self, level: Level) -> dict[Pos, BlockState]:
        """The blocks being moved: from the world, or from the prefab."""
        if self.prefab is None:
            return level.blocks
        ox, oy, oz = self.regions[0].low
        return {
            (ox + dx, oy + dy, oz + dz): blocks.parse_state(text)
            for dx, dy, dz, text, _ in self.prefab.blocks
        }

    def placed_prefab(self) -> tuple[Pos, Prefab]:
        """A dragged-in prefab as it goes into the world: its minimum corner and its
        blocks turned and mirrored like the preview."""
        assert self.prefab is not None
        turns, mirrored = decompose(self.linear)
        box = self.boxes()[0]
        ox, oy, oz = self.regions[0].low
        entries = []
        for dx, dy, dz, text, data in self.prefab.blocks:
            state = blocks.parse_state(text)
            if mirrored:
                state = mirror_state(state, "x")
            state = rotate_state(state, turns)
            x, y, z = self.map((ox + dx, oy + dy, oz + dz))
            entries.append((x - box.low[0], y - box.low[1], z - box.low[2], repr(state), data))
        entries.sort(key=lambda entry: (entry[2], entry[1], entry[0]))
        return box.low, Prefab(self.prefab.name, box.size, entries)

    def _then(self, operation: Callable[[Pos], Pos]) -> Floating:
        """This map followed by ``operation`` (affine on block positions)."""
        origin = operation(self.map((0, 0, 0)))
        east = operation(self.map((1, 0, 0)))
        south = operation(self.map((0, 0, 1)))
        linear = (
            east[0] - origin[0],
            south[0] - origin[0],
            east[2] - origin[2],
            south[2] - origin[2],
        )
        return replace(self, linear=linear, shift=origin)

    # ------------------------------------------------------------------ changes
    def moved(self, offset: Pos) -> Floating:
        dx, dy, dz = offset
        return replace(self, shift=(self.shift[0] + dx, self.shift[1] + dy, self.shift[2] + dz))

    def turned(self, quarter_turns: int) -> Floating:
        """Turned clockwise (seen from above) around the middle of where the boxes go."""
        boxes = self.boxes()
        if self.turn_pivot is not None and self.turn_pivot[0] == boxes:
            pivot = self.turn_pivot[1]
        else:
            pivot = default_pivot2(*bounding_box(list(boxes)))
        turns = quarter_turns % 4
        result = self._then(lambda pos: rotate_about(pos, pivot, turns))
        return replace(result, turn_pivot=(result.boxes(), pivot))

    def flipped(self, axis: str) -> Floating:
        """Mirrored east-west (``"x"``) or north-south (``"z"``) within where the boxes go."""
        low, high = bounding_box(list(self.boxes()))
        if axis == "x":
            return self._then(lambda p: (low[0] + high[0] - p[0], p[1], p[2]))
        return self._then(lambda p: (p[0], p[1], low[2] + high[2] - p[2]))

    # ------------------------------------------------------------------ the blocks
    def cells(self) -> Iterator[Pos]:
        """Every selected cell once (boxes may overlap)."""
        seen: set[Pos] = set()
        for region in self.regions:
            for pos in region.positions():
                if pos not in seen:
                    seen.add(pos)
                    yield pos

    def preview(self, level: Level) -> dict[Pos, BlockState]:
        """The selected blocks as they would be placed, at ``map`` minus ``shift`` (so a
        preview made once follows a move by its offset alone): position → block state."""
        turns, mirrored = decompose(self.linear)
        a, b, c, d = self.linear
        sources = self._sources(level)
        out: dict[Pos, BlockState] = {}
        for pos in self.cells():
            state = sources.get(pos)
            if state is None or state.is_air:
                continue
            if mirrored:
                state = mirror_state(state, "x")
            state = rotate_state(state, turns)
            x, y, z = pos
            out[(a * x + b * z, y, c * x + d * z)] = state
        return out

    def replaced(self, level: Level) -> list[Pos]:
        """Blocks outside the selection that placing would overwrite (every selected cell
        is placed, air too, as ``/clone`` does)."""
        own = set(self.cells())
        hit = []
        for pos in own:
            target = self.map(pos)
            state = level.blocks.get(target)
            if state is not None and not state.is_air and (self.keeps_source or target not in own):
                hit.append(target)
        return hit

    def action(self) -> tuple[int, str | None, tuple[int, int], Pos]:
        """Arguments for ``Document.transform_regions``: quarter turns, mirror, pivot,
        offset. Its map (mirror within the bounding box, turn around the pivot, shift)
        equals ``map``."""
        turns, mirrored = decompose(self.linear)
        low, high = bounding_box(list(self.regions))
        pivot = default_pivot2(low, high)
        x = low[0] + high[0] - low[0] if mirrored else low[0]
        turned = rotate_about((x, low[1], low[2]), pivot, turns)
        target = self.map(low)
        offset = (target[0] - turned[0], target[1] - turned[1], target[2] - turned[2])
        return turns, "x" if mirrored else None, pivot, offset
