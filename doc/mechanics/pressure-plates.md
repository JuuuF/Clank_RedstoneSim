# Pressure plates

Sources: `BasePressurePlateBlock.java`, `PressurePlateBlock.java`,
`WeightedPressurePlateBlock.java`, `BlockSetType` (sensitivity), `Entity.applyEffectsFromBlocks`.

- Entities are not simulated. The editor puts **visitors** on a plate instead
  (Inspector → "Step on it": players/mobs, items, for N ticks; `Document.plate_visitors`).
  They stand on it from the next tick on; in that tick's entity phase an unpressed plate is
  pressed (`entityInside` → `checkPressed`).
- `checkPressed` L71: if the strength changed, `setBlock` (flags 2) and updates around the
  plate and around the block below; while pressed, a recheck is scheduled in 20 ticks
  (10 for weighted plates). The recheck releases the plate once nobody is left.
- Strength: stone and polished blackstone plates count mobs (players are mobs), wooden
  plates every entity: 15 if any. Weighted: `ceil(min(n, max)/max · 15)` (float math),
  light (gold) max 15, heavy (iron) max 150.
- Strong power only into the block below; weak power to all sides. Popped by pistons.
- The pressed shape is half a pixel high; the simulator keeps the 1-pixel shape (no
  collision, nothing rests on plates: no outcome changes).

Game check: the harness spawns real entities (`summon armor_stand` with gravity, since a
`NoGravity` armor stand has no physics and ignores blocks, `ArmorStand.hasPhysics` L115;
`summon item` with no gravity) and kills them later; the simulator turns them into
visitors. EXP-046 (`pressure_plates`) matches.

Status: implemented (`world/blocks/pressure_plate.py`; stone, polished blackstone, 12
wooden, light and heavy weighted). Tests: `tests/sim/test_pressure_plate.py`.
