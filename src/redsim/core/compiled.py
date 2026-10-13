"""Support for the optional compiled build (mypyc, doc/implementation-notes.md).

The simulator runs as plain Python; ``python -m tools.build_compiled`` can compile the hot
core modules with mypyc for speed. Compiled classes may only be subclassed by plain
Python classes when they say so (``mypyc_attr``); without mypy installed the decorator is
a no-op.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

try:
    from mypy_extensions import mypyc_attr
except ImportError:  # pragma: no cover - mypy is a development dependency

    def mypyc_attr(*attrs: str, **kwattrs: Any) -> Callable[[T], T]:  # type: ignore[misc]
        def identity(cls: T) -> T:
            return cls

        return identity


__all__ = ["mypyc_attr"]
