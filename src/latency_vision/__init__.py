# SPDX-License-Identifier: Apache-2.0
"""
latency_vision: canonical import alias for the Vision SDK.
Re-exports the public API from the internal 'vision' package.
"""
from vision import *  # noqa: F401,F403 - re-export by design
from vision import __version__ as __version__  # keep version in sync

__all__ = [*globals().keys()]  # best-effort export surface
