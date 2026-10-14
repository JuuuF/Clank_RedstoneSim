"""The game's own block models and textures, read at runtime from the supplied client jar.

Nothing is copied into the repository: the jar stays where the owner put it
(``data/minecraft_jars/client.jar``, or ``$REDSIM_MINECRAFT_JAR``); without it the editor
falls back to the colored box models of ``style``. See doc/decisions.md ADR-023.

Port of the relevant parts of the client's model pipeline (paths relative to
``data/minecraft_src/client-src/``):

* blockstates: ``variants`` (property conditions → model, ``x``/``y`` rotation) and
  ``multipart`` (``when`` conditions with ``OR``/``AND`` and ``a|b`` values → parts);
* models: ``parent`` chains, ``textures`` with ``#name`` references (strings or
  ``{"sprite": …}``), ``elements`` (``from``/``to``, ``rotation``, ``shade``, faces with
  ``uv``, ``rotation``, ``texture``, ``cullface``, ``tintindex``);
* baking (``client/resources/model/cuboid/FaceBakery.java``): default face UVs
  (``defaultFaceUV``), vertex order (``client/renderer/FaceInfo.java``), UV corners
  (``CuboidFace.UVs.getVertexU/V`` shifted by the face rotation, ``Quadrant``), element
  rotation around its origin (with ``rescale``), then the variant rotation around the block
  center: x first, then y (``Quadrant.fromXYZAngles``; ``BLOCK_ROT_Y_90`` maps
  (x, z) → (−z, x) around the center, ``BLOCK_ROT_X_90`` maps (y, z) → (z, −y)).

``uvlock`` is not applied (none of the in-scope blocks need it to look right).
"""

from __future__ import annotations

import copy
import json
import math
import os
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import redsim
from redsim.core.direction import Direction
from redsim.world.block import BlockState

REPO_ROOT = redsim.REPO_ROOT  # not from __file__: a compiled build lives elsewhere
DEFAULT_JAR = REPO_ROOT / "data" / "minecraft_jars" / "client.jar"

#: FaceInfo vertex order per face: which corner (min/max) on x, y, z.
FACE_VERTICES: dict[Direction, tuple[tuple[int, int, int], ...]] = {
    Direction.DOWN: ((0, 0, 1), (0, 0, 0), (1, 0, 0), (1, 0, 1)),
    Direction.UP: ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
    Direction.NORTH: ((1, 1, 0), (1, 0, 0), (0, 0, 0), (0, 1, 0)),
    Direction.SOUTH: ((0, 1, 1), (0, 0, 1), (1, 0, 1), (1, 1, 1)),
    Direction.WEST: ((0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)),
    Direction.EAST: ((1, 1, 1), (1, 0, 1), (1, 0, 0), (1, 1, 0)),
}
_BY_NAME = {d.name.lower(): d for d in Direction}

Vec = tuple[float, float, float]


@dataclass(frozen=True)
class Quad:
    """One baked face: corners in block units (FaceInfo order), UVs in 0..1 of its
    texture, the texture id (``minecraft:block/stone``), the direction it is culled by
    (``None``: never), the direction it faces (for shading), whether it is shaded, and
    its tint index (-1: none)."""

    corners: tuple[Vec, Vec, Vec, Vec]
    uvs: tuple[tuple[float, float], ...]
    texture: str
    cull: Direction | None
    facing: Direction
    shade: bool
    tint: int
    translucent: bool


