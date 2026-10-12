"""Generate ``src/redsim/world/instruments.py``: the note-block instrument of every block
(``BlockBehaviour.Properties.instrument``) from the decompiled ``Blocks.java``.

Usage: ``python -m tools.extract_instruments`` (rewrites the module). Handled: explicit
``.instrument(...)``, copies (``ofFullCopy``/``ofLegacyCopy``, ``registerSlab``/
``registerStair``-style helpers taking a base block), property helper methods,
16-color collections, and mob heads (their instrument comes from the skull type).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "data/minecraft_src/client-src/net/minecraft/world/level/block/Blocks.java"
OUT = ROOT / "src/redsim/world/instruments.py"

COLORS = (
    "white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
    "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black",
)  # fmt: skip
#: ``Blocks.COPPER_BLOCK`` (a ``WeatheringCopperCollection``): instrument per stage.
COPPER = {
    "copper_block": "trumpet",
    "exposed_copper": "trumpet_exposed",
    "weathered_copper": "trumpet_weathered",
    "oxidized_copper": "trumpet_oxidized",
}
#: ``SkullBlock.Types`` → instrument (``SkullBlock.Type.getInstrument``).
HEADS = {
    "skeleton_skull": "skeleton",
    "wither_skeleton_skull": "wither_skeleton",
    "zombie_head": "zombie",
    "creeper_head": "creeper",
    "dragon_head": "dragon",
    "piglin_head": "piglin",
    "player_head": "custom_head",
}


def _statements(src: str) -> list[tuple[str, str]]:
    """(constant name, body) of every ``public static final … NAME = …;`` declaration."""
    out = []
    for match in re.finditer(r"public static final (?:Block|ColorCollection<Block>) (\w+) = ", src):
        depth, i = 0, match.end()
        while i < len(src):
            c = src[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == ";" and depth == 0:
                break
            i += 1
        out.append((match.group(1), src[match.end() : i]))
    return out


def _helpers(src: str) -> dict[str, str]:
    """Bodies of ``private static BlockBehaviour.Properties helper(...)`` methods."""
    out = {}
    for match in re.finditer(r"private static BlockBehaviour\.Properties (\w+)\([^)]*\) \{", src):
        depth, i = 1, match.end()
        while depth and i < len(src):
            depth += {"{": 1, "}": -1}.get(src[i], 0)
            i += 1
        out[match.group(1)] = src[match.end() : i]
    return out


def extract() -> dict[str, str]:
    src = BLOCKS.read_text(encoding="utf-8")
    helpers = _helpers(src)
    direct: dict[str, str] = {}
    copies: dict[str, str] = {}
    collections: dict[str, str] = {}
    for name, body in _statements(src):
        found = re.search(r"\.instrument\(NoteBlockInstrument\.(\w+)\)", body)
        if found is None:
            for helper, helper_body in helpers.items():
                if re.search(rf"\b{helper}\(", body):
                    found = re.search(r"\.instrument\(NoteBlockInstrument\.(\w+)\)", helper_body)
                    if found:
                        break
        is_collection = "ColorCollection" in body[:80] or "registerBlocks" in body
        target = collections if is_collection else direct
        if found:
            target[name] = found.group(1).lower()
            continue
        copy = re.search(r"of(?:Full|Legacy)Copy\((\w+)\)", body) or re.search(
            r"register\w*\(\s*BlockItemIds\.\w+,\s*(\w+)\s*[,)]", body
        )
        if copy and copy.group(1).isupper():
            copies[name] = copy.group(1)
    for name, base in copies.items():  # copies of copies resolve in a few rounds
        seen = 0
        while base in copies and seen < 8:
            base, seen = copies[base], seen + 1
        if base in direct:
            direct.setdefault(name, direct[base])
    result = {f"minecraft:{name.lower()}": value for name, value in direct.items()}
    for name, value in collections.items():
        for color in COLORS:
            result[f"minecraft:{color}_{name.lower()}"] = value
    # ``COPPER_BLOCK`` is the one weathering collection with an instrument per stage.
    for stage, value in COPPER.items():
        result[f"minecraft:{stage}"] = value
        result[f"minecraft:waxed_{stage}"] = value
    for head, value in HEADS.items():
        result[f"minecraft:{head}"] = value
        wall = head.replace("_skull", "_wall_skull").replace("_head", "_wall_head")
        result[f"minecraft:{wall}"] = value
    return {k: v for k, v in sorted(result.items()) if v != "harp"}


def main() -> None:
    table = extract()
    lines = [
        '"""Note-block instrument of each block (``BlockBehaviour.Properties.instrument``),',
        "generated from the decompiled ``Blocks.java`` by ``tools/extract_instruments.py``;",
        'blocks not listed use ``harp``. Do not edit by hand."""',
        "",
        "INSTRUMENTS: dict[str, str] = {",
        *(f'    "{k}": "{v}",' for k, v in table.items()),
        "}",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(table)} blocks written to {OUT}")


if __name__ == "__main__":
    main()
