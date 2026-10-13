"""The optional compiled build (mypyc): used only when built from the current sources."""

from __future__ import annotations

import redsim


def test_a_compiled_build_is_used_only_for_the_current_sources() -> None:
    fingerprint = redsim.source_fingerprint()
    assert len(fingerprint) == 16
    if redsim.COMPILED is not None:  # running on a compiled build: it must match
        assert redsim.COMPILED.endswith(fingerprint)
    # File lookups start from the sources, also when modules come from a build.
    assert (redsim.REPO_ROOT / "src" / "redsim" / "__init__.py").is_file()
