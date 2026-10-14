# Tutorial

**Help → Tutorial** opens the tutorial world and a card at the top right of the view
that teaches the simulator in nine short lessons. Each step says what to do; the card
notices when it is done ("✔ Done!") and moves on. **Next** skips a step, **Back** goes
back, **Lessons** jumps to any lesson, × closes the card. Help → Tutorial continues
where you stopped (progress: `tutorial.json` in the config folder, next to
`preferences.json`). The card is drawn like the game's own tutorial hints (the
`toast/tutorial` sprite and its icons, read from the jar).

The tutorial world is built fresh each time (an untitled document; your files are never
touched): nine stations on stone squares, one per lesson, each with signs. When a lesson
starts, the camera glides to its station. Key names in the card come from your keymap,
so rebound keys show as you bound them.

After the tutorial, the showcase ([[tour]]) has 44 working stations.

## The lessons

This list is generated from `src/redsim/tutorial/lessons.py` (default keys shown).

### 1. Look around

1. **Welcome!** *(read, then Next)*: This card teaches the simulator one step at a time. It notices when you have done what a step asks and moves on by itself; **Next** skips a step, **Lessons** jumps to any lesson. Each lesson has its own station in this tutorial world, with signs. Nothing here touches your files.
2. **Orbit**: Drag with **Middle Drag** to turn the camera around the orange pivot.
3. **Zoom**: Turn the mouse wheel (**Wheel**) to zoom in and out.
4. **Move**: Move the pivot: drag with **Shift+Middle Drag**, or hold **W** **A** **S** **D**.
5. **Focus**: Point at the lit lamp and press **F**: the pivot moves to it, and the camera turns around it from now on.

### 2. Use and inspect

1. **NORMAL mode**: You are in **NORMAL** mode (the badge at the bottom left; **Esc** gets you back here from any mode). Right-click (**Right Click**) the lever in the front row: the lamp lights at once.
2. **Inspect**: Left-click (**Left Click**) the lamp. The **Inspector** tab on the right shows its state and lets you change every property.
3. **Block popup**: Point at the repeater in the back row and press **E**: the same inspector opens next to the cursor.
4. **Change the delay**: Right-click the repeater (or use the arrows in the popup) to change its delay. Every change is one undo step.

### 3. Time

1. **Run and pause**: Press **Space** to run the simulation (20 ticks a second, like the game) and press it again to pause.
2. **Step tick by tick**: Flip the lever of this station, then press **Right** a few times: the dust lights at once, the lamp after the repeater's 4 game ticks.
3. **Rewind**: Press **Left** to step back. The history replays exactly, so you can go back and forth as often as you like.
4. **Tick 0 is the build**: Press **Shift+Left** to jump to tick 0, the build. Edits at tick 0 change the build itself; edits later in time are recorded on the timeline.
5. **Scrub the timeline**: Click or drag on the timeline's ruler (below the view) to jump to any recorded tick.

### 4. Build

1. **BUILD mode**: Press **B** for **BUILD** mode. The hotbar appears at the bottom. (Holding **Tab** shows a ring with every mode.)
2. **Choose redstone dust**: Press the number key of the **Redstone** folder, then the number of **Redstone Dust**. Or search: **Ctrl+Space**, type “dust”, Enter.
3. **Place a line**: On the white square, drag with the left mouse button from the lever towards the lamp: a line of dust, placed as one edit.
4. **Make it work**: Fill any gaps until the dust reaches the lamp, then flip the lever (**Ctrl+Right Click** in BUILD mode). The lamp lights up.
5. **Remove a block**: Right-click (**Right Click**) a block in BUILD mode to remove it.
6. **Turn a block**: Place a repeater, then point at it and press **Q** to turn it.
7. **Undo**: Press **Ctrl+Z** to undo the last edit (**Ctrl+Y** redoes it). Edit → Undo History goes back several steps at once.
8. **The build layer**: New blocks go on the layer at the pivot's height (the grid around the cursor). **Shift+Wheel** moves the layer up or down a block, for building in the air.

### 5. Select, copy and paste

1. **SELECT mode**: Press **V** for **SELECT** mode.
2. **Draw a box**: Drag across the inverter (the lever, the block with the torch and the lamp) to put a box around it. Drag a face's arrow to resize the box.
3. **Copy it**: Hold Ctrl and drag from inside the box to drop a copy beside it. (Or **Ctrl+C**, then **Ctrl+V** and a click to place.)
4. **Turn and flip**: Press **R** to turn the box's contents, **H** to flip them. Levers, torches and dust turn with them.
5. **Several boxes**: Hold Shift and drag somewhere else to draw a second box: moving, copying, turning and flipping act on all boxes together.
6. **Delete**: Press **Del** to clear the boxes (it fills them with air).

