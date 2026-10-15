# redsim-cli: the simulator on the command line

`redsim-cli` lets you build, change, run, inspect and test Minecraft redstone contraptions
from a terminal, one command at a time. It is written for **AI agents and people
alike**: everything it prints is plain text that both can read, everything it does is
saved in an ordinary world file that the editor (`redsim`) opens, and the same commands
work typed by hand, in scripts and inside tests. The simulation is the same one the editor
uses: a port of Minecraft Java Edition 26.3's server code, compared tick by tick with the
real game ([[experiments/index]]; what differs is listed in [[differences]]).

This page is the guide: what the parts are and how they fit together, with worked
examples. Every command is described in full in [[cli-reference]], which is generated
from the same text `redsim-cli help COMMAND` prints. How the program is built (for
developers who change or extend it) is in [[cli-internals]].

Contents: 1 Quick start · 2 Running redsim-cli · 3 The world file · 4 Positions,
directions and blocks · 5 Time: the build, the timeline and the view · 6 Building ·
7 Looking at a contraption · 8 Labels and notes · 9 Targets: testing a contraption ·
10 Workflows · 11 Output for programs (`--json`) · 12 Exchanging builds with Minecraft ·
13 Rules and pitfalls · 14 Glossary

## 1. Quick start

```sh
redsim-cli gate.redsim.json new                      # a world with a stone floor at y=0
redsim-cli gate.redsim.json place 0 1 0 lever face=floor
redsim-cli gate.redsim.json place 1 1 0 redstone_lamp
redsim-cli gate.redsim.json label IN 0 1 0
redsim-cli gate.redsim.json label OUT 1 1 0
redsim-cli gate.redsim.json show                     # a map of what is there
redsim-cli gate.redsim.json -c "at 3 use @IN; run 10; waves"
```

The last line records "flip the lever at tick 3" on the timeline, simulates 10 ticks and
prints a signal timeline:

```
> at 3 use @IN
used @IN: lever[face=floor,facing=north,powered=true] (tick 3)
> run 10
now at tick 10 of 10
  @IN=15  @OUT=15
> waves
tick                0         1
                    01234567890
@IN lever           ...ffffffff
@OUT redstone_lamp  ...ffffffff
(ticks 0..10; digit = value 1-15 in hex, . = 0)
```

A longer example, an AND gate with a test, is `examples/cli/and_gate.cli.txt`
(section 10.1).

## 2. Running redsim-cli

### 2.1 Installing

`redsim-cli` comes with the simulator: in the project's environment (doc/README.md,
`environment.yml`) `pip install -e .` installs both `redsim` (the editor) and
`redsim-cli`. Without installing, `PYTHONPATH=src python -m redsim.cli …` does the same.
It needs no display: it never loads the editor's window code.

### 2.2 Ways to call it

```
redsim-cli [OPTIONS] WORLD COMMAND [ARGS...]     one command
redsim-cli [OPTIONS] WORLD -c "CMD; CMD; ..."    several commands
redsim-cli [OPTIONS] WORLD < script.cli.txt      commands from standard input
redsim-cli [OPTIONS] WORLD                       (in a terminal) a summary of the world
redsim-cli WORLD shell                           an interactive prompt
redsim-cli help [COMMAND]                        help (also: help --markdown)
```

`WORLD` is the world file (section 3). A script is a text file with one command per
line; `#` starts a comment, `;` separates commands on one line, quotes keep spaces
inside one argument (`note "two words"`). When several commands run, each command's
output starts with a line `> the command`.

Options, before the world or right after it:

| Option | Effect |
|---|---|
| `--json` | One JSON object per command instead of text (section 11). |
| `--dry-run` | Run everything, but do not save the world file. |
| `--keep-going` | Do not stop at the first failing command. |

Exit codes: **0** every command worked (and every `check` passed), **1** a command failed
or a target failed, **2** the call itself was wrong. A failing command prints
`error: …` saying what was wrong and, where it can, how to fix it (a missing support
block, the allowed values of a property, close matches for a misspelled name). Without
`--keep-going` the commands after a failing one do not run, but what ran before it is
saved.

### 2.3 One run, many commands

Every run opens the world file, re-simulates its recorded history (milliseconds for a
typical contraption) and saves it if something changed. Running a script, or many commands
with `-c`, does this once instead of once per command: prefer it for anything longer
than a few commands. Within one run, many building commands in a row are simulated once
at the end (section 5.5).

