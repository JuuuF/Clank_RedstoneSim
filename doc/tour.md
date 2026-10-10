# Guided tour of the example world

How to open it:

```sh
conda activate redsim
redsim examples/showcase.redsim.json     # or: python -m redsim examples/showcase.redsim.json
```

The camera opens looking south over eight circuits, one per row. Inputs are on the left,
outputs on the right. Blue outlines mark inputs, green outlines outputs, orange the
processing parts, purple the clock, and white boxes are groups. Fly with WASD, Space and
Shift; hold the right mouse button and drag to look around.

## Things to try

1. **Lever and lamp (front row).** Right-click the lever: the lamp lights at once. Flip it
   back, then press **T** (step one tick) four times. The lamp turns off on the 4th tick,
   matching the game ([[experiments/index]] EXP-001).
2. **Inverter.** The lamp starts lit (torch on). Flip the lever and step ticks: the torch goes
   out after 2 ticks, then the lamp after 4 more.
3. **Dust and repeater (delay 4).** Flip the lever: the dust lights instantly, and the lamp
   follows after 8 ticks. Right-click the repeater to change its delay.
4. **AND gate.** The lamp only lights when both levers are on.
5. **Comparator (subtract).** The cake behind it gives 14. Flip the side lever: the side
   input becomes 14, so the output drops to 0. Right-click the cake to eat a slice and
   watch the values change. Ctrl+click the comparator to see its stored output in the
   inspector.
6. **Sliding block.** Flip the lever: the sticky piston pushes the planks, and pulls them
   back when switched off.
7. **Piston door.** One lever opens both pistons: the bottom one is powered by
   quasi-connectivity ([[mechanics/pistons]]).
8. **Torch burnout loop.** Press **P** to run. The torch flickers, burns out after 8
   turn-offs, and stays out ([[quirks]] Q-TORCH-BURNOUT-STUCK). Place a block next to it to
   wake it up.

## Looking under the hood

- **Step event (E)** runs one engine step at a time. The **Diagnostics** panel shows the
  pending scheduled ticks and, under "Last step trace", every neighbor update and block
  change that step caused.
- **Rewind:** Shift+T (tick back), Shift+E (step back), or drag the timeline slider. Replay
  is exact.
- **Contraptions → Groups** lists each circuit's ports with live values. Double-click an
  input port to flip its lever.
- **Copy a circuit:** press B on two opposite corners, Ctrl+C, point somewhere else and
  press Ctrl+V. Press R to rotate the clipboard first.
- Ctrl+Z undoes the last edit (it rewinds to just before it).

Regenerate the file with `python -m tools.make_examples`.
