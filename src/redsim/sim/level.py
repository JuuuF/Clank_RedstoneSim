"""The simulated level: a port of the redstone-relevant parts of ``Level``/``ServerLevel``.

Source paths are relative to ``data/minecraft_src/client-src/net/minecraft/``:

* ``world/level/Level.java``: ``setBlock`` L216, ``removeBlock`` L268, ``destroyBlock`` L274,
  ``neighborShapeChanged`` L320, ``tickBlockEntities`` L527, ``updateNeighbourForOutputSignal``
  L1008, ``nextSubTickCount`` L1090, ``getBlockEntity`` L691, ``setBlockEntity`` L701.
* ``world/level/chunk/LevelChunk.java``: ``setBlockState`` L269, ``getBlockEntity`` L369,
  ``addAndRegisterBlockEntity`` L396, ``setBlockEntity`` L423, ``removeBlockEntity`` L473,
  ``removeBlockEntityTicker`` L504, ``updateBlockEntityTicker`` L709.
* ``server/level/ServerLevel.java``: ``updateNeighborsAt`` L1170 and friends, ``blockEvent``
  L1260.
* ``world/level/SignalGetter.java``: all signal queries.
* ``world/level/redstone/NeighborUpdater.java``: ``executeShapeUpdate`` L36, ``executeUpdate``.
* ``world/level/block/Block.java``: ``updateOrDestroy`` L212.

Lighting, sounds, particles, game events, entities and client synchronization are omitted.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from redsim.core.direction import ALL, HORIZONTAL, Direction
from redsim.core.pos import Pos, offset
from redsim.sim import trace as tr
from redsim.sim.neighbor_updater import MAX_CHAINED_NEIGHBOR_UPDATES, CollectingNeighborUpdater
from redsim.sim.ticks import LevelTicks, ScheduledTick, TickPriority
from redsim.sim.trace import Trace
from redsim.world import ids
from redsim.world.block import Block, BlockState, UpdateFlags
from redsim.world.properties import POWER

if TYPE_CHECKING:
    from redsim.world.block_entity import BlockEntity

WORLD_HORIZONTAL_LIMIT = 30_000_000
#: Default world border half-size (``WorldBorder.absoluteMaxSize``).
WORLD_BORDER = 29_999_984

BlockEventKey = tuple[Pos, str, int, int]


class _BoundTicker:
    """``LevelChunk.BoundTickingBlockEntity``."""

    __slots__ = ("block_entity",)

    def __init__(self, block_entity: BlockEntity) -> None:
        self.block_entity = block_entity

    def is_removed(self) -> bool:
        return self.block_entity.removed

    def tick(self, level: Level) -> None:
        be = self.block_entity
        if be.removed:
            return
        state = level.get_block_state(be.pos)
        if state.block.id in be.valid_blocks:
            be.tick(level, be.pos, state)


class TickerWrapper:
    """``LevelChunk.RebindableTickingBlockEntityWrapper``: keeps its list position."""

    __slots__ = ("ticker",)

    def __init__(self, ticker: _BoundTicker | None) -> None:
        self.ticker = ticker  # None is NULL_TICKER

    def rebind(self, ticker: _BoundTicker | None) -> None:
        self.ticker = ticker

    def is_removed(self) -> bool:
        return self.ticker is None or self.ticker.is_removed()

    @property
    def pos(self) -> Pos | None:
        return None if self.ticker is None else self.ticker.block_entity.pos

    def tick(self, level: Level) -> None:
        if self.ticker is not None:
            self.ticker.tick(level)


class Level:
    """Block storage plus the server-side update machinery."""

    def __init__(
        self,
        min_y: int = -64,
        max_y: int = 319,
        trace: Trace | None = None,
        max_chained_neighbor_updates: int = MAX_CHAINED_NEIGHBOR_UPDATES,
    ) -> None:
        from redsim.world import blocks

        self.air = blocks.AIR.default_state
        self.min_y = min_y
        self.max_y = max_y
        self.blocks: dict[Pos, BlockState] = {}
        #: Positions whose block changed since a viewer last looked (``take_touched``).
        self.touched: set[Pos] = set()
        self.block_entities: dict[Pos, BlockEntity] = {}
        self.game_time = 0
        self.sub_tick_count = 0
        self.block_ticks = LevelTicks()
        self.block_events: dict[BlockEventKey, None] = {}  # insertion-ordered dedup set
        #: Projectiles that hit target blocks in the next entity phase: (pos, strength, ticks).
        self.projectile_hits: list[tuple[Pos, int, int]] = []
        #: Entities standing on pressure plates (not simulated as entities): pos → (mobs,
        #: other entities, last game time they are there).
        self.plate_visitors: dict[Pos, tuple[int, int, int]] = {}
        #: Power given to positions by the editor's sequences (not a game mechanic: like an
        #: invisible redstone block next to the block, from every side): pos → (strength,
        #: last game time it is on). Locked to the position, whatever block is there.
        self.forced_power: dict[Pos, tuple[int, int]] = {}
        #: 0-tick pulses: (pos, strength) that switch on at the next tick's start and off
        #: right after its block events (``zero_tick_ends``), inside one tick.
        self.zero_tick_pulses: list[tuple[Pos, int]] = []
        self.zero_tick_ends: list[Pos] = []
        #: Plates whose visitors step on them in this tick's entity phase (in order).
        self.entity_queue: list[Pos] = []
        #: Entities (falling blocks, ``sim/entities.py``) by id, in the order they joined
        #: (``EntityTickList``), the next id, and the ids still to tick in this entity phase.
        self.entities: dict[int, Any] = {}
        self.next_entity_id = 0
        self.entity_tick_queue: list[int] = []
        self.tickers: list[TickerWrapper] = []
        self.pending_tickers: list[TickerWrapper] = []
        self.tickers_by_pos: dict[Pos, TickerWrapper] = {}
        self.ticking_block_entities = False
        self.handling_tick = False
        #: The yaw of the player using a block right now (``Player.getDirection`` for
        #: fence gates); set by the engine's ``use`` action, south by default.
        self.player_yaw = 0.0
        #: ``RedstoneTorchBlock.RECENT_TOGGLES`` for this level: (pos, gameTime) entries.
        self.torch_toggles: list[tuple[Pos, int]] = []
        self.trace = trace if trace is not None else Trace()
        self.neighbor_updater = CollectingNeighborUpdater(self, max_chained_neighbor_updates)

    # =================================================================== block access
    def is_in_valid_bounds(self, pos: Pos) -> bool:
        x, y, z = pos
        return (
            self.min_y <= y <= self.max_y
            and -WORLD_HORIZONTAL_LIMIT <= x < WORLD_HORIZONTAL_LIMIT
            and -WORLD_HORIZONTAL_LIMIT <= z < WORLD_HORIZONTAL_LIMIT
        )

    def is_within_world_border(self, pos: Pos) -> bool:
        """``WorldBorder.isWithinBounds`` for the default, centered border."""
        return -WORLD_BORDER <= pos[0] < WORLD_BORDER and -WORLD_BORDER <= pos[2] < WORLD_BORDER

    def get_block_state(self, pos: Pos) -> BlockState:
        return self.blocks.get(pos, self.air)

    def iter_blocks(self) -> Iterator[tuple[Pos, BlockState]]:
        return iter(self.blocks.items())

    def add_blocks(self, states: dict[Pos, BlockState]) -> None:
        """Put blocks in without updates, like the game loading a chunk."""
        self.blocks.update(states)
        self.touched.update(states)

    def take_touched(self) -> set[Pos]:
        """The positions changed since the last call (for a viewer's mesh)."""
        touched, self.touched = self.touched, set()
        return touched

    # =================================================================== setBlock
    def set_block(self, pos: Pos, state: BlockState, flags: int, limit: int = 512) -> bool:
        """``Level.setBlock`` (Level.java L216). In the trace, the change is the cause of
        the updates it sends (for "why did this change?")."""
        if not self.is_in_valid_bounds(pos):
            return False
        current = self.blocks.get(pos, self.air)
        if current is state:
            return False
        trace = self.trace
        trace.push(trace.emit(tr.SET_BLOCK, pos, old=repr(current), new=repr(state), flags=flags))
        try:
            old_state = self._chunk_set_block_state(pos, state, flags)
            if old_state is None:
                return False
            new_state = self.get_block_state(pos)
            if new_state is state:
                if flags & UpdateFlags.NEIGHBORS:
                    self.update_neighbors_at(pos, old_state.block)
                    if state.has_analog_output_signal():
                        self.update_neighbour_for_output_signal(pos, state.block)
                if not flags & UpdateFlags.KNOWN_SHAPE and limit > 0:
                    neighbour_flags = flags & -34
                    old_state.update_indirect_neighbour_shapes(
                        self, pos, neighbour_flags, limit - 1
                    )
                    state.update_neighbour_shapes(self, pos, neighbour_flags, limit - 1)
                    state.update_indirect_neighbour_shapes(self, pos, neighbour_flags, limit - 1)
            return True
        finally:
            trace.pop()

    def _chunk_set_block_state(self, pos: Pos, state: BlockState, flags: int) -> BlockState | None:
        """``LevelChunk.setBlockState`` (LevelChunk.java L269) minus lighting/heightmaps."""
        old_state = self.blocks.get(pos, self.air)
        if old_state is state:
            return None
        if state.is_air:
            del self.blocks[pos]
        else:
            self.blocks[pos] = state
        self.touched.add(pos)

        block_changed = old_state.block is not state.block
        moved_by_piston = bool(flags & UpdateFlags.MOVE_BY_PISTON)
        side_effects = not flags & UpdateFlags.SKIP_BLOCK_ENTITY_SIDEEFFECTS
        if block_changed and old_state.has_block_entity:
            if side_effects:
                be = self.block_entities.get(pos)
                if be is not None:
                    be.pre_remove_side_effects(self, pos, old_state)
            self.remove_block_entity(pos)

        if (block_changed or state.block.is_rail) and (
            flags & UpdateFlags.NEIGHBORS or moved_by_piston
        ):
            old_state.affect_neighbors_after_removal(self, pos, moved_by_piston)

        if not self.get_block_state(pos).is_(state.block):
            return None

        if not flags & UpdateFlags.SKIP_ON_PLACE:
            state.on_place(self, pos, old_state, moved_by_piston)

        if state.has_block_entity and self.get_block_state(pos).is_(state.block):
            be = self.get_block_entity(pos, create=False)
            if be is not None and state.block.id not in be.valid_blocks:
                self.remove_block_entity(pos)
                be = None
            if be is None:
                new_be = state.block.new_block_entity(pos, state)
                if new_be is not None:
                    self.add_and_register_block_entity(new_be)
            else:
                be.block_state = state
                self._update_block_entity_ticker(be)
        return old_state

    def set_block_and_update(self, pos: Pos, state: BlockState) -> bool:
        return self.set_block(pos, state, UpdateFlags.ALL)

    def remove_block(self, pos: Pos, moved_by_piston: bool = False) -> bool:
        """``Level.removeBlock`` (no fluids: always air)."""
        flags = UpdateFlags.ALL | (UpdateFlags.MOVE_BY_PISTON if moved_by_piston else 0)
        return self.set_block(pos, self.air, flags)

    def destroy_block(self, pos: Pos, drop_resources: bool = True, limit: int = 512) -> bool:
        """``Level.destroyBlock`` (drops are not simulated)."""
        if self.get_block_state(pos).is_air:
            return False
        return self.set_block(pos, self.air, UpdateFlags.ALL, limit)

    def update_neighbours_on_block_set(self, pos: Pos, old_state: BlockState) -> None:
        """``ServerLevel.updateNeighboursOnBlockSet`` (used by ``/setblock`` and ``/fill``)."""
        state = self.get_block_state(pos)
        if not old_state.is_(state.block):
            old_state.affect_neighbors_after_removal(self, pos, False)
        self.update_neighbors_at(pos, state.block)
        if state.has_analog_output_signal():
            self.update_neighbour_for_output_signal(pos, state.block)

    def update_or_destroy(
        self, old: BlockState, new: BlockState, pos: Pos, flags: int, limit: int = 512
    ) -> None:
        """``Block.updateOrDestroy`` (Block.java L212)."""
        if new is not old:
            if new.is_air:
                self.destroy_block(pos, not flags & UpdateFlags.SUPPRESS_DROPS, limit)
            else:
                self.set_block(pos, new, flags & -33, limit)

    def update_from_neighbour_shapes(self, state: BlockState, pos: Pos) -> BlockState:
        """``Block.updateFromNeighbourShapes`` (Block.java L194)."""
        from redsim.core.direction import SHAPE_UPDATE_ORDER

        new_state = state
        for direction in SHAPE_UPDATE_ORDER:
            neighbor_pos = offset(pos, direction)
            new_state = new_state.update_shape(
                self, pos, direction, neighbor_pos, self.get_block_state(neighbor_pos)
            )
        return new_state

    # =================================================================== neighbor updates
    def update_neighbors_at(self, pos: Pos, source: Block) -> None:
        self.neighbor_updater.update_neighbors_at_except_from_facing(pos, source, None)

    def update_neighbors_at_except_from_facing(
        self, pos: Pos, source: Block, skip: Direction
    ) -> None:
        self.neighbor_updater.update_neighbors_at_except_from_facing(pos, source, skip)

    def neighbor_changed(self, pos: Pos, source: Block) -> None:
        self.neighbor_updater.neighbor_changed(pos, source)

    def neighbor_changed_full(
        self, state: BlockState, pos: Pos, source: Block, moved_by_piston: bool = False
    ) -> None:
        self.neighbor_updater.neighbor_changed_full(state, pos, source, moved_by_piston)

    def neighbor_shape_changed(
        self,
        direction: Direction,
        pos: Pos,
        neighbor_pos: Pos,
        neighbor_state: BlockState,
        flags: int,
        limit: int,
    ) -> None:
        """``Level.neighborShapeChanged`` (Level.java L320)."""
        self.neighbor_updater.shape_update(
            direction, neighbor_state, pos, neighbor_pos, flags, limit
        )

    def execute_neighbor_update(
        self,
        cause: int | None,
        state: BlockState,
        pos: Pos,
        source: Block,
        moved_by_piston: bool,
        kind: str,
        source_pos: Pos | None = None,
    ) -> None:
        """``NeighborUpdater.executeUpdate``."""
        record = self.trace.emit(
            tr.NEIGHBOR_UPDATE,
            pos,
            parent=cause,
            source=source.name,
            source_pos=source_pos,
            target=repr(state),
            via=kind,
        )
        self.trace.push(record)
        try:
            state.handle_neighbor_changed(self, pos, source, moved_by_piston)
        finally:
            self.trace.pop()

    def execute_shape_update(
        self,
        cause: int | None,
        direction: Direction,
        pos: Pos,
        neighbor_pos: Pos,
        neighbor_state: BlockState,
        flags: int,
        limit: int,
    ) -> None:
        """``NeighborUpdater.executeShapeUpdate`` (NeighborUpdater.java L36)."""
        current = self.get_block_state(pos)
        if flags & UpdateFlags.SKIP_SHAPE_UPDATE_ON_WIRE and current.block.id == ids.REDSTONE_WIRE:
            return
        record = self.trace.emit(
            tr.SHAPE_UPDATE,
            pos,
            parent=cause,
            direction=direction.serialized,
            neighbor_pos=neighbor_pos,
            target=repr(current),
        )
        self.trace.push(record)
        try:
            new_state = current.update_shape(self, pos, direction, neighbor_pos, neighbor_state)
            emitted = self.trace.get(record)
            if emitted is not None:
                emitted.detail["changed"] = new_state is not current
            self.update_or_destroy(current, new_state, pos, flags, limit)
        finally:
            self.trace.pop()

    def update_neighbour_for_output_signal(self, pos: Pos, source: Block) -> None:
        """``Level.updateNeighbourForOutputSignal`` (Level.java L1008)."""
        for direction in HORIZONTAL:
            relative = offset(pos, direction)
            state = self.get_block_state(relative)
            if state.block.id == ids.COMPARATOR:
                self.neighbor_changed_full(state, relative, source, False)
            elif state.is_redstone_conductor(self, relative):
                relative = offset(relative, direction)
                state = self.get_block_state(relative)
                if state.block.id == ids.COMPARATOR:
                    self.neighbor_changed_full(state, relative, source, False)

    # =================================================================== signals
    def get_direct_signal(self, pos: Pos, direction: Direction) -> int:
        return self.get_block_state(pos).get_direct_signal(self, pos, direction)

    def get_direct_signal_to(self, pos: Pos) -> int:
        """``SignalGetter.getDirectSignalTo`` (L17): D, U, N, S, W, E with early exit."""
        result = 0
        for direction in ALL:
            result = max(result, self.get_direct_signal(offset(pos, direction), direction))
            if result >= 15:
                return result
        return result

    def get_control_input_signal(self, pos: Pos, direction: Direction, only_diodes: bool) -> int:
        """``SignalGetter.getControlInputSignal`` (L48)."""
        state = self.get_block_state(pos)
        if only_diodes:
            return self.get_direct_signal(pos, direction) if state.block.is_diode else 0
        block_id = state.block.id
        if block_id == ids.REDSTONE_BLOCK:
            return 15
        if block_id == ids.REDSTONE_WIRE:
            return int(state.get(POWER))
        return self.get_direct_signal(pos, direction) if state.is_signal_source() else 0

    def get_signal(self, pos: Pos, direction: Direction) -> int:
        """``SignalGetter.getSignal`` (L65). Editor power (``forced_power``) at the position
        asking (``pos`` moved against ``direction``) arrives from every side."""
        if self.forced_power:
            forced = self.forced_power.get(offset(pos, direction.opposite))
            if forced is not None:
                return max(forced[0], self._get_signal(pos, direction))
        return self._get_signal(pos, direction)

    def _get_signal(self, pos: Pos, direction: Direction) -> int:
        state = self.get_block_state(pos)
        signal = state.get_signal(self, pos, direction)
        if state.is_redstone_conductor(self, pos):
            return max(signal, self.get_direct_signal_to(pos))
        return signal

    def has_signal(self, pos: Pos, direction: Direction) -> bool:
        return self.get_signal(pos, direction) > 0

    def has_neighbor_signal(self, pos: Pos) -> bool:
        """``SignalGetter.hasNeighborSignal`` (L76): D, U, N, S, W, E, short-circuit."""
        return any(self.get_signal(offset(pos, d), d) > 0 for d in ALL)

    def get_best_neighbor_signal(self, pos: Pos) -> int:
        """``SignalGetter.getBestNeighborSignal`` (L90)."""
        best = 0
        for direction in ALL:
            signal = self.get_signal(offset(pos, direction), direction)
            if signal >= 15:
                return 15
            best = max(best, signal)
        return best

    # =================================================================== scheduled ticks
    def next_sub_tick_count(self) -> int:
        value = self.sub_tick_count
        self.sub_tick_count += 1
        return value

    def schedule_tick(
        self, pos: Pos, block: Block, delay: int, priority: TickPriority = TickPriority.NORMAL
    ) -> bool:
        """``ScheduledTickAccess.scheduleTick`` via ``LevelAccessor.createTick`` (L31)."""
        tick = ScheduledTick(
            block.id, pos, self.game_time + delay, priority, self.next_sub_tick_count()
        )
        accepted = self.block_ticks.schedule(tick)
        self.trace.emit(
            tr.SCHEDULE_TICK,
            pos,
            block=block.name,
            delay=delay,
            priority=priority.name,
            trigger_tick=tick.trigger_tick,
            sub_tick=tick.sub_tick,
            accepted=accepted,
        )
        return accepted

    def force_power(self, pos: Pos, strength: int, until: int) -> None:
        """Editor power at ``pos`` (strength 0: off) until game time ``until``; the block
        there gets a neighbor update, as from a redstone block placed or removed next to
        it."""
        from redsim.world import blocks

        if strength > 0:
            self.forced_power[pos] = (strength, until)
        elif self.forced_power.pop(pos, None) is None:
            return
        note = self.trace.emit(
            tr.NOTE, pos, text=f"sequence power {strength} (until game time {until})"
        )
        self.trace.push(note)  # the update's cause, for "why did this change?"
        try:
            self.neighbor_changed(pos, blocks.REDSTONE_BLOCK)
        finally:
            self.trace.pop()

    def release_forced_power(self) -> None:
        """Editor power whose time is over goes off (between ticks, in order of start)."""
        for pos, (_, until) in list(self.forced_power.items()):
            if until <= self.game_time:
                self.force_power(pos, 0, until)

    def plate_visitors_at(self, pos: Pos) -> tuple[int, int]:
        """(mobs, other entities) on the plate at ``pos`` now: its visitors, and the falling
        blocks in its ``TOUCH_AABB`` (``Block.column(14, 0, 4)``)."""
        mobs, others, until = self.plate_visitors.get(pos, (0, 0, -1))
        if self.game_time > until:
            mobs, others = 0, 0
        if self.entities:
            from redsim.sim.entities import entities_in

            x, y, z = pos
            touch = (x + 0.0625, y + 0.0, z + 0.0625, x + 0.9375, y + 0.25, z + 0.9375)
            others += len(entities_in(self, touch))
        return mobs, others

    def new_entity_id(self) -> int:
        """``Entity.ENTITY_COUNTER``: ids in creation order."""
        self.next_entity_id += 1
        return self.next_entity_id

    def add_entity(self, entity: Any) -> None:
        """``addFreshEntity``: it ticks from this tick's entity phase on."""
        self.entities[entity.id] = entity

    def has_scheduled_tick(self, pos: Pos, block: Block) -> bool:
        return self.block_ticks.has_scheduled_tick(pos, block.id)

    def will_tick_this_tick(self, pos: Pos, block: Block) -> bool:
        return self.block_ticks.will_tick_this_tick(pos, block.id)

    # =================================================================== block events
    def block_event(self, pos: Pos, block: Block, b0: int, b1: int) -> None:
        """``ServerLevel.blockEvent`` (L1260): insertion-ordered set of event records."""
        key: BlockEventKey = (pos, block.id, b0, b1)
        accepted = key not in self.block_events
        if accepted:
            self.block_events[key] = None
        self.trace.emit(
            tr.BLOCK_EVENT_QUEUED, pos, block=block.name, b0=b0, b1=b1, accepted=accepted
        )

    # =================================================================== block entities
    def get_block_entity(self, pos: Pos, create: bool = True) -> BlockEntity | None:
        """``Level.getBlockEntity`` (``create=True``: IMMEDIATE) or the CHECK variant."""
        if not self.is_in_valid_bounds(pos):
            return None
        be = self.block_entities.get(pos)
        if be is None:
            if create:
                state = self.get_block_state(pos)
                if state.has_block_entity:
                    be = state.block.new_block_entity(pos, state)
                    if be is not None:
                        self.add_and_register_block_entity(be)
        elif be.removed:
            del self.block_entities[pos]
            return None
        return be

    def set_block_entity(self, be: BlockEntity) -> None:
        """``Level.setBlockEntity`` → ``LevelChunk.addAndRegisterBlockEntity``."""
        if self.is_in_valid_bounds(be.pos):
            self.add_and_register_block_entity(be)

    def add_and_register_block_entity(self, be: BlockEntity) -> None:
        self._chunk_set_block_entity(be)
        self._update_block_entity_ticker(be)
        self.trace.emit(tr.BLOCK_ENTITY, be.pos, action="added", info=be.describe())

    def _chunk_set_block_entity(self, be: BlockEntity) -> None:
        """``LevelChunk.setBlockEntity`` (L423)."""
        state = self.get_block_state(be.pos)
        if not state.has_block_entity:
            return
        if state is not be.block_state:
            if state.block.id not in be.valid_blocks:
                return
            be.block_state = state
        be.removed = False
        previous = self.block_entities.get(be.pos)
        self.block_entities[be.pos] = be
        if previous is not None and previous is not be:
            previous.set_removed()

    def remove_block_entity(self, pos: Pos) -> None:
        """``LevelChunk.removeBlockEntity`` (L473)."""
        be = self.block_entities.pop(pos, None)
        if be is not None:
            be.set_removed()
            self.trace.emit(tr.BLOCK_ENTITY, pos, action="removed", info=be.describe())
        self._remove_block_entity_ticker(pos)

    def _remove_block_entity_ticker(self, pos: Pos) -> None:
        wrapper = self.tickers_by_pos.pop(pos, None)
        if wrapper is not None:
            wrapper.rebind(None)

    def _update_block_entity_ticker(self, be: BlockEntity) -> None:
        """``LevelChunk.updateBlockEntityTicker`` (L709)."""
        if not be.block_state.block.has_ticker:
            self._remove_block_entity_ticker(be.pos)
            return
        ticker = _BoundTicker(be)
        existing = self.tickers_by_pos.get(be.pos)
        if existing is not None:
            existing.rebind(ticker)
        else:
            wrapper = TickerWrapper(ticker)
            (self.pending_tickers if self.ticking_block_entities else self.tickers).append(wrapper)
            self.tickers_by_pos[be.pos] = wrapper

    # =================================================================== time
    def shift_time(self, delta: int) -> None:
        """Move the clock and every stored game time by ``delta``. Only differences of game
        times matter to the simulation, so behavior is unchanged; used to put tick 0 (the
        build) at game time 0."""
        self.game_time += delta
        self.trace.game_time = self.game_time
        self.block_ticks.shift_time(delta)
        self.torch_toggles = [(pos, time + delta) for pos, time in self.torch_toggles]
        self.forced_power = {p: (s, until + delta) for p, (s, until) in self.forced_power.items()}
        self.plate_visitors = {
            p: (mobs, others, until + delta)
            for p, (mobs, others, until) in self.plate_visitors.items()
        }
        entities = {id(be): be for be in self.block_entities.values()}
        for wrapper in [*self.tickers, *self.pending_tickers]:
            if wrapper.ticker is not None:
                entities.setdefault(id(wrapper.ticker.block_entity), wrapper.ticker.block_entity)
        for entity in entities.values():
            entity.shift_time(delta)
        for mob in self.entities.values():
            mob.piston_deltas_time += delta

    # =================================================================== snapshots
    def clone(self) -> Level:
        """Deep copy of all simulation state (trace not included)."""
        other = Level.__new__(Level)
        other.air = self.air
        other.min_y = self.min_y
        other.max_y = self.max_y
        other.blocks = dict(self.blocks)
        other.touched = set()
        be_map: dict[int, BlockEntity] = {}
        other.block_entities = {}
        for pos, be in self.block_entities.items():
            copy_be = be.clone()
            be_map[id(be)] = copy_be
            other.block_entities[pos] = copy_be

        def copy_wrapper(wrapper: TickerWrapper) -> TickerWrapper:
            if wrapper.ticker is None:
                return TickerWrapper(None)
            be = wrapper.ticker.block_entity
            copy_be = be_map.get(id(be))
            if copy_be is None:  # a removed entity still referenced by its wrapper
                copy_be = be.clone()
                be_map[id(be)] = copy_be
            return TickerWrapper(_BoundTicker(copy_be))

        wrapper_map: dict[int, TickerWrapper] = {}
        other.tickers = []
        for wrapper in self.tickers:
            wrapper_map[id(wrapper)] = copy_wrapper(wrapper)
            other.tickers.append(wrapper_map[id(wrapper)])
        other.pending_tickers = []
        for wrapper in self.pending_tickers:
            wrapper_map[id(wrapper)] = copy_wrapper(wrapper)
            other.pending_tickers.append(wrapper_map[id(wrapper)])
        other.tickers_by_pos = {pos: wrapper_map[id(w)] for pos, w in self.tickers_by_pos.items()}
        other.game_time = self.game_time
        other.sub_tick_count = self.sub_tick_count
        other.block_ticks = self.block_ticks.clone()
        other.block_events = dict(self.block_events)
        other.projectile_hits = list(self.projectile_hits)
        other.plate_visitors = dict(self.plate_visitors)
        other.forced_power = dict(self.forced_power)
        other.zero_tick_pulses = list(self.zero_tick_pulses)
        other.zero_tick_ends = list(self.zero_tick_ends)
        other.entity_queue = list(self.entity_queue)
        other.entities = {i: e.clone() for i, e in self.entities.items()}
        other.next_entity_id = self.next_entity_id
        other.entity_tick_queue = list(self.entity_tick_queue)
        other.ticking_block_entities = self.ticking_block_entities
        other.handling_tick = self.handling_tick
        other.torch_toggles = list(self.torch_toggles)
        other.trace = Trace(enabled=self.trace.enabled)
        other.neighbor_updater = CollectingNeighborUpdater(other, self.neighbor_updater.max_chained)
        return other
