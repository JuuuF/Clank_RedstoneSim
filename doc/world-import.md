# Opening Minecraft worlds (design)

Owner request (round 8, 2026-10-12): open Minecraft worlds, e.g. the example save in
`data/minecraft_saves/Redstone/`. Do not load everything at once; load chunks around the
player like the game; keep an own fast format, keyed by the save folder (and seed); write
changes back into the game's format.

## What a 26.3 save looks like (measured on the example)

- `level.dat`: gzipped NBT. `Data.LevelName`, `DataVersion` 5023, `Time`, `spawn`
  (`pos`, `dimension`). The seed moved to `data/minecraft/world_gen_settings.dat`
  (`data.seed`, plus the flat-world layers).
- Player position: `players/data/<uuid>.dat` (`Pos`, `Rotation`, `Dimension`).
- Chunks: `dimensions/minecraft/overworld/region/r.X.Z.mca` (moved there in 26.x; the old
  `region/` at the top level is gone), 32×32 chunks per file, zlib-compressed NBT in
  4 KiB sectors. Each chunk: `sections` (16³ blocks each, `Y` index), `block_entities`,
  `block_ticks`, `fluid_ticks`, `Status`, `LastUpdate`.
- Section palettes in 26.x mix three entry forms: bare id strings (`"minecraft:air"`),
  `{"": id}` and `{"id", "properties"}` (older: `{"Name", "Properties"}`). All are read.
- Example world: 12 regions (12 288 chunks), a flat world of bedrock, stone and 116
  layers of quartz (y −64 … 55), and 1 042 non-terrain blocks in one 79×48×70 box
  (glass, dust, observers, pistons, repeaters, lamps, note blocks, signs, …).
- Speed (pure Python): decoding a full chunk ~10 ms; scanning the palettes of all
  12 288 chunks ~2 s, so finding where the builds are is cheap.

## Design

**Read, never touch.** The save is opened read-only. The game must not be running for
write-back (check `session.lock`); write-back goes to a copy first (`<name> (redsim)`), or
in place only after an explicit choice, with a backup of each region file it changes.

**Load around a point, like the game.** `mcworld.World` opens the save (level.dat, seed,
player position) and reads chunks on demand from their region files (header read once,
chunks by sector). The editor imports the chunks within a radius (default 4 chunks) of
the player, or of a chosen point; later, as the camera moves, further chunks stream in
(the game's view distance), and far ones are dropped if unchanged.

**Index first.** A scan of the palettes (no full decode) finds the chunks and sections
holding anything but terrain ("interesting" sections) and their bounding boxes. Opening
a world can then offer "go to the builds" instead of landing in a sea of quartz, and
only sections that matter are decoded fully.

**Do not import buried terrain.** A flat world holds millions of hidden blocks. Imported
are: every non-terrain block; terrain within 13 blocks of a non-terrain block (a piston
moves at most 12, so everything a contraption can touch is there); and elsewhere only
terrain with an exposed face (the surface the camera sees). Terrain = plain full cubes
that redstone cannot change (stone, quartz, bedrock, …).

**Unknown blocks stay what they are.** Blocks the simulator does not model yet (signs,
note blocks, stairs, leaves, copper bulbs, …) are imported as *foreign* blocks: they
keep their exact state text, are drawn with the game's model, are listed after the import
("not simulated: …"), and behave inertly: full-cube models as solid conductors, others as
non-solid. Writing back restores their original state untouched.

**Own fast format (cache).** Per save, in `~/.cache/redsim/worlds/<hash of the save
path>-<seed>/`: the index (interesting sections, bounds) and decoded chunks as compact
arrays (palette + uint16 indices, gzipped), each tagged with its region file's chunk
timestamp. A chunk is re-read from the save only when its timestamp changed (the game
saved it since). With ~10 ms per chunk the cache matters for large areas and the index.

**Writing back.** Only chunks with edits are rewritten: their original NBT is kept and
only the changed sections get a new palette and packed data; block entities of changed
positions are replaced; `LastUpdate` and the region header timestamp are updated; region
files are rewritten with fresh sector allocation. Scheduled ticks and moving pistons at
the moment of writing are stored the way the game stores them (`block_ticks`,
`minecraft:piston` block entities) or the write is refused while they are pending.

## Phases

1. **Done first:** NBT reader/writer (byte-exact round trip of `level.dat`), region
   reader, section decoding (all palette forms), whole-world palette scan.
2. **Done:** File → Open Minecraft world… imports the chunks within 4 of the player into a
   document (terrain rules above; foreign blocks drawn with their real textures; block
   entities from their NBT; pending block ticks), the camera at the player's eyes. The
   example opens in ~3.7 s: 69 chunks, 81 741 blocks kept, 2 032 865 buried terrain blocks
   left out (whole one-block terrain sections are skipped without decoding). The status
   line lists what is approximated (note blocks, signs, stairs, leaves, copper bulbs, …).
3. **Streaming done (2026-10-12):** `mcworld.stream.WorldStream` keeps every loaded
   section compactly (a one-block section as its text, others as palette + uint16
   indices, decoded with numpy) and decides per section, on the section and a one-block
   rim of its 26 neighbors, which blocks enter the document (rules above; terrain touching
   a build by a face, edge or corner; the bottom of the world never shows). A block at the
   edge of the loaded area waits until its neighbor chunk is known, and loading a chunk
   re-checks the 8 chunks around it, so the result does not depend on the load order
   (tested). The example's first area (radius 4) now opens in ~1 s (was 3.7 s) with the
   same blocks minus the bedrock floor's underside; further chunks take ~9 ms each.
   The editor loads the nearest missing chunks around the camera every 60 ms for at most
   25 ms (`MainWindow._stream_world`), up to the view distance (Preferences → Minecraft
   worlds, default 8 chunks). New blocks join the current level, every keyframe and every
   undo base (`Document.add_world_blocks`), without updates; positions a level already
   has are kept. The chunked mesh follows the level's touched positions
   (`Level.take_touched`) instead of diffing all blocks per frame, and the timeline keeps
   fewer periodic keyframes for large levels (6 M block entries in all).
   Left for this phase: the index and "go to the builds", the on-disk cache.
4. Write back (copy first), with a round-trip test: import → export → import is
   identical, and untouched chunks are byte-identical.
