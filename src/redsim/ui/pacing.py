"""Real-time pacing of the simulation, independent of drawing (pure Python, no Qt).

The run loop asks :class:`TickPacer` how many game ticks are due by the wall clock, runs them,
and then asks for one repaint. Drawing therefore never slows the simulation down below the
target rate (the game does the same: the server ticks at 20/s, the client draws frames as
fast as it can). :class:`RateMeter` measures what was actually achieved.
"""

from __future__ import annotations

from collections import deque

#: Falling further behind than this drops the backlog instead of racing to catch up.
MAX_LAG_SECONDS = 0.25


class TickPacer:
    """Ticks due at ``rate`` per second since :meth:`start`."""

    def __init__(self, rate: float) -> None:
        self.rate = rate
        self._origin = 0.0
        self._done = 0

    def start(self, now: float) -> None:
        self._origin = now
        self._done = 0

    def set_rate(self, rate: float, now: float) -> None:
        """Change the rate without a jump: the ticks already run stay on schedule."""
        self.rate = rate
        self._origin = now - self._done / rate

    def due(self, now: float) -> int:
        """Ticks to run now; call :meth:`ran` with how many actually ran."""
        behind = int((now - self._origin) * self.rate + 1e-6) - self._done  # 1e-6: rounding
        cap = max(1, int(self.rate * MAX_LAG_SECONDS))
        if behind > cap:
            # Too slow for the target (a heavy world or a stall): skip the backlog.
            self._origin += (behind - cap) / self.rate
            behind = cap
        return max(0, behind)

    def ran(self, count: int) -> None:
        self._done += count


class RateMeter:
    """Events per second over the last ``window`` seconds."""

    def __init__(self, window: float = 1.0) -> None:
        self.window = window
        self._events: deque[tuple[float, int]] = deque()
        self._total = 0
        self._since: float | None = None

    def reset(self, now: float | None = None) -> None:
        """Forget all events; ``now`` marks the start of measuring (else the first event)."""
        self._events.clear()
        self._total = 0
        self._since = now

    def record(self, now: float, count: int = 1) -> None:
        if self._since is None:
            self._since = now
        self._events.append((now, count))
        self._total += count
        self._trim(now)

    def rate(self, now: float) -> float:
        self._trim(now)
        events = self._events
        if len(events) >= 2:
            # Events after the first, over the time they took: steady even when the window
            # edge falls between two events (a plain count would flicker between 20 and 21).
            first_time, first_count = events[0]
            span = events[-1][0] - first_time
            if span > 0 and now - events[-1][0] <= max(0.25, 3 * span / (len(events) - 1)):
                return (self._total - first_count) / span
        if self._since is None:
            return 0.0
        span = min(self.window, now - self._since)
        return self._total / span if span > 0 else 0.0

    def _trim(self, now: float) -> None:
        events = self._events
        while events and events[0][0] <= now - self.window:
            self._total -= events.popleft()[1]
