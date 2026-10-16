# R-003: short pulses and short gaps

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-003-short-pulses.cli.txt` · **Status:** verified
- **Question:** What does each component do with a pulse shorter than (or about as long
  as) its own delay, and with a short gap in a long signal? Does it matter whether the
  pulse comes from a player (a lever flipped between ticks) or from another component
  (switching inside a tick's scheduled-tick phase)?
- **Hypothesis** (from the source, [[repeater]], [[comparator]], [[redstone-torch]]):
  - Repeater: it schedules its tick when its input differs from its output and ignores
    the input while that tick is pending; when the tick runs it turns on (and, if the
    input is gone, schedules turning off again). So pulses and gaps shorter than its
    delay D become D long; longer ones pass with their length.
  - Comparator and torch: they schedule a tick 2 ticks after a change and *re-read the
    input when it runs*. A change that has reverted by then is lost: a 1-tick lever
    pulse is lost; a 2-tick lever pulse is seen, because a lever flips after the
    tick's scheduled ticks. A 2-tick pulse made by an observer or repeater ends *inside*
    the scheduled-tick phase, before the torch's or comparator's tick (higher priority or
    scheduled earlier), so it is lost too.
  - Sticky piston: a pulse too short for the 2-tick move leaves the block behind
    (EXP-016).
  - Lamp, copper bulb, dropper: every pulse counts (lamp +4; bulb toggles; dropper fires).
- **Setup:** a 64×64 world, rows 4 blocks apart, every component facing east.
  - Part 1, columns by stimulus: x=−24 a lever on for 1 tick, x=−12 for 2 ticks, x=0 for 3
    ticks (on at tick 2), x=12 an observer `out=east` watching a lever flipped at tick 2
    (its pulse: ticks 4–5). Rows by component, the component right after the input: z=−24
    repeater delay 1, −20 repeater delay 2, −16 comparator, −12 torch (on a stone that the
    lever hangs on, `face=wall`, or that the observer points into), −8 sticky piston with
    a stone, −4 lamp, 0 copper bulb, 4 dropper (64 stone) into a barrel.
  - Gaps, x=24: a lever on at tick 2, off at 20, on again at 20+g: delay-2 repeater g = 1…4
    (z −24…−12), comparator g = 1…3 (z −8…0), torch g = 1…3 (z 4…12).
  - Part 2, circuit-made pulses, rows z = 8 (torch), 12 (comparator), 16 (sticky piston),
    20 (repeater delay 1): a lever into a repeater at x0 feeding the component at x0+1.
    x0=−24: lever 1 tick, delay 1 → a 2-tick pulse (ticks 4–5); x0=−12: lever 3 ticks,
    delay 1 → 3-tick pulse (4–6); x0=0: lever 1 tick, delay 2 → 4-tick pulse (6–9). These
    pulses switch on and off inside the scheduled-tick phase.
- **Observations** (`waves`; levers on at tick 2):

```
                                0123456789012345678901234567890
@REP1_L1  repeater d1, 1 tick   ....ff..........
@REP1_L2  repeater d1, 2 ticks  ....ff..........
@REP1_L3  repeater d1, 3 ticks  ....fff.........
@REP1_OBS repeater d1, observer ......ff........
@REP2_L1  repeater d2, 1 tick   ......ffff......
@REP2_L3  repeater d2, 3 ticks  ......ffff......
@REP2_OBS repeater d2, observer ........ffff....
@COMP_L1  comparator, 1 tick    ................
@COMP_L2  comparator, 2 ticks   ....ff..........
@COMP_L3  comparator, 3 ticks   ....fff.........
@COMP_OBS comparator, observer  ................
@TORCH_L1 torch, 1 tick         ffffffffffffffff
@TORCH_L2 torch, 2 ticks        ffff..ffffffffff
@TORCH_L3 torch, 3 ticks        ffff...fffffffff
@TORCH_OBS torch, observer      ffffffffffffffff
@LAMP_L1 / L2 / L3 / OBS        ..fffff... / ..ffffff.. / ..fffffff. / ....ffffff
```

Gaps (lever on 2–19, off for g ticks from 20):

```
                                0         1         2         3         4
                                01234567890123456789012345678901234567890
