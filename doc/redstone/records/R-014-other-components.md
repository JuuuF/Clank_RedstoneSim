# R-014: rails, doors, gates, target blocks and lecterns in circuits

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-014-other-components.cli.txt` · **Status:** verified
- **Question:** How far does power travel along powered and activator rails? Do iron
  doors open from power at either half? How do target blocks and lecterns behave as
  signal sources?
- **Hypothesis** ([[rails]], [[target-block]], [[analog-sources]]; doors in
  [[mechanics/index]]): a powered rail powers up to 8 more rails of its kind along its
  line, both ways; a door takes power at either half and opens both; fence gates open
  at once; a hit target block gives the hit strength for 20 ticks (arrow), and wire
  connects to it from any side; a lectern gives ⌊page / (pages − 1) · 14⌋ + 1 to a
  comparator, and a 2-tick pulse when its page is turned.
- **Setup:** a 48×48 world (rows in the script's header). Rails placed with
  `shape=east_west`.
- **Procedure:** levers at tick 2; the target hit with strength 9 at tick 4
  (`hit`, an editor stand-in for an arrow, [[differences]]); the lectern's page turned to
  7 at tick 4 (`page`, a player's action).
- **Observations** (`waves`):

```
powered rails fed at the west end   1st..9th powered from tick 2, 10th..12th never
activator rails                     the same: 9 powered
powered rails fed beside the 6th    all 12 powered (5 and 6 rails each side)
iron door (lower half powered)      both halves open at 2
iron door (upper half powered)      open at 2
fence gate behind wire              open at 2
target hit at 4 (strength 9)        power 9 during 5..24; the wires on both sides 9
lectern page 0 → 7 (15 pages)       comparator 1 → 8 at 6; repeater behind it on 6..7
```

- **Result:** as predicted.
- **Conclusion** (in [[components]]):
  - Powered and activator rails: a powered rail feeds **8 more** rails of the same kind
    in a straight line (both directions from the fed one); mixed kinds stop it (G
    EXP-036). Power changes are instant.
  - Iron doors open (both halves) from power at either half, at once; fence gates and
    trapdoors open at once too (R-001).
  - A target block hit by a projectile gives the hit's strength (1–15, by how close to
    the center) for 20 ticks (arrow) or 8 (other projectiles); wire next to it connects
    and carries that strength.
  - A lectern is an analog source (page position, book length) and gives a 2-tick pulse
    each time a player turns its page (a circuit-made pulse: repeaters see it, torches
    and comparators do not, R-003).
  Confidence: high (V, S; G in EXP-025, 036, 037, 052; the page-turn pulse is S only in
  game terms: the test server has no player).
- **Not testable here (L):** detector rails (need minecarts), pressure plates and
  tripwires with real entities (only the editor's stand-in `plate`), daylight sensors,
  sculk sensors ([[differences]]).
- **Used by:** [[components]].
