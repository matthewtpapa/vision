"""Compatibility alias for the latency_vision package."""

import os as _os
import sys as _sys
from importlib import import_module as _import_module

if _os.getenv("VISION_SILENCE_DEPRECATION") != "1":
    print(
        "[deprecation] 'vision' is an alias of 'latency_vision' and will be removed in M1.2. "
        "Use 'latency_vision'.",
        file=_sys.stderr,
    )

_module = _import_module("latency_vision")
_sys.modules[__name__] = _module
