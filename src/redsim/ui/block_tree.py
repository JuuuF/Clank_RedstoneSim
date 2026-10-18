"""The inventory's folders, made from the blocks the simulator has (owner, 2026-10-14: the
pages of the game's creative tabs were "really messy"; blocks "might also appear in
multiple hierarchies").

Pure data, no Qt: ``inventory_tree()`` builds the folder tree, and ``shape_variants`` /
``color_variants`` give the blocks the variant keys step through (planks → stairs →
slab, white → light gray → … wool, copper → exposed → … copper).

* Redstone by role: wiring, switches, outputs, movement, blocks comparators read, item
  transport, rails. A block can sit in several (a chest moves items and is read by
  comparators; obsidian stops pistons and is a stone).
* Wood: a folder per wood with its planks, stairs, slab, logs, leaves, button, plate, sign.
* Stone, deepslate and tuff, bricks and sandstone, nether and end, minerals and ores: a
  folder per material family (granite, its stairs, its slab).
* Colored: by kind (wool, concrete, …) and by color (all white blocks, …).
* Copper by stage (waxed apart), natural blocks, glass and light.

A folder with more than nine entries keeps eight and puts the rest into "More…", so the
common ones stay on the first row. Anything not placed by a rule ends up in "Other".
"""

from __future__ import annotations

import functools
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

PAGE = 9  # entries per row: one per number key


@dataclass(frozen=True)
class Folder:
    title: str
    children: tuple[Folder | str, ...] = field(default_factory=tuple)  # str: block id


#: The game's color order in its creative tabs (``gameplayColorOrder``).
COLORS = (
    "white", "light_gray", "gray", "black", "brown", "red", "orange", "yellow", "lime",
    "green", "cyan", "light_blue", "blue", "purple", "magenta", "pink",
)  # fmt: skip
#: Copper stages, then their waxed forms.
COPPER_STAGES = (
    "", "exposed_", "weathered_", "oxidized_",
    "waxed_", "waxed_exposed_", "waxed_weathered_", "waxed_oxidized_",
)  # fmt: skip
WOODS = (
    "oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry",
    "pale_oak", "poplar", "bamboo", "crimson", "warped",
)  # fmt: skip
_WOOD_PARTS = (
    "planks", "stairs", "slab", "log", "stem", "wood", "hyphae", "block", "mosaic",
    "mosaic_stairs", "mosaic_slab", "leaves", "button", "pressure_plate", "sign", "fence",
    "fence_gate", "door", "trapdoor",
)  # fmt: skip
#: Shape suffixes: what turns a material into its stairs, slab, …
_SHAPES = (
    "_stairs", "_slab", "_wall", "_pressure_plate", "_button", "_sign", "_carpet",
    "_fence_gate", "_fence", "_trapdoor", "_door",
)  # fmt: skip

