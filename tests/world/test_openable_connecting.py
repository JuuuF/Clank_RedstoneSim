"""Doors, trapdoors, fence gates, fences, bars, panes and walls: the player-side paths the
test server cannot run (it has no player): placement, hand use and breaking, following
``DoorBlock``, ``TrapDoorBlock``, ``FenceGateBlock``, ``FenceBlock``, ``IronBarsBlock`` and
``WallBlock``. Redstone, shape updates and pistons are compared with the game in
EXP-052/EXP-053."""

from __future__ import annotations

from redsim.core.direction import Direction
from redsim.editor.document import Document
from redsim.editor.placement import PlaceRequest
from redsim.world import blocks
from redsim.world.rotation import mirror_state, rotate_state

P = blocks.parse_state


def look(
    yaw: float, face: Direction = Direction.UP, click: tuple[float, ...] | None = None
) -> PlaceRequest:
    return PlaceRequest(face, yaw, 30.0, click=click)  # type: ignore[arg-type]


def test_a_placed_door_gets_both_halves_and_its_hinge() -> None:
    doc = Document.new_flat()
    door = blocks.get("oak_door")
    # Looking north (yaw 180), a stone on the left (west) and above it: hinge right… the
    # balance counts full blocks right minus left: two on the left → hinge left.
    doc.setblock((-1, 1, 0), P("stone"))
    doc.setblock((-1, 2, 0), P("stone"))
    doc.place((0, 1, 0), door, look(180.0))
    lower, upper = doc.state_at((0, 1, 0)), doc.state_at((0, 2, 0))
    assert (
        repr(lower)
        == "minecraft:oak_door[half=lower,facing=north,open=false,hinge=left,powered=false]"
    )
    assert (
        repr(upper)
        == "minecraft:oak_door[half=upper,facing=north,open=false,hinge=left,powered=false]"
    )
    # With nothing beside it, the click decides: looking north, a click on the east half
    # (x > 0.5) puts the hinge on the right.
    doc.place((4, 1, 0), door, look(180.0, click=(4.8, 1.0, 0.5)))
    assert "hinge=right" in repr(doc.state_at((4, 1, 0)))
    doc.place((6, 1, 0), door, look(180.0, click=(6.2, 1.0, 0.5)))
    assert "hinge=left" in repr(doc.state_at((6, 1, 0)))
    # No room above: it cannot be placed.
    doc.setblock((8, 2, 0), P("stone"))
    assert blocks.get("oak_door").player_placement(look(0.0), doc.level, (8, 1, 0)) is None  # type: ignore[attr-defined]


def test_doors_open_by_hand_except_iron_and_break_as_a_pair() -> None:
    doc = Document.new_flat()
    doc.place((0, 1, 0), blocks.get("oak_door"), look(0.0))
    doc.place((3, 1, 0), blocks.get("iron_door"), look(0.0))
    doc.run_ticks(1)
    doc.use((0, 2, 0))  # the upper half: both halves open
    assert "open=true" in repr(doc.state_at((0, 1, 0))) and "open=true" in repr(
        doc.state_at((0, 2, 0))
    )
    doc.use((3, 1, 0))  # iron: needs redstone
    assert "open=false" in repr(doc.state_at((3, 1, 0)))
    doc.break_block((0, 2, 0))  # creative: the lower half goes first (no drop)
    assert doc.state_at((0, 1, 0)).is_air and doc.state_at((0, 2, 0)).is_air


def test_a_door_placed_next_to_power_is_open() -> None:
    doc = Document.new_flat()
    doc.setblock((1, 2, 0), P("redstone_block"))  # beside the upper half
    doc.place((0, 1, 0), blocks.get("oak_door"), look(0.0))
    assert "open=true,hinge" in repr(doc.state_at((0, 1, 0)))
    assert "powered=true" in repr(doc.state_at((0, 2, 0)))


def test_trapdoors_hang_where_clicked_and_toggle() -> None:
    doc = Document.new_flat()
    trapdoor = blocks.get("oak_trapdoor")
    # Against the east face of a block to the west, clicked high: the top half.
    doc.setblock((-1, 1, 0), P("stone"))
    doc.place((0, 1, 0), trapdoor, look(90.0, Direction.EAST, click=(0.0, 1.8, 0.5)))
    assert repr(doc.state_at((0, 1, 0))).startswith(
        "minecraft:oak_trapdoor[facing=east,open=false,half=top"
    )
    # On top of a block: faces away from the player, bottom half.
    doc.place((3, 1, 0), trapdoor, look(0.0))
    assert repr(doc.state_at((3, 1, 0))).startswith(
        "minecraft:oak_trapdoor[facing=north,open=false,half=bottom"
    )
    doc.run_ticks(1)
    doc.use((3, 1, 0))
    assert "open=true" in repr(doc.state_at((3, 1, 0)))
    doc.place((5, 1, 0), blocks.get("iron_trapdoor"), look(0.0))
    doc.use((5, 1, 0))
    assert "open=false" in repr(doc.state_at((5, 1, 0)))


