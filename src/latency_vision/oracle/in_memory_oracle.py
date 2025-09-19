"""In-memory CandidateOracle implementation."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class CandidateRecord:
    """Captured oracle candidate payload."""

    embedding: list[float]
    context: dict[str, Any]


class InMemoryCandidateOracle:
    """Thread-safe, bounded candidate oracle queue."""

    def __init__(self, maxlen: int = 2048) -> None:
        self._maxlen = max(0, int(maxlen))
        self._queue: deque[CandidateRecord] = deque()
        self._shed = 0
        self._lock = Lock()

    def enqueue_unknown(self, embedding: Sequence[float], context: Mapping[str, Any]) -> None:
        record = CandidateRecord(list(embedding), dict(context))
        if self._maxlen == 0:
            with self._lock:
                self._shed += 1
            return
        with self._lock:
            if len(self._queue) >= self._maxlen:
                self._queue.popleft()
                self._shed += 1
            self._queue.append(record)

    def next(self) -> tuple[list[str], Mapping[str, Any]] | None:
        with self._lock:
            if not self._queue:
                return None
            record = self._queue.popleft()
        payload: dict[str, Any] = dict(record.context)
        payload.setdefault("embedding", list(record.embedding))
        return [], payload

    def qsize(self) -> int:
        with self._lock:
            return len(self._queue)

    def shed_total(self) -> int:
        with self._lock:
            return self._shed


__all__ = ["CandidateRecord", "InMemoryCandidateOracle"]