@GAP1_REP2 .. @GAP3_REP2        ......fffffffffffffffffffffffffffffffffff   (gap filled)
@GAP4_REP2                      ......ffffffffffffffffff....fffffffffffff
@GAP1_COMP                      ....fffffffffffffffffffffffffffffffffffff   (gap filled)
@GAP2_COMP                      ....ffffffffffffffffff..fffffffffffffffff
@GAP3_COMP                      ....ffffffffffffffffff...ffffffffffffffff
@GAP1_TORCH                     ffff.....................................   (gap filled)
@GAP2_TORCH                     ffff..................ff.................
@GAP3_TORCH                     ffff..................fff................
```

Circuit-made pulses (part 2):

```
                                0123456789012345
@SRC_TORCH_RP2 (2-tick source)  ....ff..........
@TORCH_RP2                      ffffffffffffffff   (lost)
@COMP_RP2                       ................   (lost)
@REP1_RP2                       ......ff........   (passed)
@SRC_TORCH_RP3 (3-tick source)  ....fff.........
@TORCH_RP3                      ffffff...fffffff
@COMP_RP3                       ......fff.......
@TORCH_RP4 / @COMP_RP4 (4-tick) ffffffff....ffff / ........ffff....
```

Sticky pistons (block position at tick 15): the block was left in front ("spat") after a
1- and 2-tick lever pulse, the observer pulse and the 2-tick repeater pulse; pulled back
after a 3-tick lever pulse and the 3- and 4-tick repeater pulses. Every copper bulb
toggled once and stayed lit; every dropper fired exactly once (barrel at tick 6, at 8 for
the observer).

Why the circuit-made 2-tick pulse is lost (`at 4 ticks` in the part-2 world, the
scheduled ticks pending for tick 6):

```
  tick 6    @SRC_TORCH_RP2 repeater (VERY_HIGH)       ← the source turns off first
  tick 6    @TORCH_RP2   redstone_wall_torch (NORMAL)  ← the torch then sees no power
```

- **Result:** every hypothesis held.
- **Conclusion** (rules in [[timing]] and [[components]]):
  - **Repeater, delay D (= 2·delay):** a pulse or gap shorter than D comes out exactly D
    long; one of D or more passes with its length. Any pulse, however made, is seen.
  - **Torch and comparator:** they need the input to still be there 2 ticks after it
    changed. A 1-tick pulse or gap is lost (a gap: the output stays as it was). A
    2-tick pulse passes only if it ends *after* the scheduled-tick phase (a player's
    lever, a block event, …); 2-tick pulses made by observers and repeaters are lost.
    Pulses of 3 ticks or more always pass, with their length.
  - **Sticky piston:** needs 3 ticks or more of power to pull its block back; shorter
    pulses (any source) push the block and leave it there.
  - **Lamp:** lit for the pulse + 4. **Copper bulb, dropper:** once per pulse, any length.
  - Design consequence: an observer's pulse drives repeaters, pistons, lamps, bulbs,
    droppers and wire directly, but **not torches or comparators**: put a repeater
    (delay 2 or more) in between to stretch it, or use the observer to power a block a
    repeater reads.
  Confidence: high for the tested arrangements (V, S). The same rules are G in EXP-009
  (repeater extension), EXP-016 (sticky spitting), EXP-027 (0-tick pulses), EXP-047
  (pulses ending in scheduled ticks).
- **Open:** a 2-tick pulse ending in the scheduled-tick phase *after* the torch's tick (a
  lower-priority source) would pass: which sources do that? 0-tick pulses: R-012.
- **Used by:** [[timing]], [[components]], edge detectors and pulse circuits in
  [[circuits]].
