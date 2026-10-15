"""Labels: names for positions (``@NAME`` on the command line, ``redsim.cli``).

A label is an annotation only (it never affects the simulation): a name, the position it
stands for and an optional note ("input A", "the clock's output"). Labels are saved in the
world file (``extra["labels"]``) and shown by the editor and the command line.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from redsim.core.pos import Pos


@dataclass(frozen=True)
class Label:
    pos: Pos
    note: str = ""

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {"pos": list(self.pos)}
        if self.note:
            data["note"] = self.note
        return data

    @staticmethod
    def from_json(data: dict[str, Any]) -> Label:
        x, y, z = (int(v) for v in data["pos"])
        return Label((x, y, z), str(data.get("note", "")))
