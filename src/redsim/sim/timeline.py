"""Event-sourced simulation history: keyframes + input log + deterministic replay.

Every engine step (tick start, scheduled tick, block event, block-entity tick, player or
command action) advances ``Engine.step_index`` by one. The engine is deterministic, so the
whole history is determined by the starting snapshot and the actions applied at known step
indices. The timeline stores:

* ``keyframes``: full ``EngineSnapshot``s at some step indices (always at the start, before
  every action, and every ``keyframe_interval`` steps);
* ``inputs``: the action applied at each step index where one was applied, and
  ``input_times`` the game time it was applied at (actions at one tick boundary form one
  *edit batch*);
* ``tick_starts``: step indices of tick-start steps (for "tick back");
* ``end``: the furthest step index reached on the current branch.

``start`` is the **base** (tick 0): the build state the history starts from. Edits made at
the base are folded into it (``apply_to_base``) instead of being recorded, so they are never
replayed. Seeking restores the nearest keyframe at or before the target and re-executes.
Applying an action anywhere before ``end`` starts a new branch: everything after that point
is dropped. A failed action leaves no trace (the engine is restored). ``rewrite`` rebuilds
the whole history from a base snapshot and an edit plan (moving, merging or deleting edit
batches, and undo). See doc/decisions.md ADR-004 and ADR-022.
"""

from __future__ import annotations

from bisect import bisect_left, insort
from collections.abc import Callable

from redsim.sim.engine import Action, ActionError, Engine, EngineSnapshot, StepInfo

DEFAULT_KEYFRAME_INTERVAL = 64
MAX_KEYFRAMES = 400

#: Edits per game tick (relative to the base), in the order they were applied.
Plan = dict[int, list[Action]]


