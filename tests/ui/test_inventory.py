"""Trackmania-style inventory navigation (no display needed for the model)."""

from __future__ import annotations

from redsim.ui.inventory import INVENTORY, Folder, InventoryNav
from redsim.world import blocks


def test_numbers_open_folders_and_pick_blocks() -> None:
    nav = InventoryNav()
    assert nav.press(1) is None and nav.breadcrumb() == ["Redstone"]
    assert nav.press(3) == "minecraft:repeater"  # picking stays in the folder
    assert nav.breadcrumb() == ["Redstone"]
    assert nav.press(42) is None
    assert nav.up() and nav.breadcrumb() == [] and not nav.up()


def test_reveal_opens_the_folder_of_a_picked_block() -> None:
    nav = InventoryNav()
    assert nav.reveal("minecraft:lectern") and nav.breadcrumb() == ["Signal sources"]
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
