# Guided tour of the example world

How to open it:

```sh
conda activate redsim
redsim examples/showcase.redsim.json     # or: python -m redsim examples/showcase.redsim.json
```

The camera opens looking south over eight circuits, one per row. Inputs are on the left,
outputs on the right. Blue outlines mark inputs, green outlines outputs, orange the
processing parts, purple the clock, and white boxes are groups. Middle-drag orbits around
the orange pivot, Shift+middle-drag pans, the wheel zooms and Ctrl+wheel moves the pivot up
and down. You start in NORMAL mode: right click uses levers, left click inspects. All
controls: [[controls]].

## Things to try

1. **Lever and lamp (front row).** Right-click the lever: the lamp lights at once. Flip it
   back, then press **T** (step one tick) four times. The lamp turns off on the 4th tick,
   matching the game ([[experiments/index]] EXP-001).
2. **Inverter.** The lamp starts lit (torch on). Flip the lever and step ticks: the torch goes
   out after 2 ticks, then the lamp after 4 more.
3. **Dust and repeater (delay 4).** Flip the lever: the dust lights instantly, and the lamp
   follows after 8 ticks. Right-click the repeater to change its delay.
4. **AND gate.** The lamp only lights when both levers are on.
5. **Comparator (subtract).** The barrel behind it is a signal source giving 14 (it holds
   1 605 redstone dust). Flip the side lever: the side input becomes 14, so the output
   drops to 0. Left-click the barrel to change its strength or swap it for a lectern or
   a cake in the inspector. Left-click the comparator to see its stored output in the
   inspector.
6. **Sliding block.** Flip the lever: the sticky piston pushes the planks, and pulls them
   back when switched off.
7. **Piston door.** One lever opens both pistons: the bottom one is powered by
   quasi-connectivity ([[mechanics/pistons]]).
8. **Torch burnout loop.** Press **P** to run. The torch flickers, burns out after 8
   turn-offs, and stays out ([[quirks]] Q-TORCH-BURNOUT-STUCK). Place a block next to it to
   wake it up.

The top-left corner of the viewport shows whether the simulation runs, the achieved ticks
per second and frames per second. It should hold the target rate (20 by default).

## Looking under the hood

- **Step event (E)** runs one engine step at a time. The **Diagnostics** panel shows the
  pending scheduled ticks and, under "Last step trace", every neighbor update and block
  change that step caused.
- **Rewind:** ← (tick back), Shift+← (step back), or drag the timeline slider. Replay is
  exact. → steps a tick forward, Shift+→ one event.
- **Contraptions → Groups** lists each circuit's ports with live values. Double-click an
  input port to flip its lever.
- **Copy a circuit:** press V (SELECT mode), drag a box over the circuit, then Ctrl+drag
  from inside the box to drop a copy elsewhere. Or Ctrl+C, then Ctrl+V shows a preview at
  the cursor (R rotates it) and a left click places it. Plain drag from inside the box
  moves the circuit; drag a face handle to resize the box.
- **Build:** press B (or pick a block in the inventory with 1–9): left click breaks, right click places where the
  white outline shows.
- Ctrl+Z undoes the last edit (it rewinds to just before it).

Regenerate the file with `python -m tools.make_examples`.
