"""Note block: ``net/minecraft/world/level/block/NoteBlock.java``.

It tracks ``powered``, plays (a block event, ``blockEvent(pos, this, 0, 0)``) on a rising
signal or a player's use, and takes its instrument from the block above (mob heads) or
below. Sound, particles and the ``NOTE_BLOCK_PLAY`` game event (only sculk sensors hear
it, which are not simulated) have no effect here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.direction import Direction
from redsim.core.pos import Pos, above, below
from redsim.world.block import Block, BlockState, PlacementContext
from redsim.world.properties import POWERED, Property, integer

if TYPE_CHECKING:
    from redsim.sim.level import Level

#: ``NoteBlockInstrument`` in declaration order (``BlockStateProperties.NOTEBLOCK_INSTRUMENT``).
INSTRUMENT_VALUES = (
    "harp", "basedrum", "snare", "hat", "bass", "flute", "bell", "guitar", "chime",
    "xylophone", "iron_xylophone", "cow_bell", "didgeridoo", "bit", "banjo", "pling",
    "trumpet", "trumpet_exposed", "trumpet_oxidized", "trumpet_weathered", "zombie",
    "skeleton", "creeper", "dragon", "wither_skeleton", "piglin", "custom_head",
)  # fmt: skip
#: ``Type.MOB_HEAD`` and ``Type.CUSTOM``: these work only from above the note block.
ABOVE_ONLY = frozenset(INSTRUMENT_VALUES[20:])
INSTRUMENT = Property("instrument", INSTRUMENT_VALUES)
NOTE = integer("note", 0, 24)


def works_above(instrument: str) -> bool:
    """``NoteBlockInstrument.worksAboveNoteBlock``."""
    return instrument in ABOVE_ONLY


class NoteBlock(Block):
    properties = (INSTRUMENT, NOTE, POWERED)

    def __init__(self) -> None:
        super().__init__("minecraft:note_block", destroy_speed=0.8)
        self.register_default_state(
            self.default_state.with_(INSTRUMENT, "harp").with_(NOTE, 0).with_(POWERED, False)
        )

    def _set_instrument(self, level: Level, pos: Pos, state: BlockState) -> BlockState:
        """``setInstrument`` L47: a mob head above wins, else the block below (a head
        below counts as a plain harp)."""
        on_top = level.get_block_state(above(pos)).block.instrument
        if works_above(on_top):
            return state.with_(INSTRUMENT, on_top)
        under = level.get_block_state(below(pos)).block.instrument
        return state.with_(INSTRUMENT, "harp" if works_above(under) else under)

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement`` L59: from the default state (the note resets to 0)."""
        return self._set_instrument(ctx.level, ctx.pos, self.default_state)

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        """``updateShape`` L64: blocks above and below set the instrument."""
        if direction in (Direction.UP, Direction.DOWN):
            return self._set_instrument(level, pos, state)
        return state

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        """``neighborChanged`` L81: a rising signal plays the note before ``powered`` is
        set (``setBlockAndUpdate``, flags 3)."""
        signal = level.has_neighbor_signal(pos)
        if signal != state.get(POWERED):
            if signal:
                self._play_note(state, level, pos)
            level.set_block_and_update(pos, state.with_(POWERED, signal))

    def _play_note(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``playNote`` L94: only with air above, unless the instrument is a head's."""
        if works_above(state.get(INSTRUMENT)) or level.get_block_state(above(pos)).is_air:
            level.block_event(pos, self, 0, 0)

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``useWithoutItem`` L117: tune one step up (24 wraps to 0), then play."""
        state = state.cycle(NOTE)
        level.set_block_and_update(pos, state)
        self._play_note(state, level, pos)
        return True

    def trigger_event(self, state: BlockState, level: Level, pos: Pos, b0: int, b1: int) -> bool:
        """``triggerEvent`` L141: plays the sound (nothing to simulate). Not as in the game:
        a custom head's sound needs the head's block entity, which is not simulated: it
        fails like a head without a sound."""
        return state.get(INSTRUMENT) != "custom_head"