#: Redstone by role (ids without the namespace; missing ones are skipped).
REDSTONE = (
    ("Wiring", (
        "redstone_wire", "redstone_torch", "repeater", "comparator", "observer",
        "redstone_block", "target",
    )),
    ("Switches", (
        "lever", "stone_button", "oak_button", "stone_pressure_plate", "oak_pressure_plate",
        "light_weighted_pressure_plate", "heavy_weighted_pressure_plate", "trapped_chest",
    )),
    ("Outputs", (
        "redstone_lamp", "copper_bulb", "note_block", "piston", "sticky_piston", "dispenser",
        "dropper", "target",
    )),
    ("Movement", (
        "piston", "sticky_piston", "slime_block", "honey_block", "obsidian",
        "white_glazed_terracotta", "crying_obsidian", "observer", "campfire", "soul_campfire",
    )),
    ("Read by comparators", (
        "barrel", "chest", "trapped_chest", "hopper", "dropper", "dispenser", "lectern",
        "cake", "composter", "cauldron", "water_cauldron", "lava_cauldron", "furnace",
        "blast_furnace", "smoker",
    )),
    ("Items", ("hopper", "dropper", "dispenser", "chest", "trapped_chest", "barrel")),
    ("Doors", (
        "iron_door", "iron_trapdoor", "oak_door", "oak_trapdoor", "oak_fence_gate",
        "copper_door", "copper_trapdoor",
    )),
    ("Rails", ("rail", "powered_rail", "activator_rail")),
    ("Gravity", (
        "sand", "red_sand", "gravel", "white_concrete_powder", "anvil", "chipped_anvil",
        "damaged_anvil", "dragon_egg",
    )),
)  # fmt: skip
#: Building materials: category → family names (``material``) matched in order.
STONE_GROUPS = (
    ("Stone", r"(stone|smooth_stone|cobblestone|mossy_cobblestone|(cracked_|chiseled_|mossy_)?"
              r"stone_brick|(polished_)?(granite|diorite|andesite))"),
    ("Deepslate & tuff", r"(cobbled_|polished_|chiseled_|reinforced_)?deepslate(_brick|_tile)?|"
                         r"cracked_deepslate_(brick|tile)|(polished_|chiseled_)?tuff(_brick)?|"
                         r"chiseled_tuff_brick|calcite|dripstone"),
    ("Bricks & sandstone", r"brick|packed_mud|mud_brick|(chiseled_)?resin_brick|"
                           r"(chiseled_|smooth_|cut_)?(red_)?sandstone|"
                           r"(polished_|chiseled_)?(cinnabar|sulfur)(_brick)?|"
                           r"(dark_)?prismarine(_brick)?"),
    ("Nether & end", r"netherrack|(cracked_|chiseled_|red_)?nether_brick|"
                     r"(smooth_|polished_)?basalt|gilded_blackstone|"
                     r"(chiseled_)?(polished_)?blackstone(_brick)?|"
                     r"cracked_polished_blackstone_brick|end_stone(_brick)?|purpur(_pillar)?|"
                     r"(chiseled_|smooth_)?quartz(_brick|_pillar)?|crying_obsidian|obsidian"),
    ("Minerals & ores", r".*_ore|raw_\w+|ancient_debris|(coal|iron|gold|diamond|emerald|lapis|"
                        r"redstone|netherite|amethyst)|budding_amethyst"),
)  # fmt: skip
NATURAL_GROUPS = (
    ("Ground", r"grass_block|podzol|mycelium|(coarse_|rooted_)?dirt|clay|mud|packed_mud|"
               r"(red_)?sand|gravel|"
               r"(pale_)?moss_block|moss_carpet|muddy_mangrove_roots|dirt_path|farmland"),
    ("Logs", r"(stripped_)?\w+_(log|stem|wood|hyphae)|mushroom_stem"),
    ("Leaves", r"\w+_leaves"),
    ("Nether & end", r"netherrack|\w+_nylium|soul_soil|soul_sand|magma_block|glowstone|"
                     r"shroomlight|\w+_wart_block|bone_block|end_stone|(smooth_)?basalt|"
                     r"blackstone|crying_obsidian|obsidian|ancient_debris"),
    ("Ice & snow", r"(packed_|blue_)?ice|snow_block|powder_snow"),
    ("Farm & ocean", r"melon|pumpkin|carved_pumpkin|jack_o_lantern|hay_block|dried_kelp_block|"
                     r"(wet_)?sponge|honeycomb_block|slime_block|honey_block|resin_block|"
                     r"dead_\w+_coral_block|\w+_coral_block|\w+_mushroom_block|sculk"),
)  # fmt: skip
GLASS_AND_LIGHT = (
    "glass", "glass_pane", "iron_bars", "tinted_glass", "glowstone", "sea_lantern",
    "shroomlight", "redstone_lamp",
    "copper_bulb", "ochre_froglight", "verdant_froglight", "pearlescent_froglight",
    "jack_o_lantern",
)  # fmt: skip
#: Colored blocks by kind (base names after the color).
COLORED_KINDS = (
    ("Wool", "wool"), ("Carpet", "carpet"), ("Concrete", "concrete"),
    ("Concrete powder", "concrete_powder"),
    ("Terracotta", "terracotta"), ("Glazed terracotta", "glazed_terracotta"),
    ("Stained glass", "stained_glass"), ("Glass panes", "stained_glass_pane"),
    ("Wool stairs", "wool_stairs"),
    ("Wool slabs", "wool_slab"), ("Concrete stairs", "concrete_stairs"),
    ("Concrete slabs", "concrete_slab"),
)  # fmt: skip


