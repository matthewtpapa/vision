from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Protocol


class VerifyResult(Protocol):
    @property
    def accepted(self) -> bool: ...

    @property
    def evidence_path(self) -> str: ...


class VerifyWorker:
    """Minimal stub VerifyWorker consuming a gallery manifest."""

    def __init__(self, manifest_path: str) -> None:
        self.manifest_path = manifest_path
        self._rows: list[dict[str, str]] | None = None

    def load_manifest(self) -> tuple[int, dict[str, str] | None]:
        if self._rows is None:
            with open(self.manifest_path, encoding="utf-8") as fh:
                self._rows = [json.loads(line) for line in fh if line.strip()]
        count = len(self._rows)
        sample = self._rows[0] if self._rows else None
        return count, sample

    def verify(
        self, embedding: Sequence[float], candidate_label: str
    ) -> VerifyResult:  # pragma: no cover - stub
        raise NotImplementedError("verify() not implemented yet")
