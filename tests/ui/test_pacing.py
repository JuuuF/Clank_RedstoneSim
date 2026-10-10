"""Real-time pacing of the run loop (no display needed)."""

from __future__ import annotations

from redsim.ui.pacing import RateMeter, TickPacer


def run(pacer: TickPacer, now: float) -> int:
    count = pacer.due(now)
    pacer.ran(count)
    return count


def test_pacer_runs_the_target_rate_regardless_of_frame_timing() -> None:
    pacer = TickPacer(20)
    pacer.start(0.0)
    total = 0
    now = 0.0
    for frame in range(600):  # 10 s of uneven frames: 8 ms and 25 ms alternating
        now += 0.008 if frame % 2 else 0.025
        total += run(pacer, now)
    assert total == int(now * 20)


def test_pacer_drops_the_backlog_after_a_stall() -> None:
    pacer = TickPacer(20)
    pacer.start(0.0)
    assert run(pacer, 0.1) == 2
    assert run(pacer, 5.0) == 5  # 98 ticks behind: capped at 0.25 s worth
    assert run(pacer, 5.05) == 1  # and back on schedule from there
    assert run(pacer, 5.1) == 1


def test_pacer_rate_change_keeps_schedule() -> None:
    pacer = TickPacer(20)
    pacer.start(0.0)
    assert run(pacer, 1.0) == 5  # capped: 20 due, 5 allowed at once
    pacer.set_rate(10, 1.0)
    assert run(pacer, 1.0) == 0
    assert run(pacer, 2.0) == 2  # 10 more due, capped to 0.25 s at 10/s


def test_rate_meter_reports_events_per_second() -> None:
    meter = RateMeter()
    meter.reset(0.0)
    for i in range(1, 41):
        meter.record(i * 0.05)  # 20 per second for 2 s
    assert meter.rate(2.0) == 20
    assert meter.rate(2.02) == 20  # between two events
    assert meter.rate(2.5) == 10  # the last half second had none
    assert meter.rate(4.0) == 0


def test_rate_meter_counts_batches() -> None:
    meter = RateMeter()
    meter.reset(0.0)
    for i in range(1, 31):
        meter.record(i * 0.035, 100)  # warp: batches of 100 ticks every 35 ms
    assert round(meter.rate(30 * 0.035)) == round(100 / 0.035)