## 3. The world file

A world is one file, `NAME.redsim.json`: the editor's own format. It holds everything:

| What | Where it comes from |
|---|---|
| the **build** (the contraption at tick 0) | building commands |
| the **timeline**: edits recorded at ticks, power pulses | `at T …`, `pulse` |
| how far the history is simulated, and the **view** (the tick you look at) | `run`, `seek`, `back`, `step` |
| **labels**, **notes**, **targets**, monitored blocks, markers | `label`, `note`, `target`, `monitor`, `marker` |
| the **log** of the last 500 commands that changed it | every changing command (`log` shows it) |

So you can stop at any point and continue later, or hand the file to someone else: a
person opens it in the editor (`redsim NAME.redsim.json`) and sees the same contraption,
timeline and view; the editor's **World** tab lists the notes, labels and targets and
runs `check` with a button, and labeled blocks show their label in the inspector and on
the timeline. An agent runs `redsim-cli NAME.redsim.json info` and `log`.

Next to the world, `NAME.redsim.json.undo` keeps the last 20 versions of the file, for
`undo` across runs (section 5.6). It can be deleted at any time.

`new` creates a world: a 32×32 smooth stone floor at y=0 (`new size N`, `new floor BLOCK`,
`new floor none`). `open-save` creates one from a Minecraft save (section 12).

## 4. Positions, directions and blocks

### 4.1 Positions

Minecraft's coordinates: **+x is east, +z is south, +y is up.** A new world's floor is at
y=0, so things are built from y=1 up. A position is written in any of these forms:

| Form | Meaning |
|---|---|
| `3 1 -2` | three numbers x y z |
| `3,1,-2` | one word |
| `@OUT` | a label (section 8) |
| `@OUT+1,0,-2` | the position 1 east and 2 north of the label (each part may be negative: `@OUT-1,0,0`) |

Output always writes positions as `x y z`, followed by the label in brackets if one names
it (`5 1 0 (@OUT)`), or just `@OUT` in tables.

### 4.2 Directions

`north south east west up down`, or `n s e w u d`. North is −z, south +z, east +x, west −x.

### 4.3 Blocks and block states

A block is written like in Minecraft's `/setblock` command: an id with or without
`minecraft:`, optionally with properties in brackets, or with properties as further
`key=value` words:

```
redstone_wire
minecraft:repeater[facing=west,delay=2]
repeater facing=west delay=2
```

Properties you leave out keep their default (the first value the game lists). Output
writes states without `minecraft:` (`repeater[delay=2,facing=west,locked=false,powered=false]`),
in a form the commands read back.

**Which way things face.** The game's `facing` property means different things for
different blocks; getting it wrong is the most common building mistake:

| Block | `facing` points … | so its signal or push goes … |
|---|---|---|
| repeater, comparator | towards its **input** | the opposite way |
| observer | towards the side it **watches** | the opposite way |
| piston, sticky piston, dispenser, dropper | where it **pushes / outputs** | that way |
| hopper (`facing=down` or a side) | where it outputs | that way |
| wall torch | **away from** the wall it is on | (it powers the block above it, not the wall) |
| lever, button | with `face=wall`: away from the wall; `face=floor`/`ceiling`: the player's direction | |

For repeaters, comparators and observers you can write **`out=DIRECTION`** instead: the
side the signal leaves from (`repeater out=east` is `repeater[facing=west]`). The map
(`show`) draws these blocks with an arrow pointing where the signal goes, whatever the
property says.

Blocks the simulator does not model (water, TNT, beds, …) can be set and are kept, but
they do nothing in the simulation (foreign blocks, [[differences]] section 1).

## 5. Time: the build, the timeline and the view

This is the most important section: almost every surprise comes from mixing these up.

### 5.1 Ticks

The simulation advances in **game ticks** (20 per second in Minecraft; a redstone tick is
2 game ticks; all numbers here are game ticks). **Tick 0 is the build**: the contraption
as you built it. **Tick T** is the world after T ticks of simulation.

### 5.2 The build and the timeline

- **The build** is the contraption itself. `place`, `set`, `break`, `use`, `fill`, `copy`,
  … change the build. They do this **wherever the view is**: after `run 50`, a `place`
  still changes the build, and the history is simulated again from tick 0 with the
  changed build.