### 6. Sequences and the timeline

1. **Edits in time**: Run the simulation (**Space**), flip this station's lever while it runs, then pause. The flip is recorded: a yellow diamond in the timeline's **Used** row. Drag diamonds to move edits in time.
2. **ANIMATE mode**: Press **K** for **ANIMATE** mode: clicks power a position from the current tick on.
3. **Add a pulse**: Scrub to a tick on the timeline and click one of the lamps: it gets a pulse (strength and duration come from the **Sequence** tab). The **Powered** row shows it as a bar.
4. **A 0-tick pulse**: In the Sequence tab set the duration to 0, scrub to another tick and click the sticky piston: power on and off inside one tick.
5. **Watch it**: Jump to tick 0 (**Shift+Left**) and run: the 0-tick pulse makes the piston spit its block instead of pulling it back.

### 7. See inside

1. **Debug screen**: Press **F3** for the debug screen: signal values on the blocks, and details of the block under the cursor on the right.
2. **Heat view**: Press **Alt+H**: powered blocks glow from dark red (strength 1) to yellow (15). Watch the dust lose one per block.
3. **X-ray**: Press **Alt+Z** (again for more, a third time for off): building blocks turn see-through.
4. **Signal sources**: Left-click the barrel and change its **strength** in the inspector: the comparator follows. Barrels, lecterns, cakes, composters, hoppers and chests can all be sources.
5. **Why did this change?**: Flip the back lever, left-click the lamp at the end of that row and open **Diagnostics → Why?**: the chain of causes back to the lever.
6. **Monitor tracks**: In the Inspector, press **Monitor**: the block gets a track on the timeline, like a logic analyzer.

### 8. Organize

1. **Sections**: Inspect the lever and choose a **Section** in the inspector (input, output, …): it gets a colored outline. Sections are notes; they never change the simulation.
2. **Groups**: Draw a box around this station (SELECT mode), open **Circuit → Groups** and press **Group selection…**. Ports show live values; a double click on a group takes the camera there.
3. **Prefabs**: With the box still there, open **Circuit → Prefabs** and press **Save selection…**: a reusable piece, kept with the world.
4. **Signs**: Place a sign (inventory folder **Special**) and type its text in the inspector.
5. **Markers**: Press **Ctrl+M** to name the current tick: a marker on the timeline.

### 9. Files and worlds

1. **Save and open** *(read, then Next)*: **Ctrl+S** saves a world as a **.redsim.json** file, with its timeline and notes. **Ctrl+O** shows the **Select World** screen with your recent worlds and the examples.
2. **Minecraft worlds** *(read, then Next)*: File → **Open Minecraft world…** opens a Java 26.3 save; chunks load around the camera. **Builds in this world…** finds the redstone in it, **Save as Minecraft world…** writes a copy you can open in the game.
3. **Schematics** *(read, then Next)*: **Region → Import schematic…** reads Litematica, WorldEdit and structure files; **Export selection as schematic…** writes them.
4. **Make it yours** *(read, then Next)*: **Settings → Keymap…** changes any key, **Preferences** the look. **F1** lists every key; the hint bar at the bottom shows the ones that matter right now.
5. **Done!** *(read, then Next)*: That's everything. Open the **showcase** (File → Open…, Simulation worlds) for 44 working stations: logic, signal strength, pistons, items, clocks and a recorded sequence.

## How it works (for developers)

- `redsim/tutorial/world.py`: the tutorial world (`build()`), station origins
  (`STATIONS`, `station(index, pos)`) and the positions lessons check.
- `redsim/tutorial/lessons.py`: `LESSONS` (title, station, steps); a `Step` has a text
  (`{key:action.id}` shows the user's binding as a keycap, `{cap:…}` a keycap as written),
  an optional check and an optional camera target. Checks are plain functions of a
  `Snapshot` (mode, tick, running, inspected block, selection boxes, camera, view flags,
  side tab, chosen block, undo labels) and the step's `memo`; Qt-free, so
  `tests/tutorial/test_lessons.py` plays the whole tutorial through with document
  operations and checks that every step notices, and not before it is done.
- `redsim/editor/builder.py`: the `Builder` both the tutorial world and the showcase are
  built with (player-like placement, `/setblock` with block-entity data, signs, groups,
  `settle()` to make the settled state tick 0, `set_later()` for changes that should
  start when the world runs).
- `redsim/ui/tutorial_card.py` (the card) and `redsim/ui/window_tutorial.py` (Help →
  Tutorial, the snapshots, polled with the hint bar every 120 ms).

Adding a lesson: a station builder in `world.py` (append to `_BUILDERS` and `STATIONS`),
a `Lesson` in `LESSONS`, its actions in the play-through test, and an icon in
`tutorial_card.ICONS`.
