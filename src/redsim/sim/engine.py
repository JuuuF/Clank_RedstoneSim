"""Tick loop as an explicit, steppable state machine.

Port of the redstone-relevant part of ``ServerLevel.tick`` (ServerLevel.java L359):
``tickTime`` → block ticks (collect, then run one by one) → block events (until the queue is
empty) → block entities (registration order). Player actions run between ticks, as packet
tasks do between ``MinecraftServer.tickChildren`` calls (MinecraftServer.java L1067).

An *engine step* is one atomic unit: tick start, one scheduled tick, one block event, one
block-entity tick, or one player action (doc/decisions.md ADR-003). After each step the
engine settles through empty phases, so ``phase`` always names the phase of the next step.
All engine state is plain data and is captured by ``snapshot()``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from redsim.core.pos import Pos
from redsim.sim import trace as tr
from redsim.sim.level import Level
from redsim.sim.ticks import ScheduledTick
from redsim.world.block import BlockState, PlacementContext, UpdateFlags


class Phase(Enum):
    BETWEEN_TICKS = "between ticks"
    BLOCK_TICKS = "scheduled ticks"
    BLOCK_EVENTS = "block events"
    ENTITIES = "entities"
    BLOCK_ENTITIES = "block entities"


ActionKind = Literal[
    "place",
    "break",
    "use",
    "setblock",
    "set_block",
    "fill",
    "clone",
    "clone_region",
    "container_item",
    "sign_text",
    "lectern_page",
    "transform_region",
    "transform_regions",
    "stack_region",
    "projectile_hit",
    "plate_visitors",
    "power_pulse",
]

#: ``GameRules.MAX_BLOCK_MODIFICATIONS`` default: the largest /fill or /clone volume.
MAX_BLOCK_MODIFICATIONS = 32768
CLONE_MODES = ("normal", "force", "move")
#: ``2 | 816``: the flags of ``/clone … strict`` (no shape updates, no drops, no block-entity
#: side effects, no ``onPlace``); also always used for the barrier placeholders.
STRICT_FLAGS = 818


@dataclass(frozen=True)
class Action:
    """An input applied between ticks. ``state`` uses ``id[prop=value]`` syntax.

    * ``place``/``break``/``use``: what a player does (``BlockItem.place``,
      ``ServerPlayerGameMode.destroyBlock``, ``useWithoutItem``).
    * ``setblock``: the ``/setblock`` command in replace mode (``SetBlockCommand.setBlock``);
      ``payload={"nbt": {...}}`` adds block-entity data like ``/setblock … {…}``.
    * ``set_block``: a raw ``Level.setBlock`` with explicit flags (editor tool, not vanilla).
    * ``fill``: ``/fill <pos> <payload["to"]> <state>`` in replace mode (``FillCommand``).
    * ``clone``: place a captured region at ``pos`` like ``/clone`` (replace mode) would place
      it (``CloneCommands.clone``); ``payload`` holds the blocks (see
      ``redsim.editor.clipboard``) and optionally ``strict`` (``/clone … strict``: no block
      updates). Scheduled ticks are not copied.
    * ``clone_region``: the full ``/clone <begin> <end> <pos> [strict] replace <mode>``
      reading the live source region (``payload``: ``begin``, ``end``, ``mode`` =
      normal/force/move, optional ``strict``); scheduled ticks inside the region are
      copied. Used to drag selections.
    * ``sign_text``: a player writing on a sign (``payload``: ``side`` front/back,
      ``lines``): ``SignBlockEntity.updateSignText`` (new text, ``setChanged``).
    * ``container_item``: ``/item replace block <pos> container.<slot> with <item> <count>``
      (``payload``: ``slot``, ``item`` or None for empty, ``count``): ``Container.setItem``.
    * ``transform_region``: editor tool, not vanilla: rotate (``quarter_turns`` clockwise
      seen from above, around the box center) and/or mirror (``mirror``: ``"x"``/``"z"``) the
      region ``payload["begin"]``-``payload["end"]`` in place, without block updates; block
      states turn with it (``BlockState.rotate``/``mirror``) and pending scheduled ticks
      move with their blocks.
    * ``transform_regions``: editor tool, not vanilla: several boxes (``payload["boxes"]``:
      ``[[begin, end], …]``) moved together, without block updates: mirrored within their
      bounding box (``mirror``), turned around ``pivot2`` (``quarter_turns``), then shifted
      by ``offset``; with ``copy`` the sources stay. Pending ticks go (or are copied) with
      their blocks. Used when several selections are moved, copied, turned or flipped.
    * ``stack_region``: editor tool: ``count`` copies of the region, each ``step`` further,
      as ``/clone … strict replace force`` (no block updates; ticks copied).
    * ``projectile_hit``: a projectile that will hit a target block (``payload``: ``strength``
      1-15, ``ticks`` 20 for arrows or 8 for others). Like a projectile summoned now, it hits
      in the next tick's entity phase (``TargetBlock.onProjectileHit``), after block events
      and before block entities.
    * ``lectern_page``: a player turning a lectern's book to ``payload["page"]``
      (``LecternBlockEntity.setPage``: comparator update and a 2-tick pulse). Not a command;
      there is no player on the test server, so this path is verified by source reading.
    """

    kind: ActionKind
    pos: Pos
    state: str | None = None
    flags: int = UpdateFlags.ALL
    payload: Any = None  # JSON-compatible data for fill/clone
    #: Editor label (e.g. "place wire"); ignored by the engine.
    label: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "pos": list(self.pos),
            "state": self.state,
            "flags": self.flags,
            "payload": self.payload,
            "label": self.label,
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> Action:
        x, y, z = data["pos"]
        return Action(
            data["kind"],
            (x, y, z),
            data.get("state"),
            data.get("flags", 3),
            data.get("payload"),
            data.get("label", ""),
        )


@dataclass
class StepInfo:
    index: int
    kind: str
    game_time: int
    pos: Pos | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    record: int | None = None

    def describe(self) -> str:
        where = f" at {self.pos}" if self.pos is not None else ""
        info = self.detail.get("info", "")
        return f"#{self.index} t={self.game_time} {self.kind}{where} {info}".rstrip()


class ActionError(Exception):
    """A player action that cannot be applied (wrong phase, invalid placement, ...)."""


class Engine:
    def __init__(self, level: Level | None = None) -> None:
        self.level = level if level is not None else Level()
        self.phase = Phase.BETWEEN_TICKS
        self.step_index = 0
        self.be_index = 0

    # ------------------------------------------------------------------ inspection
    @property
    def game_time(self) -> int:
        return self.level.game_time

    def at_tick_boundary(self) -> bool:
        return self.phase is Phase.BETWEEN_TICKS

    def peek_next_step(self) -> str:
        """Human-readable description of what ``step()`` will do next."""
        level = self.level
        if self.phase is Phase.BETWEEN_TICKS:
            return f"tick start (game time {level.game_time} → {level.game_time + 1})"
        if self.phase is Phase.BLOCK_TICKS and level.block_ticks.to_run:
            t = level.block_ticks.to_run[0]
            name = t.block_id.removeprefix("minecraft:")
            return f"scheduled tick {name} at {t.pos} ({t.priority.name})"
        if self.phase is Phase.BLOCK_EVENTS and level.block_events:
            pos, block_id, b0, b1 = next(iter(level.block_events))
            return f"block event {block_id.removeprefix('minecraft:')} at {pos} ({b0}, {b1})"
        if self.phase is Phase.ENTITIES and level.zero_tick_ends:
            return f"the 0-tick pulse at {level.zero_tick_ends[0]} ends"
        if self.phase is Phase.ENTITIES and level.projectile_hits:
            pos, strength, ticks = level.projectile_hits[0]
            return f"projectile hits the target at {pos} (strength {strength}, {ticks} ticks)"
        if self.phase is Phase.ENTITIES and level.entity_queue:
            return f"entities on the pressure plate at {level.entity_queue[0]}"
        if self.phase is Phase.BLOCK_ENTITIES:
            for wrapper in level.tickers[self.be_index :]:
                if not wrapper.is_removed():
                    return f"block entity at {wrapper.pos}"
        return self.phase.value

    # ------------------------------------------------------------------ stepping
    def step(self) -> StepInfo:
        """Execute exactly one engine step."""
        level = self.level
        if self.phase is Phase.BETWEEN_TICKS:
            info = self._begin_step("tick_start", None, {})
            try:
                # Editor power that has run out goes off first, still between ticks.
                level.release_forced_power()
                level.handling_tick = True
                level.game_time += 1  # ServerLevel.tickTime
                level.trace.game_time = level.game_time
                info.game_time = level.game_time
                count = level.block_ticks.collect(level.game_time)
                # 0-tick pulses switch on inside the tick (off after its block events).
                for pos, strength in level.zero_tick_pulses:
                    level.force_power(pos, strength, level.game_time)
                    level.zero_tick_ends.append(pos)
                level.zero_tick_pulses = []
                info.detail["info"] = f"{count} scheduled tick(s) due"
                self.phase = Phase.BLOCK_TICKS
            finally:
                self._end_step()
        elif self.phase is Phase.BLOCK_TICKS:
            tick = level.block_ticks.pop_next()
            assert tick is not None, "settle() guarantees a pending tick"
            info = self._begin_step(
                "scheduled_tick",
                tick.pos,
                {"block": tick.block_id, "priority": tick.priority.name, "sub_tick": tick.sub_tick},
            )
            try:
                state = level.get_block_state(tick.pos)
                if state.block.id == tick.block_id:  # ServerLevel.tickBlock L823
                    state.tick(level, tick.pos)
                else:
                    info.detail["info"] = "skipped: block changed"
            finally:
                self._end_step()
        elif self.phase is Phase.BLOCK_EVENTS:
            key = next(iter(level.block_events))
            del level.block_events[key]
            pos, block_id, b0, b1 = key
            info = self._begin_step("block_event", pos, {"block": block_id, "b0": b0, "b1": b1})
            try:
                state = level.get_block_state(pos)
                if state.block.id == block_id:  # ServerLevel.doBlockEvent L1291
                    state.trigger_event(level, pos, b0, b1)
                else:
                    info.detail["info"] = "skipped: block changed"
            finally:
                self._end_step()
        elif self.phase is Phase.ENTITIES and level.zero_tick_ends:
            pos = level.zero_tick_ends.pop(0)
            info = self._begin_step("zero_tick_end", pos, {})
            try:
                level.force_power(pos, 0, level.game_time)  # the 0-tick pulse ends
            finally:
                self._end_step()
        elif self.phase is Phase.ENTITIES and not level.projectile_hits:
            from redsim.world.blocks.pressure_plate import BasePressurePlateBlock

            pos = level.entity_queue.pop(0)
            info = self._begin_step("entity_inside", pos, {})
            try:
                state = level.get_block_state(pos)
                if isinstance(state.block, BasePressurePlateBlock):
                    state.block.entity_inside(state, level, pos)
                else:
                    info.detail["info"] = "skipped: no pressure plate"
            finally:
                self._end_step()
        elif self.phase is Phase.ENTITIES:
            from redsim.world.blocks.target import TargetBlock

            pos, strength, ticks = level.projectile_hits.pop(0)
            info = self._begin_step("projectile_hit", pos, {"strength": strength})
            try:
                block = level.get_block_state(pos).block
                if not isinstance(block, TargetBlock):
                    info.detail["info"] = "skipped: no target block"
                elif not block.hit(level, pos, strength, ticks):
                    info.detail["info"] = "no effect: a reset tick is pending"
            finally:
                self._end_step()
        else:
            wrapper = level.tickers[self.be_index]
            info = self._begin_step("block_entity", wrapper.pos, {})
            try:
                wrapper.tick(level)
                self.be_index += 1
            finally:
                self._end_step()
        self._settle()
        return info

    def _settle(self) -> None:
        """Advance through phases that have no work left (no game logic runs here)."""
        level = self.level
        while True:
            if self.phase is Phase.BLOCK_TICKS:
                if level.block_ticks.to_run:
                    return
                level.block_ticks.cleanup_after_tick()
                self.phase = Phase.BLOCK_EVENTS
            elif self.phase is Phase.BLOCK_EVENTS:
                if level.block_events:
                    return
                level.handling_tick = False
                self.phase = Phase.ENTITIES  # ServerLevel.tick: entities after block events
                # Entities standing on plates step on them (Entity.applyEffectsFromBlocks).
                level.plate_visitors = {
                    p: v for p, v in level.plate_visitors.items() if v[2] >= level.game_time
                }
                level.entity_queue = list(level.plate_visitors)
            elif self.phase is Phase.ENTITIES:
                if level.zero_tick_ends or level.projectile_hits or level.entity_queue:
                    return
                # Level.tickBlockEntities L527: pending tickers join the list first.
                level.ticking_block_entities = True
                level.tickers.extend(level.pending_tickers)
                level.pending_tickers.clear()
                self.be_index = 0
                self.phase = Phase.BLOCK_ENTITIES
            elif self.phase is Phase.BLOCK_ENTITIES:
                while self.be_index < len(level.tickers):
                    if level.tickers[self.be_index].is_removed():
                        del level.tickers[self.be_index]
                    else:
                        return
                level.ticking_block_entities = False
                self.phase = Phase.BETWEEN_TICKS
            else:
                return

    def _begin_step(self, kind: str, pos: Pos | None, detail: dict[str, Any]) -> StepInfo:
        trace = self.level.trace
        trace.step = self.step_index
        trace.game_time = self.level.game_time
        record = trace.emit(tr.STEP, pos, parent=None, kind=kind, **detail)
        trace.push(record)
        info = StepInfo(self.step_index, kind, self.level.game_time, pos, detail, record)
        self.step_index += 1
        return info

    def _end_step(self) -> None:
        self.level.trace.pop()

    def finish_tick(self) -> list[StepInfo]:
        """Run steps until the current tick is complete (no-op between ticks)."""
        steps: list[StepInfo] = []
        while self.phase is not Phase.BETWEEN_TICKS:
            steps.append(self.step())
        return steps

    def run_tick(self) -> list[StepInfo]:
        """Finish the current tick, or run one whole tick when between ticks."""
        if self.phase is Phase.BETWEEN_TICKS:
            steps = [self.step()]
            steps += self.finish_tick()
            return steps
        return self.finish_tick()

    def run_ticks(self, count: int) -> None:
        for _ in range(count):
            self.run_tick()

    # ------------------------------------------------------------------ player actions
    def apply(self, action: Action) -> StepInfo:
        """Apply a player action between ticks (``ActionError`` otherwise)."""
        from redsim.world.blocks import parse_state

        if self.phase is not Phase.BETWEEN_TICKS:
            raise ActionError("player actions happen between ticks; finish the tick first")
        level = self.level
        if not level.is_in_valid_bounds(action.pos):
            raise ActionError(f"position {action.pos} is outside the world")
        info = self._begin_step("action", action.pos, {"action": action.kind, "info": action.kind})
        try:
            if action.kind == "place":
                assert action.state is not None
                self._place(action.pos, parse_state(action.state))
            elif action.kind == "break":
                self._break(action.pos)
            elif action.kind == "use":
                state = level.get_block_state(action.pos)
                if not state.block.use_without_item(state, level, action.pos):
                    info.detail["info"] = "use: no effect"
            elif action.kind == "setblock":
                assert action.state is not None
                nbt = action.payload.get("nbt") if action.payload else None
                if not self._setblock_command(action.pos, action.state, nbt):
                    info.detail["info"] = "setblock: no change"
            elif action.kind == "sign_text":
                from redsim.world.blocks.sign import SignBlockEntity

                entity = level.get_block_entity(action.pos)
                if not isinstance(entity, SignBlockEntity):
                    raise ActionError(f"no sign at {action.pos}")
                payload = action.payload
                entity.set_text(level, str(payload.get("side", "front")), list(payload["lines"]))
            elif action.kind == "container_item":
                self._container_item(action.pos, action.payload)
            elif action.kind == "lectern_page":
                self._lectern_page(action.pos, int(action.payload["page"]))
            elif action.kind == "power_pulse":
                # Editor power at the position for ``ticks`` ticks (sequences, not vanilla).
                payload = action.payload
                ticks = int(payload["ticks"])
                if payload.get("muted"):  # bypassed: kept in the timeline, no effect
                    info.detail["info"] = "muted pulse: skipped"
                elif ticks == 0:  # a 0-tick pulse: on and off inside the next tick
                    level.zero_tick_pulses.append((action.pos, int(payload["strength"])))
                else:
                    level.force_power(action.pos, int(payload["strength"]), level.game_time + ticks)
            elif action.kind == "plate_visitors":
                # Entities step on the plate from the next tick on, for ``ticks`` ticks.
                payload = action.payload
                until = level.game_time + int(payload["ticks"])
                level.plate_visitors[action.pos] = (
                    int(payload["mobs"]),
                    int(payload.get("others", 0)),
                    until,
                )
            elif action.kind == "projectile_hit":
                # A projectile launched now hits during the next tick's entity phase.
                strength, ticks = int(action.payload["strength"]), int(action.payload["ticks"])
                level.projectile_hits.append((action.pos, strength, ticks))
            elif action.kind == "transform_region":
                payload = action.payload
                pivot = payload.get("pivot2")
                self._transform_region(
                    tuple(payload["begin"]),
                    tuple(payload["end"]),
                    int(payload.get("quarter_turns", 0)),
                    payload.get("mirror"),
                    (int(pivot[0]), int(pivot[1])) if pivot else None,
                )
            elif action.kind == "transform_regions":
                payload = action.payload
                pivot = payload.get("pivot2")
                self._transform_regions(
                    [(tuple(b[0]), tuple(b[1])) for b in payload["boxes"]],
                    tuple(payload.get("offset", (0, 0, 0))),
                    int(payload.get("quarter_turns", 0)),
                    payload.get("mirror"),
                    (int(pivot[0]), int(pivot[1])) if pivot else None,
                    bool(payload.get("copy", False)),
                )
            elif action.kind == "stack_region":
                payload = action.payload
                step = tuple(payload["step"])
                low = tuple(payload["begin"])
                for i in range(1, int(payload["count"]) + 1):
                    target = (low[0] + step[0] * i, low[1] + step[1] * i, low[2] + step[2] * i)
                    self._clone_region_command(low, tuple(payload["end"]), target, "force", True)
            elif action.kind == "fill":
                assert action.state is not None
                tx, ty, tz = action.payload["to"]
                self._fill_command(action.pos, (tx, ty, tz), action.state)
            elif action.kind == "clone":
                self._clone_command(action.pos, action.payload)
            elif action.kind == "clone_region":
                payload = action.payload
                begin, end = tuple(payload["begin"]), tuple(payload["end"])
                strict = bool(payload.get("strict", False))
                count = self._clone_region_command(begin, end, action.pos, payload["mode"], strict)
                info.detail["info"] = f"clone {payload['mode']}: {count} blocks"
            elif action.kind == "set_block":
                assert action.state is not None
                level.set_block(action.pos, parse_state(action.state), action.flags)
            else:
                raise ActionError(f"unknown action {action.kind}")
        finally:
            self._end_step()
        return info

    def _place(self, pos: Pos, requested: BlockState) -> None:
        """``BlockItem.place`` (BlockItem.java L55) with an editor-chosen orientation."""
        level = self.level
        current = level.get_block_state(pos)
        if not current.is_air:
            raise ActionError(f"position {pos} is occupied by {current.block.name}")
        state = requested.block.get_state_for_placement(PlacementContext(level, pos, requested))
        if state is None or not state.can_survive(level, pos):
            raise ActionError(f"{requested.block.name} cannot be placed at {pos} (no support)")
        if not level.set_block(pos, state, UpdateFlags.ALL_IMMEDIATE):
            raise ActionError(f"placing {requested.block.name} at {pos} failed")
        placed = level.get_block_state(pos)
        if placed.is_(state.block):
            placed.block.set_placed_by(level, pos, placed)

    def _setblock_command(self, pos: Pos, text: str, nbt: dict[str, Any] | None = None) -> bool:
        """``SetBlockCommand.setBlock`` (replace mode, not strict): ``BlockInput.place`` with
        flags 2|256 (shape-adjusted state, explicit properties re-applied, then the block
        entity data loaded; ``setChanged`` only if the data changed, ``BlockInput`` L79), then
        ``updateNeighboursOnBlockSet``."""
        from redsim.world.blocks import parse_state_explicit

        level = self.level
        state, explicit = parse_state_explicit(text)
        old_state = level.get_block_state(pos)
        placed = level.update_from_neighbour_shapes(state, pos)
        if placed.is_air:
            placed = state
        if placed is not state:
            for prop in explicit:
                placed = placed.with_(prop, state.get(prop))
        flags = UpdateFlags.CLIENTS | UpdateFlags.SKIP_BLOCK_ENTITY_SIDEEFFECTS
        affected = level.set_block(pos, placed, flags)
        if nbt is not None:
            entity = level.get_block_entity(pos)
            if entity is not None:
                before = entity.to_json()
                entity.load_json(nbt)
                if entity.to_json() != before:
                    affected = True
                    current = level.get_block_state(pos)
                    if not current.is_air:  # BlockEntity.setChanged
                        level.update_neighbour_for_output_signal(pos, current.block)
        if not affected:
            return False  # "Could not set the block": no neighbor updates either
        level.update_neighbours_on_block_set(pos, old_state)
        return True

    def _container_item(self, pos: Pos, payload: dict[str, Any]) -> None:
        """``/item replace block``: ``Container.setItem`` on one slot (barrels call
        ``setChanged``, hoppers do not)."""
        from redsim.world.blocks.container import ContainerBlockEntity

        entity = self.level.get_block_entity(pos)
        if not isinstance(entity, ContainerBlockEntity):
            raise ActionError(f"no container at {pos}")
        slot = int(payload["slot"])
        if not 0 <= slot < entity.SIZE:
            raise ActionError(f"slot {slot} does not exist")
        item = payload.get("item")
        entity.set_item(self.level, slot, (item, int(payload["count"])) if item else None)

    def _lectern_page(self, pos: Pos, page: int) -> None:
        """A player turning the page (``LecternMenu`` → ``LecternBlockEntity.setPage``)."""
        from redsim.world.blocks.lectern import LecternBlockEntity

        entity = self.level.get_block_entity(pos)
        if not isinstance(entity, LecternBlockEntity) or not entity.has_book():
            raise ActionError(f"no lectern with a book at {pos}")
        entity.set_page(self.level, page)

    def _fill_command(self, corner_a: Pos, corner_b: Pos, text: str) -> None:
        """``FillCommand.fillBlocks`` (replace mode, not strict): place every position like
        ``/setblock`` (x fastest, then y, then z), then ``updateNeighboursOnBlockSet`` for all
        changed positions in the same order."""
        from redsim.world.blocks import parse_state_explicit

        level = self.level
        state, explicit = parse_state_explicit(text)
        (x0, x1), (y0, y1), (z0, z1) = (sorted(p) for p in zip(corner_a, corner_b, strict=True))
        updated: list[tuple[Pos, BlockState]] = []
        for z in range(z0, z1 + 1):
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    pos = (x, y, z)
                    old_state = level.get_block_state(pos)
                    if self._block_input_place(pos, state, explicit):
                        updated.append((pos, old_state))
        for pos, old_state in updated:
            level.update_neighbours_on_block_set(pos, old_state)

    def _block_input_place(self, pos: Pos, state: BlockState, explicit: list[Any]) -> bool:
        """``BlockInput.place`` with flags 2|256 (shape-adjusted, explicit props kept)."""
        level = self.level
        placed = level.update_from_neighbour_shapes(state, pos)
        if placed.is_air:
            placed = state
        if placed is not state:
            for prop in explicit:
                placed = placed.with_(prop, state.get(prop))
        flags = UpdateFlags.CLIENTS | UpdateFlags.SKIP_BLOCK_ENTITY_SIDEEFFECTS
        return level.set_block(pos, placed, flags)

    def _clone_command(self, destination: Pos, payload: dict[str, Any]) -> None:
        """Placement half of ``CloneCommands.clone`` (replace mode, not strict).

        ``payload["blocks"]`` lists ``[dx, dy, dz, state, block_entity_data | None]`` in source
        iteration order (z outer, then y, then x). Blocks are grouped like the command does:
        solid (full collision), then blocks with block entities, then the rest; then
        ``_clone_place`` runs the placement passes.
        """
        from redsim.world import blocks

        level = self.level
        solid, entities, other = [], [], []
        for dx, dy, dz, text, entity_data in payload["blocks"]:
            pos = (destination[0] + dx, destination[1] + dy, destination[2] + dz)
            state = blocks.parse_state(text)
            info = (pos, state, entity_data, level.get_block_state(pos))
            if state.has_block_entity:
                entities.append(info)
            elif not state.is_collision_shape_full_block():
                other.append(info)
            else:
                solid.append(info)
        self._clone_place(solid, entities, other, bool(payload.get("strict", False)))

    def _clone_region_command(
        self, begin: Pos, end: Pos, destination: Pos, mode: str, strict: bool = False
    ) -> int:
        """``CloneCommands.clone`` (L198) in replace mode, not strict, within this level.

        Reads the source live (z outer, then y, then x). Classification: blocks with a block
        entity; else "other" when the collision shape is not a full block (the game also
        requires ``!isSolidRender``, which only differs for blocks with a full occlusion but
        partial collision shape, none of which are in scope); else solid. The clear list gets
        "other" positions at the front and the rest at the back. ``move`` first sets every
        cleared position to barrier (flags 818), then to air (flags 3; strict: 818), then
        places as usual. Finally the scheduled ticks inside the source box are copied
        (``copyAreaFrom``). Returns the number of blocks set.
        """
        from redsim.world import blocks

        if mode not in CLONE_MODES:
            raise ActionError(f"unknown clone mode {mode!r}")
        level = self.level
        low = (min(begin[0], end[0]), min(begin[1], end[1]), min(begin[2], end[2]))
        high = (max(begin[0], end[0]), max(begin[1], end[1]), max(begin[2], end[2]))
        offset = (destination[0] - low[0], destination[1] - low[1], destination[2] - low[2])
        dest_high = (high[0] + offset[0], high[1] + offset[1], high[2] + offset[2])
        overlaps = all(destination[i] <= high[i] and low[i] <= dest_high[i] for i in range(3))
        if mode == "normal" and overlaps:
            raise ActionError("The source and destination areas cannot overlap")
        area = (high[0] - low[0] + 1) * (high[1] - low[1] + 1) * (high[2] - low[2] + 1)
        if area > MAX_BLOCK_MODIFICATIONS:
            raise ActionError(f"Too many blocks in the specified area ({area} > 32768)")
        solid, entities, other = [], [], []
        clear: deque[Pos] = deque()
        for z in range(low[2], high[2] + 1):
            for y in range(low[1], high[1] + 1):
                for x in range(low[0], high[0] + 1):
                    source = (x, y, z)
                    target = (x + offset[0], y + offset[1], z + offset[2])
                    state = level.get_block_state(source)
                    entity = level.get_block_entity(source)
                    previous = level.get_block_state(target)
                    if entity is not None:
                        entities.append((target, state, entity.to_json(), previous))
                        clear.append(source)
                    elif not state.is_collision_shape_full_block():
                        other.append((target, state, None, previous))
                        clear.appendleft(source)
                    else:
                        solid.append((target, state, None, previous))
                        clear.append(source)
        if mode == "move":
            barrier, air = blocks.BARRIER.default_state, blocks.AIR.default_state
            for pos in clear:
                level.set_block(pos, barrier, STRICT_FLAGS)
            for pos in clear:
                level.set_block(pos, air, STRICT_FLAGS if strict else UpdateFlags.ALL)
        count = self._clone_place(solid, entities, other, strict)
        level.block_ticks.copy_area(low, high, offset)
        return count

    def _transform_region(
        self,
        begin: Pos,
        end: Pos,
        quarter_turns: int,
        mirror: str | None,
        pivot2: tuple[int, int] | None = None,
    ) -> tuple[Pos, Pos]:
        """Rotate and/or mirror a region in place (editor tool, strict: no block updates);
        see ``_transform_regions``. Returns the new box."""
        return self._transform_regions([(begin, end)], (0, 0, 0), quarter_turns, mirror, pivot2)[0]

    def _transform_regions(
        self,
        boxes: list[tuple[Pos, Pos]],
        offset: Pos,
        quarter_turns: int,
        mirror: str | None,
        pivot2: tuple[int, int] | None = None,
        copy: bool = False,
    ) -> list[tuple[Pos, Pos]]:
        """Move several boxes together (editor tool, strict: no block updates).

        Captures states, block-entity data and pending ticks of every cell in a box (each
        cell once, in z/y/x order over the boxes' bounding box); clears them (air, flags
        818) unless ``copy``; places the transformed blocks with the ``/clone`` placement
        passes in strict mode; schedules the ticks at their blocks' new places (copied
        ticks sort after the existing ones, as ``/clone`` does). Mirroring happens first
        (within the bounding box), then the clockwise rotation around ``pivot2`` (twice
        the x/z point; default: the bounding box's center, ``rotation.default_pivot2``),
        then the shift by ``offset``. Returns the boxes at their new places."""
        from redsim.world import blocks
        from redsim.world.rotation import (
            default_pivot2,
            mirror_state,
            rotate_about,
            rotate_state,
            transformed_boxes,
        )

        level = self.level
        boxes = [
            (
                (min(b[0], e[0]), min(b[1], e[1]), min(b[2], e[2])),
                (max(b[0], e[0]), max(b[1], e[1]), max(b[2], e[2])),
            )
            for b, e in boxes
        ]
        low = tuple(min(box[0][i] for box in boxes) for i in range(3))
        high = tuple(max(box[1][i] for box in boxes) for i in range(3))
        cells = sum((h[0] - lo[0] + 1) * (h[1] - lo[1] + 1) * (h[2] - lo[2] + 1) for lo, h in boxes)
        if cells > MAX_BLOCK_MODIFICATIONS:
            raise ActionError("Too many blocks in the selection (more than 32768)")
        turns = quarter_turns % 4
        pivot = pivot2 if pivot2 is not None else default_pivot2(low, high)  # type: ignore[arg-type]

        def inside(pos: Pos) -> bool:
            return any(all(lo[i] <= pos[i] <= h[i] for i in range(3)) for lo, h in boxes)

        def new_pos(pos: Pos) -> Pos:
            x, y, z = pos
            if mirror == "x":
                x = low[0] + high[0] - x
            elif mirror == "z":
                z = low[2] + high[2] - z
            x, y, z = rotate_about((x, y, z), pivot, turns)
            return (x + offset[0], y + offset[1], z + offset[2])

        captured = []
        for z in range(low[2], high[2] + 1):
            for y in range(low[1], high[1] + 1):
                for x in range(low[0], high[0] + 1):
                    pos = (x, y, z)
                    if len(boxes) > 1 and not inside(pos):
                        continue
                    state = level.get_block_state(pos)
                    entity = level.get_block_entity(pos, create=False)
                    data = entity.to_json() if entity is not None else None
                    captured.append((pos, state, data))
        if copy:
            ticks = [t for t in level.block_ticks.pending() if inside(t.pos)]
        else:
            ticks = [t for lo, h in boxes for t in level.block_ticks.take_in_box(lo, h)]
            air = blocks.AIR.default_state
            for pos, _, _ in captured:
                level.set_block(pos, air, STRICT_FLAGS)
        solid, entities, other = [], [], []
        for pos, state, data in captured:
            if mirror is not None:
                state = mirror_state(state, mirror)
            state = rotate_state(state, turns)
            target = new_pos(pos)
            info = (target, state, data, level.get_block_state(target))
            if state.has_block_entity:
                entities.append(info)
            elif not state.is_collision_shape_full_block():
                other.append(info)
            else:
                solid.append(info)
        self._clone_place(solid, entities, other, strict=True)
        shift = 0
        if copy and ticks:  # after every pending tick, keeping their order (copyAreaFrom)
            pending = level.block_ticks.pending()
            shift = max(t.sub_tick for t in pending) + 1 - min(t.sub_tick for t in ticks)
        for tick in ticks:
            moved = ScheduledTick(
                tick.block_id,
                new_pos(tick.pos),
                tick.trigger_tick,
                tick.priority,
                tick.sub_tick + shift,
            )
            level.block_ticks.schedule(moved)
        return transformed_boxes(boxes, offset, turns, mirror, pivot)

    def _clone_place(
        self,
        solid: list[tuple[Pos, BlockState, Any, BlockState]],
        entities: list[tuple[Pos, BlockState, Any, BlockState]],
        other: list[tuple[Pos, BlockState, Any, BlockState]],
        strict: bool = False,
    ) -> int:
        """Placement passes of ``CloneCommands.clone``: barriers in reverse order (flags
        818), every block with flags 2 (strict: 818, i.e. no shape updates, no ``onPlace``),
        block-entity data loaded (``setChanged``, also when strict) and the state set again,
        then, unless strict, ``updateNeighboursOnBlockSet`` in reverse order with the state
        found at the destination before the clone. Returns the number of blocks set."""
        from redsim.world import blocks

        level = self.level
        flags = STRICT_FLAGS if strict else UpdateFlags.CLIENTS
        ordered = solid + entities + other
        barrier = blocks.BARRIER.default_state
        for pos, _, _, _ in reversed(ordered):
            level.set_block(pos, barrier, STRICT_FLAGS)
        count = 0
        for pos, state, _, _ in ordered:
            if level.set_block(pos, state, flags):
                count += 1
        for pos, state, entity_data, _ in entities:
            entity = level.get_block_entity(pos)
            if entity is None and strict and entity_data and state.block is blocks.MOVING_PISTON:
                # Editor tool (strict clones: drags, pastes), not vanilla: a moving piston
                # keeps its movement. The game's /clone leaves a moving_piston without its
                # block entity (an invisible "block 36" that never finishes).
                from redsim.world.blocks.piston import PistonMovingBlockEntity

                entity = PistonMovingBlockEntity(pos, state)
                level.set_block_entity(entity)
            if entity_data is not None and entity is not None:
                entity.load_json(entity_data)
                if not state.is_air:  # BlockEntity.setChanged
                    level.update_neighbour_for_output_signal(pos, state.block)
            level.set_block(pos, state, flags)
        if not strict:
            for pos, _, _, previous in reversed(ordered):
                level.update_neighbours_on_block_set(pos, previous)
        return count

    def _break(self, pos: Pos) -> None:
        """``ServerPlayerGameMode.destroyBlock`` (L286)."""
        level = self.level
        state = level.get_block_state(pos)
        if state.is_air:
            raise ActionError(f"nothing to break at {pos}")
        adjusted = state.block.player_will_destroy(level, pos, state)
        if level.remove_block(pos, False):
            state.block.destroy(level, pos, adjusted)

    # ------------------------------------------------------------------ snapshots
    def snapshot(self) -> EngineSnapshot:
        return EngineSnapshot(self.level.clone(), self.phase, self.step_index, self.be_index)

    def restore(self, snapshot: EngineSnapshot) -> None:
        trace = self.level.trace
        self.level = snapshot.level.clone()
        self.level.trace = trace
        trace.game_time = self.level.game_time
        self.phase = snapshot.phase
        self.step_index = snapshot.step_index
        self.be_index = snapshot.be_index


@dataclass(frozen=True)
class EngineSnapshot:
    level: Level
    phase: Phase
    step_index: int
    be_index: int
