"""Generate ``src/redsim/world/blocks/catalog_data.py``: every block of the game with the
facts the simulator needs to model the simple ones (owner, 2026-10-14: "include as many
blocks as possible"), from the decompiled ``Blocks.java``.

Per block id: the Java class that implements it (``Block``, ``RotatedPillarBlock``,
``SlabBlock``, …), its destroy time (``strength``/``destroyTime``/``instabreak``), push
reaction, redstone-conductor rule (``isRedstoneConductor(Blocks::never/always)``), the
``noCollision``/``noOcclusion``/``forceSolidOn``/``forceSolidOff`` flags and its map color
(for the untextured look). Copies (``ofFullCopy``/``ofLegacyCopy`` and the slab, stair
and wall helpers) inherit from their base and apply their own settings on top.

Usage: ``python -m tools.extract_block_table && ruff format src/redsim/world/blocks``
(rewrites the module).
"""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/minecraft_src/client-src/net/minecraft"
BLOCKS = SRC / "world/level/block/Blocks.java"
ITEM_IDS = SRC / "references/BlockItemIds.java"
BLOCK_IDS = SRC / "references/BlockIds.java"
MAP_COLOR = SRC / "world/level/material/MapColor.java"
DYE_COLOR = SRC / "world/item/DyeColor.java"
JAR = ROOT / "data/minecraft_jars/client.jar"
OUT = ROOT / "src/redsim/world/blocks/catalog_data.py"

WEATHERING = ("", "exposed_", "weathered_", "oxidized_")
WAXED = ("waxed_", "waxed_exposed_", "waxed_weathered_", "waxed_oxidized_")
FLAG_NAMES = {"noCollision": 1, "noOcclusion": 2, "forceSolidOn": 4, "forceSolidOff": 8}
#: Flag of blocks whose class has a block entity (``EntityBlock``): pistons never move them
#: (``PistonBaseBlock.isPushable``: ``!state.hasBlockEntity()``).
BLOCK_ENTITY = 16
CLASSES = SRC / "world/level/block"