def _name(block_id: str) -> str:
    return block_id.split(":", 1)[-1]


def _id(name: str) -> str:
    return f"minecraft:{name}"


def _leaves_of(name: str) -> str | None:
    """The wood of a leaves block (``oak_leaves``, ``red_poplar_leaves``), if any."""
    if not name.endswith("_leaves"):
        return None
    stem = name.removesuffix("_leaves")
    for color in COLORS:
        if stem.startswith(color + "_") and stem[len(color) + 1 :] in WOODS:
            return stem[len(color) + 1 :]
    return stem if stem in WOODS else None


def wood_of(block_id: str) -> str | None:
    """The wood a block is made of (``oak`` for oak stairs, stripped oak logs, …)."""
    name = _name(block_id).removeprefix("stripped_")
    for wood in sorted(WOODS, key=len, reverse=True):
        if name.startswith(wood + "_") and name[len(wood) + 1 :] in _WOOD_PARTS:
            return wood
    return None


def material(block_id: str) -> str:
    """The material a block's shape is made of: ``granite`` for granite stairs, ``stone_brick``
    for stone bricks and their slab, ``oak`` for anything oak, ``exposed_cut_copper`` for
    its stairs."""
    wood = wood_of(block_id)
    if wood is not None:
        return wood
    name = _name(block_id)
    for suffix in _SHAPES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    if name.endswith("bricks") or name.endswith("tiles"):
        name = name[:-1]
    return name.removesuffix("_block")


def color_of(block_id: str) -> tuple[str, str] | None:
    """(color, kind) of a dyed block (``red_wool`` → ("red", "wool"))."""
    name = _name(block_id)
    for color in sorted(COLORS, key=len, reverse=True):
        if name.startswith(color + "_"):
            return color, name[len(color) + 1 :]
    return None


def copper_stage(block_id: str) -> tuple[str, str] | None:
    """(stage prefix, base) of a copper block (``waxed_exposed_cut_copper`` → (…, "cut_copper"))."""
    name = _name(block_id)
    if "copper" not in name or name.endswith("_ore") or name.startswith("raw_"):
        return None
    for prefix in sorted(COPPER_STAGES, key=len, reverse=True):
        if prefix and name.startswith(prefix):
            base = name[len(prefix) :]
            return prefix, "copper_block" if base == "copper" else base
    return "", name


def _copper_name(prefix: str, base: str) -> str:
    """``exposed_`` + ``copper_block`` is ``exposed_copper`` (the plain block keeps
    ``_block`` only unweathered: ``copper_block``, ``waxed_copper_block``)."""
    if base == "copper_block" and prefix not in ("", "waxed_"):
        return f"{prefix}copper"
    return prefix + base


#: Shape order within a family: the block itself first.
_SHAPE_ORDER = {
    "": 0, "_stairs": 1, "_slab": 2, "_wall": 3, "_fence": 4, "_fence_gate": 5, "_door": 6,
    "_trapdoor": 7, "_button": 8, "_pressure_plate": 9,
}  # fmt: skip


def _shape_rank(block_id: str) -> tuple[int, str]:
    name = _name(block_id)
    for suffix, rank in _SHAPE_ORDER.items():
        if suffix and name.endswith(suffix):
            return rank, name
    return 0, name