def test_fence_gates_open_away_from_the_player() -> None:
    doc = Document.new_flat()
    doc.place((0, 1, 0), blocks.get("oak_fence_gate"), look(180.0))  # faces north
    doc.run_ticks(1)
    doc.use((0, 1, 0), yaw=0.0)  # the player looks south, from the north: it turns south
    assert repr(doc.state_at((0, 1, 0))).startswith(
        "minecraft:oak_fence_gate[facing=south,open=true"
    )
    doc.use((0, 1, 0), yaw=0.0)
    assert "open=false" in repr(doc.state_at((0, 1, 0)))
    doc.setblock((4, 1, 0), P("cobblestone_wall"))
    doc.place((5, 1, 0), blocks.get("oak_fence_gate"), look(180.0))
    assert "in_wall=true" in repr(doc.state_at((5, 1, 0)))


def test_fences_and_walls_connect_when_placed_and_turn_with_the_selection() -> None:
    doc = Document.new_flat()
    doc.setblock((1, 1, 0), P("stone"))
    doc.place((0, 1, 0), blocks.get("oak_fence"), look(0.0))
    fence = doc.state_at((0, 1, 0))
    assert "east=true" in repr(fence) and "north=false" in repr(fence)
    assert "south=true" in repr(rotate_state(fence, 1)) and "east=false" in repr(
        rotate_state(fence, 1)
    )
    assert "west=true" in repr(mirror_state(fence, "x"))
    doc.place((0, 1, 3), blocks.get("cobblestone_wall"), look(0.0))
    doc.place((1, 1, 3), blocks.get("cobblestone_wall"), look(0.0))
    wall = doc.state_at((0, 1, 3))
    assert "east=low" in repr(wall) and "up=true" in repr(wall)
    assert "south=low" in repr(rotate_state(wall, 1))
    doc.place((0, 1, 6), blocks.get("glass_pane"), look(0.0))
    doc.place((1, 1, 6), blocks.get("iron_bars"), look(0.0))
    assert "east=true" in repr(doc.state_at((0, 1, 6)))


def test_placing_a_given_state_still_applies_the_placement_rules() -> None:
    """``place_state`` (the command line's ``place``) gives the orientation directly; the
    rest still follows ``getStateForPlacement``: open and powered only with a signal, a
    gate in a wall, leaves persistent, a campfire lit."""
    doc = Document.new_flat()
    doc.place_state((0, 1, 0), P("oak_door[facing=east,hinge=right,open=true]"))
    assert repr(doc.state_at((0, 1, 0))) == (
        "minecraft:oak_door[half=lower,facing=east,open=false,hinge=right,powered=false]"
    )
    assert "half=upper" in repr(doc.state_at((0, 2, 0)))
    doc.place_state((3, 1, 0), P("oak_trapdoor[facing=south,half=top,open=true]"))
    assert repr(doc.state_at((3, 1, 0))) == (
        "minecraft:oak_trapdoor[facing=south,open=false,half=top,powered=false,waterlogged=false]"
    )
    doc.setblock((5, 1, 1), P("redstone_block"))
    doc.place_state((5, 1, 0), P("oak_trapdoor"))
    assert "open=true" in repr(doc.state_at((5, 1, 0)))  # powered: placed open
    doc.setblock((7, 1, 1), P("cobblestone_wall"))
    doc.place_state((7, 1, 0), P("oak_fence_gate[facing=west,open=true]"))
    assert repr(doc.state_at((7, 1, 0))) == (
        "minecraft:oak_fence_gate[facing=west,open=false,powered=false,in_wall=true]"
    )
    doc.place_state((0, 1, 3), P("oak_leaves[persistent=false]"))
    assert "persistent=true" in repr(doc.state_at((0, 1, 3)))
    doc.place_state((2, 1, 3), P("campfire[facing=east,lit=false]"))
    assert repr(doc.state_at((2, 1, 3))) == (
        "minecraft:campfire[lit=true,signal_fire=false,waterlogged=false,facing=east]"
    )


def test_a_wall_reads_a_moving_piston_above_it_with_the_level() -> None:
    """LegDen's 8x8 door (EXP-068): a retracting sticky piston above a wall becomes a moving
    piston whose collision shape (from its block entity) is the extended base, so the
    wall's sides under it stay tall; the context-free shape of a moving piston is empty."""
    from redsim.sim.engine import Action, Engine

    engine = Engine()
    for pos, text in (
        ((0, 0, 0), "stone"), ((1, 0, 0), "stone"), ((1, 0, -1), "stone"),
        ((1, 0, 1), "observer[facing=north]"),
        ((1, 1, 0), "sticky_piston[facing=north,extended=true]"),
        ((1, 1, -1), "piston_head[facing=north,type=sticky]"), ((2, 1, 0), "redstone_block"),
        ((1, 0, 0), "stone_brick_wall"),
    ):  # fmt: skip
        engine.apply(Action("setblock", pos, text))
    wall = engine.level.get_block_state((1, 0, 0)).properties_dict()
    assert (wall["north"], wall["west"], wall["south"]) == ("low", "tall", "tall")
    engine.apply(Action("setblock", (2, 1, 0), "air"))  # the piston retracts
    engine.run_tick()
    assert engine.level.get_block_state((1, 1, 0)).block.id == "minecraft:moving_piston"
    wall = engine.level.get_block_state((1, 0, 0)).properties_dict()
    assert (wall["west"], wall["south"]) == ("tall", "tall")
