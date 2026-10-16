# R-004: wire shapes and what they power; steps up and down

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-004-wire-geometry.cli.txt` · **Status:** verified
- **Question:** Which neighbors does a wire power, depending on its shape (cross, dot,
  line, corner)? When does wire connect one block up or down, and what cuts it? Do glass
  and slabs behave differently from stone? Does wire next to a repeater's side power it?
- **Hypothesis** ([[redstone-wire]], `RedstoneWireBlock.getSignal`,
  `getConnectingSide`): wire powers the block under it and each neighbor its shape
  *points into* (a side marked `side` or `up`). A lone wire placed by a player is a cross
  (points into all four sides); right-clicked it becomes a dot (points nowhere). A wire
  with one connection becomes a line through both ends. A wire steps up onto a block
  next to it (and down from it) when the block above the lower wire is not a solid
  block; over a non-conductor (glass, top slab) only the upward direction carries power
  (Q-WIRE-GLASS-UP). A repeater takes input only from its back.
- **Setup:** a 48×48 world; rows 6 blocks apart in two columns. Each row is lit by a lever
  flipped at tick 2. Lamps (some `set` floating at y=2) are the probes.

| Row | Build | Probes |
|---|---|---|
| CROSS (−12, −20) | stone powered by a repeater from the west; a lone wire placed on top (a cross) | lamps on its 4 sides at y=2 |
| DOT (−12, −14) | the same, the wire right-clicked (`use`) into a dot | lamps on its 4 sides |
| LINE (−12, −8) | lever, 3 wires east | lamps beside the last wire (N, S) and in front (E) |
| CORNER (−12, −3) | lever, 2 wires east, the 2nd turning south to a 3rd wire | lamps E and N of the corner wire, S of the end |
| STEPUP (−12, 4) | lever, wire, stone with wire on top | lamp after the top wire |
| STEPDOWN (−12, 10) | lever on a stone, wire on a 2nd stone, then wire on the floor | lamp after the low wire |
| CUT (−12, 16) | as STEPUP with a stone `set` over the lower wire | lamp after the top wire |
| GLASSUP / GLASSDOWN (8, −20 / −14) | as STEPUP / STEPDOWN over glass | |
| SLABUP / SLABDOWN (8, −8 / −2) | over a `smooth_stone_slab[type=top]` | |
| REPSIDE (8, 4) | wire line passing along the north side of a repeater `out=east` | the repeater |
| UNDER (8, 10) | a floating stone with a lever on top; wire under it on the floor | lamp east of the wire |

- **Observations** (`waves` ticks 0..10, levers at tick 2):

```
@CROSS redstone_wire           ....fffffff     (via the repeater: from tick 4)
@CROSS_E / _W / _N / _S        ....fffffff  (all four)
@DOT redstone_wire             ....fffffff
@DOT_E / _W / _N / _S          ...........  (none)
@LINE_END redstone_wire        ..ddddddddd
@LINE_FRONT / _SIDE_N / _SIDE_S ..fffffffff / ........... / ...........
@CORNER redstone_wire          ..eeeeeeeee   [north=none,east=none,south=side,west=side]
@CORNER_E / _N / _END          ........... / ........... / ..fffffffff
@STEPUP_LOW / _HIGH / _LAMP    ..fffffffff / ..eeeeeeeee / ..fffffffff
@STEPDOWN_HIGH / _LOW / _LAMP  ..fffffffff / ..eeeeeeeee / ..fffffffff
@CUT_LOW / _HIGH / _LAMP       ..fffffffff / ........... / ...........
@GLASSUP_HIGH / _LAMP          ..eeeeeeeee / ..fffffffff
@GLASSDOWN_HIGH / _LOW / _LAMP ..fffffffff / ........... / ...........
@SLABUP_HIGH / _LAMP           ..eeeeeeeee / ..fffffffff
@SLABDOWN_HIGH / _LOW / _LAMP  ..fffffffff / ........... / ...........
@REPSIDE_WIRE / @REPSIDE       ..eeeeeeeee / ...........   (not powered, not locked)
@UNDER / @UNDER_LAMP           ..fffffffff / ..fffffffff
```

- **Result:** every hypothesis held.
- **Conclusion** (in [[signals]], section Wire):
  - Wire powers the block under it and what it **points into**: a cross all four
    sides, a line its two ends, a corner its two arms, a dot nothing beside it. A lone
    wire placed by a player is a cross; `use` (right-click) toggles cross ↔ dot.
  - A wire with one connection extends into a line: it points straight on, into
    whatever is beyond its end (here a lamp).
  - Steps: wire climbs onto and comes down from a solid block next to it, losing 1 per
    wire as usual; a solid block directly above the lower wire cuts the step.
  - Glass and top slabs carry wire too, but power only goes **up** onto them, never down.
  - Wire passing a repeater's side does nothing to it (input is the back only; locking
    needs a repeater or comparator, R-006).
  - Wire **under** a strongly powered block takes 15 from it (as wire beside one does,
    R-002).
  Confidence: high (V; S; G for glass in EXP-007 and dust shapes in EXP-029).
- **Open:** wire onto stairs, upside-down stairs, hoppers and other partial blocks (only
  the ones a wire can stand on matter); which components wire *connects* to visually
  (repeater ends, observers, torches) and whether that changes the shape: partly in
  [[redstone-wire]].
- **Used by:** [[signals]], every wired circuit.
