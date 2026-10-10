"""Player-like placement orientation for the editor.

The game decides a placed block's orientation from the player's view and the clicked face
(``BlockPlaceContext``). This module ports the relevant pieces so editor placement gives
the same states a player would get:

* ``Direction.orderedByNearest`` (Direction.java L86): directions sorted by how closely the
  player looks along them;
* ``BlockPlaceContext.getNearestLookingDirections`` (L71): the opposite of the clicked face
  is moved to the front (unless replacing the clicked block);
* ``Entity.getDirection`` → ``Direction.fromYRot`` (L299): the horizontal facing;
* per-block rules: ``FaceAttachedHorizontalDirectionalBlock.getStateForPlacement`` (L34),
  ``StandingAndWallBlockItem.getPlacementState`` (torches),
  ``WallTorchBlock.getStateForPlacement``, ``DiodeBlock.getStateForPlacement`` (L153).

Yaw/pitch use Minecraft's conventions: yaw 0 looks south (+z), 90 west, 180 north,
270 east; positive pitch looks down. ``Mth.sin`` uses a 65 536-entry lookup table; this port
uses exact trigonometry, which can only differ at exact ties between two axes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.sim.level import Level
from redsim.world import blocks
from redsim.world.block import Block, BlockState, PlacementContext
from redsim.world.blocks.attached import FaceAttachedBlock
from redsim.world.blocks.diode import DiodeBlock
from redsim.world.blocks.torch import RedstoneTorchBlock, RedstoneWallTorchBlock
from redsim.world.properties import ATTACH_FACE, HORIZONTAL_FACING

_FROM_2D = (Direction.SOUTH, Direction.WEST, Direction.NORTH, Direction.EAST)


@dataclass(frozen=True)
class PlaceRequest:
    """Where and how the player clicked."""

    clicked_face: Direction  # face of the targeted block that was hit (its outward normal)
    yaw: float
    pitch: float
    replace_clicked: bool = False


def horizontal_direction(yaw: float) -> Direction:
    """``Entity.getDirection()`` = ``Direction.fromYRot(yRot)``."""
    return _FROM_2D[math.floor(yaw / 90.0 + 0.5) & 3]


def ordered_by_nearest(yaw: float, pitch: float) -> list[Direction]:
    """``Direction.orderedByNearest``."""
    pitch_rad = math.radians(pitch)
    yaw_rad = -math.radians(yaw)
    pitch_sin, pitch_cos = math.sin(pitch_rad), math.cos(pitch_rad)
    yaw_sin, yaw_cos = math.sin(yaw_rad), math.cos(yaw_rad)
    x_pos, y_pos, z_pos = yaw_sin > 0.0, pitch_sin < 0.0, yaw_cos > 0.0
    x_yaw = yaw_sin if x_pos else -yaw_sin
    y_mag = -pitch_sin if y_pos else pitch_sin
    z_yaw = yaw_cos if z_pos else -yaw_cos
    x_mag, z_mag = x_yaw * pitch_cos, z_yaw * pitch_cos
    axis_x = Direction.EAST if x_pos else Direction.WEST
    axis_y = Direction.UP if y_pos else Direction.DOWN
    axis_z = Direction.SOUTH if z_pos else Direction.NORTH

    def make(a: Direction, b: Direction, c: Direction) -> list[Direction]:
        return [a, b, c, c.opposite, b.opposite, a.opposite]

    if x_yaw > z_yaw:
        if y_mag > x_mag:
            return make(axis_y, axis_x, axis_z)
        return make(axis_x, axis_z, axis_y) if z_mag > y_mag else make(axis_x, axis_y, axis_z)
    if y_mag > z_mag:
        return make(axis_y, axis_z, axis_x)
    return make(axis_z, axis_x, axis_y) if x_mag > y_mag else make(axis_z, axis_y, axis_x)


def nearest_looking_directions(request: PlaceRequest) -> list[Direction]:
    """``BlockPlaceContext.getNearestLookingDirections``."""
    directions = ordered_by_nearest(request.yaw, request.pitch)
    if request.replace_clicked:
        return directions
    first = request.clicked_face.opposite
    directions.remove(first)
    return [first, *directions]


def placement_state(
    block: Block, request: PlaceRequest, level: Level, pos: Pos
) -> BlockState | None:
    """The state a player placing ``block`` at ``pos`` would request (``None``: cannot place).

    The result still goes through the block's own ``get_state_for_placement`` when the
    engine applies the ``place`` action (wire connections, lamp ``lit``, repeater ``locked``).
    """
    directions = nearest_looking_directions(request)
    if isinstance(block, FaceAttachedBlock):
        for direction in directions:
            if direction.axis.is_horizontal:
                state = block.default_state.with_(ATTACH_FACE, "wall").with_(
                    HORIZONTAL_FACING, direction.opposite
                )
            else:
                state = block.default_state.with_(
                    ATTACH_FACE, "ceiling" if direction is Direction.UP else "floor"
                ).with_(HORIZONTAL_FACING, horizontal_direction(request.yaw))
            if state.can_survive(level, pos):
                return state
        return None
    if isinstance(block, RedstoneTorchBlock) and not isinstance(block, RedstoneWallTorchBlock):
        wall_state = _wall_torch_state(directions, level, pos)
        for direction in directions:
            if direction is Direction.UP:
                continue
            candidate: BlockState | None = (
                block.default_state if direction is Direction.DOWN else wall_state
            )
            if candidate is not None and candidate.can_survive(level, pos):
                return candidate
        return None
    if isinstance(block, DiodeBlock):
        return block.default_state.with_(
            HORIZONTAL_FACING, horizontal_direction(request.yaw).opposite
        )
    return block.get_state_for_placement(PlacementContext(level, pos, block.default_state))


def _wall_torch_state(directions: list[Direction], level: Level, pos: Pos) -> BlockState | None:
    """``WallTorchBlock.getStateForPlacement`` for the redstone wall torch."""
    wall = blocks.REDSTONE_WALL_TORCH
    for direction in directions:
        if direction.axis.is_horizontal:
            state = wall.default_state.with_(HORIZONTAL_FACING, direction.opposite)
            if state.can_survive(level, pos):
                return state
    return None
