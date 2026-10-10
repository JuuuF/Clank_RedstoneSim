"""Event-sourced simulation history: keyframes + input log + deterministic replay.

Every engine step (tick start, scheduled tick, block event, block-entity tick, player or
command action) advances ``Engine.step_index`` by one. The engine is deterministic, so the
whole history is determined by the starting snapshot and the actions applied at known step
indices. The timeline stores:

* ``keyframes``: full ``EngineSnapshot``s at some step indices (always at the start, before
  every action, and every ``keyframe_interval`` steps);
* ``inputs``: the action applied at each step index where one was applied;
* ``tick_starts``: step indices of tick-start steps (for "tick back");
* ``end``: the furthest step index reached on the current branch.

Seeking restores the nearest keyframe at or before the target and re-executes. Applying an
action anywhere before ``end`` starts a new branch: everything after that point is dropped.
See doc/decisions.md ADR-004.
"""

from __future__ import annotations

from bisect import bisect_left, insort

from redsim.sim.engine import Action, Engine, EngineSnapshot, StepInfo

DEFAULT_KEYFRAME_INTERVAL = 200
MAX_KEYFRAMES = 400


class Timeline:
    def __init__(self, engine: Engine, keyframe_interval: int = DEFAULT_KEYFRAME_INTERVAL) -> None:
        self.engine = engine
        self.keyframe_interval = keyframe_interval
        self.start = engine.step_index
        self.end = engine.step_index
        self.keyframes: dict[int, EngineSnapshot] = {engine.step_index: engine.snapshot()}
        self.inputs: dict[int, Action] = {}
        self.tick_starts: list[int] = []
        self._replaying = False

    # ------------------------------------------------------------------ positions
    @property
    def position(self) -> int:
        return self.engine.step_index

    def can_step_back(self) -> bool:
        return self.position > self.start

    def action_indices(self) -> list[int]:
        return sorted(self.inputs)

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
        steps = [self.step()]
        while not self.engine.at_tick_boundary():
            steps.append(self.step())
        return steps

    def finish_tick(self) -> list[StepInfo]:
        steps = []
        while not self.engine.at_tick_boundary():
            steps.append(self.step())
        return steps

    def apply(self, action: Action) -> StepInfo:
        """Apply a new action at the current position (truncating any recorded future)."""
        index = self.position
        self._truncate_after(index)
        self.keyframes.setdefault(index, self.engine.snapshot())
        info = self.engine.apply(action)  # may raise ActionError; nothing recorded then
        self.inputs[index] = action
        self._after_step(index, info)
        return info

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
