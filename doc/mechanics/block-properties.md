# Block properties that matter mechanically

- **Status:** researched; implemented for the initial block set (`world/shape.py`, `world/blocks/simple.py`); glass non-conduction confirmed in game (EXP-007).
- **Summary:** "Solid" is not one property in the game. Redstone conduction, support for
  attached components, piston mobility, and signal emission are separate, independently
  overridable properties.
- **Scope:** The blocks in the simulator's initial block set.

## Source

- `net/minecraft/world/level/block/state/BlockBehaviour.java`: `Properties` defaults
  (L1022 `pushReaction = PUSH_PULL`, L1030 `isRedstoneConductor = isCollisionShapeFullBlock`),
  `getShape` (default full block), `getCollisionShape` (= shape if `hasCollision`, else empty),
  `getBlockSupportShape` (= collision shape), `isFaceSturdy` (through the cache, L892–897),
  `Cache` (`isCollisionShapeFullBlock`, `faceSturdy`).
- `net/minecraft/world/level/block/SupportType.java`: FULL, CENTER, RIGID.
- `net/minecraft/world/level/block/Blocks.java`: per-block property overrides.
- `net/minecraft/world/level/block/piston/PistonBaseBlock.java` `isPushable` L213.

## Rules

| Property | Definition in source | Used by |
|---|---|---|
| Collision full block | collision shape is exactly the unit cube | default conductor predicate |
| **Redstone conductor** | `isRedstoneConductor` predicate; default = collision full block | `SignalGetter.getSignal` (a conductor passes on strong power), wire connection and step-up/step-down rules, comparator reading through a block |
| Face sturdy (FULL) | the support shape's face covers the whole 16×16 face | levers, buttons, wire (`UP` face) |
| Face sturdy (CENTER) | face covers the central 2×2 (column 7–9) | standing torches (`canSupportCenter`) |
| Face sturdy (RIGID) | face covers the outer 2-pixel ring | repeaters and comparators (`canSupportRigidBlock`) |
| Signal source | `isSignalSource`; default false | wire connection, comparator side inputs |
| Push reaction | PUSH_PULL (default), PUSH, POPPED, IMMOVEABLE, IGNORE_ENTITY | piston structure resolution |
| Unbreakable | `destroySpeed == −1` | immovable by pistons |
| Has block entity | block implements `EntityBlock` | immovable by pistons (except piston bases) |

### Initial block set

| Block | Conductor | Faces sturdy | Push | Notes |
|---|---|---|---|---|
| stone, smooth stone, other full cubes | yes | all | PUSH_PULL | default properties |
| glass | **no** (`never`) | all (full collision) | PUSH_PULL | wire and components can sit on glass |
| glowstone | **no** | all | PUSH_PULL | |
| redstone block | **no** | all | PUSH_PULL | signal source 15 |
| redstone lamp | yes | all | PUSH_PULL | |
| obsidian | yes | all | **IMMOVEABLE** | |
| bedrock | yes | all | immovable (destroy speed −1) | |
| slime block | yes (full collision) | all | PUSH_PULL | sticky |
| honey block | no (collision 14×15 column) | DOWN: CENTER only | PUSH_PULL | sticky; does not stick to slime |
| slabs (bottom/top/double) | double only | bottom: DOWN; top: UP; double: all | PUSH_PULL | |
| piston, sticky piston | **no** | retracted: all; extended: from shape | IMMOVEABLE property, but special-cased in `isPushable` (movable when retracted) | |
| piston head, moving piston | no | — | IMMOVEABLE | moving piston: destroy speed −1 |
| wire, repeater, comparator, torches, lever, buttons, cake | no | — | POPPED | destroyed when pushed |
| barrel | yes | all | PUSH_PULL but has block entity → immovable | comparator analog source |
| lectern | no (2-px slab + 8-px post) | DOWN only (full bottom) | PUSH_PULL but has block entity → immovable | analog source; 2-tick pulse on page turns ([[analog-sources]]) |

## Edge cases and quirks

- [[quirks]] Q-PROP-GLASS: glass and glowstone support redstone components but are not
  conductors, so they neither take strong power nor cut wire diagonals.
- [[quirks]] Q-PROP-REDBLOCK: the redstone block is not a conductor; pistons and
  components beside it are powered by it directly, but it does not pass power through.

## Tests

- Shapes and support types are exercised by the component tests (wire/torch/lever support,
  popping) and by every game scenario's floor. Dedicated per-block property tests are still
  to do (`tests/world/`).

## Unknowns

- Exact support faces of blocks outside the table must be derived from their shapes when
  added; the shape helper reproduces `SupportType` with 1/16-pixel voxel grids.

## Related

[[power-queries]] · [[redstone-wire]] · [[pistons]]
