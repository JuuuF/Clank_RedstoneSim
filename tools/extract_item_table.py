"""Generate ``src/redsim/world/items_data.py``: the max stack size of every item of the game
that does not stack to 64, which container signals depend on
(``AbstractContainerMenu.getRedstoneSignalFromContainer``: ``count / maxStackSize``).

The sizes come from the game itself: the 26.3 server jar's data generator
(``net.minecraft.data.Main --reports``) writes every item's default components to
``reports/minecraft/components/item/<id>.json``, ``minecraft:max_stack_size`` among them
(set by ``Item.Properties.stacksTo``, ``durability`` and everything built on them). The
generator runs in a temporary folder (the bundler unpacks its libraries there) and starts
no server.

Usage: ``python -m tools.extract_item_table [REPORTS_DIR]`` (rewrites the module; with a
folder of already generated reports the jar is not run).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.gameserver.server import SERVER_JAR, find_java

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src/redsim/world/items_data.py"
DEFAULT_STACK = 64

HEADER = '''"""Max stack sizes of the game's items that do not stack to {default}
(generated from the 26.3 data generator's item component report by
``tools/extract_item_table.py``; do not edit by hand). Every other item stacks to {default}."""

ITEM_MAX_STACK: dict[str, int] = {{
'''


def read_sizes(reports: Path) -> dict[str, int]:
    folder = reports / "minecraft" / "components" / "item"
    sizes = {}
    for path in sorted(folder.glob("*.json")):
        components = json.loads(path.read_text())["components"]
        sizes[f"minecraft:{path.stem}"] = int(components["minecraft:max_stack_size"])
    if not sizes:
        raise SystemExit(f"no item reports in {folder}")
    return sizes


def generate_reports(work: Path) -> Path:
    out = work / "generated"
    command = [find_java(), "-DbundlerMainClass=net.minecraft.data.Main", "-jar",
               str(SERVER_JAR), "--reports", "--output", str(out)]  # fmt: skip
    subprocess.run(command, cwd=work, check=True, stdout=subprocess.DEVNULL)
    return out / "reports"


def write_module(sizes: dict[str, int]) -> None:
    lines = [HEADER.format(default=DEFAULT_STACK)]
    lines += [f'    "{item}": {size},\n' for item, size in sizes.items() if size != DEFAULT_STACK]
    lines.append("}\n")
    OUT.write_text("".join(lines))


def main(argv: list[str]) -> int:
    if argv:
        sizes = read_sizes(Path(argv[0]))
    else:
        with tempfile.TemporaryDirectory(prefix="redsim-datagen-") as work:
            sizes = read_sizes(generate_reports(Path(work)))
    write_module(sizes)
    other = sum(1 for size in sizes.values() if size != DEFAULT_STACK)
    print(f"{len(sizes)} items, {other} not stacking to {DEFAULT_STACK}: wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
