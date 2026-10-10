"""Groups: named parts of a circuit with exposed input/output ports.

Groups are an abstraction for *reading* a circuit, not for simulating it differently. The
internals keep running block by block with unchanged timing (the brief forbids hiding
internal behavior unless the user explicitly picks an abstract model, which does not exist
yet). Ports name positions whose state the UI reports live, and input ports that hold a
usable block (lever, button) can be toggled from the panel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from redsim.core.pos import Pos
from redsim.editor.clipboard import Region
from redsim.sim.level import Level
from redsim.world.properties import LIT, POWER, POWERED

Role = Literal["input", "output"]


@dataclass
class Port:
    name: str
    pos: Pos
    role: Role


@dataclass
class Group:
    name: str
    region: Region
    ports: list[Port] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "low": list(self.region.low),
            "high": list(self.region.high),
            "ports": [{"name": p.name, "pos": list(p.pos), "role": p.role} for p in self.ports],
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> Group:
        def pos(value: list[int]) -> Pos:
            return (int(value[0]), int(value[1]), int(value[2]))

        ports = [Port(p["name"], pos(p["pos"]), p["role"]) for p in data.get("ports", [])]
        return Group(data["name"], Region(pos(data["low"]), pos(data["high"])), ports)


def port_reading(level: Level, port: Port) -> str:
    """A short, signal-oriented description of the port block's current state."""
    state = level.get_block_state(port.pos)
    name = state.block.name
    if state.has(POWER):
        return f"{name} power {state.get(POWER)}"
    if state.has(POWERED):
        return f"{name} {'ON' if state.get(POWERED) else 'off'}"
    if state.has(LIT):
        return f"{name} {'ON' if state.get(LIT) else 'off'}"
    if state.is_air:
        return "air"
    signal = level.get_best_neighbor_signal(port.pos)
    return f"{name} (receives {signal})"


class Groups:
    def __init__(self) -> None:
        self.groups: dict[str, Group] = {}

    def add(self, group: Group) -> None:
        self.groups[group.name] = group

    def remove(self, name: str) -> None:
        self.groups.pop(name, None)

    def to_json(self) -> list[dict[str, Any]]:
        return [group.to_json() for group in self.groups.values()]

    @staticmethod
    def from_json(data: list[dict[str, Any]]) -> Groups:
        groups = Groups()
        for entry in data:
            groups.add(Group.from_json(entry))
        return groups
