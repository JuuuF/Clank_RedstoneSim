# Guided tour of the example world

How to open it:

```sh
conda activate redsim
redsim examples/showcase.redsim.json     # or: python -m redsim examples/showcase.redsim.json
```

Or File → Open… → Simulation worlds → showcase. New to the editor? **Help → Tutorial**
first ([[tutorial]]).

The world has eight districts on a grass field, each on its own stone square with a sign
naming it. The camera opens over district A, looking south. In every district each row is
one station: the input on the left (east), the output on the right (west), and a sign at
the input end saying what to try. Blue outlines mark inputs, green outputs, orange
processing parts, purple clocks; white boxes are groups. **Circuit → Groups** lists all
44 stations (A1 … G3); a double click takes the camera there.

```
          (camera, looking south)
   A Basics   B Logic   C Strength   D Pistons      ← north row
   E Items    F Clocks  G Sequences  H Sandbox      ← south row
```

Regenerate the file with `PYTHONPATH=src python -m tools.make_examples`
(`tools/make_examples.py`; `tests/editor/test_examples.py` checks every station).

## A · Basics

Lever and lamp, inverter, dust into a delay-4 repeater, torch AND gate, comparator in
subtract mode (a barrel source of 14 minus a side lever), sticky piston, 1×2 piston door
(the bottom piston is quasi-connected), and the torch burnout loop (press P: it flickers,
burns out after 8 turn-offs and stays out until a block is placed next to it).

## B · Logic and memory

OR gate; repeater lock (flip the front lever to lock: the lamp holds its state); copper
bulb T flip-flop (each button press toggles it, a comparator reads it); observer chain
(an observer watches the lever, each observer the next: the pulse runs down the line);
stone versus wooden buttons (20 and 30 ticks); a torch tower (2 ticks per torch up to the
lamp on top); pressure plates (Inspector → **Step on it**; the weighted plate gives one
per entity); a target block (Inspector → **Arrow**); a note block with an observer
(right-click it: the next note is a state change the observer sees).

## C · Signal strength

Six signal sources read by comparators into 13 blocks of dust: barrel 15, lectern 9,
cake 14, composter 6, hopper 3 and chest 8. Turn on the heat view (**Alt+H**) or the
debug screen (**F3**) to see the strength fall by one per block; only the barrel's ruler
reaches its lamp. Then a lever with 15 dust (power 1 still lights the lamp) and a
comparator reading a barrel through a solid block. Change any source in the inspector.

## D · Pistons

Push limit (12 planks move), slime and honey in the air (the slime block drags the
stone on top and beside it, not the honey block), a piston moving a redstone block next
to a lamp, a budded piston (powered from above: place any block beside it and it
extends), an observer watching a piston extend, 12 powered rails (power reaches 8 rails
past the powered one) and a rail junction that switches when powered.

## E · Items

Press P and watch items move: a dropper (one item per button press) into a hopper and
a chest; a barrel feeding a chain of three hoppers into a second barrel (comparators on
both sides, lamps showing contents); a hopper that stops when its lever powers it; a
double chest read the same from both halves; a composter at level 7 that becomes ready
20 ticks later and is emptied by the hopper below.

## F · Clocks

Repeater delays 1 to 4 from one lever (the lamps light one after another); an observer
clock (two observers watching each other; the dust behind them shows each pulse); a
repeater loop started by a button, with lamps in the floor under its corners; a hopper
clock passing one item back and forth.

The red lights on firing observers (top and output face, fading out right after the
pulse) are the editor's; the game only shows the red dot on the back texture.

## G · Sequences

This district has a recorded history: press P from tick 0 and watch.

- **Pulses (ANIMATE mode):** eight lamps lit one after another, twice (timeline group
  "Chaser"); a sticky piston gets a 0-tick pulse at tick 20 (it spits its planks) and a
  10-tick pulse at tick 40 (it pulls them back).
- **Keyframes:** the lever is flipped at tick 30 and 70 (the *Used* row), the repeater's
  delay is changed to 4 at tick 50 (*Changed*: the lamp now goes out 8 ticks after the
  lever, not 2), a redstone block is placed at tick 90 and removed at 110 (*Placed*,
  *Removed*).
- Named **markers** on the ruler mark each of these; three **monitor tracks** (the first
  chaser lamp, the piston, the keyframe lamp) show their values per tick.
- ↑/↓ jump between edits; drag diamonds or pulse bars to move them; Ctrl+Z undoes.

The world also holds three prefabs (Circuit → Prefabs: AND gate, T flip-flop, repeater
lock) to paste anywhere.

## H · Sandbox

An empty square to build on.

## Looking under the hood

- **Why?** Select a lamp, open Diagnostics → Why?: the chain of causes back to the lever.
- **Step event** (Ctrl+→) runs one engine step; Diagnostics → Last step trace lists
  every update it caused.
- **F** over any coordinates (a timeline line or diamond, a monitor track, a Diagnostics
  row) takes the camera to that block.

All controls: [[controls]].