class Timeline:
    def __init__(self, engine: Engine, keyframe_interval: int = DEFAULT_KEYFRAME_INTERVAL) -> None:
        self.engine = engine
        self.keyframe_interval = keyframe_interval
        self.start = engine.step_index
        self.end = engine.step_index
        self.keyframes: dict[int, EngineSnapshot] = {engine.step_index: engine.snapshot()}
        self.inputs: dict[int, Action] = {}
        self.input_times: dict[int, int] = {}
        self.tick_starts: list[int] = []
        self.base_time = engine.level.game_time

    # ------------------------------------------------------------------ positions
    @property
    def position(self) -> int:
        return self.engine.step_index

    def can_step_back(self) -> bool:
        return self.position > self.start

    def action_indices(self) -> list[int]:
        return sorted(self.inputs)

    @property
    def at_base(self) -> bool:
        return self.position == self.start

    @property
    def base(self) -> EngineSnapshot:
        return self.keyframes[self.start]

    def tick(self) -> int:
        """Game ticks since the base (tick 0)."""
        return self.engine.level.game_time - self.base_time

    def plan(self) -> Plan:
        """The recorded edits per tick since the base, in application order."""
        plan: Plan = {}
        for index in sorted(self.inputs):
            plan.setdefault(self.input_times[index] - self.base_time, []).append(self.inputs[index])
        return plan

    def end_tick(self) -> int:
        """The last tick of the recorded history (relative to the base): every tick start
        recorded since the base is one tick."""
        return len(self.tick_starts)

    # ------------------------------------------------------------------ recording
    def step(self) -> StepInfo:
        """Run one engine step (re-applying a recorded action if the future is known)."""
        index = self.position
        if index < self.end and index in self.inputs:
            info = self._apply_recorded(self.inputs[index])
        else:
            info = self.engine.step()
        self._after_step(index, info)
        return info

    def run_tick(self) -> list[StepInfo]:
        """Run to the next tick boundary. Recorded edits are applied as a batch: the ones
        still pending at this boundary first, then those recorded at the next boundary, so
        a tick's edits appear together with its result."""
        steps = self._recorded_edits_here()
        steps.append(self.step())
        while not self.engine.at_tick_boundary():
            steps.append(self.step())
        steps.extend(self._recorded_edits_here())
        return steps

    def _recorded_edits_here(self) -> list[StepInfo]:
        steps = []
        while self.position < self.end and self.position in self.inputs:
            steps.append(self.step())
        return steps

    def finish_tick(self) -> list[StepInfo]:
        steps = []
        while not self.engine.at_tick_boundary():
            steps.append(self.step())
        return steps

    def apply(self, action: Action) -> StepInfo:
        """Apply a new action at the current position (truncating any recorded future).

        If the action fails (``ActionError``), the engine is restored to the state before
        it and nothing is recorded: a half-applied action would shift every later step."""
        index = self.position
        before = self.keyframes.get(index) or self.engine.snapshot()
        try:
            info = self.engine.apply(action)
        except ActionError:
            self._restore_snapshot(before, index)
            raise
        self._truncate_after(index)
        self.keyframes.setdefault(index, before)
        self.inputs[index] = action
        self.input_times[index] = self.engine.level.game_time
        self._after_step(index, info)
        return info

    def apply_to_base(self, action: Action) -> StepInfo:
        """An edit at tick 0: applied, then folded into the base (not recorded, never
        replayed). Any recorded future is dropped."""
        if not self.at_base:
            raise ActionError("not at the base (tick 0)")
        index = self.position
        before = self.base
        try:
            info = self.engine.apply(action)
        except ActionError:
            self._restore_snapshot(before, index)
            raise
        self.rebase()
        return info

    def rebase(self) -> None:
        """Make the current state the base (tick 0): the history before it is dropped."""
        if not self.engine.at_tick_boundary():
            raise ActionError("the base must be at a tick boundary")
        self.start = self.end = self.position
        self.keyframes = {self.start: self.engine.snapshot()}
        self.inputs, self.input_times, self.tick_starts = {}, {}, []
        self.base_time = self.engine.level.game_time

    def rewrite(
        self,
        base: EngineSnapshot,
        plan: Plan,
        end_tick: int,
        observe: Callable[[], None] | None = None,
    ) -> list[tuple[int, Action, str]]:
        """Rebuild the history from ``base`` with the edits in ``plan`` (tick 0 edits are
        folded into the base) up to ``end_tick``. Returns the edits that failed."""
        self._restore_snapshot(base, base.step_index)
        self.rebase()
        failures: list[tuple[int, Action, str]] = []
        for action in plan.get(0, []):
            try:
                self.apply_to_base(action)
            except ActionError as exc:
                failures.append((0, action, str(exc)))
        if observe is not None:
            observe()
        last = max([end_tick, *plan]) if plan else end_tick
        while self.tick() < last:
            while True:
                self.step()
                if self.engine.at_tick_boundary():
                    break
            for action in plan.get(self.tick(), []):
                try:
                    self.apply(action)
                except ActionError as exc:
                    failures.append((self.tick(), action, str(exc)))
            if observe is not None:
                observe()
        return failures

    def _restore_snapshot(self, snapshot: EngineSnapshot, index: int) -> None:
        self.engine.restore(snapshot)
        self.engine.level.trace.truncate_from_step(index)

    def _apply_recorded(self, action: Action) -> StepInfo:
        return self.engine.apply(action)

    def _after_step(self, index: int, info: StepInfo) -> None:
        if info.kind == "tick_start":
            i = bisect_left(self.tick_starts, index)
            if i == len(self.tick_starts) or self.tick_starts[i] != index:
                insort(self.tick_starts, index)
        self.end = max(self.end, self.position)
        if (self.position - self.start) % self.keyframe_interval == 0:
            self.keyframes.setdefault(self.position, self.engine.snapshot())
            self._thin_keyframes()

    def _truncate_after(self, index: int) -> None:
        if index >= self.end:
            return
        self.inputs = {i: a for i, a in self.inputs.items() if i < index}
        self.input_times = {i: t for i, t in self.input_times.items() if i < index}
        self.keyframes = {i: k for i, k in self.keyframes.items() if i <= index}
        self.tick_starts = [i for i in self.tick_starts if i < index]
        self.end = index

    def _thin_keyframes(self) -> None:
        """Drop every other periodic keyframe when there are too many (keep action ones)."""
        if len(self.keyframes) <= MAX_KEYFRAMES:
            return
        protected = set(self.inputs) | {self.start}
        periodic = sorted(k for k in self.keyframes if k not in protected)
        for index in periodic[::2]:
            del self.keyframes[index]

    # ------------------------------------------------------------------ seeking
    def seek(self, target: int) -> None:
        """Move to ``target`` (start ≤ target ≤ end) by restore + deterministic replay."""
        target = max(self.start, min(target, self.end))
        if target == self.position:
            return
        if target < self.position or target - self.position > self.keyframe_interval:
            base = max(k for k in self.keyframes if k <= target)
            if not (self.position <= target and self.position >= base):
                self._restore(base)
        while self.position < target:
            index = self.position
            if index in self.inputs:
                self.engine.apply(self.inputs[index])
            else:
                self.engine.step()

    def _restore(self, index: int) -> None:
        self.engine.restore(self.keyframes[index])
        self.engine.level.trace.truncate_from_step(index)

    def step_back(self) -> None:
        self.seek(self.position - 1)

    def tick_back(self) -> None:
        """Go to the previous tick boundary (the start of the current or previous tick)."""
        position = self.position
        i = bisect_left(self.tick_starts, position)
        if i == 0:
            self.seek(self.start)
            return
        self.seek(self.tick_starts[i - 1])

    def tick_forward(self) -> None:
        """Advance to the next tick boundary (replays the recorded future if any)."""
        if self.engine.at_tick_boundary():
            self.run_tick()
        else:
            self.finish_tick()

    def undo_target(self) -> int | None:
        """Step index just before the most recent action at or before the position."""
        earlier = [i for i in self.inputs if i < self.position]
        return max(earlier) if earlier else None

    def redo_target(self) -> int | None:
        """Step index just after the next recorded action after the position."""
        later = [i for i in self.inputs if i >= self.position]
        return min(later) + 1 if later else None