- **The timeline** holds what happens *while the contraption runs*: edits recorded at a
  tick (`at 5 use @LEVER` flips the lever at tick 5), and power pulses (`pulse @IN at 2
  for 10`). The recorded history replays them every time the simulation passes their
  tick. `edits` lists them (E1, E2, …), `edit` moves or deletes them.

An edit at tick T happens **between tick T and tick T+1**, like a player acting at that
moment: the view at tick T already shows it, and its effects unfold from tick T+1 on.
Edits recorded later stay at their ticks when you add or change an earlier one
([[decisions]] ADR-022).

### 5.3 The view

The **view** is the tick that inspection commands look at (`show`, `inspect`, `why`, …).
`run N` moves it forward (simulating further when it passes the end of the recorded
history), `back N` and `seek T` move it anywhere, `where` says where it is. `at T
COMMAND` runs one inspection at tick T without moving the view (`at 8 show y=1`). The view
is saved with the world.

`step` moves the view one **engine step** at a time *inside* a tick. A tick runs in a
fixed order of steps (doc/mechanics/tick-scheduling.md): the tick start, the scheduled
ticks (repeaters switching, torches turning, lamps turning off, observers pulsing; by
priority), block events (pistons starting to move), entities (falling blocks), block
entities (pistons moving on, hoppers). `step` prints each step with the blocks it
changed, so you can see exactly in which order things happen. A tick with nothing to do
is one step. `run` finishes a started tick.

### 5.4 Settling the build

Right after building, a contraption is often not in its steady state: a torch placed
next to a powered block is still lit, a lamp still on. They react in the first ticks.
**`settle`** simulates the build alone until nothing changes or is pending any more and
makes that state the build. Run it after building, before testing: otherwise a test
sees the start-up reaction. A clock never settles (`settle` says so and changes nothing).
`rebase` makes the view tick the build instead (the editor's "Set tick 0 here").

### 5.5 How a run handles edits

Within one run, building commands change the build one after the other; the recorded
history is simulated again only when a command needs it (an inspection, a timeline
command) and at the end. The view then returns to where it was. You do not need to do
anything about this; it only explains why a script of 100 `place` commands takes as long
as one.

### 5.6 Undo

`undo` reverts the last command that changed something in the current run; when there is
nothing left in this run, it restores the world file as it was before the previous run
that changed it (from the undo file, 20 versions). `redo` reverses an `undo`.

### 5.7 Power pulses: exact timing

`pulse POS at T for N [strength S]` gives the position signal strength S (default 15) from
every side, like an invisible redstone block next to it: it switches on between tick T and
T+1 and off at the start of tick T+N+1, so the views of ticks T to T+N show it on. A lamp
powered by a pulse at 2 for 3 is lit at ticks 2 to 8 (it turns off 4 ticks after the
pulse ends, as lamps do). `for 0` is a 0-tick pulse (on and off inside tick T+1). Pulses
are an editor tool, not a game mechanic: use them to drive a contraption's inputs in
tests, or flip the real input (`at T use @LEVER`) when the input is a lever or button.

## 6. Building

| Command | What it does |
|---|---|
| `place POS BLOCK` | Like a player placing the block: needs air and support; the game's placement rules fill in what you did not give (wire connections, a lamp lit next to power, a repeater locked by a side repeater, a door's upper half). **The normal way to build components.** |
| `set POS BLOCK [nbt JSON]` | Like the `/setblock` command: replaces anything, no support needed, no placement rules (a lamp set next to power stays off until something updates it, exactly as in Minecraft). For terrain, for block-entity data, for states placement would not give. |
| `break POS` | A player breaking it (creative: no drops); neighbors update. |
| `use POS [look DIR]` | A right click: lever, button, repeater delay, comparator mode, door, … |
| `fill POS POS BLOCK`, `clear POS POS` | `/fill` over a box (at most 32768 blocks). |
| `line POS POS BLOCK` | `place` along a straight line, skipping taken spots (listed). |
| `copy`, `move`, `rotate`, `mirror`, `stack` | Box operations like the editor's (no block updates inside: strict). |
| `source POS KIND STRENGTH` | A comparator source of a strength (barrel, chest, hopper, lectern, cake, composter). |
| `container`, `sign`, `page` | Container slots, sign text, a lectern's page. |
| `plate`, `hit` | Mobs or items on a pressure plate, a projectile hitting a target block (editor stand-ins for entities, [[differences]] section 3). |
| `import FILE at POS` | Paste a schematic or structure file. |

