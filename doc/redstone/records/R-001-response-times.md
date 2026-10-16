# R-001: response times of the basic components

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-001-response-times.cli.txt` · **Status:** verified
- **Question:** How many game ticks after its input changes does each basic component
  react, for a rising and a falling input? How long do buttons stay on?
- **Hypothesis:** from common knowledge and the mechanics pages: lamp on at once and off
  after 4; wire instant with −1 per block; torch 2; repeater 2 per delay step; comparator
  2; observer pulse 2 ticks long after 2; piston extended 1 tick later and the block in
  place after 3 (block event, then a 2-tick move); dropper 4; note block, copper bulb,
  trapdoor, powered rail and hopper lock at once; stone button 20 ticks, oak button 30.
- **Setup:** a 48×48 world. One row per component along +x, rows 2 blocks apart (z = −20
  … 16), the input at x=−14 and the component at x=−13:

| Row z | Input | Component | Probe label |
|---|---|---|---|
| −20 | lever on the floor | redstone lamp | `@LAMP` |
| −18 | lever | 15 wires (x −13…1) and a lamp | `@WIRE1`, `@WIRE15`, `@WIRELAMP` |
| −16 | lever on top of a stone | wall torch on the stone's east face | `@TORCH` |
| −14…−8 | lever | repeater `out=east`, delay 1, 2, 3, 4 | `@REP1` … `@REP4` |
| −6 | lever | comparator `out=east` (compare) | `@COMP` |
| −4 | lever | observer `out=east` (watching the lever) | `@OBS` |
| −2, 0 | lever | piston / sticky piston facing east, stone in front | `@PIST`, `@PIST_F1` (in front), `@PIST_F2` (one further) |
| 2 | lever | dropper facing east (1 stone inside), barrel in front | `@DROP`, `@DROP_BARREL` |
| 4, 6 | lever | note block, copper bulb | `@NOTE`, `@BULB` |
| 8, 10 | — | stone button, oak button on the floor, lamp beside | `@STONEBTN`, `@OAKBTN` |
| 12, 14, 16 | lever | iron trapdoor, powered rail, hopper | `@TRAP`, `@RAIL`, `@HOP` |

- **Procedure:** every lever flipped on at tick 2 (`at 2 use`) and off at tick 40; both
  buttons pressed at tick 2. Read with `waves`, `changes` and `delays`.
- **Observations** (`waves`, ticks 0..60; the timeline as in the targets):

```
tick                          0         1         2         3         4         5         6
                              0123456789012345678901234567890123456789012345678901234567890
@LAMP redstone_lamp           ..ffffffffffffffffffffffffffffffffffffffffff.................
@WIRE15 redstone_wire         ..11111111111111111111111111111111111111.....................
@WIRELAMP redstone_lamp       ..ffffffffffffffffffffffffffffffffffffffffff.................
@TORCH redstone_wall_torch    ffff......................................fffffffffffffffffff
@REP1 repeater                ....ffffffffffffffffffffffffffffffffffffff...................
@REP2 repeater                ......ffffffffffffffffffffffffffffffffffffff.................
@REP3 repeater                ........ffffffffffffffffffffffffffffffffffffff...............
@REP4 repeater                ..........ffffffffffffffffffffffffffffffffffffff.............
@COMP comparator              ....ffffffffffffffffffffffffffffffffffffff...................
@OBS observer                 ....ff....................................ff.................
@PIST piston                  ...ffffffffffffffffffffffffffffffffffffff....................
@STONEBTN stone_button        ..ffffffffffffffffffff.......................................
@STONEBTN_LAMP redstone_lamp  ..ffffffffffffffffffffffff...................................
@OAKBTN oak_button            ..ffffffffffffffffffffffffffffff.............................
@OAKBTN_LAMP redstone_lamp    ..ffffffffffffffffffffffffffffffffff.........................
@BULB copper_bulb             ..fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
```

`changes` of the piston rows:

```
@PIST       tick 0 piston[extended=false]  tick 3 extended=true  tick 41 moving_piston  tick 43 piston[extended=false]
@PIST_F1    tick 0 stone  tick 3 moving_piston  tick 5 piston_head  tick 41 air
@PIST_F2    tick 0 air    tick 3 moving_piston  tick 5 stone
@STICKY_F1  tick 0 stone  tick 3 moving_piston  tick 5 piston_head  tick 41 moving_piston  tick 43 stone
@STICKY_F2  tick 0 air    tick 3 moving_piston  tick 5 stone        tick 41 air
```

The dropper was `triggered` at tick 2 and the barrel held the item from tick 6. Note
block, copper bulb, trapdoor, powered rail and hopper changed state at tick 2 (on) and 40
(off); the copper bulb turned on at 2 and *stayed* on when its power went at 40.

- **Result:** every hypothesis held, to the tick.
- **Conclusion:** the base timing table in [[timing]]: lamp 0 / +4; wire 0; torch +2 /
  +2; repeater +2·delay both ways; comparator +2 both ways; observer: on +2 after a change
  for 2 ticks, for a change in either direction; piston: `extended` +1, pushed block in
  place +3, retraction: block gone (or pulled back) +1 and done +3; dropper fires +4;
  note block, copper bulb, iron trapdoor, powered rail, hopper lock: 0. Stone button 20
  ticks on, oak button 30. Confidence: high (V; the same timings are G in EXP-001, 002,
  008, 012, 015, 032, 044).
- **Open:** only a lever's direct input was tested; inputs through powered blocks, wire
  and quasi-connectivity have their own records. Short pulses (shorter than a component's
  delay) are R-003.
- **Used by:** [[timing]], [[components]].
