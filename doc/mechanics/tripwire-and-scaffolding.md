# Tripwire and scaffolding

Ported in `world/blocks/tripwire.py` (`TripWireHookBlock`, `TripWireBlock`) and
`world/blocks/scaffolding.py` (`ScaffoldingBlock`, `ScaffoldingBlockItem`). Verified on the
real 26.3 server: EXP-064 (`tripwires`) and EXP-065 (`scaffolding`), block states and the
falling block entities (exact positions and motion) compared every tick.

## Tripwire hooks and tripwire

A line is a hook, up to 40 tripwire (placed with string) and a second hook facing back,
at most 41 blocks apart (`WIRE_DIST_MAX` 42). Both blocks have no collision, break
instantly, and pistons pop them (`PushReaction.POPPED`).

| Block | Properties | Signal |
|---|---|---|
| `tripwire_hook` | `facing` (from the block it hangs on toward the wire), `attached`, `powered` | 15 while powered, to every side; strong power only into the block it hangs on |
| `tripwire` | `attached` (part of a line), `powered` (an entity in it), `disarmed` (cut with shears), `north/east/south/west` (connections) | none: only the hooks give power |

**Hooks.** A hook needs a sturdy face behind it (`canSurvive`) and breaks when that block
goes. Placed by a player it looks for its line at once (`setPlacedBy` →
`calculateState`); put by `/setblock` (or by the CLI's `set`) it does not, and stays
unattached until a wire of its line changes (EXP-064, z=9).

**`calculateState`** (one hook, scanning along `facing`): the line is `attached` if every
block up to a hook facing back is tripwire and that hook is at least 2 blocks away; it is
`powered` if it is attached and some armed wire on it is powered. It sets both hooks
(`setBlockAndUpdate`, then neighbor updates around each hook and its block), and when
`attached` changed, every wire between. A wire change that started it (`wireSource`)
makes the hook check again 10 ticks later.

**Wires** connect to wire and to hooks facing them. When a wire is placed (a new block) or
removed, the hooks south and west of it run `calculateState` over their line
(`updateSource`); the removed wire counts as powered, so **breaking a wire or a piston
popping it powers the hooks once** (until their recheck 10 ticks later finds the gap and
detaches the line). Cut with shears (`break POS shears`), a wire is disarmed first, so
the hooks just detach (EXP-064, z=3: removing a disarmed wire gives no pulse).

**Entities.** A wire is pressed when an entity that does not ignore block triggers is in
its shape (`entityInside`, only while unpowered and without a pending tick), rechecked
every 10 ticks while pressed and once more 1 tick after it was released. Falling blocks
are real entities here: sand falling through a wire presses it (EXP-064, z=11; the wire's
`getEntityInsideCollisionShape` is its thin shape, and the falling block's movement must
touch it). Mobs and items are editor visitors (`plate POS mobs N for TICKS`, the
inspector's "Step on it"), as on pressure plates.

Timing (EXP-064): an entity summoned between ticks presses the wire in the next tick's
entity phase, and both hooks are powered in that same tick; the lamps on their blocks light
at once. After the entity leaves, the hooks turn off at the first 10-tick recheck that
finds the wire empty.

Quirks the server confirmed:

- **A disarmed wire in a line** never powers the hooks, but stepping on it detaches the
  whole line (the source wire is unarmed: `attached &= wireArmed`) until the hook's
  recheck 10 ticks later re-attaches it (EXP-064, z=3).
- **When a hook breaks**, the other hook detaches but the wires keep `attached=true`:
  `calculateState` finds the hook gone and returns before it updates the wires
  (EXP-064, z=9 at tick 30).
- Hooks only scan from the south and west ends: a wire change asks the hook south or west
  of it, which sets both hooks.

Not simulated: the hooks' sounds and game events (sculk sensors are not simulated). See
[[differences]].

## Scaffolding

`scaffolding[distance=0..7, bottom, waterlogged]`:

- **`distance`** (`getDistance`): 0 on a sturdy top; on scaffolding, the distance of the
  scaffolding below; else one more than the nearest scaffolding beside it; 7 means
  unsupported. A bridge reaches 6 blocks out from a tower; a player cannot place one
  where it would have distance 7 (`ScaffoldingBlockItem`).
- **`bottom`**: held from the side with no scaffolding below (drawn with a bottom frame).
- Every new state, and any neighbor change, makes it check itself 1 tick later
  (`onPlace`, `updateShape`). At distance 7 it **breaks** (`destroyBlock`), or **falls**
  as a falling block if it already had distance 7 (a scaffolding put by `/setblock` in
  the air; EXP-065). When a tower's base goes, the pieces count their distances up from
  each other 1 tick at a time until they reach 7 and break (EXP-065, z=1: the 6-long
  bridge is gone within 7 ticks of losing its base).
- **Shapes:** the stable shape is a 2-pixel top and four 2×2 legs; with `bottom` a
  2-pixel bottom too. Support (and `CollisionContext.empty()`) uses the stable shape: the
  top is sturdy, so torches, wire and rails stand on it; the sides and bottom are not
  (no levers or wall torches on its side). It never conducts (EXP-065: a repeater into it
  does not light the lamp behind) and is never `solid` (dynamic shape: no shape cache).
- **Collision for entities** depends on the entity: above it (feet higher than its top,
  minus 1e-5), the stable shape (a falling block lands on top: EXP-065, z=3); inside a
  `bottom` scaffolding, the 2-pixel bottom; otherwise nothing. Placing a block ignores it.
- Pistons pop it (EXP-065, z=7: the one above then breaks).

Not simulated: water (`waterlogged` stays inert). In the editor a scaffolding is placed where
you point; in the game clicking scaffolding sends the new one to the top of the column or
along the bridge, which gives the same block at that spot.