def _default_uv(lo: Vec, hi: Vec, face: Direction) -> tuple[float, float, float, float]:
    """``FaceBakery.defaultFaceUV``."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    if face is Direction.DOWN:
        return (x0, 16 - z1, x1, 16 - z0)
    if face is Direction.UP:
        return (x0, z0, x1, z1)
    if face is Direction.NORTH:
        return (16 - x1, 16 - y1, 16 - x0, 16 - y0)
    if face is Direction.SOUTH:
        return (x0, 16 - y1, x1, 16 - y0)
    if face is Direction.WEST:
        return (z0, 16 - y1, z1, 16 - y0)
    return (16 - z1, 16 - y1, 16 - z0, 16 - y0)


def _rotate_axis(v: Vec, axis: str, degrees: float, origin: Vec, rescale: bool) -> Vec:
    """Rotate ``v`` around ``origin`` by ``degrees`` about ``axis`` (right-handed, like
    ``Matrix4f.rotation(angle, unit axis)``), optionally rescaled (``CuboidRotation``)."""
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = (v[0] - origin[0], v[1] - origin[1], v[2] - origin[2])
    if axis == "x":
        x, y, z = x, y * c - z * s, y * s + z * c
        scale = (1.0, 1 / max(abs(c), abs(s)), 1 / max(abs(c), abs(s)))
    elif axis == "y":
        x, y, z = x * c + z * s, y, -x * s + z * c
        scale = (1 / max(abs(c), abs(s)), 1.0, 1 / max(abs(c), abs(s)))
    else:
        x, y, z = x * c - y * s, x * s + y * c, z
        scale = (1 / max(abs(c), abs(s)), 1 / max(abs(c), abs(s)), 1.0)
    if rescale:
        x, y, z = x * scale[0], y * scale[1], z * scale[2]
    return (x + origin[0], y + origin[1], z + origin[2])


def _rotate_block(v: Vec, x_rot: int, y_rot: int) -> Vec:
    """The variant rotation around the block center: x first, then y, in 90° steps."""
    px, py, pz = v[0] - 0.5, v[1] - 0.5, v[2] - 0.5
    for _ in range((x_rot // 90) % 4):
        py, pz = pz, -py
    for _ in range((y_rot // 90) % 4):
        px, pz = -pz, px
    return (px + 0.5, py + 0.5, pz + 0.5)


def _rotate_direction(d: Direction, x_rot: int, y_rot: int) -> Direction:
    step = d.step
    moved = _rotate_block((0.5 + step[0], 0.5 + step[1], 0.5 + step[2]), x_rot, y_rot)
    delta = tuple(round(moved[i] - 0.5) for i in range(3))
    return next(direction for direction in Direction if direction.step == delta)


def _facing(corners: tuple[Vec, ...]) -> Direction:
    """``FaceBakery.calculateFacing``: the direction closest to the quad's normal."""
    a, b, c = corners[0], corners[1], corners[2]
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    w = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
    return max(Direction, key=lambda d: sum(n[i] * d.step[i] for i in range(3)))


def _extrude(lo: Vec, hi: Vec, faces: dict[str, Any]) -> tuple[Vec, Vec, dict[str, Any]]:
    """Give a flat element (zero size on an axis) one pixel of thickness, towards the
    block center. A floor-flat element (dust, rails) also gets thin side faces cut from
    the edge of its top texture, so it reads as a 1-pixel slab (presentation only)."""
    low, high = list(lo), list(hi)
    flat = [a for a in range(3) if abs(high[a] - low[a]) < 1e-6]
    if not flat:
        return lo, hi, faces
    axis = flat[0]
    if axis == 1 and low[axis] <= 1:
        low[axis], high[axis] = 0, 1  # on the floor (rails at 1, dust at 0.25): lie on it
    elif low[axis] <= 8:
        high[axis] = low[axis] + 1
    else:
        low[axis] = high[axis] - 1
    new_lo: Vec = (low[0], low[1], low[2])
    new_hi: Vec = (high[0], high[1], high[2])
    top = faces.get("up")
    if axis != 1 or top is None:
        return new_lo, new_hi, faces
    u0, v0, u1, v1 = top.get("uv") or _default_uv(new_lo, new_hi, Direction.UP)
    du = 1 if u1 >= u0 else -1
    dv = 1 if v1 >= v0 else -1
    base = {"texture": top.get("texture", ""), "tintindex": top.get("tintindex", -1)}
    sides = {
        "north": {**base, "uv": [u0, v0, u1, v0 + dv]},
        "south": {**base, "uv": [u0, v1 - dv, u1, v1]},
        "west": {**base, "uv": [u0, v0, u0 + du, v1], "rotation": 90},
        "east": {**base, "uv": [u1 - du, v0, u1, v1], "rotation": 90},
    }
    merged = dict(faces)
    for name, face in sides.items():
        merged.setdefault(name, face)
    return new_lo, new_hi, merged


