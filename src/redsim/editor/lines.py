"""Timeline lines: one line per block position of a category (powered positions, placed
blocks, …), in named, colored groups (like Ableton Live's group tracks), in the order the
user chose. Annotations only: they never change the simulation, they are saved with the
document (``extra``).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from redsim.core.pos import Pos

#: Colors offered for new groups, in turn (Ableton-like, readable on the dark theme).
GROUP_COLORS = ("#e05050", "#4f8fe0", "#5fbf4a", "#e0a030", "#b060d0", "#40c0c0", "#d07090")
DEFAULT_GROUP = "Pulses"
#: The first group of the other categories' lines (Placed, Removed, …).
BLOCKS_GROUP = "Blocks"


@dataclass
class LineGroup:
    name: str
    color: str
    members: list[Pos] = field(default_factory=list)
    collapsed: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "color": self.color,
            "members": [list(p) for p in self.members],
            "collapsed": self.collapsed,
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> LineGroup:
        members = [(int(x), int(y), int(z)) for x, y, z in data.get("members", [])]
        return LineGroup(
            str(data.get("name", DEFAULT_GROUP)),
            str(data.get("color", GROUP_COLORS[0])),
            members,
            bool(data.get("collapsed", False)),
        )


@dataclass
class Lines:
    groups: list[LineGroup] = field(default_factory=list)

    # ------------------------------------------------------------------ queries
    def group_of(self, pos: Pos) -> int | None:
        return next((i for i, g in enumerate(self.groups) if pos in g.members), None)

    def color_of(self, pos: Pos) -> str:
        index = self.group_of(pos)
        return self.groups[index].color if index is not None else GROUP_COLORS[0]

    # ------------------------------------------------------------------ changes
    def sync(
        self, positions: Iterable[Pos], default: str = DEFAULT_GROUP, color: str = GROUP_COLORS[0]
    ) -> bool:
        """Every position has a line (new ones join the first group, made as ``default``
        when there is none); lines of other positions go. Returns whether anything
        changed."""
        wanted = list(dict.fromkeys(positions))
        changed = False
        for group in self.groups:
            kept = [p for p in group.members if p in wanted]
            changed |= kept != group.members
            group.members = kept
        missing = [p for p in wanted if self.group_of(p) is None]
        if missing:
            if not self.groups:
                self.groups.append(LineGroup(default, color))
            self.groups[0].members.extend(missing)
            changed = True
        return changed

    def move(self, pos: Pos, group: int, row: int) -> None:
        """Put ``pos``'s line into group ``group`` at ``row`` (clamped)."""
        if not 0 <= group < len(self.groups):
            return
        old = self.group_of(pos)
        if old is not None:
            members = self.groups[old].members
            at = members.index(pos)
            members.remove(pos)
            if old == group and at < row:
                row -= 1
        target = self.groups[group].members
        target.insert(max(0, min(row, len(target))), pos)

    def add_group(self, name: str, members: Iterable[Pos] = ()) -> int:
        color = GROUP_COLORS[len(self.groups) % len(GROUP_COLORS)]
        self.groups.append(LineGroup(name, color))
        index = len(self.groups) - 1
        for pos in members:
            self.move(pos, index, len(self.groups[index].members))
        return index

    def remove_group(self, index: int) -> None:
        """Delete a group; its lines move to the group before it (or the next one)."""
        if not 0 <= index < len(self.groups):
            return
        members = self.groups.pop(index).members
        if not self.groups:
            self.groups.append(LineGroup(DEFAULT_GROUP, GROUP_COLORS[0]))
        self.groups[max(0, index - 1)].members.extend(members)

    def move_group(self, index: int, step: int) -> None:
        other = index + step
        if 0 <= index < len(self.groups) and 0 <= other < len(self.groups):
            self.groups[index], self.groups[other] = self.groups[other], self.groups[index]

    # ------------------------------------------------------------------ saving
    def to_json(self) -> list[dict[str, Any]]:
        return [g.to_json() for g in self.groups]

    @staticmethod
    def from_json(data: Any) -> Lines:
        groups = [LineGroup.from_json(g) for g in data or [] if isinstance(g, dict)]
        return Lines(groups)
