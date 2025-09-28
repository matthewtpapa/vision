from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class CandidateOracle(Protocol):
    """Protocol describing unknown-candidate orchestration."""

    def enqueue_unknown(self, embedding: Sequence[float], context: Mapping[str, Any]) -> None:
        """Add an unknown embedding and associated *context* to the queue."""

        raise NotImplementedError

    def next(self) -> tuple[list[str], Mapping[str, Any]] | None:
        """Return the next candidate labels and context, or ``None`` if empty."""

        raise NotImplementedError