def _up_face_uv(lo: Vec, hi: Vec, face: dict[str, Any]) -> Any:
    """(x, z) in element pixels → (u, v) on an up face's texture, as the bake maps its
    corners (UV rectangle and face rotation)."""
    u0, v0, u1, v1 = face.get("uv") or _default_uv(lo, hi, Direction.UP)
    shift = (int(face.get("rotation", 0)) // 90) % 4

    def corner(index: int) -> tuple[float, float]:
        k = (index + shift) % 4
        return (u0 if k in (0, 1) else u1, v0 if k in (0, 3) else v1)

    # FACE_VERTICES[UP]: 0 = (lo x, lo z), 1 = (lo x, hi z), 3 = (hi x, lo z).
    origin, along_z, along_x = corner(0), corner(1), corner(3)
    width, depth = max(hi[0] - lo[0], 1e-6), max(hi[2] - lo[2], 1e-6)

    def uv(x: float, z: float) -> tuple[float, float]:
        fx, fz = (x - lo[0]) / width, (z - lo[2]) / depth
        return (
            origin[0] + fx * (along_x[0] - origin[0]) + fz * (along_z[0] - origin[0]),
            origin[1] + fx * (along_x[1] - origin[1]) + fz * (along_z[1] - origin[1]),
        )

    return uv


#: Blocks the game draws with a block-entity renderer (no JSON model): their texture
#: (``ChestSpecialRenderer``: ``entity/chest/<name>``, ``_left``/``_right`` for double
#: chests).
ENTITY_MODELS = {
    "minecraft:chest": "minecraft:entity/chest/normal",
    "minecraft:trapped_chest": "minecraft:entity/chest/trapped",
}
#: ``ChestRenderer.createModelTransformation``: the model faces south and turns by
#: -facing.toYRot() (in model-JSON terms, a y rotation of toYRot).
_Y_ROT = {"south": 0, "west": 90, "north": 180, "east": 270}


def _cube_faces(
    u: float, v: float, w: float, h: float, d: float, hidden: str | None = None
) -> dict[str, Any]:
    """``ModelPart.Cube``'s faces for a box at texture offset (u, v) of size w×h×d in a
    64×64 texture, as model-JSON UVs (0–16): each JSON corner gets the texture point the
    game's polygon gives that corner. ``hidden``: a face the game leaves out."""

    def face(u0: float, v0: float, u1: float, v1: float) -> dict[str, Any]:
        return {"texture": "#chest", "uv": [u0 / 4, v0 / 4, u1 / 4, v1 / 4]}

    faces = {
        "down": face(u + d, v, u + d + w, v + d),
        "up": face(u + d + w, v + d, u + d + 2 * w, v),
        "west": face(u + d, v + d + h, u, v + d),
        "north": face(u + d + w, v + d + h, u + d, v + d),
        "east": face(u + 2 * d + w, v + d + h, u + d + w, v + d),
        "south": face(u + 2 * d + 2 * w, v + d + h, u + 2 * d + w, v + d),
    }
    if hidden is not None:
        faces.pop(hidden)
    return faces


def chest_model(state: BlockState) -> tuple[dict[str, Any], int]:
    """A block model for a chest (``ChestModel``: bottom, lid and lock, facing south, from
    the entity texture), and its y rotation. The halves of a double chest use the
    ``createDoubleBody{Left,Right}Layer`` boxes and their own textures."""
    props = state.properties_dict()
    facing, kind = props.get("facing", "north"), props.get("type", "single")
    texture = ENTITY_MODELS[state.block.id] + ("" if kind == "single" else f"_{kind}")
    if kind == "left":  # the partner is to the west (of a south-facing chest)
        x0, width, lock, hidden = 0.0, 15.0, (0.0, 1.0), "west"
    elif kind == "right":
        x0, width, lock, hidden = 1.0, 15.0, (15.0, 1.0), "east"
    else:
        x0, width, lock, hidden = 1.0, 14.0, (7.0, 2.0), None
    lock_x, lock_w = lock
    elements = [
        {
            "from": [x0, 0, 1],
            "to": [x0 + width, 10, 15],
            "faces": _cube_faces(0, 19, width, 10, 14, hidden),
        },
        {
            "from": [x0, 9, 1],
            "to": [x0 + width, 14, 15],
            "faces": _cube_faces(0, 0, width, 5, 14, hidden),
        },
        {
            "from": [lock_x, 7, 15],
            "to": [lock_x + lock_w, 11, 16],
            "faces": _cube_faces(0, 0, lock_w, 4, 1, hidden),
        },
    ]
    model = {"textures": {"chest": texture, "particle": texture}, "elements": elements}
    return model, _Y_ROT.get(facing, 0)


def _matches(condition: dict[str, Any], props: dict[str, str]) -> bool:
    """A multipart ``when``: ``OR``/``AND`` lists or ``property: "a|b"``. A property the
    simulator does not model (e.g. ``waterlogged``) counts as its default
    (``false``/``none``)."""
    if "OR" in condition:
        return any(_matches(c, props) for c in condition["OR"])
    if "AND" in condition:
        return all(_matches(c, props) for c in condition["AND"])
    for name, wanted in condition.items():
        options = str(wanted).lower().split("|")
        value = props.get(name)
        if value is None:
            if not ({"false", "none"} & set(options)):
                return False
        elif value not in options:
            return False
    return True


def _state_props(state: BlockState) -> dict[str, str]:
    return state.properties_dict()


def _observer_arrows(model: dict[str, Any]) -> dict[str, Any]:
    """The observer shows its arrow on all four sides around its facing (owner,
    2026-10-14): the game draws it only on two (``#top``, pointing towards the output);
    its other two sides (``#side``) get the same texture, turned so the arrow points
    towards the output too (west face: u runs north → south; east face: south → north)."""
    elements = copy.deepcopy(model["elements"])
    faces = elements[0]["faces"]
    faces["west"] = {**faces["west"], "texture": "#top", "rotation": 90}
    faces["east"] = {**faces["east"], "texture": "#top", "rotation": 270}
    return {**model, "elements": elements}


#: Models the simulator draws differently from the game (by resolved model name).
MODEL_PATCHES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "minecraft:block/observer": _observer_arrows,
}


