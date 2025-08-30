"""Factory for building the best available matcher backend."""

from __future__ import annotations

import logging

from .matcher_protocol import MatcherProtocol

logger = logging.getLogger(__name__)


def build_matcher(dim: int) -> MatcherProtocol:
    """Return a matcher backend, preferring FAISS when available."""
    try:
        from .faiss_backend import FaissMatcher

        matcher = FaissMatcher(dim)
        logger.info("[matcher] backend: %s", "FAISS")
        return matcher
    except Exception:  # pragma: no cover - exercised via tests
        from .py_fallback import NumpyMatcher  # lazy to avoid numpy at import-time

        logger.info("[matcher] backend: %s", "NumPy")
        return NumpyMatcher()
