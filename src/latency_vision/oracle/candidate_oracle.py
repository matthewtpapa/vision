from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class CandidateOracle(Protocol):
    def enqueue_unknown(self, embedding: Sequence[float], context: Mapping[str, Any]) -> None: ...
    def next(self) -> tuple[list[str], Mapping[str, Any]] | None: ...