class Assets:
    """Read-only access to the client jar's block assets, with caches."""

    def __init__(self, jar: Path) -> None:
        self.jar = jar
        self._zip = zipfile.ZipFile(jar)
        self._names = set(self._zip.namelist())
        self._models: dict[str, dict[str, Any]] = {}
        self._quads: dict[BlockState, tuple[Quad, ...]] = {}
        #: Flat elements (dust, rails) get one pixel of thickness (owner preference).
        self.extrude_flat = True
        self._masks: dict[str, list[list[bool]] | None] = {}

    @staticmethod
    @lru_cache(maxsize=1)
    def find() -> Assets | None:
        """The assets of ``$REDSIM_MINECRAFT_JAR`` or the supplied jar, if present."""
        if os.environ.get("REDSIM_NO_GAME_ASSETS"):
            return None
        path = Path(os.environ.get("REDSIM_MINECRAFT_JAR") or DEFAULT_JAR)
        try:
            return Assets(path) if path.is_file() else None
        except (OSError, zipfile.BadZipFile):
            return None

    # ------------------------------------------------------------------ raw files
    def _path(self, resource: str, folder: str, suffix: str) -> str:
        namespace, _, name = (
            resource.partition(":") if ":" in resource else ("minecraft", "", resource)
        )
        return f"assets/{namespace}/{folder}/{name}{suffix}"

    def has(self, path: str) -> bool:
        return path in self._names

    def json(self, path: str) -> Any:
        return json.loads(self._zip.read(path))

    def texture_bytes(self, texture: str) -> bytes | None:
        path = self._path(texture, "textures", ".png")
        return self._zip.read(path) if path in self._names else None

    def file_bytes(self, path: str) -> bytes | None:
        return self._zip.read(path) if path in self._names else None

    # ------------------------------------------------------------------ models
    def model(self, name: str) -> dict[str, Any]:
        """A model with its parent chain resolved: merged ``textures`` (child wins) and the
        nearest ``elements``."""
        if ":" not in name:
            name = f"minecraft:{name}"
        cached = self._models.get(name)
        if cached is not None:
            return cached
        path = self._path(name, "models", ".json")
        data: dict[str, Any] = self.json(path) if path in self._names else {}
        resolved: dict[str, Any] = {"textures": {}, "elements": None, "parent_chain": [name]}
        parent = data.get("parent")
        if parent and not parent.startswith("builtin/"):
            base = self.model(parent)
            resolved["textures"].update(base["textures"])
            resolved["elements"] = base["elements"]
            resolved["parent_chain"] = [name, *base["parent_chain"]]
        elif parent:
            resolved["parent_chain"] = [name, parent]
        for key, value in data.get("textures", {}).items():
            resolved["textures"][key] = value
        if "elements" in data:
            resolved["elements"] = data["elements"]
        patch = MODEL_PATCHES.get(name)
        if patch is not None:
            resolved = patch(resolved)
        self._models[name] = resolved
        return resolved

    def is_generated_item(self, name: str) -> bool:
        """Whether a model is a flat item sprite (``item/generated`` chain)."""
        chain = self.model(name)["parent_chain"]
        return any(link.endswith(("item/generated", "item/handheld")) for link in chain)

    @staticmethod
    def resolve_texture(textures: dict[str, Any], ref: str) -> tuple[str, bool] | None:
        """``#name`` → texture id and whether it is forced translucent."""
        translucent = False
        seen = 0
        while ref.startswith("#") and seen < 16:
            value = textures.get(ref[1:])
            if value is None:
                return None
            if isinstance(value, dict):
                translucent = translucent or bool(value.get("force_translucent"))
                value = value.get("sprite", "")
            ref, seen = value, seen + 1
        if not ref or ref.startswith("#"):
            return None
        return (ref if ":" in ref else f"minecraft:{ref}"), translucent

    # ------------------------------------------------------------------ blockstates
    def parts(self, state: BlockState) -> list[dict[str, Any]]:
        """The model references (``model``, ``x``, ``y``) the blockstate file gives
        ``state``."""
        path = self._path(state.block.id, "blockstates", ".json")
        if path not in self._names:
            return []
        data = self.json(path)
        props = _state_props(state)
        chosen: list[dict[str, Any]] = []
        if "variants" in data:
            best: Any = None
            for key, value in data["variants"].items():
                conditions = dict(part.split("=", 1) for part in key.split(",") if "=" in part)
                if _matches(conditions, props):
                    best = value
                    break
            if best is None:
                # A save may store a bare id (the default state, e.g. ``oak_sign``): take
                # the first variant that agrees on the properties the state does have.
                for key, value in data["variants"].items():
                    conditions = dict(p.split("=", 1) for p in key.split(",") if "=" in p)
                    if all(props.get(k, v) == v for k, v in conditions.items()):
                        best = value
                        break
            if best is not None:
                chosen.append(best[0] if isinstance(best, list) else best)
        for part in data.get("multipart", []):
            if "when" not in part or _matches(part["when"], props):
                apply = part["apply"]
                chosen.append(apply[0] if isinstance(apply, list) else apply)
        return chosen

    def block_quads(self, state: BlockState) -> tuple[Quad, ...]:
        """All baked faces of ``state``'s block model."""
        cached = self._quads.get(state)
        if cached is not None:
            return cached
        quads: list[Quad] = []
        for part in self.parts(state):
            model = self.model(part["model"])
            quads.extend(self.bake(model, int(part.get("x", 0)), int(part.get("y", 0))))
        if not quads and state.block.id in ENTITY_MODELS:  # drawn by a renderer in the game
            model, y_rot = chest_model(state)
            quads.extend(self.bake(model, 0, y_rot))
        result = tuple(quads)
        self._quads[state] = result
        return result

    def bake(self, model: dict[str, Any], x_rot: int = 0, y_rot: int = 0) -> list[Quad]:
        quads = []
        textures = model["textures"]
        for element in model["elements"] or []:
            lo = tuple(float(v) for v in element["from"])
            hi = tuple(float(v) for v in element["to"])
            rotation = element.get("rotation")
            shade = bool(element.get("shade", True))
            override = _BY_NAME.get(str(element.get("shade_direction_override", "")))
            faces = element.get("faces", {})
            parts: list[tuple[Vec, Vec, dict[str, Any]]] = [(lo, hi, faces)]  # type: ignore[list-item]
            if self.extrude_flat:
                parts = self._extruded(lo, hi, faces, textures)  # type: ignore[arg-type]
            for lo, hi, faces in parts:  # noqa: B020 - each part is baked like an element
                for face_name, face in faces.items():
                    direction = _BY_NAME[face_name]
                    resolved = self.resolve_texture(textures, face.get("texture", ""))
                    if resolved is None:
                        continue
                    texture, translucent = resolved
                    u0, v0, u1, v1 = face.get("uv") or _default_uv(lo, hi, direction)
                    shift = (int(face.get("rotation", 0)) // 90) % 4
                    corners: list[Vec] = []
                    uvs: list[tuple[float, float]] = []
                    for index, pick in enumerate(FACE_VERTICES[direction]):
                        v: Vec = (
                            (hi if pick[0] else lo)[0] / 16,
                            (hi if pick[1] else lo)[1] / 16,
                            (hi if pick[2] else lo)[2] / 16,
                        )
                        if rotation:
                            origin = tuple(float(c) / 16 for c in rotation.get("origin", (8, 8, 8)))
                            if "axis" in rotation:
                                v = _rotate_axis(
                                    v,
                                    rotation["axis"],
                                    float(rotation.get("angle", 0)),
                                    origin,  # type: ignore[arg-type]
                                    bool(rotation.get("rescale", False)),
                                )
                        if x_rot or y_rot:
                            v = _rotate_block(v, x_rot, y_rot)
                        corners.append(v)
                        k = (index + shift) % 4
                        uvs.append(
                            ((u0 if k in (0, 1) else u1) / 16, (v0 if k in (0, 3) else v1) / 16)
                        )
                    cull = face.get("cullface")
                    cull_dir = (
                        _rotate_direction(_BY_NAME[cull], x_rot, y_rot)
                        if cull in _BY_NAME
                        else None
                    )
                    corner_tuple = (corners[0], corners[1], corners[2], corners[3])
                    facing = _facing(corner_tuple)
                    if override is not None:
                        facing = _rotate_direction(override, x_rot, y_rot)
                    quads.append(
                        Quad(
                            corner_tuple,
                            tuple(uvs),
                            texture,
                            cull_dir,
                            facing,
                            shade,
                            int(face.get("tintindex", -1)),
                            translucent,
                        )
                    )
        return quads

    def _extruded(
        self, lo: Vec, hi: Vec, faces: dict[str, Any], textures: dict[str, str]
    ) -> list[tuple[Vec, Vec, dict[str, Any]]]:
        """A flat element as a solid one pixel high model (owner preference): a slab with
        the top texture on top and below, and for a floor-flat element (dust, rails) a
        side face for every edge between an opaque pixel and a transparent one or the
        element's border, like the game extrudes item sprites. Each side face shows the
        pixel it belongs to."""
        new_lo, new_hi, merged = _extrude(lo, hi, faces)
        top = faces.get("up")
        flat_y = abs(hi[1] - lo[1]) < 1e-6
        resolved = self.resolve_texture(textures, top.get("texture", "")) if top else None
        mask = self._opaque_mask(resolved[0]) if resolved else None
        if not flat_y or top is None or mask is None:
            return [(new_lo, new_hi, merged)]
        parts: list[tuple[Vec, Vec, dict[str, Any]]] = [
            (new_lo, new_hi, {"up": top, "down": dict(top)})
        ]
        uv_at = _up_face_uv(new_lo, new_hi, top)
        x_cells = range(math.floor(new_lo[0]), math.ceil(new_hi[0]))
        z_cells = range(math.floor(new_lo[2]), math.ceil(new_hi[2]))
        texel: dict[tuple[int, int], tuple[int, int]] = {}
        for cx in x_cells:
            for cz in z_cells:
                u, v = uv_at(cx + 0.5, cz + 0.5)
                tu, tv = min(15, max(0, math.floor(u))), min(15, max(0, math.floor(v)))
                if mask[tv][tu]:
                    texel[(cx, cz)] = (tu, tv)
        base = {"texture": top.get("texture", ""), "tintindex": top.get("tintindex", -1)}
        y0, y1 = new_lo[1], new_hi[1]
        for (cx, cz), (tu, tv) in texel.items():
            for name, dx, dz in (
                ("north", 0, -1),
                ("south", 0, 1),
                ("west", -1, 0),
                ("east", 1, 0),
            ):
                if (cx + dx, cz + dz) in texel:
                    continue  # inside the solid: no face
                face = {**base, "uv": [tu, tv, tu + 1, tv + 1]}
                parts.append(((cx, y0, cz), (cx + 1, y1, cz + 1), {name: face}))
        return parts

    def _opaque_mask(self, texture: str) -> list[list[bool]] | None:
        """Which pixels of a 16×16 texture (its first animation frame) are opaque."""
        if texture not in self._masks:
            from PySide6.QtGui import QImage

            data = self.texture_bytes(texture)
            image = QImage.fromData(data) if data else QImage()
            if image.isNull() or image.width() != 16:
                self._masks[texture] = None
            else:
                self._masks[texture] = [
                    [image.pixelColor(x, y).alpha() >= 26 for x in range(16)] for y in range(16)
                ]
        return self._masks[texture]

    def block_textures(self, block_id: str) -> set[str]:
        """Every texture any model of the block's blockstate file uses."""
        path = self._path(block_id, "blockstates", ".json")
        if path not in self._names:
            return set()
        data = self.json(path)
        models: set[str] = set()

        def add(entry: Any) -> None:
            for item in entry if isinstance(entry, list) else [entry]:
                models.add(item["model"])

        for value in data.get("variants", {}).values():
            add(value)
        for part in data.get("multipart", []):
            add(part["apply"])
        found = set()
        for name in models:
            model = self.model(name)
            for element in model["elements"] or []:
                for face in element.get("faces", {}).values():
                    resolved = self.resolve_texture(model["textures"], face.get("texture", ""))
                    if resolved is not None:
                        found.add(resolved[0])
        return found

    def item_model(self, block_id: str) -> str | None:
        """The model an inventory shows for the block's item (``items/<id>.json``)."""
        path = self._path(block_id, "items", ".json")
        if path not in self._names:
            return None
        data = self.json(path).get("model", {})
        for _ in range(16):  # select/condition/special wrappers, a few levels deep
            if not isinstance(data, dict) or not data:
                return None
            if data.get("type") == "minecraft:model":
                return data.get("model")
            if data.get("type") == "minecraft:special":
                return None  # drawn by a special renderer (chests): use the block model
            data = data.get("fallback") or data.get("model") or {}
        return None
