from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class EvidenceLedger(Protocol):
    """Protocol describing append-only evidence loggers."""

    def append(self, record: Mapping[str, Any]) -> None:
        """Append *record* to the evidence ledger."""

        raise NotImplementedError