Every building command prints the resulting block state and where the edit went:
`placed 4 2 1: redstone_lamp[lit=false] (the build)` or `… (tick 5)`. Put `at T` in
front to record it on the timeline at tick T instead.

## 7. Looking at a contraption

### 7.1 Maps: `show`

`show` draws the area around everything above the floor, one layer at a time from above,
with two characters per block:

```
y=2  blocks at tick 0 of 0  (from above: x → right (east >), z ↓ (north ^ at the top), up +, down -)
x:     -2 -1  0  1  2  3  4  5
z= -1  .. .. .. .. .. .. .. ..
z=  0  .. .. T. .. .. .. .. ..
z=  1  .. .. wf we ## t> l. ..
z=  2  .. .. T. .. .. .. .. ..
z=  3  .. .. .. .. .. .. .. ..
```

Reading it: the column header gives x, each row starts with its z. The first character
says what the block is. For components an **upper-case letter means on** (powered, lit,
extended, pressed) and **lower case off**. The second character is an arrow (where it
outputs or pushes), a signal strength (wire `wf` = power 15; hex: `a` = 10 … `f` = 15),
or a mark. Above, `T.` are lit torches on the floor, `wf we` wire with power 15 and 14,
`##` a solid block, `t>` an unlit wall torch pointing east, `l.` an unlit lamp. A legend
under the maps explains every code that appears.

| Code | Block | Code | Block |
|---|---|---|---|
| `..` | air | `##` | full block that conducts (stone, …) |
| `::` | full block that does not conduct (glass, …) | `**` | redstone block |
| `w0`…`wf` | redstone wire, power 0-15 | `R>` | repeater, output east |
| `C>` / `K>` | comparator (`K`: subtract mode) | `T.` / `T>` | torch on the floor / on a wall |
| `V.` | lever | `B.` | button |
| `P_` | pressure plate | `L.` | redstone lamp |
| `Q.` | copper bulb | `O>` | observer, output east (it watches west) |
| `I>` / `J>` | piston / sticky piston, pushing east | `H>` | piston head |
| `M>` | block being moved by a piston | `X7` | target block, power 7 |
| `N.` | note block | `D>` / `E>` | dispenser / dropper |
| `U-` | hopper (output down) | `==`, `G=`, `A=` | rail, powered rail, activator rail |
| `%%` | falling block (entity) | `Ab` | any other block: two letters, named in the legend |

Arrows: `>` and `<` along the map's horizontal axis, `^` and `v` along its vertical axis
(up and down the page), `+` and `-` along the axis looking into the page. From above:
`^` north, `v` south, `>` east, `<` west, `+` up, `-` down. The other views: `show z=Z` is
a vertical slice seen from the south (x to the right, up at the top, `+` south towards
you), `show x=X` one seen from the west (z to the right, i.e. south to the right). Each
map's first line says which.

Variants: `show y=1` (one layer), `show y=1..3`, `show from POS to POS`, `show around POS
radius R`, `show power` (signal strengths instead of blocks: what each block gives or
receives, `.` for none), `at T show …`.

### 7.2 One block: `inspect`

```
4 1 0  redstone_wire[north=none,east=side,south=none,west=side,power=15]   (at tick 2 of 2)
  receives  down 15, west 15, east 15
  gives     down 15 (direct 15), west 15 (direct 15), east 15 (direct 15)
  conducts  no
  value     15  (what the monitor and waves show)
  neighbors
    down  4 0 0  smooth_stone
    west  3 1 0  redstone_wall_torch[facing=east,lit=true]
    east  @OUT  redstone_lamp[lit=true]
```

- **receives SIDE N**: the neighbor on that side gives this block signal N (the game's
  `getSignal`, which is what lamps, pistons, repeater inputs and wire read).
- **gives SIDE N (direct M)**: this block gives N to that neighbor; M is the *direct*
  part (`getDirectSignal`), the part that powers a solid block it goes into.
