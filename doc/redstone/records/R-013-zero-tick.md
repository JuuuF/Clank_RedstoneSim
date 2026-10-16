# R-013: 0-tick pulses: power on and off at one moment

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-013-zero-tick.cli.txt` · **Status:** verified
- **Question:** A "0-tick pulse" turns a signal on and off with no tick in between (in
  the game: two block changes in one moment, e.g. a redstone block placed and removed,
  or made by pistons). Which components react to one (Q3)?
- **Hypothesis** (the components' `neighborChanged` code): components that only
  *schedule* on a change and re-read the input later (comparator, torch) see nothing;
  components that act in `neighborChanged` itself react: a lamp turns on at once and its
  turn-off waits 4 ticks; a copper bulb toggles; a dropper sets `triggered` and schedules
  its shot, which fires regardless; a repeater schedules, and when its tick runs it turns
  on and then off after its delay. Pistons queue an extend event, but the event re-checks
  power and finds none. Wire switches on and off inside the moment. An observer sees the
  wire's two changes as one.
- **Setup:** a 48×48 world, rows 4 blocks apart; a redstone block is set west of each
  component and removed again, both at tick 2 (two recorded edits at the same tick).
  Components: repeater (delay 1), comparator, torch on a stone, lamp, 3 wires, piston and
  sticky piston with a stone in front, copper bulb, dropper (64 stone) into a barrel, note
  block, observer watching a wire.
- **Observations** (`waves`):

```
repeater          ....ff...........   full 2-tick pulse at 4..5
comparator        .................
torch             fffffffffffffffff   never goes out
lamp              ..ffff...........   lit 2..5
wire (3rd)        .................
pistons           never extend; the stones in front stay
copper bulb       ..fffffffffffffff   toggled at 2
dropper → barrel  ......111111111     fired at 6
note block        powered=false throughout (its sound is not simulated)
observer of wire  ....ff...........
```

- **Result:** as predicted.
- **Conclusion** (in [[timing]], [[components]]):
  - **React to a 0-tick pulse:** repeater (outputs a full pulse of its delay, 2 ticks
    later), lamp (4-tick flash), copper bulb (toggles), dropper/dispenser (fires 4 ticks
    later), observer watching the changing block (one 2-tick pulse).
  - **Ignore it:** comparator (answers Q3: no), torch, pistons (no movement), and wire
    shows no lasting change.
  - So a repeater is a "0-tick catcher": it turns any 0-tick event into a real pulse.
  Confidence: high (V; S; G EXP-027 for repeater, comparator, torch, lamp, pistons, dust).
- **Note:** the editor's `pulse … for 0` is a different stand-in (on at the start of the
  next tick, off after its block events, [[differences]]); this record used real block
  edits.
- **Used by:** [[timing]], [[components]].
