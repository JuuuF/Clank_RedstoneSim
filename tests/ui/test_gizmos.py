"""Selection gizmos: hot spots and picking (no display needed)."""

from __future__ import annotations

import numpy as np

from redsim.editor.clipboard import Region
from redsim.ui.gizmos import pick_hotspot, selection_gizmos
from redsim.ui.selection_tools import Handle

BOX = Region((0, 0, 0), (3, 1, 2))


def test_every_face_has_a_resize_arrow_plus_rotate_and_flip_spots() -> None:
    triangles, spots = selection_gizmos(BOX, 0.2, 0.0, stacking=False, hover=None)
    kinds = [spot.kind for spot in spots]
    assert kinds.count("resize") == 6 and kinds.count("rotate") == 2 and kinds.count("flip") == 4
    assert triangles.shape[1] == 7 and len(triangles) % 3 == 0
    stacked, _ = selection_gizmos(BOX, 0.2, 0.0, stacking=True, hover=None)
    assert not np.array_equal(stacked, triangles)  # Shift changes the arrows' look


def test_picking_the_top_arrow_and_the_rotate_heads() -> None:
    _, spots = selection_gizmos(BOX, 0.2, 0.0, stacking=False, hover=None)
    top = next(s for s in spots if s.kind == "resize" and s.data == Handle(1, True))
    origin = np.array(top.center) + [0.0, 0.0, -10.0]
    picked = pick_hotspot(origin, np.array([0.0, 0.0, 1.0]), spots)
    assert picked is not None and picked.data == Handle(1, True)
    # Camera north of the box (yaw 0): the rotate heads sit on the north side of the ring.
    heads = [s for s in spots if s.kind == "rotate"]
    assert {s.data for s in heads} == {1, -1}
    assert all(s.center[2] < 1.5 for s in heads)
    assert pick_hotspot(np.array([50.0, 50.0, 50.0]), np.array([1.0, 0.0, 0.0]), spots) is None