- **conducts**: whether it is a solid block that passes power on, and how much direct
  power it has (a solid block powered directly powers the components around it).
- In Minecraft's terms: torches, repeaters, comparators, levers and buttons give *strong*
  power to the block they point into (it then powers wire next to it too); redstone wire
  gives *weak* power (the block then powers lamps, pistons and repeaters next to it, but
  not other wire). Both show as "direct" here, because that is what the game's code
  computes; wire is what ignores blocks powered only by wire.
- Sides are always listed in the game's order: down, up, north, south, west, east.
- Also listed: pending scheduled ticks at the block, block events, block-entity data
  (container items, a comparator's output) and the neighbors.

### 7.3 Signals over time: `waves`

`waves [POS ...] [ticks A..B]` is a logic analyzer: one character per tick, `.` for 0,
`1`-`f` for 1-15 (see the example in section 1). Without positions it shows every labeled
and monitored block. The value is the editor's monitor value: the power of wire and
target blocks, a comparator's output, 15 for anything lit / powered / extended (lamps,
torches, repeaters, levers, pistons) and 0 otherwise, a source's reading, and for other
blocks the strongest signal they receive.

### 7.4 Blocks over time: `changes`

`changes POS [ticks A..B]` lists a block's state at the start and every tick it changed.
Use it for blocks whose *state* matters more than a signal (where a piston pushed a
block, when a repeater locked):

```
2 1 0 (@OUT) (ticks 0..16):
  tick 0    air
  tick 4    moving_piston[facing=east,type=normal]
  tick 6    stone
  tick 11   air
```

### 7.5 Why did it change? `why`

`why POS` follows the causes of the block's last change (up to the view tick) back to
where they started: the update that made it change, the block change that sent that
update, the scheduled tick or block event behind that, back across ticks to the edit,
pulse or build change that started it. For a piston it also says where its power came
from (including quasi-connectivity). Newest first:

```
2 1 0 last changed at tick 4: moving piston placed
  ← tick 4    @P           block event of sticky piston
  ← tick 3    @P           sticky piston queued a block event (0, 5)
  ← tick 3    @P           neighbor update from lever at -1 1 0
  ← tick 3    @L           lever: powered false → true
  ← tick 3    @L           edit or player action: use
  where the piston's power comes from:
  ← tick 3    @L           the piston is powered by lever at -1 1 0
```

`at T why POS` asks about an earlier moment. When something does *not* happen, `why` the
block that should have caused it, and `inspect` the block that should have reacted (does
it receive anything? from which side?).

### 7.6 Step by step: `trace`, `step`, `ticks`, `diff`

- `trace T [near POS]`: every engine step of tick T in order, with the blocks each changed.
- `step [N]`: walk through the current tick step by step (section 5.3).
- `ticks`: pending scheduled ticks (with the tick they run at and their priority) and
  block events.
- `diff A [B]`: every block that differs between two ticks (`diff 0`: everything that
  changed since the build).
- `find BLOCK [PROP=VALUE] [in POS POS]`, `entities`, `info`.

## 8. Labels and notes

`label NAME POS ["NOTE"]` names a position; `@NAME` then works everywhere a position
does. Label the inputs and outputs of every contraption first: commands, maps, waves and
targets become readable (`@OUT` instead of `4 2 1`), and labeled blocks show up in
`waves` and after `run` without being named. `labels` lists them, `label NAME delete`
removes one. `note "TEXT"` adds a note to the world (what it is, how to use it, what is
left to do); `info` and `notes` show them. Labels and notes never affect the simulation.

## 9. Targets: testing a contraption

A **target** is an acceptance test: what a contraption must do, written as commands. It
is saved in the world, and `check` runs it. Use targets to decide when a design is done,
and to notice when a change breaks something that worked.

### 9.1 Writing a target

```
target new door "the block is out from tick 6 to 10 and back by tick 13"
target door do at 3 use @L
target door do at 10 use @L
target door expect @OUT block=stone during 6..10
target door expect @OUT block=air at 13
```

- **`do COMMAND`** adds a stimulus: `at T use POS`, `at T set POS BLOCK`, `pulse POS at T
  for N`, `at T plate …`, `at T hit …`; or an edit without `at`, which changes the build
  for this test only.