#: Blocks the game never gives as items.
_TECHNICAL = frozenset({"air", "cave_air", "void_air", "moving_piston", "piston_head"})
#: Order of a wood's blocks in its folder.
_WOOD_ORDER = {
    "planks": 0, "stairs": 1, "slab": 2, "log": 3, "stem": 3, "block": 3, "wood": 5,
    "hyphae": 5, "leaves": 7, "door": 8, "trapdoor": 9, "fence": 10, "fence_gate": 11,
    "button": 12, "pressure_plate": 13, "sign": 14,
}  # fmt: skip


def wood_rank(block_id: str, wood: str) -> tuple[int, bool]:
    """Order of a wood's blocks: planks, stairs, slab, logs, wood, leaves, button, …"""
    name = _name(block_id)
    part = name.removeprefix("stripped_").removeprefix(wood + "_")
    key = "leaves" if part.endswith("leaves") else part
    return _WOOD_ORDER.get(key, 6), name.startswith("stripped_")


def _wood_key(wood: str, block_id: str) -> tuple[int, bool]:
    return wood_rank(block_id, wood)


class BlockIndex:
    """The registered blocks by material, color and copper stage."""

    def __init__(self, block_ids: Iterable[str], order: Iterable[str] = ()) -> None:
        known = set(block_ids)
        ranking: dict[str, int] = {}
        for index, block_id in enumerate(order):
            ranking.setdefault(block_id, index)  # the first tab that lists it
        self.ids = sorted(known, key=lambda b: (ranking.get(b, len(ranking)), b))
        self.known = known
        self.families: dict[str, list[str]] = {}
        for block_id in self.ids:
            self.families.setdefault(material(block_id), []).append(block_id)
        for members in self.families.values():
            wood = wood_of(members[0])
            if wood is None:
                members.sort(key=_shape_rank)
            else:
                members.sort(key=functools.partial(_wood_key, wood))

    def has(self, name: str) -> bool:
        return _id(name) in self.known

    def shape_variants(self, block_id: str) -> list[str]:
        """The block's family: the same material in other shapes (one entry: none)."""
        return self.families.get(material(block_id), [block_id])

    def color_variants(self, block_id: str) -> list[str]:
        """The same block in every color, or every copper stage (one entry: none)."""
        colored = color_of(block_id)
        if colored is not None:
            out = [_id(f"{c}_{colored[1]}") for c in COLORS if self.has(f"{c}_{colored[1]}")]
            return out if block_id in out else [block_id]
        stage = copper_stage(block_id)
        if stage is not None:
            out = [_id(_copper_name(p, stage[1])) for p in COPPER_STAGES]
            out = [b for b in out if b in self.known]
            return out if block_id in out else [block_id]
        return [block_id]

    # ------------------------------------------------------------------ folders
    def _family_entry(self, family: list[str], title: str) -> Folder | str:
        if len(family) == 1:
            return family[0]
        return paged(title, family)

    def _grouped(
        self, groups: tuple[tuple[str, str], ...], names: Callable[[str], str]
    ) -> list[Folder]:
        """Folders of families whose material matches each group's pattern (in the order
        the families first appear)."""
        out = []
        for title, pattern in groups:
            regex = re.compile(rf"^(?:{pattern})$")
            entries: list[Folder | str] = []
            for key, family in self.families.items():
                if wood_of(family[0]) is None and regex.match(key):
                    entries.append(self._family_entry(family, names(family[0])))
            if entries:
                out.append(paged(title, entries))
        return out

    def _matching(self, groups: tuple[tuple[str, str], ...]) -> list[Folder]:
        """Folders of single blocks whose name matches each group's pattern."""
        out = []
        for title, pattern in groups:
            regex = re.compile(rf"^(?:{pattern})$")
            found = [b for b in self.ids if regex.match(_name(b))]
            if found:
                out.append(paged(title, found))
        return out

    def tree(self, names: Callable[[str], str]) -> Folder:
        placed: set[str] = set()

        def ids(names_: Iterable[str]) -> list[str]:
            return [_id(n) for n in names_ if self.has(n)]

        redstone = [paged(title, ids(members)) for title, members in REDSTONE if ids(members)]
        woods = []
        for wood in WOODS:
            members = [b for b in self.ids if wood_of(b) == wood]
            leaves = [b for b in self.ids if _leaves_of(_name(b)) == wood]
            members += [b for b in leaves if b not in members]
            if members:
                members.sort(key=functools.partial(_wood_key, wood))
                woods.append(paged(names(members[0]).replace(" Planks", ""), members))
        stone = self._grouped(STONE_GROUPS, names)
        colored_kinds = []
        for title, kind in COLORED_KINDS:
            members = [_id(f"{c}_{kind}") for c in COLORS if self.has(f"{c}_{kind}")]
            if kind == "terracotta" and self.has("terracotta"):
                members.insert(0, _id("terracotta"))
            if members:
                colored_kinds.append(paged(title, members))
        by_color = []
        for color in COLORS:
            members = [
                _id(f"{color}_{kind}") for _, kind in COLORED_KINDS if self.has(f"{color}_{kind}")
            ]
            if members:
                by_color.append(paged(color.replace("_", " ").title(), members))
        copper = []
        bases = ("copper_block", "chiseled_copper", "copper_grate", "cut_copper",
                 "cut_copper_stairs", "cut_copper_slab", "copper_bulb", "copper_door",
                 "copper_trapdoor", "copper_bars")  # fmt: skip
        stage_names = ("Copper", "Exposed", "Weathered", "Oxidized")
        stages = [
            paged(
                title,
                [_id(_copper_name(prefix, b)) for b in bases if self.has(_copper_name(prefix, b))],
            )
            for title, prefix in zip(stage_names, COPPER_STAGES[:4], strict=True)
        ]
        waxed = [
            paged(
                title,
                [_id(_copper_name(prefix, b)) for b in bases if self.has(_copper_name(prefix, b))],
            )
            for title, prefix in zip(stage_names, COPPER_STAGES[4:], strict=True)
        ]
        copper = [s for s in stages if s.children] + [
            paged("Waxed", [s for s in waxed if s.children])
        ]
        natural = self._matching(NATURAL_GROUPS)
        glass = ids(GLASS_AND_LIGHT) + [
            _id(f"{c}_stained_glass") for c in COLORS if self.has(f"{c}_stained_glass")
        ]
        top: list[Folder | str] = [
            paged("Redstone", redstone),
            paged("Wood", woods),
            paged("Stone & minerals", stone),
            paged("Colored", [paged("By kind", colored_kinds), paged("By color", by_color)]),
            paged("Copper", copper),
            paged("Natural", natural),
            paged("Glass & light", glass),
        ]
        collect(Folder("", tuple(top)), placed)
        other = [
            b
            for b in self.ids
            if b not in placed and _name(b) not in _TECHNICAL and "_wall_" not in _name(b)
        ]  # wall signs and torches are how signs and torches are placed, not blocks to pick
        if other:
            top.append(paged("Other", other))
        return paged("Inventory", top)


def collect(folder: Folder, into: set[str]) -> None:
    for child in folder.children:
        if isinstance(child, Folder):
            collect(child, into)
        else:
            into.add(child)


def paged(title: str, entries: list[Folder | str] | list[str] | list[Folder]) -> Folder:
    """A folder; past nine entries, the ninth slot holds "More…" with the rest."""
    items: list[Folder | str] = list(entries)
    if len(items) <= PAGE:
        return Folder(title, tuple(items))
    return Folder(title, (*items[: PAGE - 1], paged("More…", items[PAGE - 1 :])))
