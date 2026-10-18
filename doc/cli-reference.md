# redsim-cli command reference

Generated from the command registry (`redsim-cli help --markdown`); do not edit by
hand. The concepts (positions, ticks, the build and the timeline, labels, targets,
output formats) are explained in [[cli]]. Each command below shows its syntax, what
it does, examples and what its `--json` output holds.

Syntax: `UPPER` words are values you fill in, `[brackets]` are optional, `A|B`
means one of them, `...` means repeatable. POS is a position (`x y z`, `x,y,z` or
`@label[+dx,dy,dz]`), BLOCK a block state (`repeater[facing=west]` or
`repeater facing=west`), T a tick, A..B a range of ticks.

## World

Creating, describing and saving world files.

### `new`

`new [size N] [floor BLOCK|none] [force]`

Create a new world file with a flat floor at y=0.

Creates the world file named on the command line: an N×N floor (default 32×32) of
smooth stone at y=0, from x,z = -N/2 to N/2-1, placed without block updates like
terrain. Build on top of it, from y=1 up. `floor BLOCK` uses another block for the
floor, `floor none` makes an empty world. An existing file is only replaced with
`force` (its previous content goes to the undo file, so `undo` brings it back).

The world starts at tick 0 (the build) with an empty timeline.

Examples:

```
redsim-cli gate.redsim.json new
redsim-cli big.redsim.json new size 64 floor stone
redsim-cli sky.redsim.json new floor none
```

JSON `data`: {"path", "floor": block or null, "size"}

### `info`

`info`

Summarize the world: blocks, view tick, timeline, labels, targets.

Prints what is in the world: the box around the blocks above the floor, how many of
each block there are, the view tick and the simulated length, the recorded timeline
(edits and power pulses), monitors, labels, notes, targets, falling blocks and pending
scheduled ticks. Running `redsim-cli WORLD` without a command in a terminal prints this.

Examples:

```
info
```

JSON `data`: {"tick", "end_tick", "box": [low, high] or null, "blocks": {id: count},
    "edits", "pulses", "labels": {name: [x, y, z]}, "notes", "targets", "monitors",
    "entities", "scheduled_ticks"}

### `log`

`log [N]`

Show the last N command lines that changed this world (default 20).

Every command that changed the world (or the timeline, labels, notes, targets) is
written to the world file's log (the last 500). `log` shows the newest ones, oldest
first, so you can see how the world came to be, or continue where someone stopped.

Examples:

```
log
log 100
```

JSON `data`: {"lines": [command line, ...]}

### `save-as`

`save-as FILE`

