"""The F3 debug screen's text (pure Python, no Qt), like Minecraft's debug overlay.

Left column: engine and world state. Right column: the block under the cursor, with every
property, its block entity, the power it receives from each side (strong and weak), its
analog output, scheduled ticks and physical properties.
"""

from __future__ import annotations

from redsim.core.direction import ALL, Direction
from redsim.core.pos import Pos, offset
from redsim.editor.clipboard import Region
from redsim.editor.document import Document

SIDE_NAMES = {
    Direction.DOWN: "↓",
    Direction.UP: "↑",
    Direction.NORTH: "N",
    Direction.SOUTH: "S",
    Direction.WEST: "W",
    Direction.EAST: "E",
}


def world_lines(
    document: Document,
    rates: str,
    camera: str,
    mode: str,
    region: Region | None,
    confirmed: bool,
) -> list[str]:
    engine, history, level = document.engine, document.history, document.level
    lines = [
        "Redstone Simulator (Minecraft Java 26.3 rules)",
        rates,
        f"Game time: {engine.game_time} · phase: {engine.phase.value}",
        f"Engine step: {history.position} of {history.end} · next: {engine.peek_next_step()}",
        f"Scheduled ticks: {level.block_ticks.count()} pending · block events: "
        f"{len(level.block_events)} · ticking block entities: {len(level.tickers)}",
        f"Blocks: {len(level.blocks)} · block entities: {len(level.block_entities)}",
        camera,
        f"Mode: {mode.upper()}",
    ]
    if region is not None:
        x, y, z = region.size
        state = " (confirmed)" if confirmed else ""
        lines.append(f"Selection: {x}×{y}×{z} = {x * y * z} blocks{state}")
    return lines


def block_lines(document: Document, pos: Pos) -> list[str]:
    level = document.level
    state = level.get_block_state(pos)
    lines = [f"Targeted block: {pos[0]}, {pos[1]}, {pos[2]}", state.block.id]
    for prop in state.block.properties:
        lines.append(f"{prop.name}: {prop.serialize(state.get(prop))}")
    entity = level.get_block_entity(pos, create=False)
    if entity is not None:
        lines.append(f"Block entity: {entity.describe()}")
    if state.has_analog_output_signal():
        analog = state.block.get_analog_output_signal(state, level, pos, Direction.NORTH)
        lines.append(f"Analog output (comparator reading): {analog}")
    strong = " ".join(f"{SIDE_NAMES[d]}{level.get_direct_signal(offset(pos, d), d)}" for d in ALL)
    weak = " ".join(f"{SIDE_NAMES[d]}{level.get_signal(offset(pos, d), d)}" for d in ALL)
    lines.append(f"Receives strong: {strong}")
    lines.append(f"Receives weak:   {weak}")
    lines.append(f"Best neighbor signal: {level.get_best_neighbor_signal(pos)}")
    pending = [t for t in level.block_ticks.pending() if t.pos == pos]
    for tick in pending:
        lines.append(
            f"Scheduled tick: at {tick.trigger_tick} ({tick.priority.name}, sub {tick.sub_tick})"
        )
    lines.append(
        f"Conductor: {'yes' if state.is_redstone_conductor(level, pos) else 'no'} · "
        f"solid: {'yes' if state.is_solid() else 'no'} · "
        f"push: {state.get_piston_push_reaction().name}"
    )
    return lines
