"""User-defined circuit sections (input, processing, output, clock, …).

Sections are annotations only: they color the view and never affect simulation. They live
next to the world, not inside block states, and are saved in the save file's ``extra``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from redsim.core.pos import Pos

DEFAULT_SECTIONS = {
    "input": "#3fa9f5",
    "processing": "#f5a623",
    "output": "#7ed321",
    "clock": "#bd10e0",
}


@dataclass
class Section:
    name: str
    color: str  # "#rrggbb"
    positions: set[Pos] = field(default_factory=set)


class Sections:
    def __init__(self) -> None:
        self.sections: dict[str, Section] = {
            name: Section(name, color) for name, color in DEFAULT_SECTIONS.items()
        }

    def add(self, name: str, color: str) -> Section:
        section = self.sections.get(name)
        if section is None:
            section = Section(name, color)
            self.sections[name] = section
        else:
            section.color = color
        return section

    def remove(self, name: str) -> None:
        self.sections.pop(name, None)

    def assign(self, pos: Pos, name: str | None) -> None:
        """Put ``pos`` into section ``name`` (``None``: no section). One section per block."""
        for section in self.sections.values():
            section.positions.discard(pos)
        if name is not None:
            self.sections[name].positions.add(pos)

    def section_at(self, pos: Pos) -> Section | None:
        for section in self.sections.values():
            if pos in section.positions:
                return section
        return None

    def to_json(self) -> dict[str, Any]:
        return {
            name: {"color": s.color, "positions": sorted(list(p) for p in s.positions)}
            for name, s in self.sections.items()
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> Sections:
        sections = Sections()
        sections.sections = {}
        for name, entry in data.items():
            positions = {(int(p[0]), int(p[1]), int(p[2])) for p in entry.get("positions", [])}
            sections.sections[name] = Section(name, entry["color"], positions)
        return sections
