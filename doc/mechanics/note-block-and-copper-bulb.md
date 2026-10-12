# Note blocks and copper bulbs

## Note block (`NoteBlock.java`)

- Properties `instrument` (27 values, `NoteBlockInstrument`), `note` 0–24, `powered`.
- `neighborChanged` L81: `powered` follows `hasNeighborSignal`; on a rising signal it plays
  first (a block event `blockEvent(pos, this, 0, 0)`), then `setBlockAndUpdate` (flags 3).
- It plays only with air above, unless the instrument is a mob head's (`worksAboveNoteBlock`).
- Instrument: a mob head above wins, else the instrument of the block below
  (`setInstrument` L47), refreshed by `updateShape` from above/below. Every block's
  instrument comes from `Blocks.java` (`BlockBehaviour.Properties.instrument`), extracted by
  `tools/extract_instruments.py` into `world/instruments.py` (707 blocks; copper blocks
  have trumpet stages).
- Using it (right click) cycles `note` (24 → 0) and plays. Placing resets the note to 0.
- Not simulated: sound, particles, the `NOTE_BLOCK_PLAY` game event (sculk sensors).

Status: implemented (`world/blocks/note_block.py`). Tests: `tests/sim/test_note_block.py`;
game EXP-042 (`note_blocks`).

## Copper bulb (`CopperBulbBlock.java`)

- Properties `lit`, `powered`. `checkAndFlip` L29 (from `onPlace` when the block type
  changes, and `neighborChanged`): if the signal differs from `powered`, a rising signal
  toggles `lit`; `setBlockAndUpdate` with `powered = signal`. A T flip-flop.
- Comparator output 15 while lit (re-reads the block at its position). Never a conductor.
- All 8 bulbs (4 weathering stages, waxed or not) behave the same; oxidation needs random
  ticks (off).

Status: implemented (`world/blocks/copper_bulb.py`). Tests: `tests/sim/test_copper_bulb.py`;
game EXP-043 (`copper_bulbs`).
