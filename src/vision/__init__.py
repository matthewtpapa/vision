"""Compatibility layer that re-exports ``latency_vision`` while allowing local modules."""

from __future__ import annotations

import os as _os
import sys as _sys
from importlib import import_module as _import_module
from typing import Any

_latency = _import_module("latency_vision")

if _os.getenv("VISION_SILENCE_DEPRECATION") != "1":
    print(
        "[deprecation] 'vision' is an alias of 'latency_vision' and only re-exports it; "
        "the compatibility layer will be removed in a future release. Import from "
        "'latency_vision' directly.",
        file=_sys.stderr,
    )

# Re-export public symbols so ``from vision import foo`` continues to work.
if hasattr(_latency, "__all__"):
    __all__ = list(getattr(_latency, "__all__"))
    globals().update({name: getattr(_latency, name) for name in __all__})
else:  # pragma: no cover - defensive fallback for packages without __all__
    __all__ = []


def __getattr__(name: str) -> Any:  # pragma: no cover - simple delegation
    """Delegate attribute lookups to :mod:`latency_vision`."""

    return getattr(_latency, name)


def __dir__() -> list[str]:  # pragma: no cover - cosmetic
    base = set(globals().keys()) | set(dir(_latency))
    return sorted(base)
