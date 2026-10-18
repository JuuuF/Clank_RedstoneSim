"""Jukeboxes: a signal source (15 to every side while a song plays; redstone wire connects to
it always) and a comparator source (the inserted disc's value).

Sources:

* ``world/level/block/JukeboxBlock.java``: ``has_record``; always a signal source,
  ``ownSignal`` 15 while playing; comparator output from the block entity; using it with an
  empty hand ejects the disc; the ticker only while ``has_record``;
  ``affectNeighborsAfterRemoval`` (comparators).
* ``world/level/block/entity/JukeboxBlockEntity.java``: one disc (``RecordItem``),
  ``setTheItem`` (sets ``has_record`` with flags 2, then plays or stops), ``popOutTheItem``,
  ``onSongChanged`` (neighbor updates and ``setChanged``), ``getComparatorOutput`` (the
  disc's song, playing or not), loading (a saved disc plays on only with
  ``ticks_since_song_started``), ``preRemoveSideEffects`` (ejects the disc).
* ``world/item/JukeboxSongPlayer.java``: ``play``, ``stop``, ``tick`` (a song stops
  ``lengthInTicks + 20`` ticks after it started, ``JukeboxSong.hasFinished``).
* ``world/item/JukeboxSongs.java`` (lengths and comparator values) and
  ``world/item/Items.java`` (which disc plays which song): the tables below.
* ``Blocks.java``: a full block (it conducts), a block entity (pistons cannot move it).

Not as in the game (doc/differences.md): an ejected disc is an item, which is not simulated
(it disappears); hoppers and droppers leave jukeboxes alone (in the game they put discs in
and take them out); sounds, particles and the game events (allays, sculk sensors) are left
out.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.world.block import BlockState
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.blocks.catalog import CatalogBlock
from redsim.world.blocks.container import ContainerBlockEntity
from redsim.world.properties import boolean

if TYPE_CHECKING:
    from redsim.sim.level import Level

HAS_RECORD = boolean("has_record")
#: ``JukeboxSongs.bootstrap``: song → (length in seconds, comparator output).
SONGS: dict[str, tuple[int, int]] = {
    "13": (178, 1), "cat": (185, 2), "blocks": (345, 3), "chirp": (185, 4), "far": (174, 5),
    "mall": (197, 6), "mellohi": (96, 7), "stal": (150, 8), "strad": (188, 9),
    "ward": (251, 10), "11": (71, 11), "wait": (238, 12), "pigstep": (149, 13),
    "otherside": (195, 14), "5": (178, 15), "relic": (218, 14), "precipice": (299, 13),
    "creator": (176, 12), "creator_music_box": (73, 11), "tears": (175, 10),
    "lava_chicken": (134, 9), "bounce": (234, 8),
}  # fmt: skip
#: ``Items.java``: the discs (``jukeboxPlayable``) and their songs.
DISCS: dict[str, str] = {f"minecraft:music_disc_{song}": song for song in SONGS}
#: ``JukeboxSong.SONG_END_PADDING_TICKS``.
SONG_END_PADDING = 20


def song_of(item: str | None) -> str | None:
    """``JukeboxSong.fromStack``."""
    return DISCS.get(item) if item is not None else None


def has_finished(song: str, ticks: int) -> bool:
    """``JukeboxSong.hasFinished``: ``lengthInTicks`` is ``ceil(seconds · 20)``."""
    return ticks >= math.ceil(SONGS[song][0] * 20.0) + SONG_END_PADDING


class JukeboxBlockEntity(ContainerBlockEntity):
    """``JukeboxBlockEntity`` with its ``JukeboxSongPlayer``; slot 0 holds the disc."""

    type_id = "jukebox"
    valid_blocks = frozenset({"minecraft:jukebox"})
    SIZE = 1
    NAME = "jukebox"

    def __init__(self, pos: Pos, state: BlockState) -> None:
        super().__init__(pos, state)
        self.song: str | None = None
        self.ticks_since_song_started = 0

    @property
    def item(self) -> str | None:
        stack = self.items[0]
        return stack[0] if stack is not None else None

    def is_playing(self) -> bool:
        return self.song is not None

    def comparator_output(self) -> int:
        """``getComparatorOutput``: the disc's song value, playing or not."""
        song = song_of(self.item)
        return SONGS[song][1] if song is not None else 0

    def signal(self) -> int:
        return self.comparator_output()

    # --- the song player ----------------------------------------------------------------
    def on_song_changed(self, level: Level) -> None:
        """``onSongChanged``: neighbor updates, then ``setChanged`` (both with the entity's
        own block state, which is still the jukebox while it is being removed)."""
        level.update_neighbors_at(self.pos, self.block_state.block)
        if not self.block_state.is_air:
            level.update_neighbour_for_output_signal(self.pos, self.block_state.block)

    def play(self, level: Level, song: str) -> None:
        self.song = song
        self.ticks_since_song_started = 0
        self.on_song_changed(level)

    def stop(self, level: Level) -> None:
        if self.song is not None:
            self.song = None
            self.ticks_since_song_started = 0
            self.on_song_changed(level)

    def tick(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``JukeboxSongPlayer.tick``."""
        if self.song is not None:
            if has_finished(self.song, self.ticks_since_song_started):
                self.stop(level)
            else:
                self.ticks_since_song_started += 1

    # --- the disc -----------------------------------------------------------------------
    def set_the_item(self, level: Level, item: str | None) -> None:
        """``setTheItem``."""
        self.items[0] = (item, 1) if item is not None else None
        inserted = item is not None
        song = song_of(item)
        if level.get_block_state(self.pos) is self.block_state:  # notifyItemChangedInJukebox
            level.set_block(self.pos, self.block_state.with_(HAS_RECORD, inserted), 2)
        if inserted and song is not None:
            self.play(level, song)
        else:
            self.stop(level)

    def set_item(self, level: Level, slot: int, stack: tuple[str, int] | None) -> None:
        """``ContainerSingleItem.setItem`` (``/item replace``, the editor's slots)."""
        if slot == 0:
            self.set_the_item(level, stack[0] if stack is not None and stack[1] > 0 else None)

    def remove_item(self, level: Level, slot: int, count: int) -> tuple[str, int] | None:
        if slot != 0 or self.items[0] is None or count <= 0:
            return None
        taken = self.items[0]
        self.set_the_item(level, None)  # splitTheItem
        return taken

    def pop_out_the_item(self, level: Level) -> None:
        """``popOutTheItem``. Not as in the game: the disc would drop as an item."""
        if self.items[0] is not None:
            self.set_the_item(level, None)  # removeTheItem → splitTheItem
            self.on_song_changed(level)

    def pre_remove_side_effects(self, level: Level, pos: Pos, state: BlockState) -> None:
        self.pop_out_the_item(level)

    # --- saving -------------------------------------------------------------------------
    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.item is not None:
            out["RecordItem"] = {"id": self.item, "count": 1}
        if self.song is not None:
            out["ticks_since_song_started"] = self.ticks_since_song_started
        return out

    def load_json(self, data: dict[str, Any]) -> None:
        """``loadAdditional``: a different disc stops the song (no level here: the
        loading side effects are those of the game's ``stop`` without a level change)."""
        record = data.get("RecordItem")
        new_item = str(record["id"]) if isinstance(record, dict) and "id" in record else None
        if self.item is not None and new_item != self.item:
            self.song = None
            self.ticks_since_song_started = 0
        self.items[0] = (new_item, 1) if new_item is not None else None
        if "ticks_since_song_started" in data:
            song = song_of(new_item)
            ticks = int(data["ticks_since_song_started"])
            if song is not None and not has_finished(song, ticks):  # setSongWithoutPlaying
                self.song = song
                self.ticks_since_song_started = ticks

    def describe(self) -> str:
        if self.item is None:
            return "jukebox: empty"
        state = f"playing, {self.ticks_since_song_started} ticks in" if self.song else "silent"
        return f"jukebox: {self.item} ({state}), comparator {self.comparator_output()}"


class JukeboxBlock(CatalogBlock):
    """``JukeboxBlock``."""

    properties = (HAS_RECORD,)
    has_block_entity = True

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(self.default_state.with_(HAS_RECORD, False))

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return JukeboxBlockEntity(pos, state)

    def block_entity_ticks(self, state: BlockState) -> bool:
        """``getTicker``: only while it holds a disc."""
        return bool(state.get(HAS_RECORD))

    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        entity = level.get_block_entity(pos, create=False)
        return 15 if isinstance(entity, JukeboxBlockEntity) and entity.is_playing() else 0

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        entity = level.get_block_entity(pos)
        return entity.comparator_output() if isinstance(entity, JukeboxBlockEntity) else 0

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``useWithoutItem``: eject the disc (it would drop as an item)."""
        entity = level.get_block_entity(pos)
        if state.get(HAS_RECORD) and isinstance(entity, JukeboxBlockEntity):
            entity.pop_out_the_item(level)
            return True
        return False

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        level.update_neighbour_for_output_signal(pos, self)


def is_jukebox(entity: BlockEntity | None) -> bool:
    return isinstance(entity, JukeboxBlockEntity)


# Registered here, not with a class decorator (classes stay compilable by mypyc).
register_block_entity(JukeboxBlockEntity)
