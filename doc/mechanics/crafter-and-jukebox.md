# Crafters and jukeboxes

Ported in `world/blocks/crafter.py` (`CrafterBlock`, `CrafterBlockEntity`) and
`world/blocks/jukebox.py` (`JukeboxBlock`, `JukeboxBlockEntity`, `JukeboxSongPlayer`).
Verified on the real 26.3 server: EXP-067 (`crafters_jukeboxes`), and inside Nile's 5x5 vault
door and LegDen's 7x7 and 8x8 piston doors (EXP-068). Detector rails, the third block those
doors needed, are on [[rails]].

## Crafters

`crafter[orientation=…, triggered, crafting]`; `orientation` is a `FrontAndTop` (12 values
such as `north_up`, `up_east`). A full block: it conducts; a block entity: pistons cannot
move it.

- **Power:** when a neighbor update finds it powered and it is not `triggered`, it becomes
  `triggered` with flags 2 (shape updates, so an **observer watching it fires**, but no
  neighbor updates) and tries to craft 4 ticks later; when power goes, it becomes
  untriggered (and not `crafting`) the same way. Doors use this as a power-to-observer
  converter (EXP-067: each change pulses the observer's lamp).
- **Comparator:** the number of slots that hold an item or are disabled (EXP-067: 2 items
  and 2 disabled slots read 4). A slot can only be disabled while empty; putting an item in
  a disabled slot enables it.
- **Crafting:** not simulated (no recipe data). In the game a crafter whose grid matches a
  recipe crafts on that attempt: it pushes the result out of its front, uses up one item
  per filled slot and is `crafting` for 6 ticks. The simulator always fails the attempt,
  which is exact for an empty grid or one that matches no recipe (the game then only plays
  a sound). See [[differences]].
- Hoppers and droppers leave crafters alone in the simulator (the game fills them one item
  at a time, evenly). The `container` command and the editor's slots fill them.

## Jukeboxes

`jukebox[has_record]`, a full block (conducts) with a block entity (immovable).

- **Always a signal source**, so redstone wire next to it always connects to it (EXP-067),
  which doors use to point wire; while a song plays it gives 15 to every side.
- **Comparator:** the disc's value (`JukeboxSongs`: 13 → 1 … 5 → 15, playing or not); 0
  when empty.
- **Discs:** put one in with `container POS 0 music_disc_cat 1` (`/item replace`): `has_record`
  turns on (flags 2), the song starts (neighbor and comparator updates). A song stops
  `ceil(length · 20) + 20` ticks after it started (EXP-067: a jukebox saved 10 ticks before
  the end of 11 turns its wire off then). Using it with an empty hand ejects the disc (the
  item is not simulated). A saved disc keeps playing only if `ticks_since_song_started` is
  saved with it.
- Hoppers and droppers leave jukeboxes alone in the simulator (in the game they insert and
  take discs).
