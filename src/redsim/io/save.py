"""Save and load the complete engine state as JSON.

A save captures everything that influences future behavior, so loading and continuing
reproduces the original run exactly, even when saved in the middle of a tick:

* blocks (``id[prop=value]`` strings through a palette), block entities (type, position,
  cached state, removed flag, data);
* scheduled ticks (pending, in drain order) and the ticks already collected for the
  current tick (``to_run``, in run order);
* queued block events (in order), the block-entity ticker list, pending tickers and the
  per-position wrapper map (wrapper identity matters for rebinding);
* game time, sub-tick counter, torch toggle list, phase flags and the engine position
  (phase, step index, block-entity iteration index).

The trace is not saved. ``extra`` carries editor data (annotations, camera), opaque here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from redsim.core.pos import Pos
from redsim.sim.engine import Engine, Phase
from redsim.sim.level import Level, TickerWrapper, _BoundTicker
from redsim.sim.ticks import ScheduledTick, TickPriority
from redsim.world import blocks
from redsim.world.block_entity import BLOCK_ENTITY_TYPES, BlockEntity

FORMAT = "redsim-save"
VERSION = 1


def _pos(value: list[int]) -> Pos:
    x, y, z = value
    return (int(x), int(y), int(z))


def _tick_to_json(tick: ScheduledTick) -> dict[str, Any]:
    return {
        "block": tick.block_id,
        "pos": list(tick.pos),
        "trigger_tick": tick.trigger_tick,
        "priority": tick.priority.name,
        "sub_tick": tick.sub_tick,
    }


def _tick_from_json(data: dict[str, Any]) -> ScheduledTick:
    return ScheduledTick(
        data["block"],
        _pos(data["pos"]),
        int(data["trigger_tick"]),
        TickPriority[data["priority"]],
        int(data["sub_tick"]),
    )


def engine_to_json(engine: Engine) -> dict[str, Any]:
    level = engine.level
    palette: dict[str, int] = {}
    block_rows: list[list[int]] = []
    for pos, state in sorted(level.blocks.items()):
        key = repr(state)
        index = palette.setdefault(key, len(palette))
        block_rows.append([*pos, index])

    # Block entities: every distinct object reachable from the map or from tickers.
    entity_ids: dict[int, int] = {}
    entities: list[dict[str, Any]] = []

    def entity_id(be: BlockEntity) -> int:
        key = id(be)
        if key not in entity_ids:
            entity_ids[key] = len(entities)
            entities.append(
                {
                    "type": be.type_id,
                    "pos": list(be.pos),
                    "state": repr(be.block_state),
                    "removed": be.removed,
                    "data": be.to_json(),
                    **({"runtime": be.runtime_json()} if be.runtime_json() else {}),
                }
            )
        return entity_ids[key]

    entity_map = {f"{p[0]},{p[1]},{p[2]}": entity_id(be) for p, be in level.block_entities.items()}

    wrapper_ids: dict[int, int] = {}
    wrappers: list[int | None] = []

    def wrapper_id(wrapper: TickerWrapper) -> int:
        key = id(wrapper)
        if key not in wrapper_ids:
            wrapper_ids[key] = len(wrappers)
            ticker = wrapper.ticker
            wrappers.append(None if ticker is None else entity_id(ticker.block_entity))
        return wrapper_ids[key]

    tickers = [wrapper_id(w) for w in level.tickers]
    pending = [wrapper_id(w) for w in level.pending_tickers]
    by_pos = {f"{p[0]},{p[1]},{p[2]}": wrapper_id(w) for p, w in level.tickers_by_pos.items()}

    return {
        "format": FORMAT,
        "version": VERSION,
        "game_version": "26.3",
        "level": {
            "min_y": level.min_y,
            "max_y": level.max_y,
            "game_time": level.game_time,
            "sub_tick_count": level.sub_tick_count,
            "palette": list(palette),
            "blocks": block_rows,
            "block_entities": entities,
            "block_entity_map": entity_map,
            "scheduled_ticks": [_tick_to_json(t) for t in level.block_ticks.pending()],
            "ticks_to_run": [_tick_to_json(t) for t in level.block_ticks.to_run],
            "overdue_collected": level.block_ticks.overdue_collected,
            "block_events": [[list(p), b, b0, b1] for p, b, b0, b1 in level.block_events],
            "projectile_hits": [[list(p), s, t] for p, s, t in level.projectile_hits],
            "plate_visitors": [[list(p), *v] for p, v in level.plate_visitors.items()],
            "forced_power": [[list(p), *v] for p, v in level.forced_power.items()],
            "entity_queue": [list(p) for p in level.entity_queue],
            "wrappers": wrappers,
            "tickers": tickers,
            "pending_tickers": pending,
            "tickers_by_pos": by_pos,
            "ticking_block_entities": level.ticking_block_entities,
            "handling_tick": level.handling_tick,
            "torch_toggles": [[list(p), t] for p, t in level.torch_toggles],
            "max_chained_neighbor_updates": level.neighbor_updater.max_chained,
        },
        "engine": {
            "phase": engine.phase.name,
            "step_index": engine.step_index,
            "be_index": engine.be_index,
        },
    }


def engine_from_json(data: dict[str, Any]) -> Engine:
    if data.get("format") != FORMAT:
        raise ValueError("not a redsim save file")
    if int(data.get("version", 0)) > VERSION:
        raise ValueError(f"save version {data['version']} is newer than supported ({VERSION})")
    raw = data["level"]
    level = Level(
        min_y=int(raw["min_y"]),
        max_y=int(raw["max_y"]),
        max_chained_neighbor_updates=int(raw.get("max_chained_neighbor_updates", 1_000_000)),
    )
    level.game_time = int(raw["game_time"])
    level.sub_tick_count = int(raw["sub_tick_count"])
    level.trace.game_time = level.game_time
    palette = [blocks.parse_state(text) for text in raw["palette"]]
    for x, y, z, index in raw["blocks"]:
        level.blocks[(int(x), int(y), int(z))] = palette[index]

    entities: list[BlockEntity] = []
    for entry in raw["block_entities"]:
        cls = BLOCK_ENTITY_TYPES[entry["type"]]
        be = cls(_pos(entry["pos"]), blocks.parse_state(entry["state"]))
        be.removed = bool(entry["removed"])
        be.load_json(entry["data"])
        be.load_runtime_json(entry.get("runtime", {}))
        entities.append(be)
    for key, index in raw["block_entity_map"].items():
        level.block_entities[_pos([int(v) for v in key.split(",")])] = entities[index]

    for tick_data in raw["scheduled_ticks"]:
        level.block_ticks.schedule(_tick_from_json(tick_data))
    for tick_data in raw["ticks_to_run"]:
        level.block_ticks.restore_collected(_tick_from_json(tick_data))
    level.block_ticks.overdue_collected = int(raw.get("overdue_collected", 0))
    for p, block_id, b0, b1 in raw["block_events"]:
        level.block_events[(_pos(p), block_id, int(b0), int(b1))] = None
    for p, strength, ticks in raw.get("projectile_hits", []):
        level.projectile_hits.append((_pos(p), int(strength), int(ticks)))
    for p, mobs, others, until in raw.get("plate_visitors", []):
        level.plate_visitors[_pos(p)] = (int(mobs), int(others), int(until))
    for p, strength, until in raw.get("forced_power", []):
        level.forced_power[_pos(p)] = (int(strength), int(until))
    level.entity_queue = [_pos(p) for p in raw.get("entity_queue", [])]

    wrappers = [
        TickerWrapper(None if index is None else _BoundTicker(entities[index]))
        for index in raw["wrappers"]
    ]
    level.tickers = [wrappers[i] for i in raw["tickers"]]
    level.pending_tickers = [wrappers[i] for i in raw["pending_tickers"]]
    level.tickers_by_pos = {
        _pos([int(v) for v in key.split(",")]): wrappers[i]
        for key, i in raw["tickers_by_pos"].items()
    }
    level.ticking_block_entities = bool(raw["ticking_block_entities"])
    level.handling_tick = bool(raw["handling_tick"])
    level.torch_toggles = [(_pos(p), int(t)) for p, t in raw["torch_toggles"]]

    engine = Engine(level)
    engine.phase = Phase[data["engine"]["phase"]]
    engine.step_index = int(data["engine"]["step_index"])
    engine.be_index = int(data["engine"]["be_index"])
    return engine


def save(path: Path, engine: Engine, extra: dict[str, Any] | None = None) -> None:
    document = engine_to_json(engine)
    document["extra"] = extra or {}
    path.write_text(json.dumps(document, indent=1) + "\n")


def load(path: Path) -> tuple[Engine, dict[str, Any]]:
    document = json.loads(path.read_text())
    return engine_from_json(document), dict(document.get("extra", {}))