- **`expect POS CONDITION WHEN`** adds an expectation.
  - CONDITION is `KEY=VALUE`, or `KEY!=VALUE`, or for numbers `KEY<N`, `<=`, `>`, `>=`.
  - KEY is a block property (`lit`, `powered`, `extended`, `power`, `delay`, …), or
    `block` (the block id without `minecraft:`), or `power` (the value `waves` shows, for
    any block), `signal` (the strongest signal it receives), `direct` (how much a solid
    block is powered). Note that the property `power` (wire) and the key `power` agree.
  - WHEN is `at T` (that tick), `during A..B` (every tick of the range) or `within A..B`
    (at least one tick of it).
- `target NAME show` lists the lines (numbered), `target NAME remove N` deletes one,
  `target NAME delete` the whole target, `targets` lists all.

### 9.2 Truth tables

For logic (gates, decoders, comparators of numbers), a truth table is quicker:

```
target new and "the lamp is on only when both levers are on"
target and truth @A @B -> @OUT rows 00:0 01:0 10:0 11:1
```

Each row is one case: the input bits, `:`, the output bits. An input that is 1 is
switched on at tick 1: a lever is flipped with `use` (it must be off in the build), any
other block gets a power pulse that lasts the whole case. Each output must be on
(`power>=1`) for 1 and off (`power=0`) for 0 at tick 1 + settle; settle defaults to 10
ticks (`… rows … settle 20` for slower circuits). Lines added with `do` and `expect`
apply to every case.

### 9.3 Running targets: `check`