def entity_classes() -> set[str]:
    """Block classes that implement ``EntityBlock``, directly or through a parent."""
    parents: dict[str, str] = {}
    entity: set[str] = set()
    for path in CLASSES.rglob("*.java"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(
            r"\bclass (\w+)(?:<[^>{]*>)?(?: extends (\w+)(?:<[^>{]*>)?)?"
            r"(?: implements ([^{]+))?\s*\{",
            text,
        ):
            name, parent, interfaces = match.groups()
            if parent:
                parents[name] = parent
            if interfaces and re.search(r"\bEntityBlock\b", interfaces):
                entity.add(name)
    changed = True
    while changed:
        changed = False
        for name, parent in parents.items():
            if parent in entity and name not in entity:
                entity.add(name)
                changed = True
    return entity


@dataclass(frozen=True)
class Spec:
    kind: str = "Block"
    destroy: float = 0.0
    push: str = "PUSH_PULL"
    conductor: str = "default"
    flags: int = 0
    color: int = 0


@dataclass
class Statement:
    name: str
    body: str
    collection: str = ""  # "", "color", "copper"
    ids: list[str] = field(default_factory=list)
    colors: list[int] = field(default_factory=list)  # per id, for dye collections


def _balanced(src: str, start: int, end_char: str = ";") -> int:
    depth, i = 0, start
    while i < len(src):
        c = src[i]
        if c in "({":
            depth += 1
        elif c in ")}":
            depth -= 1
        elif c == end_char and depth == 0:
            return i
        i += 1
    return i


def _statements(src: str) -> list[Statement]:
    out = []
    pattern = (
        r"public static final (Block|ColorCollection<Block>|WeatheringCopperCollection<Block>)"
        r" (\w+) = "
    )
    for match in re.finditer(pattern, src):
        end = _balanced(src, match.end())
        kind = {"Block": "", "ColorCollection<Block>": "color"}.get(match.group(1), "copper")
        out.append(Statement(match.group(2), src[match.end() : end], kind))
    return out


def _helpers(src: str) -> dict[str, str]:
    out = {}
    for match in re.finditer(r"private static BlockBehaviour\.Properties (\w+)\([^)]*\) \{", src):
        depth, i = 1, match.end()
        while depth and i < len(src):
            depth += {"{": 1, "}": -1}.get(src[i], 0)
            i += 1
        out[match.group(1)] = src[match.end() : i]
    return out


def _item_ids() -> dict[str, list[str]]:
    """``BlockItemIds``/``BlockIds`` constant → the ids it names."""
    out: dict[str, list[str]] = {}
    for path in (ITEM_IDS, BLOCK_IDS):
        text = path.read_text(encoding="utf-8")
        for name, value in re.findall(r"(\w+) = (?:BlockItemId\.)?create\(\"(\w+)\"\)", text):
            out[name] = [value]
        for name, base in re.findall(r"(\w+) = createSimpleColored\(\"(\w+)\"\)", text):
            out[name] = [f"{color}_{base}" for color in _dye_names()]
        for name, base in re.findall(r"(\w+) = createSimpleCopper\(\"(\w+)\"\)", text):
            out[name] = [p + base for p in WEATHERING + WAXED]
    out["COPPER_BLOCK"] = [
        "copper_block", "exposed_copper", "weathered_copper", "oxidized_copper",
        "waxed_copper_block", "waxed_exposed_copper", "waxed_weathered_copper",
        "waxed_oxidized_copper",
    ]  # fmt: skip
    return out


def _dye_names() -> list[str]:
    text = DYE_COLOR.read_text(encoding="utf-8")
    return [name for _, name in re.findall(r"^\s+(\w+)\(\d+, \"(\w+)\"", text, re.M)]


def _dye_map_colors(map_colors: dict[str, int]) -> tuple[list[int], list[int]]:
    """Per dye color: its map color and its terracotta color."""
    text = DYE_COLOR.read_text(encoding="utf-8")
    rows = re.findall(r"^\s+\w+\(\d+, \"\w+\", \d+, MapColor\.(\w+), MapColor\.(\w+)", text, re.M)
    return [map_colors.get(a, 0) for a, _ in rows], [map_colors.get(b, 0) for _, b in rows]


def _map_colors() -> dict[str, int]:
    text = MAP_COLOR.read_text(encoding="utf-8")
    pattern = r"public static final MapColor (\w+) = new MapColor\(\d+, (\d+)\)"
    return {name: int(value) for name, value in re.findall(pattern, text)}


def _kind(statement: Statement) -> str:
    body = statement.body
    if re.search(r"registerSlab\(", body):
        return "SlabBlock"
    if re.search(r"register(?:Legacy)?Stair\(", body):
        return "StairBlock"
    if re.search(r"registerWall\(", body):
        return "WallBlock"
    found = re.search(r"\b([A-Z]\w*Block)::new", body) or re.search(r"new ([A-Z]\w*Block)\(", body)
    if statement.collection == "copper":
        classes = re.findall(r"\b([A-Z]\w*Block)::new", body)
        classes += re.findall(r"new ([A-Z]\w*Block)\(", body)
        named = [c for c in classes if c != "Block"]
        return named[0] if named else "Block"
    return found.group(1) if found else "Block"


def _own(text: str, base: Spec, map_colors: dict[str, int]) -> Spec:
    """The settings ``text`` makes, on top of ``base`` (the last call of each kind wins)."""
    spec = base
    for call in re.finditer(r"\.(\w+)\(([^()]*(?:\([^()]*\)[^()]*)*)\)", text):
        method, args = call.group(1), call.group(2).strip()
        if method in ("strength", "destroyTime"):
            number = re.match(r"(-?[\d.]+)F?", args)
            if number:
                spec = replace(spec, destroy=float(number.group(1)))
        elif method == "instabreak":
            spec = replace(spec, destroy=0.0)
        elif method == "pushReaction":
            found = re.search(r"PushReaction\.(\w+)", args)
            if found:
                spec = replace(spec, push=found.group(1))
        elif method == "isRedstoneConductor":
            if "never" in args:
                spec = replace(spec, conductor="never")
            elif "always" in args:
                spec = replace(spec, conductor="always")
            else:
                spec = replace(spec, conductor="custom")
        elif method in FLAG_NAMES:
            spec = replace(spec, flags=spec.flags | FLAG_NAMES[method])
        elif method == "mapColor":
            found = re.search(r"MapColor\.(\w+)", args)
            if found and found.group(1) in map_colors:
                spec = replace(spec, color=map_colors[found.group(1)])
    return spec


def extract() -> tuple[dict[str, Spec], list[str]]:
    src = BLOCKS.read_text(encoding="utf-8")
    helpers = _helpers(src)
    item_ids = _item_ids()
    map_colors = _map_colors()
    dye_map, dye_terracotta = _dye_map_colors(map_colors)
    statements = _statements(src)
    by_name = {s.name: s for s in statements}
    specs: dict[str, Spec] = {}

    def spec_of(name: str, depth: int = 0) -> Spec:
        if name in specs:
            return specs[name]
        statement = by_name.get(name)
        if statement is None or depth > 12:
            return Spec()
        body = statement.body
        base = Spec()
        copy = re.search(r"of(?:Full|Legacy)Copy\((\w+)(?:\.\w+\(\))*(?:\.pick\([^)]*\))?\)", body)
        helper = r"register(?:Slab|Stair|LegacyStair|Wall)\(\s*[\w.]+,\s*(\w+)"
        helper_base = re.search(helper, body)
        source = copy.group(1) if copy else helper_base.group(1) if helper_base else None
        if source is not None and source in by_name and source != name:
            inherited = spec_of(source, depth + 1)
            base = replace(inherited, kind="Block", flags=inherited.flags & ~(4 | 8))
        text = body
        for helper, helper_body in helpers.items():
            if re.search(rf"\b{helper}\(", body):
                text = helper_body + text
        own = _own(text, base, map_colors)
        if not own.color:  # a color passed to a helper (``logProperties(MapColor.WOOD, …)``)
            found = re.search(r"MapColor\.(\w+)", body)
            if found and found.group(1) in map_colors:
                own = replace(own, color=map_colors[found.group(1)])
        if "registerWall(" in body:
            own = replace(own, flags=own.flags | 4)  # forceSolidOn
        spec = replace(own, kind=_kind(statement))
        specs[name] = spec
        return spec

    entities = entity_classes()
    table: dict[str, Spec] = {}
    for statement in statements:
        spec = spec_of(statement.name)
        if spec.kind in entities:
            spec = replace(spec, flags=spec.flags | BLOCK_ENTITY)
        ids_ref = re.search(r"(?:BlockItemIds|BlockIds)\.(\w+)", statement.body)
        ids = item_ids.get(ids_ref.group(1), []) if ids_ref else []
        if not ids:
            ids = [statement.name.lower()]
        terracotta = "getTerracottaColor" in statement.body
        dyed = "getMapColor()" in statement.body
        picked = re.search(r"(\w+)\.pick\(color\)", statement.body)
        base_ids = []
        if picked and picked.group(1) in by_name:
            ref = re.search(r"(?:BlockItemIds|BlockIds)\.(\w+)", by_name[picked.group(1)].body)
            base_ids = item_ids.get(ref.group(1), []) if ref else []
        for index, block_id in enumerate(ids):
            color = spec.color
            if statement.collection == "color" and (dyed or terracotta) and index < len(dye_map):
                color = (dye_terracotta if terracotta else dye_map)[index]
            elif index < len(base_ids) and f"minecraft:{base_ids[index]}" in table:
                color = table[f"minecraft:{base_ids[index]}"].color  # a wool or concrete stair
            table[f"minecraft:{block_id}"] = replace(spec, color=color)
    with zipfile.ZipFile(JAR) as jar:
        known = sorted(
            "minecraft:" + Path(n).stem
            for n in jar.namelist()
            if n.startswith("assets/minecraft/blockstates/") and n.endswith(".json")
        )
    missing = [block_id for block_id in known if block_id not in table]
    return {k: v for k, v in sorted(table.items()) if k in set(known)}, missing


TABS = SRC / "world/item/CreativeModeTabs.java"
#: ``copperBlockFamilies``: the copper families the building tab lists (weathering, then waxed).
COPPER_FAMILIES = (
    "COPPER_BLOCK", "CHISELED_COPPER", "COPPER_GRATE", "CUT_COPPER", "CUT_COPPER_STAIRS",
    "CUT_COPPER_SLAB", "COPPER_DOOR", "COPPER_TRAPDOOR", "COPPER_BULB",
)  # fmt: skip


def creative_tabs() -> dict[str, list[str]]:
    """The block items of the game's Building, Colored and Natural tabs, in their order."""
    text = TABS.read_text(encoding="utf-8")
    item_ids = _item_ids()
    order = re.search(r"List<DyeColor> gameplayColorOrder = List\.of\((.*?)\);", text, re.S)
    colors = [c.lower() for c in re.findall(r"DyeColor\.(\w+)", order.group(1))] if order else []
    tabs = {}
    for title, key, next_key in (
        ("Building", "BUILDING_BLOCKS,", "COLORED_BLOCKS,"),
        ("Colored", "COLORED_BLOCKS,", "NATURAL_BLOCKS,"),
        ("Natural", "NATURAL_BLOCKS,", "FUNCTIONAL_BLOCKS,"),
    ):
        start = text.index(key, text.index("Registry.register"))
        body = text[start : text.index(next_key, start)]
        ids: list[str] = []
        for match in re.finditer(
            r"registerColoredItems\(\w+, \w+, Items\.(\w+)\)|accept\(Items\.(\w+)\)|"
            r"(copperBlockFamilies\(family -> family\.weathering)",
            body,
        ):
            colored, single, copper = match.groups()
            if colored:
                base = item_ids.get(colored, [colored.lower()])[0].split("_", 1)
                names = item_ids.get(colored)
                if names and len(names) == 16:
                    by_color = dict(zip(_dye_names(), names, strict=True))
                    ids.extend(by_color[c] for c in colors)
                else:
                    ids.extend(f"{c}_{'_'.join(base)}" for c in colors)
            elif single:
                ids.append(single.lower())
            elif copper:
                for prefixes in (WEATHERING, WAXED):
                    for family in COPPER_FAMILIES:
                        names = item_ids.get(family, [])
                        start_index = 0 if prefixes is WEATHERING else 4
                        ids.extend(names[start_index : start_index + 4])
        tabs[title] = [f"minecraft:{i}" for i in ids]
    return tabs


def _tag(jar: zipfile.ZipFile, name: str) -> set[str]:
    """A block tag of the game's data, nested tags resolved."""
    path = f"data/minecraft/tags/block/{name}.json"
    out: set[str] = set()
    for value in json.loads(jar.read(path))["values"]:
        entry = value if isinstance(value, str) else value["id"]
        if entry.startswith("#"):
            out |= _tag(jar, entry[1:].removeprefix("minecraft:"))
        else:
            out.add(entry if ":" in entry else f"minecraft:{entry}")
    return out


def main() -> None:
    table, missing = extract()
    with zipfile.ZipFile(JAR) as jar:
        keepers = sorted(_tag(jar, "prevents_nearby_leaf_decay"))
    lines = [
        '"""Every block of the game: its class and the settings the simulator needs',
        "(generated from the decompiled ``Blocks.java`` by ``tools/extract_block_table.py``;",
        "do not edit by hand). Values: class, destroy time, push reaction, redstone-conductor",
        "rule, flags (1 noCollision, 2 noOcclusion, 4 forceSolidOn, 8 forceSolidOff, 16 has a",
        "block entity), map",
        'color (0xRRGGBB)."""',
        "",
        "BLOCKS: dict[str, tuple[str, float, str, str, int, int]] = {",
        *(
            f'    "{k}": ("{v.kind}", {v.destroy!r}, "{v.push}", "{v.conductor}", {v.flags}, '
            f"0x{v.color:06X}),"
            for k, v in table.items()
        ),
        "}",
        "",
        "#: The game's creative tabs (block items, in the game's order) for the inventory.",
        "CREATIVE_TABS: dict[str, tuple[str, ...]] = {",
        *(
            f'    "{title}": (' + "".join(f'"{i}", ' for i in ids if i in table) + "),"
            for title, ids in creative_tabs().items()
        ),
        "}",
        "",
        "#: ``BlockTags.PREVENTS_NEARBY_LEAF_DECAY``: leaves next to these are at distance 1.",
        "LEAF_DECAY_KEEPERS: frozenset[str] = frozenset(",
        "    {",
        *(f'        "{k}",' for k in keepers),
        "    }",
        ")",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(table)} blocks written to {OUT}; not found in Blocks.java: {missing}")


if __name__ == "__main__":
    main()
