"""Trackmania-style inventory navigation (no display needed for the model)."""

from __future__ import annotations

from redsim.ui.inventory import INVENTORY, Folder, InventoryNav
from redsim.world import blocks


def test_numbers_open_folders_and_pick_blocks() -> None:
    nav = InventoryNav()
    assert nav.press(1) is None and nav.breadcrumb() == ["Redstone"]
    assert nav.press(1) is None and nav.breadcrumb() == ["Redstone", "Wiring"]
    assert nav.press(3) == "minecraft:repeater"  # picking stays in the folder
    assert nav.breadcrumb() == ["Redstone", "Wiring"]
    assert nav.press(42) is None
    assert nav.up() and nav.up() and nav.breadcrumb() == [] and not nav.up()


def test_reveal_opens_the_folder_of_a_picked_block() -> None:
    nav = InventoryNav()
    assert nav.reveal("minecraft:lectern")
    assert nav.breadcrumb() == ["Redstone", "Read by comparators"]
    assert not nav.reveal("minecraft:air")


def test_every_folder_fits_the_number_keys_and_every_block_exists() -> None:
    def walk(folder: Folder) -> None:
        assert 1 <= len(folder.children) <= 9, folder.title
        for child in folder.children:
            if isinstance(child, Folder):
                walk(child)
            else:
                blocks.get(child)

    walk(INVENTORY)


def test_blocks_sit_in_several_folders_and_have_variants() -> None:
    from redsim.ui.inventory import BLOCK_INDEX, all_blocks

    def holds(folder: Folder, block_id: str) -> list[str]:
        out = []
        for child in folder.children:
            if isinstance(child, Folder):
                out += [f"{child.title}/{p}" for p in holds(child, block_id)] + (
                    [child.title] if block_id in child.children else []
                )
        return out

    chest = holds(INVENTORY, "minecraft:chest")
    assert any("Items" in p for p in chest) and any("Read by comparators" in p for p in chest)
    assert any("Stone" in p for p in holds(INVENTORY, "minecraft:obsidian"))
    ids = [b for b, _ in all_blocks()]
    assert len(ids) == len(set(ids))  # the search lists each block once
    assert BLOCK_INDEX.shape_variants("minecraft:granite_slab") == [
        "minecraft:granite", "minecraft:granite_stairs", "minecraft:granite_slab",
    ]  # fmt: skip
    assert BLOCK_INDEX.shape_variants("minecraft:oak_log")[0] == "minecraft:oak_planks"
    colors = BLOCK_INDEX.color_variants("minecraft:red_concrete")
    assert len(colors) == 16 and colors[0] == "minecraft:white_concrete"
    copper = BLOCK_INDEX.color_variants("minecraft:copper_block")
    assert copper[:2] == ["minecraft:copper_block", "minecraft:exposed_copper"]
    assert "minecraft:waxed_copper_block" in copper


def test_c_and_x_step_through_shapes_and_colors() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets

    from redsim.ui.inventory import InventoryBar

    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    bar = InventoryBar()
    bar.select_block(blocks.get("minecraft:white_wool"))
    assert bar.cycle("color", 1) == "minecraft:light_gray_wool"
    assert bar.cycle("shape", 1) == "minecraft:light_gray_wool_stairs"
    assert bar.cycle("color", -1) == "minecraft:white_wool_stairs"
    rows = bar.canvas.variant_rows()
    assert [key for key, _ in rows] == ["C", "X"]  # shown above the hotbar rows
    bar.select_block(blocks.get("minecraft:lever"))
    assert bar.cycle("shape", 1) is None and bar.canvas.variant_rows() == []