`check` runs every case **from the build, in a copy of the world**, with the case's
stimuli instead of the world's own timeline, simulates to the last tick an expectation
needs and evaluates the expectations. The world itself is not changed. Here is the
output for the AND gate of section 10.1 with a deliberately wrong row (`10:1`: "A alone
lights the lamp"):

```
check: 4 cases, 3 passed, 1 failed
PASS  and [00:0]
PASS  and [01:0]
FAIL  and [10:1]
      fail expect @OUT power>=1 at 11
           saw tick 11: power=0
           ticks 11..11: .
PASS  and [11:1]
hint: 'target NAME load CASE' puts a case on the timeline; then waves, why, show
```

A failing expectation shows the ticks it failed at and what it saw, and for numbers the
values over its range in `waves` style. `check NAME …` runs some targets; `check …
verbose` also lists the expectations that passed. The exit code is 1 when a case fails.

### 9.4 Debugging a failing case

`target NAME load CASE` replaces the world's timeline with that case's stimuli (undo
brings the old timeline back). Then the whole toolbox works on exactly that run: `run`,
`waves`, `show`, `why`, `trace`, `step`.

## 10. Workflows

### 10.1 Build and test a contraption

The script `examples/cli/and_gate.cli.txt` (run it with
`redsim-cli and.redsim.json new; redsim-cli and.redsim.json < examples/cli/and_gate.cli.txt`):

```
fill 0 1 0 0 1 2 stone
place 0 2 0 redstone_torch
place 0 2 2 redstone_torch
place -1 1 0 lever face=wall facing=west
place -1 1 2 lever face=wall facing=west
place 1 1 1 stone
place 0 2 1 redstone_wire
place 1 2 1 redstone_wire
place 2 2 1 stone
place 3 2 1 redstone_wall_torch facing=east
place 4 1 1 stone
place 4 2 1 redstone_lamp
settle                              # let the torches react: that state is the build
label A -1 1 0 "input A (lever)"
label B -1 1 2 "input B (lever)"
label OUT 4 2 1 "output (lamp)"
note "AND gate: @OUT lights when both levers @A and @B are on (3 ticks later)"
target new and "the lamp is on only when both levers are on"
target and truth @A @B -> @OUT rows 00:0 01:0 10:0 11:1
check
show
```

The steps, as a habit:

1. **Write down what it must do first**: label the inputs and outputs, write the target.
   `check` fails until the contraption works.
2. **Build** with `place` (components) and `fill`/`set` (structure). Read every output
   line: it says what state the block really got.
3. **`settle`**, then **`show`** to see it, **`check`** to test it.
4. When a case fails: `target NAME load CASE`, `waves`, `why` the output, `inspect` the
   blocks along the path, `step` through the tick where it goes wrong.
5. **Leave it readable**: labels, a `note` saying what it is and how to use it.

### 10.2 Find out why something does not work

1. `show` (and `show power`) at the moment it should work (`at T show y=…`).
2. `waves` the input, the output and a few blocks along the way: where does the signal
   stop?
3. `inspect` the last block that has the signal and the first that does not: does the
   second *receive* anything, from which side? A repeater facing the wrong way receives
   nothing from the side it should; a torch on the wrong block inverts the wrong signal.
4. `why` the block that should have changed (or that changed wrongly).
5. `step` through the tick where it goes wrong to see the order of updates.

### 10.3 Timing

Clocks, pulse lengths and delays: `run` far enough, then `waves` (one column per tick)
and `changes`. Express the timing in a target (`expect @OUT powered=true within 2..7`,
`expect @OUT lit=false during 12..20`) so it stays checked.

### 10.4 Sequences

Piston doors and other sequences need inputs at chosen ticks: record them on the
timeline (`at 3 use @L`, `at 10 use @L`, or `pulse @IN at 2 for 4`), `run`, and read
`changes` of the moving blocks. `edits` lists the timeline, `edit move E2 to 15` changes
it. `examples/cli/piston_door.cli.txt` is a small example.

### 10.5 Handing a world over

A person: `redsim WORLD` opens it in the editor with everything. An agent: `info`,
`notes`, `labels`, `targets`, `log`, then `check` to see what works.

## 11. Output for programs: `--json`

With `--json` each command prints exactly one line of JSON:

```json
{"command": "place 0 1 0 stone", "ok": true, "data": {"pos": [0, 1, 0], "state": "stone", "tick": 0}}
{"command": "place 0 1 0 stone", "ok": false, "error": "place: 0 1 0 holds stone; break it first or use set"}
```

`command` is the command as it ran, `ok` whether it worked, `data` its result (fields per
command: [[cli-reference]], "JSON data" under each command) or `error` the message.
Positions are `[x, y, z]`, states are strings as in text output, ticks count from the
build. Text and JSON contain the same facts; agents that read text well can use text.

## 12. Exchanging builds with Minecraft

- `export FILE [from POS POS]` writes the build (default: everything above the floor) as
  `.litematic` (Litematica), `.schem` (WorldEdit) or `.nbt` (structure blocks and
  `/place template`), block-entity data included.
- `import FILE at POS [rotate N] [mirror x|z]` pastes one of those files.
- `open-save SAVE [center X Z] [radius R]` makes the world from a Minecraft Java save
  (the chunks around the player, or around block X Z); `export-save TARGET` writes the
  world back into a **copy** of that save (the original is never changed).

Everything the simulator does not model comes in as inert foreign blocks and is listed;
see [[world-import]] and [[differences]].

## 13. Rules and pitfalls

- **Building commands change the build, not the moment you are looking at.** Use `at T`
  to record an edit during a run.
- **`settle` after building**, before testing or reading results.
- **`place` for components, `set` for structure.** `set` does not apply placement rules:
  a lamp set next to power stays off until something updates it.
- **Facing**: repeaters, comparators and observers face their input (write `out=`);
  wall torches face away from their wall.
- **Wire needs a block below**, torches and levers a block to stand on or hang from;
  `place` tells you which.
- A **pulse** powers the position itself (as if a redstone block were next to it), not
  what is around a lever: to switch a lever, `use` it.
- **Ticks are game ticks.** A repeater's delay 1 is 2 game ticks; a lamp turns off 4
  ticks after losing power; a torch reacts after 2.
- Read the **legend** under each map; letters are only fixed for redstone components.
- What the simulator does not do (water, items, mobs, random outcomes) is in
  [[differences]]; designs relying on those cannot be tested here.

## 14. Glossary

- **Build**: the contraption at tick 0; building commands change it.
- **Timeline**: edits recorded at ticks and power pulses, replayed every run.
- **View**: the tick inspection commands look at.
- **Tick**: one game tick (1/20 s); a redstone tick is 2.
- **Engine step**: one action inside a tick (a scheduled tick, a block event, …).
- **Label**: a name for a position (`@NAME`).
- **Target / case / expectation**: an acceptance test; one run of it; one condition
  checked at given ticks.
- **Pulse**: editor power on a position for some ticks.
- **Direct signal**: the part of a signal that powers a solid block it goes into.
- **Foreign block**: a block the simulator keeps but does not simulate.
