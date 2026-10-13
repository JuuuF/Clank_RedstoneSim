"""The document's sequences: power pulses locked to positions (ADR-026), added, changed,
moved to other positions or removed, each change re-running the history with the plan."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from redsim.core.pos import Pos
from redsim.editor.document_history import EditError, HistoryState
from redsim.sim.engine import Action
from redsim.sim.timeline import Plan

if TYPE_CHECKING:
    from redsim.editor.document import Document


class SequenceOps:
    """Part of ``Document`` (a mixin; its methods run on it)."""

    def pulses(self) -> list[Pulse]:
        """The power pulses of the sequence (recorded ``power_pulse`` edits), by tick."""
        view = cast("Document", self)
        out = []
        for index, action in view.history.inputs.items():
            if action.kind == "power_pulse":
                payload = action.payload or {}
                out.append(
                    Pulse(
                        index,
                        view.edit_ticks.get(index, 0),
                        action.pos,
                        int(payload.get("strength", 15)),
                        int(payload.get("ticks", 1)),
                        bool(payload.get("muted", False)),
                    )
                )
        return sorted(out, key=lambda p: (p.tick, p.index))

    def add_pulse(self, pos: Pos, tick: int, strength: int = 15, ticks: int = 2) -> None:
        """Power the position ``pos`` (whatever block is there then) with ``strength`` from
        tick ``tick`` (≥ 1; tick 0 is the build) for ``ticks`` ticks; 0 ticks is a 0-tick
        pulse: on and off again at the same moment between ticks. Later edits stay:
        the history is re-run with the pulse in it (one undo step)."""
        view = cast("Document", self)
        if not 1 <= strength <= 15 or ticks < 0:
            raise EditError("A pulse needs a strength of 1–15 and 0 or more ticks.")
        action = Action("power_pulse", pos, payload={"strength": strength, "ticks": ticks})
        view._replan_with({max(1, tick): [replace(action, label="power pulse")]}, {}, "power pulse")

    def edit_pulse(self, index: int, tick: int, strength: int, ticks: int) -> None:
        """Change a pulse's start, strength or duration (re-runs the history)."""
        view = cast("Document", self)
        action = view.history.inputs.get(index)
        if action is None or action.kind != "power_pulse":
            raise EditError("No such pulse.")
        if not 1 <= strength <= 15 or ticks < 0:
            raise EditError("A pulse needs a strength of 1–15 and 0 or more ticks.")
        changed = replace(action, payload={**action.payload, "strength": strength, "ticks": ticks})
        view._replan_with({max(1, tick): [changed]}, {index: None}, "change a pulse")

    def edit_pulses(self, changes: list[tuple[int, int, int, int, Pos]]) -> None:
        """Change several pulses at once (index, tick, strength, ticks, position): moved
        in time, made longer, or given to another position; one re-run, one undo step."""
        view = cast("Document", self)
        additions: dict[int, list[Action]] = {}
        removed: dict[int, None] = {}
        for index, tick, strength, ticks, pos in changes:
            action = view.history.inputs.get(index)
            if action is None or action.kind != "power_pulse":
                raise EditError("No such pulse.")
            if not 1 <= strength <= 15 or ticks < 0:
                raise EditError("A pulse needs a strength of 1–15 and 0 or more ticks.")
            payload = {**action.payload, "strength": strength, "ticks": ticks}
            changed = replace(action, pos=pos, payload=payload)
            additions.setdefault(max(1, tick), []).append(changed)
            removed[index] = None
        if additions:
            label = "change a pulse" if len(changes) == 1 else f"change {len(changes)} pulses"
            view._replan_with(additions, removed, label)

    def set_pulses_muted(self, indices: list[int], muted: bool) -> None:
        """Bypass pulses (``muted``) or bring them back: they stay in the sequence and the
        timeline; muted ones have no effect. One re-run, one undo step."""
        view = cast("Document", self)
        additions: dict[int, list[Action]] = {}
        removed: dict[int, None] = {}
        for index in indices:
            action = view.history.inputs.get(index)
            if action is None or action.kind != "power_pulse":
                continue
            if bool((action.payload or {}).get("muted")) == muted:
                continue
            changed = replace(action, payload={**action.payload, "muted": muted})
            additions.setdefault(view.edit_ticks.get(index, 1), []).append(changed)
            removed[index] = None
        if additions:
            verb = "mute" if muted else "unmute"
            self._replan_with(additions, removed, f"{verb} {len(removed)} pulses")

    def _replan_with(
        self, additions: dict[int, list[Action]], removed: dict[int, None], label: str
    ) -> None:
        """Rebuild the history with edits added (tick → actions) and some removed (by
        index), keeping every other recorded edit at its tick."""
        view = cast("Document", self)
        if not view.can_edit:
            raise EditError("Finish the current tick first.")
        history = view.history
        before = view._history_state()
        plan: Plan = {}
        for index in sorted(history.inputs):
            if index not in removed:
                tick = view.edit_ticks.get(index, 0)
                plan.setdefault(tick, []).append(history.inputs[index])
        last = before.end_tick
        for tick, actions in sorted(additions.items()):
            plan.setdefault(tick, []).extend(actions)
            for action in actions:
                last = max(last, tick + int((action.payload or {}).get("ticks", 0)) + 1)
        failures = view._rebuild(HistoryState(before.base, plan, last, before.tick))
        view._undo.append(replace(before, label=label))
        view._redo.clear()
        view.notice = f"{label}." + (f" {len(failures)} edits failed." if failures else "")


@dataclass(frozen=True)
class Pulse:
    """One power pulse of a sequence: ``pos`` gets ``strength`` from ``tick`` for
    ``ticks`` ticks (``index``: the recorded edit's step index)."""

    index: int
    tick: int
    pos: Pos
    strength: int
    ticks: int
    muted: bool = False  # bypassed: shown, but without effect