Write the world to another file as well (the session's file stays).

Saves a copy of the world, with everything in it (build, timeline, labels, targets,
view), to FILE. The world file itself is still the one named on the command line.

Examples:

```
save-as backup.redsim.json
```

JSON `data`: {"path"}

## Build

Changing the contraption. These edit the build (tick 0) unless prefixed with `at T`, which records the edit on the timeline at tick T instead.

### `place`

`place POS BLOCK [PROP=VALUE ...]`

Place a block like a player, with the orientation you give.

Places BLOCK at POS the way a player placing it would (`BlockItem.place`): the spot
must be air and the block must have support (a torch needs a block to stand on, a
lever a block to attach to). The orientation is what you write (`facing`, `face`,
`half`, …); the game's placement rules derive the rest, so a lamp next to power is
placed lit, a repeater next to a powered side repeater is placed locked, wire connects
to its neighbors, a door gets its upper half. Properties you leave out keep their
defaults (`facing=north` for most blocks).

Directions: repeaters, comparators and observers have `facing` pointing to their
input (the opposite of their output); write `out=DIRECTION` to give the output side
instead. Pistons, dispensers, droppers and hoppers face where they push or output.
Wall torches and tripwire hooks face away from their wall; levers and buttons use
`face=floor|wall|ceiling` and, on a wall, `facing` away from the wall. A scaffolding
needs a sturdy block below or scaffolding within 6 blocks sideways (`distance` < 7).

Properties a player sets by right-clicking a placed block are set that way: a
repeater's `delay`, a comparator's `mode`, a lever's `powered`, a door's, trapdoor's
or fence gate's `open`, a note block's `note`. In the game these blocks are always
placed with their default value, so `place` right-clicks the block (like `use`) until
it has the value you wrote; the output says how many clicks. Any other property you
write that the placement rules change (a lamp's `lit`, an observer's `powered`) gives
a `note:` line; `set` puts a state exactly as written.

Use `set` to put a block regardless of support or to replace one (the `/setblock`
command), and `at T place …` to place it at tick T on the timeline instead of in the
build.

Examples:

```
place 0 1 0 redstone_wire
place 1 1 0 repeater out=east delay=2   # output east, 4 ticks (clicked once)
place 2 1 0 redstone_lamp
place 0 2 1 lever face=wall facing=south
at 10 place 4 1 0 redstone_block        # recorded at tick 10
```

JSON `data`: {"pos", "state" (the placed state), "tick" (0 = the build), "clicks" (right-clicks
    made after placing), "notes": [properties that came out different]}

### `set`

`set POS BLOCK [PROP=VALUE ...] [nbt JSON]`

Set a block like the /setblock command (replaces what is there).

Runs `/setblock POS BLOCK` (replace mode): the block replaces whatever is at POS, its
shape-dependent properties are adjusted to its neighbors (wire connections, stairs
corners) and the neighbors are updated, but placement rules are not applied: a lamp
set next to power stays off until something updates it, as in the game. `nbt` adds
block-entity data as JSON, like `/setblock … {…}`
(`set 0 1 0 barrel nbt '{"Items":[{"Slot":0,"id":"minecraft:stone","count":64}]}'`).

Blocks the simulator does not model (water, TNT, …) can be set too: they stay inert
(see doc/differences.md). Setting an extended piston also puts its head in front.

Examples:

```
set 0 1 0 redstone_block
set 3 1 0 repeater[facing=west,delay=4]
set 0 1 0 air            # remove without breaking (no drops, like the command)
```

JSON `data`: {"pos", "state", "tick"}

### `break`

`break POS [shears]`

Break a block like a creative player (neighbors update, no drops).

Removes the block at POS as a player in creative mode breaks it
(`ServerPlayerGameMode.destroyBlock`): its neighbors are updated, a door takes its
other half along. Items are not simulated, so nothing drops.

`shears`: the player holds shears. Only tripwire cares: it is disarmed first, so
cutting it does not trigger its hooks (they just detach). Without shears a broken
tripwire powers its hooks once, like an entity stepping in.

Examples:

```
break 2 1 0
at 20 break @WIRE shears
```

JSON `data`: {"pos", "state" (air), "tick", "shears"}

### `use`

`use POS [look DIRECTION]`

Right-click a block with an empty hand (levers, buttons, repeaters, …).

Uses the block at POS like a player with an empty hand (`useWithoutItem`): a lever
toggles, a button is pressed (it releases by itself after 20 or 30 ticks), a repeater
cycles its delay, a comparator switches mode, a door, trapdoor or fence gate opens or
closes, a note block plays. `look DIRECTION` is where the player looks (fence gates open
away from the player); default: south.

In the build (tick 0) a use changes the starting state; to flip a lever *during* a
test, record it on the timeline: `at 5 use @LEVER`.

Examples:

```
use 0 1 0
at 5 use @A        # flip lever A at tick 5
use 3 1 0   # repeater: next delay
```

JSON `data`: {"pos", "state" (after the use), "tick"}

### `fill`

`fill POS POS BLOCK [PROP=VALUE ...]`

Fill a box with a block like the /fill command.

Runs `/fill` in replace mode over the box between the two corners (both included, at
most 32768 blocks): every block in it becomes BLOCK, neighbors update as with
`/setblock`. Use it for floors, walls of solid blocks, or to clear an area (`clear`).

Examples:

```
fill -5 1 -5 5 1 5 stone
fill 0 1 0 0 1 9 redstone_wire
```

JSON `data`: {"low", "high", "state", "count", "tick"}

### `clear`

`clear POS POS`

Make a box air (the /fill command with air).

Same as `fill POS POS air`.

Examples:

```
clear -3 1 -3 3 4 3
```

JSON `data`: {"low", "high", "state", "count", "tick"}

### `line`

`line POS POS BLOCK [PROP=VALUE ...] [support BLOCK]`

Place a straight line of blocks like a player (skips taken spots).

Places BLOCK like `place` at every position from the first to the second (both
included); the two must differ along one axis only. Spots that are not air, or where
the block has no support, are skipped and listed. Use it for lines of wire, solid
blocks or repeaters (all with the same properties). `support BLOCK` first sets BLOCK
under every spot of the line that has air below it, so wire can run over a gap.

Examples:

```
line 0 1 0 9 1 0 redstone_wire
line 0 1 2 0 1 8 stone
line 0 3 0 6 3 0 redstone_wire support stone   # wire in the air, on stone
```

JSON `data`: {"placed": [[x, y, z], ...], "skipped": [{"pos", "reason"}], "tick"}

### `source`

`source POS KIND STRENGTH`

Put an analog signal source (barrel, lectern, cake, …) of a strength.

Puts a block that a comparator reads as STRENGTH (1-15) at POS: KIND is `barrel`,
`chest`, `hopper`, `lectern`, `cake` or `composter`, backed by the real block with the
contents that give that reading (a barrel with items, a lectern on a page, a cake with
bites, …). If POS holds a source already its strength (or kind) changes in place. Some
kinds cannot make every strength (cakes: even values); the nearest is used and said.

Examples:

```
source 0 1 0 barrel 7
source @IN lectern 3
```

JSON `data`: {"pos", "state", "kind", "strength", "tick"}

### `container`

`container POS SLOT ITEM COUNT | container POS empty`

Set one slot of a container (barrel, chest, hopper, dropper, furnace, …).

Puts COUNT of ITEM (an item id like `stone` or `minecraft:redstone`) into slot SLOT
(0-based) of the container at POS, replacing what was there (`/setblock` with the
block-entity data, so comparators update; a hopper keeps its transfer cooldown).
`container POS empty` empties every slot. Stacks are limited to the item's stack size.
Containers: barrels, chests, trapped chests, hoppers, droppers, dispensers and furnaces
(furnace, blast furnace, smoker: slot 0 ingredient, 1 fuel, 2 result; they do not cook
in the simulator, doc/differences.md).

Examples:

```
container 0 1 0 0 stone 64
container @CHEST empty
```

JSON `data`: {"pos", "state", "items": "slot:id*count ...", "tick"}

### `sign`

`sign POS front|back "LINE" ["LINE" ...]`

Write up to four lines on a sign.

Writes the lines on the given side of the sign at POS, as a player does (the sign's
block entity changes; comparators around it update). Quote lines that have spaces.
Signs are useful as labels inside a build that people see in the editor.

Examples:

```
sign 0 2 0 front "AND gate" "inputs: A B" "output: lamp"
```

JSON `data`: {"pos", "state", "side", "lines", "tick"}

### `plate`

`plate POS [mobs N] [others N] for TICKS`

Entities stand on a pressure plate or in a tripwire for some ticks (a stand-in).

Mobs and items are not simulated, so this puts *visitors* on the pressure plate or
into the tripwire at POS: N mobs (players count as mobs) and N other entities (items)
from the next tick on, for TICKS ticks. The plate or wire is pressed in the entity
phase and released at its next recheck after they leave, exactly as with real entities
(EXP-046, EXP-064). Stone plates only count mobs; weighted plates count everything; a
tripwire is pressed by any of them (rechecked every 10 ticks). Usually recorded on the
timeline: `at 5 plate @PLATE mobs 1 for 10`.

Examples:

```
at 5 plate 0 1 0 mobs 1 for 10
at 2 plate @P others 3 for 40
at 5 plate @WIRE mobs 1 for 3   # someone walks through a tripwire
```

JSON `data`: {"pos", "state", "mobs", "others", "ticks", "tick"}

### `hit`

`hit POS [strength S] [arrow|snowball]`

A projectile hits a target block (an editor stand-in).

Projectiles are not simulated: this makes one hit the target block at POS in the next
tick's entity phase with signal strength S (1-15, default 15: the center), keeping it
powered for 20 ticks (arrow, default) or 8 (snowball and other projectiles), as the
game does (EXP-037). Usually recorded: `at 3 hit @TARGET strength 9`.

Examples:

```
at 3 hit 0 1 0
at 3 hit @T strength 9 snowball
```

JSON `data`: {"pos", "state", "strength", "arrow", "tick"}

### `strike`

`strike POS`

Lightning strikes a lightning rod (an editor stand-in).

Weather is not simulated: this is a lightning bolt summoned on top of the lightning rod
at POS. In the next tick's entity phase it powers the rod: 15 to every side and strong
power into the block it stands on (or hangs from), for 8 ticks; a struck weathered rod
becomes a plain `lightning_rod` (EXP-066). Usually recorded: `at 5 strike @ROD`.

Examples:

```
at 5 strike 0 2 0
at 10 strike @ROD
```

JSON `data`: {"pos", "state", "tick"}

### `page`

`page POS N`

Turn a lectern's book to page N (as a player).

A player turns the book on the lectern at POS to page N (0-based): its comparator
reading changes and it gives a 2-tick redstone pulse (`LecternBlockEntity.setPage`).

Examples:

```
at 4 page @LECTERN 2
```

JSON `data`: {"pos", "state", "page", "tick"}

### `copy`

`copy POS POS to POS`

Copy a box to another place (like /clone … strict: no block updates).

Copies the box between the first two corners so that its lowest corner lands at the
third position. Like the editor's copy: `/clone … strict replace force`, so nothing in
the copy is updated (a torch keeps its state even if its input differs there) and
pending scheduled ticks inside come along. Air is copied too.

Examples:

```
copy 0 1 0 4 2 2 to 0 1 5
```

JSON `data`: {"from": [low, high], "to": [low, high], "tick"}

### `move`

`move POS POS to POS`

Move a box (like /clone … strict replace move).

Moves the box between the first two corners so that its lowest corner lands at the
third position; the old place becomes air. No block updates (strict), pending ticks
move along.

Examples:

```
move 0 1 0 4 2 2 to 10 1 0
```

JSON `data`: {"from": [low, high], "to": [low, high], "tick"}

### `rotate`

`rotate POS POS [times N]`

Turn a box clockwise (seen from above) in place, N quarter turns.

Turns the box between the corners N quarter turns clockwise seen from above (default 1)
around its center; the blocks' facing turns with it. No block updates, pending ticks
move along. A box that is not square ends up at a new place: the output says where.

Examples:

```
rotate 0 1 0 4 2 2
rotate 0 1 0 4 2 2 times 2
```

JSON `data`: {"from": [low, high], "to": [low, high], "tick"}

### `mirror`

`mirror POS POS x|z`

Mirror a box in place (x: east-west, z: north-south).

Mirrors the box between the corners in place: `x` swaps east and west, `z` north and
south; facing properties mirror with it. No block updates, pending ticks move along.

Examples:

```
mirror 0 1 0 4 2 2 x
```

JSON `data`: {"from": [low, high], "axis", "tick"}

### `stack`

`stack POS POS DIRECTION [times N] [gap G]`

Repeat a box N times next to itself in a direction.

Puts N copies (default 1) of the box between the corners next to it, one after the
other in DIRECTION (north, south, east, west, up, down), with G blocks between copies
(default 0). Strict (no block updates); pending ticks are copied. Useful for repeating
a cell of a circuit (a bit of a register, a slice of a door).

Examples:

```
stack 0 1 0 2 3 0 east times 7
stack 0 1 0 0 1 3 up times 3 gap 1
```

JSON `data`: {"from": [low, high], "box": [low, high] (all copies), "tick"}

### `prefab`

`prefab save NAME POS POS | prefab list | prefab delete NAME`

Keep a box of the build as a named prefab (a reusable module).

`prefab save NAME POS POS` captures the box between the corners **from the build**
(tick 0; air and block-entity data included) under NAME, saved with the world; the
editor lists it under Circuit → Prefabs. `paste NAME at POS` places a copy. Use it to
reuse a module that passed its targets (a gate, a memory cell, a door slice).
`prefab list` lists them with their sizes, `prefab delete NAME` removes one.

Examples:

```
prefab save and 0 1 0 4 2 2
prefab list
paste and at 0 1 6
```

JSON `data`: {"prefabs": [{"name", "size", "blocks"}]}

### `paste`

`paste NAME at POS [rotate N] [mirror x|z]`

Place a copy of a prefab with its lowest corner at POS.

Places the prefab NAME (see `prefab`) with its lowest corner at POS, turned N quarter
turns clockwise seen from above and/or mirrored, like the editor's paste (`/clone …
strict`: no block updates, air included). Run `settle` afterwards if the copy sits
next to something it should react to.

Examples:

```
paste and at 0 1 6
paste door at 10 1 0 rotate 2
```

JSON `data`: {"name", "low", "high", "tick"}

## Time

Moving the view through time and changing the timeline (recorded edits, power pulses, markers, undo).

### `at`

`at T COMMAND [ARGS ...]`

Run a command at tick T: record an edit there, or look at that tick.

With an editing command (`place`, `set`, `use`, `break`, `fill`, `plate`, `hit`, …) the
edit is recorded on the timeline at tick T instead of changing the build: it happens
between tick T and tick T+1, like a player acting at that moment, and runs again
whenever the simulation passes that tick. Edits recorded later stay where they are
(the history is simulated again from T). `at 0 …` is the same as no `at`: the build.

With a command that only looks (`show`, `inspect`, `why`, …) it looks at tick T and
leaves the view where it was.

Examples:

```
at 5 use @A              # flip lever A at tick 5
at 12 set 4 1 0 air      # remove the block at tick 12
at 8 show y=1            # the map at tick 8
at 20 inspect @OUT
```

JSON `data`: the data of COMMAND

### `run`

`run [N] | run until T`

Move the view N ticks forward (default 1), simulating as needed.

Advances the view by N ticks (or to tick T). Inside the recorded history this replays
it (with its recorded edits); past its end the simulation runs on and the history
grows. Then prints where the view is and, for every monitored or labeled block, its
value now (see `waves` for a whole timeline).

Examples:

```
run
run 20
run until 100
```

JSON `data`: {"tick", "end_tick", "inside_tick", "values": {name: value}}

### `seek`

`seek T`

Move the view to tick T (simulating further if needed).

Moves the view to tick T: back into the recorded history or forward past it.

Also: `goto`

Examples:

```
seek 0
seek 37
```

JSON `data`: {"tick", "end_tick", "inside_tick", "values"}

### `back`

`back [N]`

Move the view N ticks back (default 1).

Moves the view N ticks back in the recorded history (not before tick 0).

Examples:

```
back
back 10
```

JSON `data`: {"tick", "end_tick", "inside_tick", "values"}

### `step`

`step [N] | step back [N]`

Run N single engine steps (inside a tick) and show what each did, or go back.

A game tick is a series of steps (doc/mechanics/tick-scheduling.md): the tick start,
each scheduled tick (in priority order), each block event, each entity, each block
entity. `step` runs them one at a time and prints each with the blocks it changed, so
you can see the order things happen in. A tick with nothing to do is a single step.
The view is then *inside* a tick: inspection commands show the world at that moment;
edits still go to the build or `at T`. `run` finishes the tick. `step back [N]` goes
back N steps (the same steps run again when you step forward).

Examples:

```
step
step 5
step back
```

JSON `data`: {"steps": [{"index", "kind", "pos", "changes": [{"pos", "from", "to"}]}],
    "tick", "inside_tick"}

### `settle`

`settle [max N]`

Let the build settle (torches react, …) and make that state the build.

Right after building, a contraption is often not in its steady state yet: a torch
placed next to a powered block is still lit, a lamp still on, wire still powered. They
react in the first ticks. `settle` simulates the build alone (without the timeline's
edits) until a tick passes with no block change and nothing pending (scheduled ticks,
block events, moving pistons, falling blocks), at most N ticks (default 200), and
makes that state the new build (tick 0). The timeline's edits keep their tick numbers;
the output lists what changed. A clock never settles: then nothing changes and
`settle` says so. This is the editor's "Set tick 0 here" after letting the circuit
run, without moving the timeline.

Examples:

```
settle
settle max 50
```

JSON `data`: {"ticks": ticks it took or null, "changes": [{"pos", "from", "to"}]}

### `rebase`

`rebase`

Make the view tick the new build (the editor's "Set tick 0 here").

The world at the view tick becomes the build (tick 0): the history before it is
dropped (edits recorded before the view tick are baked into the build), edits
recorded later move earlier by the view tick, and the simulated length is kept. Use
`settle` instead to just let a fresh build react.

Examples:

```
seek 6
rebase
```

JSON `data`: {"tick": the old tick that is now 0}

### `where`

`where`

Show the view tick, the simulated length and the next engine step.

Prints where the view is in time, how far the history is simulated and, inside a
tick, what the next engine step will do.

Examples:

```
where
```

JSON `data`: {"tick", "end_tick", "inside_tick", "next"}

### `edits`

`edits`

List the timeline: recorded edits and power pulses, with ids E1, E2, ….

Lists everything recorded on the timeline, in tick order: edits made with `at T …`
and power pulses. Each gets an id (E1, E2, …) for `edit`; the ids are positions in this
list, so they change when the timeline changes: list again before using them.

Examples:

```
edits
```

JSON `data`: {"edits": [{"id", "tick", "kind", "pos", "what"}]}

### `edit`

`edit move IDS to T | edit shift IDS by N | edit delete IDS | edit merge IDS [to T]`

Move, shift, delete or merge recorded edits (ids from 'edits').

Changes the timeline. IDS are ids from `edits` (E1 E3 …) or `all`.

- `move IDS to T`: the edits happen at tick T (all of them, keeping their order);
- `shift IDS by N`: each moves N ticks (negative: earlier);
- `delete IDS`: they are removed;
- `merge IDS [to T]`: they all happen at T (default: the earliest of them).

Moving an edit to tick 0 puts it into the build. The history is simulated again; edits
that cannot happen at their new tick (their spot is taken) are dropped and reported.

Examples:

```
edit move E2 to 15
edit shift E1 E2 by -3
edit delete E4
edit delete all
```

JSON `data`: {"changed": [ids], "failed": number of edits dropped}

### `pulse`

`pulse POS at T [for N] [strength S]`

Power a position from tick T for N ticks (a test signal, editor power).

Adds a power pulse to the timeline: the position gets signal strength S (default 15)
from every side, like an invisible redstone block next to it, from tick T (at least 1)
for N ticks (default 2). It is locked to the position, whatever block is there
(ADR-026). `for 0` makes a 0-tick pulse: on and off inside tick T+1. This is the
simplest way to drive a contraption's inputs in tests; it is an editor tool, not a
game mechanic (doc/differences.md).

Exactly when it is on: it switches on between tick T and tick T+1 (like an edit at
tick T, so the view at tick T already shows it) and off at the start of tick T+N+1:
the views of ticks T … T+N show it on. A lamp powered by it lights at tick T and goes
off 4 ticks after the pulse ends, at tick T+N+5.

Examples:

```
pulse @A at 2 for 10
pulse 0 1 0 at 5 for 1 strength 7
pulse @CLK at 3 for 0
```

JSON `data`: {"pos", "tick", "ticks", "strength"}

### `marker`

`marker T ["NAME"]`

Name a tick on the timeline (no name: remove the marker).

Markers name moments ("door open", "clock period") for people looking at the
timeline in the editor.

Examples:

```
marker 12 "door open"
marker 12
```

JSON `data`: {"tick", "name"}

### `undo`

`undo`

Undo the last change (this run's last command, or the last earlier run).

Within one run of redsim-cli (a script, `-c` or a shell) `undo` reverts the last
command that changed something. When there is nothing left to undo in this run, it
restores the world file as it was before the previous run that changed it (the undo
file `WORLD.undo` keeps 20 versions). `redo` goes forward again.

Examples:

```
undo
```

JSON `data`: {"undid": "command" or "file version"}

### `redo`

`redo`

Redo what undo undid.

The reverse of `undo`: within the run command by command, else the file version that
`undo` replaced.

Examples:

```
redo
```

JSON `data`: {"redid": "command" or "file version"}

## Inspect

Looking at the world: maps, single blocks, signals, causes, changes and signal timelines. They only read; `at T` looks at tick T.

### `show`

`show [y=Y|y=A..B|x=X|z=Z] [from POS to POS | around POS [radius R]] [power] [wide]`

Draw the world as text maps: layers from above, or a slice from the side.

Draws maps with one two-character cell per block (doc/cli.md, "Reading a map"):
upper-case letters are components that are on, lower-case ones are off, the second
character is an arrow (where it outputs or pushes) or a signal strength. A legend
under the maps explains every code used.

- `y=Y` (or `y=A..B`): layers seen from above, x to the right, north at the top.
  Without a view, every layer of the area is drawn from above.
- `z=Z`: a vertical slice seen from the south (x to the right, up at the top).
- `x=X`: a vertical slice seen from the west (z to the right, south at the right).

The area is the box around everything above the floor (plus one block around it),
or `from POS to POS`, or `around POS [radius R]` (default radius 4: the layers just
below, at and above POS). `power` draws signal strengths instead of blocks (hex digit,
`.` for none). Maps wider than 64 blocks need `wide`. The labels inside the area are
listed under the legend.

Examples:

```
show
show y=1
show y=1..3 power
show z=0
show around @OUT radius 3
at 10 show y=1
```

JSON `data`: {"tick", "view": "y"|"x"|"z", "layers": [{"at": coordinate, "rows": [{"v":
    coordinate, "cells": [code, ...]}]}], "h": [first, last], "legend": {code: words},
    "entities": [[x, y, z], ...], "labels": {name: [x, y, z]} (the labels in the area)}

### `inspect`

`inspect POS [POS ...]`

Everything about a block: state, signals in and out, pending ticks, data.

For each position: its full block state, its label and note, which way it works (for
directional blocks: "input from the east, output to the west"), what signal it receives
from each side and what it gives to each side, whether it is a solid block that
conducts and how much power it has, its monitor value, what a comparator reads from
it (containers, cauldrons, lecterns, …: `analog`), its pending scheduled ticks, its
block-entity data (container items, comparator output, …) and its neighbors.

Signals, as the game computes them (doc/mechanics/power-queries.md):

- "receives west 15": the neighbor to the west gives this block 15 (`getSignal`:
  what a lamp, piston, repeater input or wire sees from that side);
- "gives east 15": this block gives 15 to its east neighbor;
- "(direct 15)": the direct part (`getDirectSignal`), which is what powers a solid
  block the signal goes into. A solid block powered directly then gives that power to
  the components around it ("powered 15" on its "conducts" line). Redstone wire gives
  a direct signal too, but other wire ignores blocks powered only by wire (that is
  Minecraft's "weak power"; torches, repeaters, comparators, levers and buttons give
  "strong power").
- Sides are listed in the game's order: down, up, north, south, west, east. Wire on a
  solid block "receives" its own power back from below; the game's `getSignal`
  returns that, wire itself ignores it.

Examples:

```
inspect 3 1 0
inspect @A @OUT
at 7 inspect @OUT
```

JSON `data`: {"blocks": [{"pos", "state", "label", "signals": {side: {"in", "in_direct",
    "out", "out_direct"}}, "orientation", "conductor", "direct_power", "best_signal", "monitor",
    "analog" (comparator reading or null),
    "scheduled": [{"block", "tick", "priority"}], "block_entity", "neighbors":
    {side: state}}], "tick"}

### `why`

`why POS [max N]`

Why did this block last change? The chain of causes, back to its origin.

Finds the last change of the block at POS (up to the view tick) and follows its causes
backwards: the update that made it change, the block change that sent that update,
the scheduled tick or block event behind that, back across ticks to the edit, pulse or
build that started it. For a piston that extended it also says where its power came
from (quasi-connectivity included) and why that is on. Newest first; each line shows
the tick and position. Use `at T why POS` to ask about an earlier moment. The chain
shows at most N links (default 60); a long one (a signal through many repeaters)
ends with a line saying it goes on: ask `why` about the block it stopped at, or give
a larger N.

Examples:

```
why @OUT
at 9 why 3 1 0
why @END max 400
```

JSON `data`: {"pos", "causes": [{"tick", "pos", "text", "branch"}], "complete", "tick"}

### `effects`

`effects POS [max N]`

Where a signal goes: every block change the block's last change caused.

The forward view of `why`: takes the last change of the block at POS up to the view
tick (a lever switched on, a repeater turning on) and lists every block change it
caused afterwards, oldest first: through the updates it sent, the scheduled ticks and
block events those queued (in later ticks too), and so on, to the end of the simulated
history. One line per block and tick: a block that changed several times in a tick
(wire turning off passes through every power level) shows its first and last state
and the number of changes. Use it to see where a signal goes and what it reaches, or
to find out why something far away reacted. At most N lines (default 200).

Examples:

```
effects @A
at 3 effects @CLOCK max 40
```

JSON `data`: {"pos", "change": {"tick", "text"} or null, "effects": [{"tick", "pos", "text",
    "changes"}]}

### `trace`

`trace [T] [near POS [radius R]]`

What happened during tick T, step by step (default: the view tick).

Lists the engine steps of tick T in the order they ran (tick start, scheduled ticks,
block events, entities, block entities, edits) and under each step the blocks it
changed. `near POS` keeps only changes within R blocks (default 3) of POS. The tick
is replayed for this (simulated first if it is past the end of the history); the
view stays where it is.

Examples:

```
trace
trace 7
trace 7 near @OUT
```

JSON `data`: {"tick", "steps": [{"index", "kind", "pos", "changes": [{"pos", "from", "to"}]}]}

### `waves`

`waves [POS ...] [ticks A..B]`

Signal timelines: one hex digit per tick for each block (a logic analyzer).

Prints, for each position, its value at every tick of the range as one character: a
hex digit 1-f for 1-15, `.` for 0. The value is what the editor's monitor shows: the
power of wire and target blocks, a comparator's output, 15 or 0 for lit/powered/
extended blocks (lamps, torches, repeaters, levers, pistons), a source's reading, and
for other blocks the strongest signal they receive. Without positions: every labeled
and monitored block. The range defaults to the whole simulated history (at most 120
ticks; give `ticks A..B` for others; ticks past the end are simulated).

Examples:

```
waves
waves @A @B @OUT ticks 0..40
waves 0 1 0 5 1 0
```

JSON `data`: {"from", "to", "rows": [{"pos", "name", "block", "values": [int, ...]}]}

### `changes`

`changes POS [POS ...] [ticks A..B]`

How a block's state changed over time: each new state with its tick.

For each position, the block state at the start of the range and then every tick
where it changed, with the new state. Where `waves` shows signal values, `changes`
shows the blocks themselves: a piston extending, a block arriving where a piston
pushed it, a repeater locking. The range defaults to the whole simulated history.

Examples:

```
changes 2 1 0
changes @DOOR @P ticks 0..30
```

JSON `data`: {"from", "to", "rows": [{"pos", "name", "changes": [{"tick", "state"}]}]}

### `monitor`

`monitor add POS [POS ...] | monitor remove POS [POS ...] | monitor list`

Choose the blocks the editor's timeline monitors (and waves shows).

Monitored blocks get a signal track in the editor's timeline and are shown by `waves`
and `run` when no positions are given (labeled blocks are shown too). They are saved
with the world.

Examples:

```
monitor add @OUT 4 1 0
monitor remove 4 1 0
monitor list
```

JSON `data`: {"monitors": [[x, y, z], ...]}

### `diff`

`diff A [B]`

Which blocks differ between tick A and tick B (default: the view tick).

Compares the world at two ticks and lists every block that is different, with its
state at A and at B. Handy after `run` (`diff 0` shows everything that changed since
the build) and for finding what a pulse or an edit affected.

Examples:

```
diff 0
diff 4 9
```

JSON `data`: {"from", "to", "changes": [{"pos", "from", "to"}]}

### `ticks`

`ticks`

Pending scheduled ticks and block events at the view.

Lists what is waiting to happen: scheduled ticks (a repeater about to switch, a lamp
about to turn off, …) with the tick they run at and their priority, and block events
(pistons) queued in the current tick.

Examples:

```
ticks
at 3 ticks
```

JSON `data`: {"scheduled": [{"pos", "block", "tick", "priority"}], "events": [{"pos",
    "block", "b0", "b1"}]}

### `find`

`find BLOCK [PROP=VALUE ...] [in POS POS]`

Where are blocks of a kind (with these properties)?

Lists the positions of every block of that id; properties given must match too
(`find repeater powered=true`). `in POS POS` limits the search to a box.

Examples:

```
find redstone_lamp
find repeater powered=true
find piston in 0 1 0 9 3 9
```

JSON `data`: {"block", "positions": [[x, y, z], ...]}

### `entities`

`entities`

The falling blocks in the world (the only simulated entities).

Lists every falling block: its block, exact position and motion, and how long it has
been falling.

Examples:

```
entities
```

JSON `data`: {"entities": [{"id", "state", "pos", "motion", "time"}]}

### `delays`

`delays FROM TO [ticks A..B]`

Measure how long a change at FROM takes to show at TO.

Follows the values of FROM and TO (as `waves` shows them) over the range (default:
the whole simulated history) and, for every change of FROM, reports the first change
of TO at or after it, and the delay in ticks. Use it to measure a circuit's delay
(input lever to output lamp), a pulse's length, or how long a piston sequence takes.
A change of FROM with no later change of TO says "no change".

Examples:

```
delays @A @OUT
delays @IN @LAMP ticks 0..60
```

JSON `data`: {"from", "to", "changes": [{"tick", "value", "to_tick", "to_value", "delay"}]}

## Annotate

Names and notes that make a world readable: labels, notes, sections.

### `label`

`label NAME POS ["NOTE"] | label NAME delete`

Name a position: @NAME then works wherever a position does.

Gives the position POS the name NAME (letters, digits, `_`, `.`, `-`; starting with a
letter or `_`), with an optional note saying what it is. Afterwards `@NAME` stands for
the position in every command (`inspect @OUT`, `pulse @A at 2`), and `@NAME+1,0,0` for
a position next to it. Labels are saved in the world and listed by `labels`, `info`
and the editor. Labeling a contraption's inputs and outputs is the first step to
testing it (`target`). `label NAME delete` removes the label.

Examples:

```
label A 0 1 0 "input A (lever)"
label OUT 6 1 0
label OUT delete
```

JSON `data`: {"name", "pos" or null, "note"}

### `labels`

`labels`

List the labels with their positions, notes and current blocks.

Lists every label: its name, position, note and the block there at the view tick.

Examples:

```
labels
```

JSON `data`: {"labels": [{"name", "pos", "note", "state"}]}

### `note`

`note "TEXT" | note delete N`

Add a note to the world (what it is, what is left to do), or delete one.

Notes are free text saved with the world and shown by `info` and `notes`: what the
contraption is for, how to use it, what still fails. Use them to hand a world over to
a person or another agent. `note delete N` removes the N-th note (see `notes`).

Examples:

```
note "2-input AND gate; inputs @A @B, output @OUT"
note delete 1
```

JSON `data`: {"notes": [text, ...]}

### `notes`

`notes`

List the world's notes.

Lists the notes, numbered (for `note delete N`).

Examples:

```
notes
```

JSON `data`: {"notes": [text, ...]}

### `group`

`group NAME POS POS [in POS NAME ...] [out POS NAME ...] | group NAME delete | groups`

Mark a box as a named part of the circuit, with input and output ports.

Groups name parts of a larger build ("adder bit 0", "clock") and their ports, the
positions where signals enter and leave. The editor shows them under Circuit →
Groups with live port readings and draws their boxes; they never change the
simulation. `in POS NAME` and `out POS NAME` add ports (repeatable).
`group NAME delete` removes a group; `groups` lists them.

Examples:

```
group and 0 1 0 4 2 2 in @A A in @B B out @OUT OUT
groups
group and delete
```

JSON `data`: {"groups": [{"name", "low", "high", "ports": [{"name", "pos", "role"}]}]}

### `groups`

`groups`

List the groups with their boxes and ports.

Lists every group: its box and its ports with what they read now.

Examples:

```
groups
```

JSON `data`: {"groups": [{"name", "low", "high", "ports": [{"name", "pos", "role", "reading"}]}]}

## Targets

Acceptance tests for contraptions: what should happen, checked from the build.

### `target`

`target new NAME ["DESCRIPTION"] | target NAME do COMMAND ... | target NAME expect POS CONDITION at T|during A..B|within A..B | target NAME truth INPUTS -> OUTPUTS rows ROW ... [settle N] | target NAME show | target NAME remove N | target NAME delete | target NAME load [CASE]`

Define an acceptance test: stimuli, expected results, or a truth table.

A target says what a contraption must do; `check` runs it. Build it up line by line:

- `target new NAME "DESCRIPTION"`: an empty target (one case, "main").
- `target NAME do COMMAND …`: a stimulus for every case: `pulse POS at T for N`,
  `at T use POS`, `at T set POS BLOCK`, `at T plate …`, or an edit without `at`, which
  changes the build for the test only.
- `target NAME expect POS CONDITION WHEN`: CONDITION is `KEY=VALUE` (also `!=`, `<`,
  `<=`, `>`, `>=` for numbers), KEY a block property (`lit`, `powered`, `extended`,
  `power`, …) or `block` (the block id), `power` (the value `waves` shows), `signal`
  (strongest signal received), `direct` (how much a solid block is powered) or
  `analog` (what a comparator reads from it: a container's fullness, …). WHEN is `at
  T`, `during A..B` (every tick) or `within A..B` (some tick).
- `target NAME truth @IN1 @IN2 -> @OUT rows 00:0 01:0 10:0 11:1 [settle N]`: one case
  per row (input bits, `:`, output bits). Inputs that are 1 switch on at tick 1 (a
  lever is flipped, anything else gets a power pulse that lasts the run); each output
  must be on (`power>=1`) or off (`power=0`) at tick 1 + settle (default 10).
- `target NAME show` lists its lines (numbered), `remove N` deletes line N,
  `delete` the whole target.
- `target NAME load [CASE]` replaces the world's timeline with the case's stimuli
  (undo brings the old one back), so `show`, `waves`, `why` can look at that run.

Targets are saved in the world. Their ticks count from the build (tick 0) of each run.

Examples:

```
target new and "lamp only when both A and B are on"
target and truth @A @B -> @OUT rows 00:0 01:0 10:0 11:1
target new clock "the clock pulses every 4 ticks"
target clock do pulse @START at 1 for 1
target clock expect @OUT powered=true within 2..6
target and load 11
```

JSON `data`: {"target": {"name", "description", "cases": [{"name", "lines"}]}}

### `targets`

`targets`

List the targets with their cases.

Lists every target: its name, description and cases.

Examples:

```
targets
```

JSON `data`: {"targets": [{"name", "description", "cases": [names]}]}

### `check`

`check [NAME ...] [verbose]`

Run the targets from the build and report what passes and what fails.

Runs every case of the named targets (default: all) in a copy of the world from the
build (tick 0), with the case's stimuli instead of the world's own timeline, and
evaluates each expectation at its ticks. Prints PASS or FAIL per case; for a failing
expectation the ticks where it failed and the values seen there, plus the block's
values over the expectation's range (as `waves` would show them). `verbose` lists
passing expectations too, a passing `within` with the tick it was first met (how
fast the contraption reacted). The world itself is not changed.

The exit code is 1 when any case fails, so scripts can stop on it.

Examples:

```
check
check and clock
check and verbose
```

JSON `data`: {"passed": cases passed, "failed": cases failed, "cases": [{"target", "case",
    "passed", "error", "expectations": [{"line", "passed", "failing_ticks" (empty when
    passed), "first_held" (first tick it held, or null), "observed": {tick: value},
    "problem"}]}]}

## Io

Exchanging builds with Minecraft: schematics and structure files, saves.

### `export`

`export FILE [from POS POS]`

Write the build (or a box) as a .litematic, .schem or .nbt file for Minecraft.

Writes the blocks of the box (default: everything above the floor) at the view tick
to FILE, in the format of its extension: `.litematic` (Litematica), `.schem`
(Sponge/WorldEdit) or `.nbt` (a structure file for structure blocks and
`/place template`). Block-entity data (container items, comparator outputs, signs)
goes along. This is how a contraption designed here gets into Minecraft.

Examples:

```
export gate.litematic
export door.nbt from -2 1 -2 4 5 3
```

JSON `data`: {"path", "low", "high", "blocks"}

### `import`

`import FILE at POS [rotate N] [mirror x|z]`

Paste a .litematic, .schem or .nbt file into the build at POS.

Reads a schematic or structure file and pastes it with its lowest corner at POS, like
the editor's paste (`/clone … strict`: no block updates, air included), after turning
it N quarter turns clockwise and/or mirroring it. Blocks the simulator does not model
come in as inert foreign blocks. `at T import …` pastes it at tick T instead.

Examples:

```
import gate.litematic at 0 1 0
import door.nbt at 10 1 0 rotate 1
```

JSON `data`: {"path", "low", "high", "blocks", "tick"}

### `open-save`

`open-save SAVE [center X Z] [radius R] [force]`

Create the world file from a Minecraft Java save (around the player).

Reads the Minecraft save folder SAVE (the one with `level.dat`) and makes the world
file from the chunks within R chunks (default 2) around the player, or around the
chunk holding block X Z. Blocks come in as they are, without updates; blocks the
simulator does not model are inert foreign blocks (listed). The world remembers the
save, so `export-save` can write changes back into a copy. Replaces an existing world
file only with `force`.

Examples:

```
open-save ~/.minecraft/saves/Redstone
open-save ./Redstone center 120 -40 radius 3
```

JSON `data`: {"save", "blocks", "foreign": {id: count}, "ticks"}

### `export-save`

`export-save TARGET`

Write the world into a copy of the Minecraft save it came from.

For a world made with `open-save`: copies the original save to the new folder TARGET
and writes the world's blocks (at the view tick) and pending scheduled ticks into the
copy, which Minecraft then opens. The original save is never changed.

Examples:

```
export-save ~/.minecraft/saves/Redstone-edited
```

JSON `data`: {"target", "blocks", "chunks"}

## Meta

Help and the command line itself.

### `help`

`help [COMMAND]`

List the commands, or show one command in full.

Without a command: every command with one line about it, by chapter. With a command:
its syntax, description, examples and what its `--json` output holds. The same text
is in doc/cli-reference.md; the concepts are explained in doc/cli.md.

Examples:

```
help
help place
```

JSON `data`: {"text"}
